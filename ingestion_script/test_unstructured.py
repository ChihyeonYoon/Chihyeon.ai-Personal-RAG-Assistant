import os
from langchain_community.document_loaders import UnstructuredFileLoader

# DATA_DIR은 ingest.py와 동일하게 설정
DATA_DIR = "../data"

# 첫 번째 PDF 파일 경로 가져오기 (실제 파일 이름으로 대체)
# 실제 파일 이름은 대학교 성적 증명서.pdf 입니다.
filepath = os.path.join(DATA_DIR, "대학교 성적 증명서.pdf")

if not os.path.exists(filepath):
    print(f"Error: File not found at {filepath}")
else:
    try:
        loader = UnstructuredFileLoader(filepath)
        docs = loader.load()
        if docs:
            print(f"Successfully loaded {len(docs)} documents/pages from {filepath}")
            print("First 500 characters of content:")
            print(docs[0].page_content[:500])
            print("\nMetadata:") # 이 부분을 수정
            print(docs[0].metadata)
        else:
            print(f"Loader returned no documents for {filepath}")
    except Exception as e:
        print(f"An error occurred while loading {filepath}: {e}")