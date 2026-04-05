import os
import sys
import time
import json
import hashlib
import glob
import re
from dotenv import load_dotenv
from langchain_community.document_loaders import UnstructuredFileLoader, WebBaseLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec
from llama_parse import LlamaParse

load_dotenv()

# 환경 변수 로드
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_CLOUD_API_KEY")

if not all([GOOGLE_API_KEY, PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX_NAME, LLAMA_CLOUD_API_KEY]):
    raise ValueError("모든 환경 변수(GOOGLE, PINECONE, LLAMA_CLOUD_API_KEY)를 .env 파일에 설정해야 합니다.")

DATA_DIR = "../data"
URLS_FILE = os.path.join(DATA_DIR, "URLs.txt")
PROCESSED_FILES_DB = "processed_files.json"
EXTRACTED_MD_DIR = "extracted_md"

os.makedirs(EXTRACTED_MD_DIR, exist_ok=True)

def get_file_hash(filepath):
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        hasher.update(f.read())
    return hasher.hexdigest()

def save_as_markdown(source, documents):
    """추출된 내용을 마크다운 파일로 로컬에 저장합니다."""
    safe_name = re.sub(r'[\\/*?:"<>|]', "_", os.path.basename(source))
    if source.startswith("http"):
        safe_name = re.sub(r'[\\/*?:"<>|]', "_", source.replace("https://", "").replace("http://", ""))
    
    md_path = os.path.join(EXTRACTED_MD_DIR, f"{safe_name}.md")
    combined_content = "\n\n".join([doc.page_content for doc in documents])
    
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(combined_content)
    print(f"  -> 마크다운 저장 완료: {md_path}")

def process_pdf_with_llamaparse(filepath):
    """LlamaParse API를 사용하여 PDF를 고품질 마크다운으로 추출합니다."""
    print(f"  [LlamaParse 파싱] '{os.path.basename(filepath)}' 분석 중...")
    
    parser = LlamaParse(
        api_key=LLAMA_CLOUD_API_KEY,
        result_type="markdown",
        verbose=True,
        language="ko", 
        num_workers=4
    )
    
    try:
        parsed_docs = parser.load_data(filepath)
        langchain_docs = []
        for doc in parsed_docs:
            metadata = {"source": filepath, "type": "llamaparse_pdf"}
            langchain_docs.append(Document(page_content=doc.text, metadata=metadata))
            
        print(f"  -> LlamaParse 추출 성공!")
        return langchain_docs
    except Exception as e:
        print(f"  -> LlamaParse 오류 발생: {e}")
        return []

def load_single_document(source, source_type):
    """소스 타입에 따라 단일 문서를 로드합니다."""
    try:
        if source_type == 'file':
            if source.endswith(".pdf"):
                return process_pdf_with_llamaparse(source)
            elif source.endswith(".md"):
                loader = TextLoader(source, encoding='utf-8')
                return loader.load()
            else: # DOCX, HTML 등
                loader = UnstructuredFileLoader(source)
                return loader.load()
        elif source_type == 'url':
            import requests
            print(f"  [Jina Reader] '{source}' 크롤링 중 (자바스크립트 렌더링 지원)...")
            jina_url = f"https://r.jina.ai/{source}"
            response = requests.get(jina_url, headers={"X-Return-Format": "markdown"})
            if response.status_code == 200:
                extracted_text = response.text
                metadata = {"source": source, "type": "jina_reader_url"}
                return [Document(page_content=extracted_text, metadata=metadata)]
            else:
                print(f"  -> URL 로드 실패 (HTTP {response.status_code})")
                return []
        return []
    except Exception as e:
        print(f"  -> {source} 로드 중 오류 발생: {e}")
        return []

def clean_documents(documents):
    """PDF가 아닌 문서의 텍스트를 LLM으로 정제합니다."""
    if not documents: return []
    
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GOOGLE_API_KEY, temperature=0)
    cleaned_docs = []
    
    template = """다음은 추출된 텍스트입니다. 
[매우 중요한 지침]: 원본의 지식, 사실, 정보, 수치 등을 절대 왜곡하거나 임의로 창작하지 마세요.
줄바꿈 오류, 불필요한 공백 등 구조적인 오류만 수정하고 마크다운 형식으로 깔끔하게 정리만 해주세요.

원시 텍스트: {text}
재구성된 텍스트:"""
    prompt = PromptTemplate.from_template(template)
    chain = prompt | llm
    
    for i, doc in enumerate(documents):
        if len(doc.page_content.strip()) < 50:
            cleaned_docs.append(doc)
            continue
        try:
            response = chain.invoke({"text": doc.page_content})
            doc.page_content = response.content
            cleaned_docs.append(doc)
            time.sleep(4)
        except Exception as e:
            print(f"  -> 정제 중 오류 발생: {e}")
            cleaned_docs.append(doc)
            time.sleep(4)
            
    return cleaned_docs

def split_documents(documents):
    if not documents: return []
    print("  -> 청크 분할 중...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)
    return chunks

def generate_embeddings_and_upsert(chunks):
    if not chunks: return
    print(f"  -> 임베딩 생성 및 Pinecone 저장 중 ({len(chunks)} chunks)...")
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", google_api_key=GOOGLE_API_KEY)
    PineconeVectorStore.from_documents(chunks, embeddings, index_name=PINECONE_INDEX_NAME)

if __name__ == "__main__":
    # 1. Pinecone 인덱스 선 생성/확인
    pc = Pinecone(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)
    if PINECONE_INDEX_NAME not in pc.list_indexes().names():
        print(f"Pinecone 인덱스 '{PINECONE_INDEX_NAME}' 생성 중...")
        pc.create_index(
            name=PINECONE_INDEX_NAME, dimension=3072, metric="cosine",
            spec=ServerlessSpec(cloud='aws', region=PINECONE_ENVIRONMENT)
        )
        while not pc.describe_index(PINECONE_INDEX_NAME).status['ready']:
            time.sleep(1)
        print("인덱스 준비 완료.")
    else:
        print(f"Pinecone 인덱스 '{PINECONE_INDEX_NAME}' 확인 완료.")

    # 2. URLs.txt 읽기
    target_urls = []
    if os.path.exists(URLS_FILE):
        with open(URLS_FILE, "r") as f:
            target_urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    # 3. 소스 리스트업
    all_sources = [{"source": f, "type": "file"} for f in glob.glob(os.path.join(DATA_DIR, "**/*.*"), recursive=True) if f.endswith(('.pdf', '.docx', '.html', '.md')) and not os.path.basename(f) == "URLs.txt"]
    all_sources.extend([{"source": url, "type": "url"} for url in target_urls])

    if not all_sources:
        print("처리할 데이터가 없습니다.")
        sys.exit(0)

    # 4. 상태 로드
    try:
        with open(PROCESSED_FILES_DB, "r") as f:
            processed_state = json.load(f)
    except:
        processed_state = {}

    updated_state = processed_state.copy()
    total_new = 0

    print(f"\n총 {len(all_sources)}개의 항목을 순차적으로 확인합니다.")

    for i, item in enumerate(all_sources):
        source, source_type = item['source'], item['type']
        current_hash = get_file_hash(source) if source_type == 'file' else hashlib.md5(source.encode()).hexdigest()
        
        if processed_state.get(source) == current_hash:
            continue

        print(f"\n[{i+1}/{len(all_sources)}] 처리 중: {source}")
        total_new += 1
        
        # 문서 로드 (PDF는 LlamaParse 사용)
        docs = load_single_document(source, source_type)
        
        if not docs:
            print("  -> 내용 추출 실패. 건너뜁니다.")
            continue
        
        # PDF가 아닌 경우만 Gemini 정제 수행
        if not source.endswith(".pdf"):
             docs = clean_documents(docs)
        
        save_as_markdown(source, docs)
        chunks = split_documents(docs)
        
        if chunks:
            generate_embeddings_and_upsert(chunks)
        
        updated_state[source] = current_hash
        
        # 즉시 상태 저장 (진행 상황 보존)
        with open(PROCESSED_FILES_DB, "w") as f:
            json.dump(updated_state, f, indent=4)

    print(f"\n✨ 작업 완료! 총 {total_new}개의 신규/수정 항목이 처리되었습니다.")
