import os
import time
import json
import hashlib
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

# 환경 변수 로드
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT") # 예: "us-east-1"
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

if not all([GOOGLE_API_KEY, PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX_NAME]):
    raise ValueError("모든 환경 변수(GOOGLE_API_KEY, PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX_NAME)를 .env 파일에 설정해야 합니다.")

# 데이터 디렉토리 경로
DATA_DIR = "../data"

def load_documents():
    """data 디렉토리에서 PDF 및 Word 문서를 로드합니다."""
    print(f"{DATA_DIR} 디렉토리에서 문서를 로드 중...")
    
    # PDF 로더
    pdf_loader = DirectoryLoader(
        DATA_DIR,
        glob="**/*.pdf",
        loader_cls=PyPDFLoader,
        show_progress=True
    )
    pdf_docs = pdf_loader.load()

    # Word 로더 (docx)
    word_loader = DirectoryLoader(
        DATA_DIR,
        glob="**/*.docx",
        loader_cls=Docx2txtLoader,
        show_progress=True
    )
    word_docs = word_loader.load()
    
    all_docs = pdf_docs + word_docs
    print(f"총 {len(all_docs)}개의 문서를 로드했습니다.")
    return all_docs

def clean_documents(documents):
    """LLM을 사용하여 추출된 텍스트를 마크다운 형식으로 깔끔하게 재구성합니다."""
    print(f"\n총 {len(documents)}개의 문서를 LLM(Gemini 2.5 Flash)으로 정제합니다. 이 과정은 API 호출 제한으로 인해 시간이 다소 소요될 수 있습니다...")
    
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GOOGLE_API_KEY, temperature=0)
    cleaned_docs = []
    
    template = """다음은 PDF 또는 Word 파일에서 추출된 원시 텍스트입니다. 
[매우 중요한 지침]: 원본의 지식, 사실, 정보, 수치 등을 절대 왜곡하거나 임의로 창작/수정하지 마세요! 반드시 있는 그대로의 정보를 유지해야 합니다.
단순히 줄바꿈 오류, 불필요한 공백, 머리글/바닥글, 깨진 글자 등 구조적인 오류만 수정하고, 
의미가 명확하게 전달되도록 마크다운 형식으로 깔끔하게 다듬고 정리만 해주세요. 
원래의 내용과 정보는 절대 누락하거나 변경해서는 안 됩니다.

원시 텍스트:
{text}

재구성된 텍스트:"""
    prompt = PromptTemplate.from_template(template)
    chain = prompt | llm
    
    for i, doc in enumerate(documents):
        source = doc.metadata.get('source', '알 수 없음')
        print(f"[{i+1}/{len(documents)}] 문서 정제 중: {source}")
        
        # 문서 내용이 너무 짧은 경우 건너뛰기
        if len(doc.page_content.strip()) < 50:
            print("  -> 내용이 너무 짧아 정제를 생략합니다.")
            cleaned_docs.append(doc)
            continue
            
        try:
            response = chain.invoke({"text": doc.page_content})
            cleaned_content = response.content
            cleaned_docs.append(Document(page_content=cleaned_content, metadata=doc.metadata))
            
            # 무료 API Rate Limit 우회를 위한 대기 (15 RPM 고려)
            time.sleep(4)
        except Exception as e:
            print(f"  -> 오류 발생: {e}")
            print("  -> 원본 텍스트를 그대로 유지합니다.")
            cleaned_docs.append(doc)
            time.sleep(4)
            
    return cleaned_docs

PROCESSED_FILES_DB = "processed_files.json"

def get_file_hash(filepath):
    """파일의 MD5 해시값을 계산합니다."""
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def filter_unprocessed_documents(documents):
    """이전에 처리되지 않았거나 변경된 문서만 필터링합니다."""
    if os.path.exists(PROCESSED_FILES_DB):
        with open(PROCESSED_FILES_DB, "r") as f:
            processed_state = json.load(f)
    else:
        processed_state = {}

    new_docs = []
    current_state = {}
    
    for doc in documents:
        source = doc.metadata.get('source')
        if not source or not os.path.exists(source):
            new_docs.append(doc)
            continue
            
        file_hash = get_file_hash(source)
        current_state[source] = file_hash
        
        # 해시값이 같으면 이미 처리된 문서로 간주
        if source in processed_state and processed_state[source] == file_hash:
            continue
        else:
            new_docs.append(doc)
            
    return new_docs, current_state

def save_processed_state(state):
    """처리된 문서의 해시 상태를 저장합니다."""
    with open(PROCESSED_FILES_DB, "w") as f:
        json.dump(state, f, indent=4)

def split_documents(documents):
    """로드된 문서를 청크로 분할합니다."""
    print("\n문서를 청크로 분할 중...")
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
    """청크에 대한 임베딩을 생성하고 Pinecone에 업서트합니다."""
    print("\n임베딩을 생성하고 Pinecone에 업서트 중...")
    
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", google_api_key=GOOGLE_API_KEY)
    
    # Pinecone 클라이언트 초기화
    pc = Pinecone(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)

    # 인덱스가 존재하지 않으면 생성 (무료 티어는 1개 인덱스 제한)
    if PINECONE_INDEX_NAME not in pc.list_indexes().names():
        print(f"Pinecone 인덱스 '{PINECONE_INDEX_NAME}'을 생성합니다.")
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=3072, # gemini-embedding-001 모델의 차원
            metric="cosine",
            spec=ServerlessSpec(cloud='aws', region=PINECONE_ENVIRONMENT) # 서버리스 스펙
        )
        print("인덱스 생성이 완료될 때까지 기다립니다...")
        while not pc.describe_index(PINECONE_INDEX_NAME).status['ready']:
            pass
        print("인덱스가 준비되었습니다.")
    
    # LangChain PineconeVectorStore를 사용하여 업서트
    vectorstore = PineconeVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings,
        index_name=PINECONE_INDEX_NAME
    )
    print(f"총 {len(chunks)}개의 청크가 Pinecone 인덱스 '{PINECONE_INDEX_NAME}'에 성공적으로 업서트되었습니다.")

if __name__ == "__main__":
    documents = load_documents()
    if documents:
        new_documents, current_state = filter_unprocessed_documents(documents)
        
        if new_documents:
            print(f"\n총 {len(new_documents)}개의 새로운 또는 수정된 문서가 발견되었습니다.")
            cleaned_documents = clean_documents(new_documents)
            chunks = split_documents(cleaned_documents)
            generate_embeddings_and_upsert(chunks)
            
            # 처리 성공 후 상태 저장
            save_processed_state(current_state)
            print("\n데이터 인제션 프로세스가 완료되었습니다.")
        else:
            print("\n새롭게 추가되거나 수정된 문서가 없습니다. (모든 문서가 이미 Pinecone에 저장되어 있습니다.)")
            # 파일이 삭제된 경우를 반영하기 위해 상태 갱신
            save_processed_state(current_state)
    else:
        print(f"{DATA_DIR} 디렉토리에 처리할 문서가 없습니다.")
