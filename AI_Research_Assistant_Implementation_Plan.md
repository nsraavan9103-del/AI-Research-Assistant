# AI Research Assistant — Production-Grade Implementation Plan

> **Document Type:** Principal Architecture & Engineering Plan
> **Version:** 1.0
> **Stack:** FastAPI · React · PostgreSQL · LangChain · Ollama · Redis · Celery
> **Scope:** Prototype → Production upgrade across 6 core modules in 5 phases

---

## Table of Contents

1. [Architectural Overview](#1-architectural-overview)
2. [Database Schema & ERD](#2-database-schema--erd)
3. [Phase 1 — Foundation & Security](#3-phase-1--foundation--security)
4. [Phase 2 — High-Precision Retrieval (Advanced RAG)](#4-phase-2--high-precision-retrieval-advanced-rag)
5. [Phase 3 — Scalability & Performance Infrastructure](#5-phase-3--scalability--performance-infrastructure)
6. [Phase 4 — Frontend & UX Overhaul](#6-phase-4--frontend--ux-overhaul)
7. [Phase 5 — Advanced Intelligence Layer](#7-phase-5--advanced-intelligence-layer)
8. [Cross-Cutting Concerns](#8-cross-cutting-concerns)
9. [Dependency & Risk Matrix](#9-dependency--risk-matrix)

---

## 1. Architectural Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  React Frontend (Vite + TypeScript)                                 │
│  Upload Progress · Citation Highlights · Dark Mode · Thinking State │
└─────────────────────────┬───────────────────────────────────────────┘
                          │ HTTPS / JWT Auth
┌─────────────────────────▼───────────────────────────────────────────┐
│  FastAPI  (Async)  ·  SlowAPI Rate Limiter  ·  JWT Middleware       │
│  /auth  /documents  /query  /agents  /admin                         │
└──────┬──────────────────┬────────────────────┬───────────────────────┘
       │                  │                    │
┌──────▼──────┐   ┌───────▼───────┐   ┌───────▼──────────────────────┐
│  PostgreSQL │   │  Redis Cache  │   │  Celery Worker               │
│  (SQLAlchemy│   │  + Rate Limit │   │  · Document Indexing         │
│  async)     │   │  + LLM Cache  │   │  · Embedding Jobs            │
└─────────────┘   └───────────────┘   └──────────────────────────────┘
                                               │
                              ┌────────────────▼─────────────────────┐
                              │  RAG Pipeline                        │
                              │  FAISS + BM25 · BGE-Reranker         │
                              │  Ollama (phi3) · nomic-embed-text    │
                              └──────────────────────────────────────┘
                                               │
                              ┌────────────────▼─────────────────────┐
                              │  Agent Orchestrator                  │
                              │  Research · FactCheck · Citation     │
                              │  Web Search (Tavily / DuckDuckGo)    │
                              └──────────────────────────────────────┘
```

### Key Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| DB Migration | SQLite → PostgreSQL | Connection pooling, async support, multi-tenant row-level security |
| Async ORM | SQLAlchemy 2.0 async | Native `asyncpg` driver, consistent with FastAPI's async model |
| Task Queue | Celery + Redis | Decouples heavy indexing from HTTP request lifecycle |
| Vector Store | FAISS (upgraded) | Add metadata filters, IVF index for scale |
| Reranker | BGE-Reranker-v2-m3 | Best open-source cross-encoder quality/speed tradeoff |
| Search | Hybrid FAISS + BM25 | Semantic recall + keyword precision, RRF fusion |

---

## 2. Database Schema & ERD

### Mermaid.js Entity Relationship Diagram

```mermaid
erDiagram
    USERS {
        uuid id PK
        varchar email UK
        varchar hashed_password
        varchar full_name
        enum role "admin | user | viewer"
        boolean is_active
        boolean is_verified
        varchar password_reset_token
        timestamp reset_token_expires
        timestamp created_at
        timestamp updated_at
    }

    DOCUMENTS {
        uuid id PK
        uuid owner_id FK
        varchar filename
        varchar original_filename
        varchar file_hash "SHA-256 dedup"
        bigint file_size_bytes
        enum status "pending | indexing | ready | failed"
        integer total_chunks
        varchar storage_path
        jsonb metadata "title, authors, tags"
        timestamp created_at
        timestamp updated_at
    }

    DOCUMENT_CHUNKS {
        uuid id PK
        uuid document_id FK
        integer chunk_index
        text content
        vector embedding "pgvector or FAISS ref"
        integer token_count
        jsonb metadata "page_num, section, headings"
        float semantic_density_score
        timestamp created_at
    }

    CONVERSATIONS {
        uuid id PK
        uuid user_id FK
        varchar title
        enum mode "standard | research | multi_doc"
        boolean is_archived
        timestamp created_at
        timestamp updated_at
    }

    MESSAGES {
        uuid id PK
        uuid conversation_id FK
        enum role "user | assistant | system"
        text content
        jsonb citations "chunk_ids, scores, snippets"
        jsonb agent_trace "steps, tools_used"
        integer prompt_tokens
        integer completion_tokens
        float latency_ms
        timestamp created_at
    }

    USER_SESSIONS {
        uuid id PK
        uuid user_id FK
        varchar jti "JWT ID for revocation"
        varchar ip_address
        varchar user_agent
        boolean is_revoked
        timestamp issued_at
        timestamp expires_at
        timestamp last_seen
    }

    API_USAGE_LOGS {
        uuid id PK
        uuid user_id FK
        varchar endpoint
        varchar method
        integer status_code
        float latency_ms
        integer request_size_bytes
        integer response_size_bytes
        varchar rate_limit_key
        timestamp created_at
    }

    DOCUMENT_ACCESS {
        uuid document_id FK
        uuid user_id FK
        enum permission "owner | read | write"
        timestamp granted_at
    }

    USERS ||--o{ DOCUMENTS : "owns"
    USERS ||--o{ CONVERSATIONS : "has"
    USERS ||--o{ USER_SESSIONS : "holds"
    USERS ||--o{ API_USAGE_LOGS : "generates"
    USERS ||--o{ DOCUMENT_ACCESS : "granted"
    DOCUMENTS ||--o{ DOCUMENT_CHUNKS : "contains"
    DOCUMENTS ||--o{ DOCUMENT_ACCESS : "controls"
    CONVERSATIONS ||--o{ MESSAGES : "contains"
```

### Schema Design Notes

- **`DOCUMENT_CHUNKS.metadata`** stores `{page_num, section_title, heading_path, source_url}` as JSONB for flexible metadata filtering without schema migrations.
- **`MESSAGES.citations`** stores a JSON array of `{chunk_id, score, snippet, page}` to power frontend citation highlighting without re-querying.
- **`USER_SESSIONS.jti`** enables token blacklisting for logout and password-reset revocation without keeping full tokens.
- **`DOCUMENT_ACCESS`** is the multi-tenancy bridge — documents can be shared across users with permission levels.

---

## 3. Phase 1 — Foundation & Security

> **Goal:** Replace all prototype-level security with production-hardened identity and file handling.
> **Duration estimate:** 1–2 weeks
> **Prerequisite:** PostgreSQL up, Alembic migrations bootstrapped, Redis running.

---

### 3.1 File Validation

**Library:** `python-magic` (MIME type), `hashlib` (SHA-256 dedup)

**Logic Flow:**

```
Upload Request
      │
      ▼
[1] Check Content-Length header → reject if > 10MB (before reading body)
      │
      ▼
[2] Read first 2048 bytes → python-magic MIME detection
      │
      ├── MIME not in whitelist {application/pdf, text/plain, text/markdown}
      │      └── → 415 Unsupported Media Type
      │
      ▼
[3] Compute SHA-256 of full file → check DOCUMENTS table for duplicate hash
      │
      ├── Duplicate found → return existing document_id (idempotent upload)
      │
      ▼
[4] Validate filename: strip path traversal, sanitize with `werkzeug.utils.secure_filename`
      │
      ▼
[5] Write to staging path → enqueue Celery indexing task
      │
      ▼
[6] Return 202 Accepted + {document_id, task_id}
```

**Implementation:**

```python
# backend/api/dependencies/file_validator.py

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIMES = {"application/pdf", "text/plain", "text/markdown"}

async def validate_upload(file: UploadFile) -> bytes:
    # Guard 1: Size from headers (early rejection)
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(413, "File exceeds 10MB limit")

    content = await file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, "File exceeds 10MB limit")

    # Guard 2: MIME via magic bytes
    mime = magic.from_buffer(content[:2048], mime=True)
    if mime not in ALLOWED_MIMES:
        raise HTTPException(415, f"File type '{mime}' not permitted")

    return content
```

**Edge Cases:**

| Scenario | Handling |
|---|---|
| File claims `.pdf` but is `.exe` | Caught by magic byte check (MIME mismatch) |
| 10MB boundary (exactly 10MB) | Allowed — comparison is `> MAX`, not `>=` |
| Concurrent duplicate uploads | SHA-256 check is atomic via DB unique constraint |
| Malformed multipart | FastAPI's `UploadFile` raises `400` before validator runs |

**Verification:** `pytest` test: upload a renamed `.exe` → assert `415`. Upload `11MB.pdf` → assert `413`. Upload same PDF twice → assert second returns same `document_id`.

---

### 3.2 JWT Authentication & Token Expiry

**Library:** `python-jose[cryptography]`, `passlib[bcrypt]`

**Token Strategy — Dual-Token (Access + Refresh):**

```
POST /auth/login
  └── Returns: { access_token (60m), refresh_token (7d) }

POST /auth/refresh
  └── Validates refresh token JTI against USER_SESSIONS
  └── Issues new access token, rotates refresh token (old JTI revoked)

POST /auth/logout
  └── Marks session JTI as is_revoked=True in USER_SESSIONS
```

**JWT Payload:**

```python
# Access Token Payload
{
  "sub": "<user_uuid>",
  "jti": "<uuid4>",          # Stored in USER_SESSIONS
  "role": "user",
  "exp": <now + 3600>,       # 60 minutes
  "iat": <now>,
  "type": "access"
}
```

**Middleware:**

```python
# backend/core/security.py
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        raise credentials_exception

    # Check Redis blacklist first (O(1) lookup before DB)
    if await redis.get(f"revoked_jti:{payload['jti']}"):
        raise credentials_exception

    user = await db.get(User, payload["sub"])
    if not user or not user.is_active:
        raise credentials_exception
    return user
```

**Verification:** Assert expired token returns `401`. Assert revoked JTI (post-logout) returns `401`. Assert refresh with valid session returns new access token.

---

### 3.3 Rate Limiting

**Library:** `slowapi` (wraps `limits` library), Redis as storage backend

**Rate Limit Strategy:**

| Endpoint Group | Limit | Window |
|---|---|---|
| `POST /auth/login` | 5 requests | per 15 minutes per IP |
| `POST /documents/upload` | 10 uploads | per hour per user |
| `POST /query` | 30 requests | per minute per user |
| `POST /agents/research` | 5 requests | per hour per user |
| Global (authenticated) | 200 requests | per minute per user |

**Implementation:**

```python
# backend/main.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379",
    strategy="fixed-window-elastic-expiry"  # Prevents boundary exploitation
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Per-endpoint
@router.post("/query")
@limiter.limit("30/minute", key_func=lambda req: req.state.user.id)
async def query_documents(...):
    ...
```

**Edge Cases:**

- Redis unavailable → fail open (log warning, don't block requests) — configurable via `RATE_LIMIT_FAIL_OPEN=true`
- Authenticated user behind shared IP → key by `user_id`, not IP, for `query` endpoints
- Burst attacks → `elastic-expiry` strategy resets window on each violation hit

**Verification:** Hammer `/auth/login` 6 times in 15 min → 6th returns `429` with `Retry-After` header.

---

### 3.4 Identity Recovery (Forgot Password)

**Flow:**

```
[1] POST /auth/forgot-password { email }
      │
      └── Find user by email (always return 200 to prevent email enumeration)
      └── Generate secure token: secrets.token_urlsafe(32)
      └── Store SHA-256(token) in users.password_reset_token, expires in 15 min
      └── Enqueue email task (Celery) → send link: https://app.com/reset?token=<raw>

[2] POST /auth/reset-password { token, new_password }
      │
      └── Hash incoming token → compare with DB
      └── Check expiry
      └── Validate new password (min 8 chars, complexity regex)
      └── bcrypt hash new password → update user
      └── Invalidate ALL USER_SESSIONS for this user (jti revocation)
      └── Clear reset token
```

**Security Hardening:**
- Token is stored as SHA-256 hash, never plaintext
- Constant-time comparison via `hmac.compare_digest` to prevent timing attacks
- All active sessions revoked on password reset (force re-login everywhere)
- Rate limit reset requests: 3 per email per hour

**Verification:** Reset link with expired token → `400`. Second use of same token → `400`. Active JWT after password reset → `401`.

---

## 4. Phase 2 — High-Precision Retrieval (Advanced RAG)

> **Goal:** Replace naive fixed-size chunking with a semantically aware, reranked hybrid retrieval pipeline.
> **Duration estimate:** 2–3 weeks
> **Prerequisite:** Phase 1 complete. Celery workers operational.

---

### 4.1 Semantic Chunking

**Library:** `langchain-text-splitters` (`SemanticChunker`), `langchain-ollama` for embeddings

**Strategy — Three-Layer Chunking:**

```
Raw Document
      │
      ▼
Layer 1: Structural Split
  └── PDFs: Split by page/section headings (PyMuPDF metadata)
  └── Text: Split by double-newline (paragraph boundaries)
      │
      ▼
Layer 2: Semantic Chunker (embedding-based boundary detection)
  └── Embed candidate sentences
  └── Compute cosine similarity between adjacent sentences
  └── Split when similarity drops below threshold (default: 0.85)
  └── Target chunk size: 512 tokens (hard cap: 1024)
      │
      ▼
Layer 3: Metadata Annotation per Chunk
  └── {page_num, section_title, heading_path, char_offset}
  └── Store in DOCUMENT_CHUNKS.metadata (JSONB)
```

**Implementation:**

```python
# backend/services/chunking.py
from langchain_experimental.text_splitter import SemanticChunker
from langchain_ollama import OllamaEmbeddings

embedder = OllamaEmbeddings(model="nomic-embed-text")

chunker = SemanticChunker(
    embeddings=embedder,
    breakpoint_threshold_type="percentile",   # More stable than gradient
    breakpoint_threshold_amount=85,
    add_start_index=True
)

async def chunk_document(text: str, metadata: dict) -> list[DocumentChunk]:
    docs = chunker.create_documents([text], metadatas=[metadata])
    return [
        DocumentChunk(
            content=doc.page_content,
            metadata=doc.metadata,
            token_count=count_tokens(doc.page_content)
        )
        for doc in docs
    ]
```

**Edge Cases:**

| Scenario | Handling |
|---|---|
| Very short document (< 3 sentences) | Skip semantic chunker, treat whole doc as one chunk |
| Single sentence > 1024 tokens | Hard-split at 1024 token boundary with 50-token overlap |
| Non-English documents | nomic-embed-text is multilingual; threshold may need lowering to 0.75 |
| Empty pages (scanned PDF) | Detect via OCR confidence score; skip low-confidence pages |

---

### 4.2 Hybrid Search (FAISS + BM25) with RRF Fusion

**Libraries:** `faiss-cpu`, `rank_bm25`, custom Reciprocal Rank Fusion

**Architecture:**

```
User Query
      │
      ├──────────────────┬────────────────────┐
      ▼                  ▼                    │
[FAISS Dense Search]  [BM25 Sparse Search]   │
  top-k=50 chunks       top-k=50 chunks      │
      │                  │                    │
      └─────────┬─────────┘                   │
                ▼                             │
      [RRF Fusion: score = Σ 1/(rank+60)]    │
                │                             │
                ▼                             │
      Merged top-100 candidates               │
                │                             │
                ▼                             │
      [Metadata Filters applied]  ◄───────────┘
        (user_id, document_ids,
         date_range, page_num)
                │
                ▼
      Top-100 passed to Reranker
```

**RRF Implementation:**

```python
# backend/services/retrieval/hybrid.py

def reciprocal_rank_fusion(
    faiss_results: list[tuple[str, float]],
    bm25_results: list[tuple[str, float]],
    k: int = 60
) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}

    for rank, (chunk_id, _) in enumerate(faiss_results):
        scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (rank + k)

    for rank, (chunk_id, _) in enumerate(bm25_results):
        scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (rank + k)

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

**FAISS Index Configuration:**

```python
# For production scale (>100k chunks): Use IVF index
import faiss

dimension = 768  # nomic-embed-text output dim
nlist = 256      # Number of Voronoi cells

quantizer = faiss.IndexFlatL2(dimension)
index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
index.nprobe = 32   # Cells to search at query time (speed/accuracy tradeoff)

# Add metadata: use IDMap for chunk_id lookup
index = faiss.IndexIDMap(index)
```

**Verification:** Run 50 benchmark queries. Assert FAISS-only recall@5 vs Hybrid recall@5. Hybrid should be ≥ 15% higher on keyword-heavy queries.

---

### 4.3 Cross-Encoder Reranking (BGE-Reranker)

**Library:** `FlagEmbedding` (`BAAI/bge-reranker-v2-m3`)

**Why Rerank After Retrieval:**
Bi-encoder retrieval (FAISS) is fast but approximate — it encodes query and document independently. A cross-encoder sees both simultaneously and scores relevance far more accurately, at the cost of speed. This is why it's applied only to the top-100 pre-filtered candidates.

**Implementation:**

```python
# backend/services/retrieval/reranker.py
from FlagEmbedding import FlagReranker

reranker = FlagReranker(
    "BAAI/bge-reranker-v2-m3",
    use_fp16=True  # 2x speed, negligible quality loss
)

async def rerank(
    query: str,
    chunks: list[DocumentChunk],
    top_n: int = 5
) -> list[DocumentChunk]:
    pairs = [[query, chunk.content] for chunk in chunks]
    scores = reranker.compute_score(pairs, normalize=True)  # [0, 1] range

    ranked = sorted(
        zip(chunks, scores),
        key=lambda x: x[1],
        reverse=True
    )
    return [chunk for chunk, score in ranked[:top_n] if score > 0.3]
```

**Edge Cases:**

- No chunks pass the `0.3` threshold → return top-1 with a low-confidence warning in the response
- Reranker model not loaded (cold start) → fallback to FAISS scores, log degraded mode
- Chunks > 512 tokens → truncate to model max length before reranking (avoids silent truncation errors)

**Verification:** Run query with deliberate keyword match but semantic mismatch. Assert BGE reranker demotes it below a semantically relevant but keyword-poor chunk.

---

### 4.4 Strict Citation Prompting

**Prompt Engineering Strategy:**

```python
CITATION_SYSTEM_PROMPT = """
You are a precise research assistant. You MUST follow these rules absolutely:

1. ONLY use information from the provided context chunks.
2. After EVERY factual claim, you MUST add a citation in the format [Source: {doc_title}, p.{page}].
3. If the context does not contain enough information to answer, respond:
   "I cannot find sufficient information in the provided documents to answer this question."
4. Do NOT use any prior knowledge beyond what is in the context.
5. Do NOT speculate or extrapolate beyond what the sources state.

Context:
{context}
"""

def build_context_block(chunks: list[DocumentChunk]) -> str:
    blocks = []
    for i, chunk in enumerate(chunks):
        blocks.append(
            f"[CHUNK {i+1}] Source: {chunk.metadata['filename']}, "
            f"Page: {chunk.metadata.get('page_num', 'N/A')}\n"
            f"{chunk.content}"
        )
    return "\n\n---\n\n".join(blocks)
```

**Citation Parsing:**

```python
import re

CITATION_PATTERN = re.compile(
    r'\[Source:\s*(?P<doc>[^,]+),\s*p\.(?P<page>\d+)\]'
)

def extract_citations(response: str) -> list[dict]:
    return [
        {"document": m.group("doc").strip(), "page": int(m.group("page"))}
        for m in CITATION_PATTERN.finditer(response)
    ]
```

**Verification:** Send query where answer exists. Assert response contains at least one `[Source: ...]` tag. Assert no fabricated document names appear in citations.

---

## 5. Phase 3 — Scalability & Performance Infrastructure

> **Goal:** Make the system non-blocking, horizontally scalable, and cache-efficient.
> **Duration estimate:** 1–2 weeks
> **Prerequisite:** Phase 1 Redis/PostgreSQL in place.

---

### 5.1 Full Async/Await Refactor

**Library:** `SQLAlchemy 2.0` async, `asyncpg` driver, `httpx` (replace `requests`)

**Async Session Factory:**

```python
# backend/core/database.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/rag_db",
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,    # Detect stale connections
    pool_recycle=3600,     # Recycle connections hourly
    echo=False
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

**Refactor Checklist:**

- [ ] All DB queries: `await db.execute(select(...))` pattern
- [ ] File I/O: `aiofiles` for reading/writing uploads
- [ ] HTTP calls (Ollama, web search): `httpx.AsyncClient`
- [ ] FAISS operations: run in `asyncio.get_event_loop().run_in_executor(None, ...)` (FAISS is CPU-bound, not natively async)
- [ ] Remove all `time.sleep()` → `asyncio.sleep()`

**Verification:** `locust` load test — 50 concurrent users querying simultaneously. Assert p95 latency < 2s. Assert zero `asyncio` blocking warnings in logs.

---

### 5.2 Background Task Queue (Celery + Redis)

**Library:** `celery[redis]`, `redis`, `flower` (monitoring UI)

**Task Architecture:**

```
HTTP Request: POST /documents/upload
      │
      └── Validate file → save to disk → return 202 immediately
                │
                └── celery.delay(index_document_task, document_id)
                              │
                              ▼ (Worker Process)
                    [index_document_task]
                      1. Load file from disk
                      2. Extract text (PyMuPDF / plain text)
                      3. Semantic chunk
                      4. Embed each chunk (nomic-embed-text)
                      5. Write chunks to DB (batch insert)
                      6. Update FAISS index
                      7. Update document.status = 'ready'
                      8. Publish SSE event to frontend
```

**Celery Configuration:**

```python
# backend/celery_app.py
from celery import Celery

celery_app = Celery(
    "rag_worker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
    include=["backend.tasks.indexing", "backend.tasks.email"]
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,           # Acknowledge only after completion
    worker_prefetch_multiplier=1,  # One task at a time per worker (heavy indexing)
    task_routes={
        "backend.tasks.indexing.*": {"queue": "indexing"},
        "backend.tasks.email.*": {"queue": "email"},
    }
)
```

**Progress Tracking via Server-Sent Events:**

```python
# backend/api/routes/documents.py
@router.get("/documents/{document_id}/progress")
async def indexing_progress(document_id: UUID):
    async def event_stream():
        while True:
            status = await get_document_status(document_id)
            yield f"data: {json.dumps(status)}\n\n"
            if status["status"] in ("ready", "failed"):
                break
            await asyncio.sleep(1.5)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

**Verification:** Upload a 5MB PDF. Assert HTTP response is `202` within 200ms. Assert document status transitions `pending → indexing → ready` within 60s. Assert worker retries once on transient DB error.

---

### 5.3 Redis Caching for LLM Responses

**Strategy — Semantic Cache (not exact-match):**

```
Incoming Query
      │
      ▼
[1] Embed query → get vector Q
      │
      ▼
[2] Scan Redis cache keys for semantic similarity
    (store embedding + response pairs in Redis with TTL)
      │
      ├── Cosine similarity > 0.95 with cached query → CACHE HIT
      │      └── Return cached response (tag: [cached])
      │
      └── Cache MISS → Run full RAG pipeline
                │
                └── Store {query_embedding, response, citations} in Redis
                    TTL: 1 hour (configurable per query type)
```

**Implementation:**

```python
# backend/services/cache.py
import hashlib, json
import numpy as np

CACHE_TTL = 3600  # 1 hour
SIMILARITY_THRESHOLD = 0.95

async def get_cached_response(
    query: str,
    query_embedding: list[float],
    redis: Redis
) -> dict | None:
    cache_keys = await redis.keys("llm_cache:*")
    query_vec = np.array(query_embedding)

    for key in cache_keys:
        cached = json.loads(await redis.get(key))
        cached_vec = np.array(cached["embedding"])
        similarity = np.dot(query_vec, cached_vec) / (
            np.linalg.norm(query_vec) * np.linalg.norm(cached_vec)
        )
        if similarity >= SIMILARITY_THRESHOLD:
            return cached["response"]
    return None

async def set_cached_response(
    query_embedding: list[float],
    response: dict,
    redis: Redis
) -> None:
    cache_key = f"llm_cache:{hashlib.md5(str(query_embedding[:5]).encode()).hexdigest()}"
    await redis.setex(
        cache_key,
        CACHE_TTL,
        json.dumps({"embedding": query_embedding, "response": response})
    )
```

**Verification:** Send identical query twice. Assert second response returns in < 50ms with `cached: true` flag. Assert cache miss with paraphrased query.

---

## 6. Phase 4 — Frontend & UX Overhaul

> **Goal:** Transform the React prototype into a polished, accessible, production UI.
> **Duration estimate:** 1–2 weeks
> **Stack:** React 18 + TypeScript + Vite + TailwindCSS + Zustand (state) + React Query (server state)

---

### 6.1 Upload Progress Bar

**Library:** `axios` (built-in `onUploadProgress`), custom `useUpload` hook

**Component Architecture:**

```typescript
// frontend/src/hooks/useUpload.ts
import { useState } from "react";
import axios from "axios";

interface UploadState {
  progress: number;       // 0-100 HTTP upload progress
  indexingProgress: number; // 0-100 from SSE events
  stage: "idle" | "uploading" | "indexing" | "ready" | "error";
  documentId: string | null;
  error: string | null;
}

export function useUpload() {
  const [state, setState] = useState<UploadState>(initialState);

  const upload = async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);

    setState(s => ({ ...s, stage: "uploading" }));

    const { data } = await axios.post("/api/documents/upload", formData, {
      onUploadProgress: (e) => {
        const progress = Math.round((e.loaded / e.total!) * 100);
        setState(s => ({ ...s, progress }));
      }
    });

    // Switch to SSE for indexing progress
    setState(s => ({ ...s, stage: "indexing", documentId: data.document_id }));
    subscribeToIndexingProgress(data.document_id, setState);
  };

  return { state, upload };
}
```

**UI States:**

```
[Idle]          → Drag-and-drop zone with file type hints
[Uploading]     → Linear progress bar (blue) + "Uploading 45%"
[Indexing]      → Pulsing indeterminate bar + "Processing document..."
[Ready]         → Green checkmark + "Ready for queries"
[Error]         → Red bar + error message + retry button
```

---

### 6.2 "Thinking" States

**Component: `ThinkingIndicator`**

```typescript
// Shows while awaiting LLM response stream

const ThinkingStages = [
  { delay: 0,    label: "Searching documents...",     icon: "🔍" },
  { delay: 1500, label: "Retrieving relevant chunks...", icon: "📄" },
  { delay: 3000, label: "Reranking results...",       icon: "⚡" },
  { delay: 5000, label: "Synthesizing answer...",     icon: "🧠" },
];

// Stream tokens as they arrive for perceived performance
// Use ReadableStream from fetch() with LangChain's streaming callback
```

**Streaming Integration:**

```typescript
async function* streamQuery(query: string, documentIds: string[]) {
  const response = await fetch("/api/query/stream", {
    method: "POST",
    body: JSON.stringify({ query, document_ids: documentIds }),
    headers: { "Content-Type": "application/json" }
  });

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    yield decoder.decode(value, { stream: true });
  }
}
```

---

### 6.3 Citation Highlighting & Preview

**Implementation Strategy:**

```
LLM Response contains: "...the methodology [Source: paper.pdf, p.12]..."
      │
      ▼
[1] Parse citation tags with regex
      │
      ▼
[2] Replace with <CitationBadge> React component
      │
      ▼
[3] On hover/click → fetch chunk content from /api/chunks/{chunk_id}
      │
      ▼
[4] Display in floating Popover:
    ┌─────────────────────────────────────┐
    │ 📄 paper.pdf — Page 12              │
    │ ─────────────────────────────────── │
    │ "...the proposed methodology uses   │
    │ a three-stage pipeline consisting   │
    │ of..."                              │
    │                        [Open Page ↗]│
    └─────────────────────────────────────┘
```

**Component:**

```typescript
// frontend/src/components/CitationBadge.tsx
interface CitationProps {
  chunkId: string;
  document: string;
  page: number;
}

export function CitationBadge({ chunkId, document, page }: CitationProps) {
  const { data: chunk } = useQuery({
    queryKey: ["chunk", chunkId],
    queryFn: () => fetchChunk(chunkId),
    staleTime: Infinity  // Chunk content never changes
  });

  return (
    <Popover>
      <PopoverTrigger>
        <span className="citation-badge">[{document}, p.{page}]</span>
      </PopoverTrigger>
      <PopoverContent>
        <ChunkPreview chunk={chunk} />
      </PopoverContent>
    </Popover>
  );
}
```

---

### 6.4 Dark Mode Theme Provider

**Implementation:** CSS custom properties + React Context + `localStorage` persistence

```typescript
// frontend/src/contexts/ThemeContext.tsx
type Theme = "light" | "dark" | "system";

const ThemeContext = createContext<{
  theme: Theme;
  setTheme: (t: Theme) => void;
}>({ theme: "system", setTheme: () => {} });

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(
    () => (localStorage.getItem("theme") as Theme) ?? "system"
  );

  useEffect(() => {
    const root = document.documentElement;
    const resolved = theme === "system"
      ? (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
      : theme;

    root.setAttribute("data-theme", resolved);
    localStorage.setItem("theme", theme);
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}
```

**CSS Variables (TailwindCSS config extension):**

```css
:root[data-theme="light"] {
  --bg-primary: #ffffff;
  --bg-secondary: #f8f9fa;
  --text-primary: #1a1a2e;
  --accent: #4f46e5;
  --border: #e2e8f0;
}

:root[data-theme="dark"] {
  --bg-primary: #0f0f1a;
  --bg-secondary: #1a1a2e;
  --text-primary: #e2e8f0;
  --accent: #818cf8;
  --border: #2d2d4e;
}
```

**Verification:** Toggle dark mode → assert `data-theme="dark"` on `<html>`. Reload → assert theme persists. Set OS to dark mode with `system` setting → assert dark theme activates.

---

## 7. Phase 5 — Advanced Intelligence Layer

> **Goal:** Upgrade from single-agent Q&A to a multi-agent, web-augmented research system.
> **Duration estimate:** 2–3 weeks
> **Prerequisite:** Phases 1–4 complete. Stable retrieval pipeline from Phase 2.

---

### 7.1 Multi-Agent Orchestration

**Framework:** LangChain `AgentExecutor` + custom tool definitions

**Agent Roles:**

```
User Research Query
      │
      ▼
[Orchestrator Agent]  ← Decides which agents to invoke based on query type
      │
      ├──────────────────────────────────────┐
      ▼                                      ▼
[Research Agent]                    [Fact-Check Agent]
  · Hybrid RAG retrieval               · Cross-reference claims
  · Synthesizes answer from docs        · Flag contradictions
  · Identifies knowledge gaps           · Confidence scoring
      │                                      │
      ▼                                      ▼
[Citation Agent]                    [Web Search Agent]  (if gaps found)
  · Validates all citations             · Tavily API / DuckDuckGo
  · Removes hallucinated references     · Supplement missing info
  · Formats final citation list         · Mark as [WEB SOURCE]
      │                                      │
      └──────────────┬───────────────────────┘
                     ▼
            [Final Synthesized Response]
            with validated citations
```

**Implementation:**

```python
# backend/agents/orchestrator.py
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain_core.tools import tool

@tool
async def research_tool(query: str, document_ids: list[str]) -> str:
    """Search and synthesize information from uploaded research documents."""
    chunks = await hybrid_search(query, document_ids)
    reranked = await rerank(query, chunks)
    return build_context_block(reranked)

@tool
async def web_search_tool(query: str) -> str:
    """Search the web for information not found in documents."""
    results = await tavily_client.search(query, max_results=5)
    return format_web_results(results)

@tool
async def fact_check_tool(claim: str, context: str) -> dict:
    """Verify a specific claim against provided context."""
    # Use BGE-reranker to find supporting/contradicting evidence
    ...

# Orchestrator assembles tools and runs the agent loop
orchestrator = create_structured_chat_agent(
    llm=ollama_llm,
    tools=[research_tool, web_search_tool, fact_check_tool],
    prompt=ORCHESTRATOR_PROMPT
)
```

**Agent Trace Storage:** All agent steps (tool calls, intermediate results) are stored in `MESSAGES.agent_trace` as JSONB for debugging and audit purposes.

---

### 7.2 Web Search Integration

**Library:** `tavily-python` (primary), `duckduckgo-search` (free fallback)

**Integration Rules:**
1. Web search is ONLY triggered when: (a) retrieval returns 0 results above threshold, OR (b) user explicitly enables "Web Search" toggle in UI
2. Web results are clearly labeled `[WEB SOURCE: url]` in responses
3. Web content is NOT persisted to the FAISS index (ephemeral per session)
4. Rate limit: 10 web searches per user per hour

```python
# backend/services/web_search.py
from tavily import TavilyClient
from duckduckgo_search import DDGS

async def web_search(query: str, max_results: int = 5) -> list[dict]:
    try:
        client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        results = client.search(query, max_results=max_results)
        return [{"title": r["title"], "url": r["url"], "content": r["content"]}
                for r in results["results"]]
    except Exception:
        # Fallback to DuckDuckGo
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))
```

---

### 7.3 Multi-Document Research Mode

**Mode Activation:** `POST /agents/research` with `mode: "multi_doc"` and multiple `document_ids`

**Research Mode Pipeline:**

```
[1] Extract key themes from each document independently
      │
      ▼
[2] Generate a cross-document knowledge graph (entities + relationships)
      │
      ▼
[3] Identify: agreements, contradictions, and knowledge gaps
      │
      ▼
[4] Synthesize a structured research report:
    - Executive Summary
    - Key Findings (with per-document attribution)
    - Contradictions/Debates
    - Consensus Points
    - Knowledge Gaps
    - Full Citation List
```

**Comparison Matrix Generation:**

```python
MULTI_DOC_SYNTHESIS_PROMPT = """
You are analyzing {n} research documents simultaneously.

Documents:
{document_summaries}

Task: Provide a structured synthesis covering:
1. CONSENSUS: Points all documents agree on
2. CONTRADICTIONS: Claims where documents disagree (cite both positions)
3. UNIQUE INSIGHTS: Important points found in only one document
4. GAPS: Questions raised but not answered by any document

Format each point as: [CLAIM] → [Source 1: agree/disagree] [Source 2: agree/disagree]
"""
```

**Verification:** Upload 3 papers on the same topic. Assert synthesis report identifies at least one genuine contradiction. Assert all cited claims reference a specific document. Assert report sections are non-empty.

---

## 8. Cross-Cutting Concerns

### 8.1 Logging & Observability

```python
# backend/core/logging.py — Structured JSON logging
import structlog

logger = structlog.get_logger()

# Every request logs: user_id, endpoint, latency, token_count, cache_hit
# All errors log: traceback, request_id, user_id
# Agent traces log: tool_name, input, output, latency per step
```

- **Tool:** OpenTelemetry → Jaeger (traces) + Prometheus (metrics) + Grafana (dashboards)
- **Key Metrics:** `query_latency_p95`, `cache_hit_rate`, `indexing_queue_depth`, `reranker_latency`

### 8.2 Environment Configuration

```
# .env structure
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://localhost:6379
SECRET_KEY=<256-bit random>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
MAX_UPLOAD_SIZE_MB=10
TAVILY_API_KEY=...
RATE_LIMIT_FAIL_OPEN=true
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

### 8.3 Testing Strategy

| Layer | Tool | Coverage Target |
|---|---|---|
| Unit (services) | `pytest` + `pytest-asyncio` | ≥ 85% |
| Integration (API) | `httpx.AsyncClient` + test DB | All endpoints |
| RAG Pipeline | Custom eval dataset (50 Q&A pairs) | Recall@5 ≥ 0.80 |
| Load Testing | `locust` | 50 concurrent users, p95 < 2s |
| Security | `bandit` static analysis | 0 high-severity issues |
| Frontend | `vitest` + `React Testing Library` | Critical flows |

### 8.4 Migration Plan (SQLite → PostgreSQL)

```bash
# 1. Export SQLite data
sqlite3 app.db .dump > dump.sql

# 2. Transform SQL dialects (SQLite → PostgreSQL)
# Key differences: AUTOINCREMENT → SERIAL, TEXT → VARCHAR, etc.

# 3. Apply Alembic migrations to new PostgreSQL DB
alembic upgrade head

# 4. Import data
psql -d rag_db -f transformed_dump.sql

# 5. Verify row counts match
```

---

## 9. Dependency & Risk Matrix

### Phase Dependencies

```
Phase 1 (Security)
      │
      ├──────────────────────────────────────────┐
      │                                          │
Phase 2 (RAG)                            Phase 3 (Scalability)
      │                                          │
      └──────────────┬───────────────────────────┘
                     │
               Phase 4 (Frontend)
                     │
               Phase 5 (Agents)
```

### Risk Register

| Risk | Severity | Mitigation |
|---|---|---|
| Ollama `phi3` quality insufficient for reranking | High | Benchmark against `phi3.5`; prepare Mistral 7B fallback |
| Redis single point of failure | High | Redis Sentinel (2 replicas) or Redis Cluster |
| FAISS index grows > RAM | Medium | IVF index + periodic index compaction; migrate to `pgvector` at scale |
| BGE-Reranker cold start latency (>5s) | Medium | Warm model on worker startup; expose health check endpoint |
| Celery worker crash during indexing | Medium | `acks_late=True` + retry with exponential backoff (max 3) |
| Web search API rate limits | Low | Tavily → DuckDuckGo fallback; cache web results in Redis (15 min TTL) |
| JWT secret rotation | Low | Build key rotation support (JWKS endpoint) before go-live |

### Estimated Timeline

| Phase | Scope | Duration |
|---|---|---|
| Phase 1 | Security & Identity | 1–2 weeks |
| Phase 2 | Advanced RAG | 2–3 weeks |
| Phase 3 | Scalability | 1–2 weeks |
| Phase 4 | Frontend UX | 1–2 weeks |
| Phase 5 | Advanced Agents | 2–3 weeks |
| **Total** | **End-to-end** | **7–12 weeks** |

---

*Plan authored for: AI Research Assistant — Prototype to Production upgrade*
*Architecture target: Single-server deployment with horizontal scale path via Celery workers*
