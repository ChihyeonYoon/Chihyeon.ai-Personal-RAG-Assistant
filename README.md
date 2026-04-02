# 🧠 Chihyeon.ai - Personal RAG Assistant Project

An interactive, high-performance **Retrieval-Augmented Generation (RAG)** chatbot designed for AI Researcher **Chihyeon Yun's** portfolio. 

Powered by **Gemini 2.5 Flash**, this assistant autonomously cleans documents, generates embeddings, and serves as a secure, serverless AI secretary that answers questions based on personal research papers and project portfolios.

---

## 🚀 Key Features & Architectural Highlights

### 1. AI-Powered Document Refinement
- **Zero-Noise Data:** Raw text extracted from PDFs/Word files is first processed by **Gemini 2.5 Flash** to fix layout issues, broken characters, and formatting errors.
- **Context-Preserving Transformation:** The assistant reformats unstructured data into clean Markdown while strictly adhering to original facts, ensuring high-quality vector search.

### 2. Smart & Efficient Ingestion
- **Redundancy Control:** Utilizes MD5 hashing via `processed_files.json` to track file states.
- **Incremental Updates:** Only new or modified documents are processed for embeddings, significantly reducing API latency and costs.

### 3. Secure Serverless Proxy (Vercel)
- **Zero API Key Leakage:** All sensitive credentials (Google, Pinecone) are managed as environment variables within **Vercel Serverless Functions**.
- **Global Accessibility:** Bypasses regional API restrictions (e.g., geo-blocking) by routing requests through US-based servers, ensuring a 100% uptime for global visitors.

### 4. Lightweight "Drop-in" UI
- **Dependency-Free:** Built with **Vanilla JavaScript (`fetch` API)** to ensure near-instant load times and zero conflicts with existing portfolio CSS.
- **Streaming Response:** Implements Server-Sent Events (SSE) for a fluid, real-time typing effect.

---

## 🏛️ System Architecture

```text
[ Data Pipeline (Local) ]
Documents (PDF/Docx) ──> Ingestion Script ──> (Cleanup) Gemini 2.5 Flash ──> (Embedding) Gemini-embedding-001 ──> Pinecone DB

[ Service Pipeline (Live) ]
Visitor (GitHub Pages) ──> Query ──> Vercel Secure Proxy ──> (Retrieve) Pinecone ──> (Generate) Gemini 2.5 Flash ──> Streaming Output
```

- **Brain:** Google Gemini 2.5 Flash
- **Embeddings:** Google `models/gemini-embedding-001` (3072-dim)
- **Vector Store:** Pinecone (Serverless)
- **Backend:** Vercel Node.js Runtime (`vercel_proxy/api/index.js`)
- **Frontend:** Pure HTML/JS Floating Widget (GitHub Pages integration)

---

## 🛠️ Components & Usage

### 1. `data/`
- Directory for personal source documents.
- *Protected by `.gitignore` to prevent leakage of private research.*

### 2. `ingestion_script/`
- Python-based CLI tool for document preprocessing and vectorization.
- **Setup:**
  1. Configure `.env` with API keys.
  2. Run `pip install -r requirements.txt`.
  3. Execute `python ingest.py` to sync local data with Pinecone.

### 3. `vercel_proxy/`
- The secure middle-layer that enables public access to the AI assistant.
- **Deployment:**
  1. Run `vercel` in this folder to create a project.
  2. Set `GOOGLE_API_KEY`, `PINECONE_API_KEY`, and `PINECONE_HOST` in Vercel settings.
  3. Deploy with `vercel --prod`.

### 4. Frontend Widget
- Injected into the portfolio's `index.html`.
- Features a prominent **"Chihyeon.ai RAG Assistant"** pill button with dynamic state transitions (Open/Close).

---

## 💡 Developer Notes & Troubleshooting
- **API Model Transition:** Successfully migrated from `text-embedding-004` to `gemini-embedding-001` (3072 dimensions) to resolve endpoint deprecation issues and improve retrieval accuracy.
- **CORS & Geo-Blocking:** Solved Hong Kong/China regional blocks by transitioning from Cloudflare Workers to Vercel (US-based) and implementing a pure JS frontend to avoid ESM dependency failures.
