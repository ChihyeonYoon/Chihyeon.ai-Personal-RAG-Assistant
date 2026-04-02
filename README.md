# 🧠 Chihyeon.ai - 개인 RAG 챗 어시스턴트 프로젝트

안녕하세요! AI 연구원 윤치현님의 개인 포트폴리오 웹사이트를 위한 **대화형 RAG(Retrieval-Augmented Generation) 챗 어시스턴트** 구축 프로젝트입니다. 

Google AI Studio의 최신 모델인 **Gemini 2.5 Flash**를 두뇌로 활용하며, 방문자들이 로그인이나 API 키 입력 없이도 안전하고 빠르게 치현님의 연구 및 포트폴리오에 대해 질문할 수 있도록 서버리스(Serverless) 아키텍처로 설계되었습니다.

---

## 🚀 프로젝트 주요 성과 및 특징

1. **데이터 품질 극대화 (AI 기반 문서 정제)**
   - 단순한 텍스트 추출을 넘어, PDF나 Word 문서의 원시 텍스트를 **Gemini 2.5 Flash** 모델이 먼저 읽고 문맥에 맞게 깔끔한 마크다운 형식으로 정제(Clean-up)한 뒤 벡터 DB에 저장합니다.
   - 정보의 왜곡(Hallucination) 없이 구조적 오류만 수정하도록 강력한 프롬프트 엔지니어링이 적용되었습니다.

2. **비용 및 시간 절감 (스마트 인제션)**
   - 파일의 MD5 해시값을 계산하여 `processed_files.json`에 기록합니다.
   - 스크립트를 여러 번 실행하더라도, **새로 추가되거나 내용이 수정된 문서만 골라서** AI 정제 및 임베딩을 수행하므로 API 호출 비용과 시간을 획기적으로 절약합니다.

3. **완벽한 보안과 글로벌 접근성 (Vercel 프록시 서버)**
   - 클라이언트 사이드(GitHub Pages)에서 직접 API를 호출할 때 발생하는 **보안 문제(API 키 노출)**와 **지역 차단 문제(일부 국가에서 Google API 접속 불가 현상)**를 완벽하게 해결했습니다.
   - 미국 기반의 **Vercel Serverless Function**을 프록시 서버로 구축하여 API 키를 안전하게 숨기고 전 세계 방문자 누구나 챗봇을 사용할 수 있게 되었습니다.

4. **초경량 프론트엔드 (No Dependencies)**
   - 무거운 외부 라이브러리(LangChain.js 등) 다운로드로 인한 로딩 지연 및 404 모듈 에러를 방지하기 위해, 프론트엔드 채팅 위젯을 **순수 JavaScript(`fetch` API)**만으로 다시 작성했습니다.
   - 즉각적인 렌더링과 Server-Sent Events(SSE)를 통한 부드러운 **실시간 스트리밍(Streaming) 답변**을 지원합니다.

---

## 🏛️ 시스템 아키텍처

```text
[데이터 파이프라인 (Local)]
개인 문서(PDF/Word) ──> Python 인제션 스크립트 ──> (정제) Gemini 2.5 Flash ──> (임베딩) Gemini-embedding-001 ──> Pinecone 벡터 DB 저장

[서비스 파이프라인 (Live)]
방문자 (GitHub Pages) ──> 질문 입력 ──> Vercel Proxy 서버 ──> (검색) Pinecone ──> (답변 생성) Gemini 2.5 Flash ──> 방문자에게 스트리밍 응답
```

*   **AI 모델**: Google Gemini 2.5 Flash (응답 및 데이터 정제)
*   **임베딩 모델**: Google `models/gemini-embedding-001` (3072차원)
*   **벡터 데이터베이스**: Pinecone (Serverless)
*   **백엔드(프록시)**: Vercel Serverless Functions (`vercel_proxy/api/index.js`)
*   **프론트엔드**: 순수 HTML/JS 플로팅 위젯 (GitHub Pages 연동)

---

## 🛠️ 폴더 구조 및 사용법

### 1. `data/`
*   챗봇이 학습할 치현님의 개인 문서(PDF, docx)를 넣는 곳입니다.
*   **보안 주의:** 이 폴더는 `.gitignore`에 등록되어 있어 GitHub에 올라가지 않습니다.

### 2. `ingestion_script/`
*   문서를 읽고, AI로 정제하고, 벡터 DB에 업로드하는 Python 스크립트가 있습니다.
*   **사용법:**
    1.  `.env` 파일을 만들고 `GOOGLE_API_KEY`, `PINECONE_API_KEY`, `PINECONE_ENVIRONMENT`, `PINECONE_INDEX_NAME`을 세팅합니다.
    2.  `pip install -r requirements.txt` 로 의존성을 설치합니다.
    3.  `python ingest.py` 를 실행하면 새로운 문서만 알아서 척척 올라갑니다.

### 3. `vercel_proxy/`
*   방문자들이 API 키 없이도 챗봇을 쓸 수 있게 해주는 Vercel 백엔드 서버 코드입니다.
*   **배포 방법:**
    1.  이 폴더 안에서 터미널을 열고 `vercel` 명령어를 쳐서 새 프로젝트로 배포합니다.
    2.  Vercel 웹사이트 설정에서 API 키 3개(Google, Pinecone Key, Pinecone Host)를 환경 변수로 등록합니다.
    3.  `vercel --prod` 로 최종 배포를 마칩니다.

### 4. 프론트엔드 위젯 (`index.html` 연동)
*   치현님의 포트폴리오 웹사이트(`ChihyeonYoon.github.io/index.html`) 하단에 이식된 코드입니다.
*   **"Chihyeon.ai RAG Assistant"** 라는 눈에 띄는 둥근 버튼 형태로 제공되며, Vercel 서버 주소(`WORKER_URL`)와 통신하여 작동합니다.

---

## 💡 개발 노트 (Troubleshooting)
*   **Gemini 임베딩 모델 변경:** 초기 `text-embedding-004` 모델의 엔드포인트 지원 종료(404 에러) 이슈를 파악하고, 최신 안정화 버전인 `gemini-embedding-001`(3072차원)으로 인제션 및 리트리벌 로직을 전면 교체하여 해결했습니다.
*   **CORS 및 모듈 에러:** 클라이언트 사이드에서 외부 라이브러리(`esm.sh`)를 불러올 때 발생하는 보안 에러를 없애기 위해, 백엔드 프록시(Vercel)를 도입하고 프론트엔드를 순수 JS `fetch`로 경량화하여 안정성을 100% 확보했습니다.