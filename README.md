# AI Research Assistant

A production-grade, full-stack AI Research Assistant application supporting advanced hybrid Retrieval-Augmented Generation (RAG), multi-agent orchestration, and citation-aware LLM responses.

## Tech Stack
*   **Backend:** FastAPI, SQLAlchemy 2.0 (async), SQLite/PostgreSQL, Redis, Celery
*   **Frontend:** React 18, Vite, TypeScript, TailwindCSS, Zustand, React Query
*   **AI/ML:** Ollama (LLM/Embeddings), LangChain, FAISS (Dense), BM25 (Sparse), BGE-Reranker (Cross-Encoder)

## Features
1.  **JWT Authentication:** Robust dual-token (Access/Refresh) system.
2.  **File Management:** Upload, validate (size, MIME, SHA-256 duplicate checking), and index PDFs, TXTs, MDs.
3.  **Advanced RAG Pipeline:**
    *   3-Layer Semantic Chunking.
    *   Hybrid retrieval (FAISS + BM25) fused with Reciprocal Rank Fusion (RRF).
    *   BGE-Reranker Cross-Encoder.
    *   Citation-Aware Prompting.
4.  **Streaming Q&A:** Token-byte streaming for immediate feedback via SSE.
5.  **Multi-Agent Research:** An orchestrator that fuses document context with web search (Tavily/DDG) and fact-checks answers.

---

## 🚀 Setup Instructions

### 1. Prerequisites
*   **Python:** 3.10+
*   **Node.js:** v18+ (v24 recommended)
*   **Ollama:** Installed and running locally. We use `phi3` for LLM and `nomic-embed-text` for embeddings by default.

Start Ollama and pull the models:
```bash
ollama serve
ollama pull phi3
ollama pull nomic-embed-text
```

### 2. Backend Setup
Navigate to the `Backend` directory:
```bash
cd Backend
```

1.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    venv\Scripts\activate  # Windows
    source venv/bin/activate  # Mac/Linux
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Environment Variables:**
    Copy the example `.env` file and set the `SECRET_KEY`:
    ```bash
    cp .env.example .env
    ```
    *Open `.env` and set a secure `SECRET_KEY`. Everything else is pre-configured to work out-of-the-box with SQLite.*

4.  **Database Initialisation (Alembic):**
    We use Alembic for asynchronous schema migrations.
    ```bash
    alembic upgrade head
    ```
    *(Note: For immediate development, `main.py` is also set up to auto-create tables on startup if migrations are skipped).*

5.  **Start the Backend Server:**
    ```bash
    uvicorn main:app --reload --port 8000
    ```
    *The API will be running at `http://localhost:8000`. API docs are at `/docs`.*

### 3. Frontend Setup
Navigate to the `frontend` directory in a new terminal:
```bash
cd frontend
```

1.  **Install dependencies:**
    ```bash
    npm install
    ```

2.  **Start the Development Server:**
    ```bash
    npm run dev
    ```
    *The frontend will be at `http://localhost:5173`.*

---

## 🛠️ Architecture Overview

The system runs heavily on **Graceful Degradation**. It is designed to run locally, but can scale to support production-grade loads:

*   **Database:** Defaults to async SQLite (`aiosqlite`). Can switch to PostgreSQL (`asyncpg`) just by changing `.env`.
*   **Vector Search:** `faiss-cpu` is preferred but falls back to basic Langchain wrappers if uninstalled. `rank-bm25` is used for hybrid scoring.
*   **Reranker:** Re-ranking defaults to simple cosine-similarity but upgrades to an advanced FP16 cross-encoder if `FlagEmbedding` is installed.
*   **Web Search:** Fuses into context using `DDGS` (DuckDuckGo) by default, or elevates to Tavily if a `TAVILY_API_KEY` is provided.

For heavier loads, turn on **Redis** for semantic response caching and **Celery** for offloading document indexing into background worker queues.
