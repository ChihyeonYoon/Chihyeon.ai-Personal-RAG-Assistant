# 🧠 Chihyeon.ai - Personal RAG Assistant Project

An interactive, high-performance **Retrieval-Augmented Generation (RAG)** chatbot designed for AI Researcher **Chihyeon Yun's** portfolio. 

Powered by **Gemini 2.5 Flash**, this assistant autonomously cleans documents, generates embeddings, and serves as a secure, serverless AI secretary that answers questions based on personal research papers, project portfolios, and curated web content.

---

## 🚀 Key Features & Architectural Highlights

### 1. High-Fidelity Document Parsing (LlamaParse & Jina Reader)
- **Flawless PDF Extraction via LlamaParse:** Complex multi-column layouts, mathematical equations, and tables in research papers are perfectly extracted into clean Markdown using the state-of-the-art **LlamaParse API**.
- **Javascript-Rendered URL Crawling:** Extracts main content from complex web pages (like SPAs or GitHub Pages) flawlessly using the **Jina Reader API**, ignoring irrelevant navigation and footer noise.
- **Local Markdown Verification:** All parsed and cleaned data is locally saved to the `extracted_md/` directory, allowing developers to review exactly what the AI will read before it gets vectorized.

### 2. Multi-turn Conversation Support (Context-Aware)
- **Short-term Memory:** The chat widget maintains a history of the current session.
- **Logical Context Flow:** Previous conversation turns are sent back to the Gemini model, allowing the assistant to understand follow-up questions (e.g., "What was the conclusion of that paper?" followed by "And what model did they use?").

### 3. Integrated Web & File Ingestion
- **Hybrid Data Sources:** Supports local files (`PDF`, `Docx`) and remote web pages via a simple `URLs.txt` list.
- **AI-Powered Refinement:** Raw text from non-PDF sources (Docx, Web) is processed by **Gemini 2.5 Flash** to fix layout issues and formatting errors before vectorization.

### 4. Smart & Efficient Ingestion
- **Redundancy Control:** Utilizes MD5 hashing via `processed_files.json` to track the state of both files and URLs.
- **Incremental Updates:** Only new or modified content is processed for embeddings, significantly reducing API latency and costs while avoiding duplicate data.

### 5. Secure Serverless Proxy (Vercel)
- **Zero API Key Leakage:** All sensitive credentials (Google, Pinecone) are managed as environment variables within **Vercel Serverless Functions**.
- **Global Accessibility:** Bypasses regional API restrictions (e.g., geo-blocking) by routing requests through US-based servers, ensuring a 100% uptime for global visitors.

### 6. Lightweight "Drop-in" UI
- **Dependency-Free:** Built with **Vanilla JavaScript (`fetch` API)** to ensure near-instant load times and zero conflicts with existing portfolio CSS.
- **Streaming Response:** Implements Server-Sent Events (SSE) for a fluid, real-time typing effect.

---

## 🏛️ System Architecture

```text
[ Data Pipeline (Local) ]
1. URLs (Jina) / DOCX ──> Text Extraction ──> (Cleanup) Gemini 2.5 Flash ──┐
2. PDFs ──> LlamaParse API ────────────────────────────────────────────────┴─> (Embedding) Gemini-embedding-001 ──> Pinecone DB

[ Service Pipeline (Live) ]
Visitor (GitHub Pages) ──> Query + Chat History ──> Vercel Secure Proxy ──> (Retrieve) Pinecone ──> (Generate) Gemini 2.5 Flash ──> Streaming Output
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
- **`URLs.txt`**: Add web URLs here (one per line) to include them in the knowledge base.
- *Protected by `.gitignore` to prevent leakage of private research.*

### 2. `ingestion_script/`
- Python-based CLI tool for document preprocessing and vectorization.
- **Setup:**
  1. Configure `.env` with API keys.
  2. Run `pip install -r requirements.txt`.
  3. Execute `python ingest.py` to sync local/web data with Pinecone.

### 3. `vercel_proxy/`
- The secure middle-layer that enables public access to the AI assistant.
- **Deployment:**
  1. Run `vercel` in this folder to create a project.
  2. Set `GOOGLE_API_KEY`, `PINECONE_API_KEY`, and `PINECONE_HOST` in Vercel settings.
  3. Deploy with `vercel --prod`.

---

## 💡 Developer Notes & Troubleshooting
- **Context Management:** Implemented conversational history passing to ensure the RAG flow feels natural and less like a static search engine.
- **API Model Transition:** Successfully migrated from `text-embedding-004` to `gemini-embedding-001` (3072 dimensions) to resolve endpoint deprecation issues and improve retrieval accuracy.
- **CORS & Geo-Blocking:** Solved Hong Kong/China regional blocks by transitioning from Cloudflare Workers to Vercel (US-based) and implementing a pure JS frontend to avoid ESM dependency failures.
