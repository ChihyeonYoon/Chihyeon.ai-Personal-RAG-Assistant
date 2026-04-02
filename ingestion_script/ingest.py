import os
import time
import json
import hashlib
import glob
import base64
import fitz  # PyMuPDF
from dotenv import load_dotenv
from langchain_community.document_loaders import Docx2txtLoader, WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langchain_core.documents import Document
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

# 환경 변수 로드
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

if not all([GOOGLE_API_KEY, PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX_NAME]):
    raise ValueError("모든 환경 변수(GOOGLE_API_KEY, PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX_NAME)를 .env 파일에 설정해야 합니다.")

DATA_DIR = "../data"
URLS_FILE = os.path.join(DATA_DIR, "URLs.txt")
PROCESSED_FILES_DB = "processed_files.json"

def get_file_hash(filepath):
    """파일의 MD5 해시값을 계산합니다."""
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        hasher.update(f.read())
    return hasher.hexdigest()

def process_pdf_with_vlm(filepath):
    """
    PyMuPDF를 사용하여 PDF의 각 페이지를 이미지로 변환한 후,
    Gemini 2.5 Flash(Vision 기능)를 사용하여 텍스트와 그림, 표를 모두 마크다운으로 완벽하게 추출합니다.
    """
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GOOGLE_API_KEY, temperature=0)
    docs = []
    
    print(f"  [VLM 파싱] '{os.path.basename(filepath)}' 파일을 시각적으로 분석 중...")
    doc = fitz.open(filepath)
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        # 해상도를 높여서 깨끗한 이미지로 변환 (zoom=2)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_data = pix.tobytes("jpeg")
        b64_img = base64.b64encode(img_data).decode("utf-8")
        
        prompt = """당신은 최고 수준의 PDF OCR 및 문서 분석가입니다.
주어진 문서 페이지의 이미지를 보고, 모든 텍스트, 표, 그리고 그림의 내용을 완벽한 마크다운 형식으로 추출하세요.
1. 텍스트: 문맥과 단락을 유지하며 오타 없이 추출하세요.
2. 표(Table): 마크다운 표 형식(|---|)으로 정확하게 복원하세요.
3. 그림/차트: 이미지에 그림이나 차트가 있다면, [그림 설명: ...] 형태로 그 그림이 어떤 의미인지, 수치나 트렌드가 어떤지 상세하게 텍스트로 풀어서 묘사하세요.
절대 임의로 내용을 지어내거나 생략하지 마세요. 오직 페이지에 있는 내용만 정확하게 추출하세요."""

        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}},
            ]
        )
        
        print(f"    - {page_num + 1}/{len(doc)} 페이지 분석 중 (표, 그림, 수식 포함)...")
        try:
            response = llm.invoke([message])
            extracted_text = response.content
            
            metadata = {"source": filepath, "page": page_num + 1, "type": "vlm_pdf"}
            docs.append(Document(page_content=extracted_text, metadata=metadata))
            
            # API 제한을 피하기 위한 대기
            time.sleep(4)
        except Exception as e:
            print(f"    -> {page_num + 1} 페이지 처리 중 오류 발생: {e}")
            time.sleep(4)
            
    doc.close()
    return docs

def load_and_process_documents(urls=None):
    """
    파일(PDF, DOCX)과 URL을 로드합니다.
    PDF의 경우 VLM(Vision) 처리를 통해 완벽한 마크다운으로 실시간 변환하고,
    DOCX와 URL은 일반 텍스트로 로드한 후 정제(Clean-up) 단계를 거치도록 분류합니다.
    """
    all_final_docs = [] # 바로 임베딩할 준비가 된 완성된 문서들
    docs_to_clean = []  # 정제(Cleanup)가 필요한 텍스트 전용 문서들 (DOCX, URL)
    current_state = {}

    if os.path.exists(PROCESSED_FILES_DB):
        with open(PROCESSED_FILES_DB, "r") as f:
            processed_state = json.load(f)
    else:
        processed_state = {}

    # 1. 로컬 파일 처리 (PDF, DOCX)
    print(f"\n{DATA_DIR} 디렉토리에서 파일을 확인 중...")
    pdf_files = glob.glob(os.path.join(DATA_DIR, "**/*.pdf"), recursive=True)
    docx_files = glob.glob(os.path.join(DATA_DIR, "**/*.docx"), recursive=True)
    
    # PDF 처리 (VLM 기반 - 완벽 추출)
    for filepath in pdf_files:
        file_hash = get_file_hash(filepath)
        current_state[filepath] = file_hash
        if filepath in processed_state and processed_state[filepath] == file_hash:
            continue
        
        print(f"\n새로운 PDF 발견: {os.path.basename(filepath)}")
        vlm_docs = process_pdf_with_vlm(filepath)
        all_final_docs.extend(vlm_docs)
        
    # DOCX 처리 (텍스트 추출 후 정제 대기열로)
    for filepath in docx_files:
        file_hash = get_file_hash(filepath)
        current_state[filepath] = file_hash
        if filepath in processed_state and processed_state[filepath] == file_hash:
            continue
            
        print(f"새로운 DOCX 발견: {os.path.basename(filepath)}")
        loader = Docx2txtLoader(filepath)
        docs_to_clean.extend(loader.load())

    # 2. URL 웹페이지 로드 (텍스트 추출 후 정제 대기열로)
    if urls:
        print(f"\n{len(urls)}개의 URL에서 웹 페이지를 확인 중...")
        for url in urls:
            # URL은 편의상 URL 문자열 자체의 해시를 기록 (또는 매번 업데이트)
            url_hash = hashlib.md5(url.encode()).hexdigest()
            current_state[url] = url_hash
            if url in processed_state and processed_state[url] == url_hash:
                continue
                
            print(f"새로운 URL 로딩: {url}")
            try:
                loader = WebBaseLoader([url])
                docs_to_clean.extend(loader.load())
            except Exception as e:
                print(f"  -> URL 로딩 오류: {e}")

    # 3. 정제 대기열(DOCX, URL)에 있는 문서들을 LLM으로 정제
    if docs_to_clean:
        print(f"\n총 {len(docs_to_clean)}개의 텍스트 문서(Word, 웹)를 LLM으로 정제합니다...")
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GOOGLE_API_KEY, temperature=0)
        
        template = """다음은 추출된 원시 텍스트입니다. 
[매우 중요한 지침]: 원본의 지식, 사실, 정보, 수치 등을 절대 왜곡하거나 임의로 창작/수정하지 마세요!
줄바꿈 오류, 불필요한 공백 등 구조적인 오류만 수정하고 마크다운 형식으로 깔끔하게 정리만 해주세요.

원시 텍스트:
{text}

재구성된 텍스트:"""
        prompt = PromptTemplate.from_template(template)
        chain = prompt | llm
        
        for i, doc in enumerate(docs_to_clean):
            source = doc.metadata.get('source', '알 수 없음')
            print(f"[{i+1}/{len(docs_to_clean)}] 텍스트 정제 중: {source}")
            if len(doc.page_content.strip()) < 50:
                all_final_docs.append(doc)
                continue
            try:
                response = chain.invoke({"text": doc.page_content})
                doc.page_content = response.content
                all_final_docs.append(doc)
                time.sleep(4)
            except Exception as e:
                print(f"  -> 오류 발생: {e}")
                all_final_docs.append(doc)
                time.sleep(4)

    return all_final_docs, current_state

def save_processed_state(state):
    with open(PROCESSED_FILES_DB, "w") as f:
        json.dump(state, f, indent=4)

def split_documents(documents):
    if not documents:
        return []
    print("\n최종 문서를 청크로 분할 중...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        is_separator_regex=False,
    )
    chunks = text_splitter.split_documents(documents)
    print(f"총 {len(chunks)}개의 청크를 생성했습니다.")
    return chunks

def generate_embeddings_and_upsert(chunks):
    if not chunks:
        return
    print("\n임베딩을 생성하고 Pinecone에 업서트 중...")
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", google_api_key=GOOGLE_API_KEY)
    vectorstore = PineconeVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings,
        index_name=PINECONE_INDEX_NAME
    )
    print(f"총 {len(chunks)}개의 청크가 Pinecone 인덱스 '{PINECONE_INDEX_NAME}'에 성공적으로 업서트되었습니다.")

if __name__ == "__main__":
    pc = Pinecone(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)
    if PINECONE_INDEX_NAME not in pc.list_indexes().names():
        print(f"Pinecone 인덱스 '{PINECONE_INDEX_NAME}'을 생성합니다...")
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=3072,
            metric="cosine",
            spec=ServerlessSpec(cloud='aws', region=PINECONE_ENVIRONMENT)
        )
        while not pc.describe_index(PINECONE_INDEX_NAME).status['ready']:
            time.sleep(1)
        print("인덱스가 준비되었습니다.")
    else:
        print(f"Pinecone 인덱스 '{PINECONE_INDEX_NAME}' 확인 완료.")

    target_urls = []
    if os.path.exists(URLS_FILE):
        with open(URLS_FILE, "r") as f:
            target_urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        if target_urls:
            print(f"{URLS_FILE}에서 {len(target_urls)}개의 URL을 로드합니다.")

    # 문서 로드, VLM 처리, 정제, 청킹, 업로드까지 한 번에 실행 (변경된 것만)
    final_documents, current_state = load_and_process_documents(urls=target_urls)
    
    if final_documents:
        chunks = split_documents(final_documents)
        generate_embeddings_and_upsert(chunks)
        save_processed_state(current_state)
        print("\n🎉 새로운 문서 업데이트가 완벽하게 완료되었습니다!")
    else:
        print("\n새로운 문서나 변경된 내용이 없어 업데이트를 생략합니다.")
        save_processed_state(current_state)