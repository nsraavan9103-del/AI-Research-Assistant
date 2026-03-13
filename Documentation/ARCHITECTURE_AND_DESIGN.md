# AI Research Assistant - Architecture & Design Decisions

## System Design Document

**Version:** 1.0  
**Last Updated:** March 2026  
**Status:** Production Ready

---

## Table of Contents

1. [Design Philosophy](#design-philosophy)
2. [Architectural Pattern](#architectural-pattern)
3. [Technology Justification](#technology-justification)
4. [Security Design](#security-design)
5. [Scalability Considerations](#scalability-considerations)
6. [Performance Optimization](#performance-optimization)
7. [Data Architecture](#data-architecture)
8. [Integration Patterns](#integration-patterns)

---

## Design Philosophy

### Core Principles

1. **User-Centric Design**
   - Simple, intuitive interface for non-technical users
   - Fast feedback loops with streaming responses
   - Clear citation attribution for transparency

2. **Data Integrity**
   - All answers grounded in uploaded documents
   - No hallucinated information from LLM
   - Traceable citation chains

3. **Modularity**
   - Independent, loosely-coupled services
   - Easy to replace or upgrade components
   - Clear separation of concerns

4. **Scalability**
   - Async processing for heavy operations
   - Horizontal scaling capability
   - Efficient resource utilization

5. **Reliability**
   - Graceful degradation on failures
   - Comprehensive error handling
   - Audit trail for compliance

---

## Architectural Pattern

### Layered Architecture

```
┌─────────────────────────────────────────────┐
│         Presentation Layer                  │
│     (React Frontend, REST API Contracts)    │
└────────────────────┬────────────────────────┘
                     │
┌────────────────────▼────────────────────────┐
│         Business Logic Layer                │
│  (FastAPI endpoints, RAG pipeline, agents)  │
└────────────────────┬────────────────────────┘
                     │
┌────────────────────▼────────────────────────┐
│         Data Access Layer                   │
│  (SQLAlchemy ORM, Vector DB, File storage)  │
└────────────────────┬────────────────────────┘
                     │
┌────────────────────▼────────────────────────┐
│         External Services Layer             │
│  (Ollama LLM, Tavily search, Cloud storage) │
└─────────────────────────────────────────────┘
```

### Component Interaction Model

```
Frontend Request
    ↓
┌─────────────────────────────────────┐
│ API Gateway                         │
│ • Route to handler                  │
│ • JWT validation                    │
│ • Rate limiting                     │
└────────────┬────────────────────────┘
             ↓
┌─────────────────────────────────────┐
│ Business Logic Handler              │
│ • Orchestrate operations            │
│ • Validate inputs                   │
│ • Error handling                    │
└────────┬────────────────┬───────────┘
         │                │
         ↓                ↓
┌─────────────────┐  ┌──────────────────────┐
│ Data Services   │  │ External Services    │
│ • Queries       │  │ • LLM inference      │
│ • Transactions  │  │ • Web search         │
│ • Caching       │  │ • Embedding models   │
└─────────────────┘  └──────────────────────┘
         │                │
         └────────┬───────┘
                  ↓
           Response to Client
```

---

## Technology Justification

### Backend: FastAPI

**Why FastAPI?**
- ✅ **Async by default** - Handles concurrent requests efficiently
- ✅ **Type hints** - Reduces bugs through static analysis
- ✅ **Auto-generated docs** - OpenAPI/Swagger at `/docs`
- ✅ **Fast performance** - Benchmarks comparable to Go/Rust frameworks
- ✅ **Pydantic validation** - Built-in request/response validation

**Alternatives Considered:**
- Django: Too heavy for lightweight API needs
- Flask: Lacks async support in core
- NodeJS: Poor for ML/data processing tasks

### Database: PostgreSQL

**Why PostgreSQL?**
- ✅ **ACID compliance** - Data consistency guarantees
- ✅ **JSON support (JSONB)** - Flexible metadata storage
- ✅ **Full-text search** - Built-in search capabilities
- ✅ **Vector extensions** - pgvector for embedding storage
- ✅ **Connection pooling** - Efficient multi-client handling

**Alternatives Considered:**
- MongoDB: Lacks transaction support; harder to scale documents
- MySQL: No JSON type support in older versions
- SQLite: Single-threaded, not suitable for production

### Vector Store: FAISS

**Why FAISS?**
- ✅ **Fast similarity search** - Optimized C++ implementation
- ✅ **No external service** - Runs locally, no latency overhead
- ✅ **Flexible indexing** - Multiple index types (IVF, HNSW)
- ✅ **Memory efficient** - Compression options for large datasets
- ✅ **Proven at scale** - Meta's production-grade library

**Alternatives Considered:**
- Pinecone: Cloud-only, recurring costs
- Elasticsearch: Overkill for vector search, slower
- Weaviate: More features but heavier

### LLM: Ollama + Phi-3

**Why Ollama + Phi-3?**
- ✅ **Local execution** - Privacy, no API costs
- ✅ **7B parameters** - Fast inference on consumer hardware
- ✅ **Fine-tuned instructions** - Better structured outputs
- ✅ **Open source** - No licensing restrictions
- ✅ **Small footprint** - Runs on 8GB RAM systems

**Alternatives Considered:**
- GPT-4 API: Expensive, privacy concerns
- LLaMA-2: Similar but slower tokenizer
- Mistral: Comparable but less optimized for instructions

### Frontend: React + Vite

**Why React + Vite?**
- ✅ **Component reusability** - Build scalable UI
- ✅ **Hot module replacement** - Instant feedback during development
- ✅ **Tree shaking** - Smaller bundle sizes
- ✅ **Rich ecosystem** - TailwindCSS, React Query, Zustand

**Frontend Architecture:**
```
src/
├── components/          # Reusable UI components
├── pages/              # Page-level components
├── hooks/              # Custom React hooks
│   ├── useStreamQuery.js    # SSE streaming
│   └── useUpload.js         # File upload
├── store/              # Zustand state management
├── contexts/           # React Context API
│   └── ThemeContext.js      # Dark mode
└── services/           # API client services
    └── api.ts              # Axios instance
```

---

## Security Design

### Authentication & Authorization

**JWT Token Strategy:**
```
┌─────────────────────────────────────────────┐
│ Access Token (Short-lived)                  │
│ • Payload: user_id, role, email             │
│ • Expiry: 1 hour                            │
│ • Usage: Every API request                  │
│ • Storage: Browser memory (not localStorage)│
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Refresh Token (Long-lived)                  │
│ • Payload: user_id, issue_timestamp         │
│ • Expiry: 30 days                           │
│ • Usage: Only to get new access token       │
│ • Storage: HTTP-only secure cookie          │
└─────────────────────────────────────────────┘
```

**Benefits of this approach:**
- Stolen access token: Limited damage (1 hour window)
- Stolen refresh token: Requires additional verification
- Separate concerns: Short-lived for requests, long-lived for refresh
- No localStorage: Protects against XSS attacks

### Password Security

**Password Requirements:**
- Minimum 12 characters (for production)
- At least one uppercase, lowercase, digit, special character
- Not in common password list (hibp check)

**Storage:**
- Hashed with Argon2 (OWASP recommended)
- Salt generated per password
- Never stored in plaintext

**Password Reset Flow:**
```
User requests reset
    ↓
Generate token (32 bytes, encrypted)
    ↓
Send via email (only valid for 1 hour)
    ↓
User clicks link with token
    ↓
Verify token signature + expiry
    ↓
Allow password change
    ↓
Invalidate all existing sessions
```

### File Upload Security

**Validation Steps:**
1. **MIME type check** - Prevent executable uploads
2. **File signature check** - Verify file content matches extension
3. **File size limit** - Max 50MB per file
4. **Virus scanning** - Optional ClamAV integration
5. **SHA-256 hash** - Detect duplicate uploads
6. **Isolated storage** - Per-user directory structure

**Filename Sanitization:**
```python
# User uploads: "../../malicious.pdf"
# Stored as: "user-uuid/original-hash-uuid.pdf"
# Never expose original filename in URLs
```

### API Security

**CORS Configuration:**
```python
CORSMiddleware(
    allow_origins=["http://localhost:5173"],  # Frontend only
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

**Rate Limiting:**
```
Per IP address:
  • 100 requests/minute for auth endpoints
  • 50 requests/minute for document upload
  • 1000 requests/hour for other endpoints
```

**Secure Headers:**
```
Strict-Transport-Security: max-age=31536000
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Content-Security-Policy: default-src 'self'
```

### Data Encryption

**In Transit:**
- HTTPS/TLS 1.3 enforced
- Certificate pinning for sensitive data

**At Rest:**
- Sensitive columns encrypted (passwords, reset tokens)
- File encryption optional (AES-256-GCM)
- Database backups encrypted

---

## Scalability Considerations

### Horizontal Scaling

```
┌──────────────────────────────────┐
│      Load Balancer (Nginx)       │
│  • Round-robin distribution      │
│  • Session persistence (if needed)│
└────────┬────────────────┬────────┘
         │                │
         ↓                ↓
┌──────────────┐  ┌──────────────┐
│ FastAPI #1   │  │ FastAPI #2   │
│ (Port 8001)  │  │ (Port 8002)  │
└──────┬───────┘  └───────┬──────┘
       │                  │
       └──────────┬───────┘
                  ↓
         ┌─────────────────┐
         │  PostgreSQL     │
         │  (Single)       │
         └─────────────────┘
         
         ┌─────────────────┐
         │  Redis Cluster  │
         │  (Multiple)     │
         └─────────────────┘
```

### Database Scaling

**Vertical Scaling (Current):**
- Single PostgreSQL instance
- Suitable for 10,000+ users
- Connection pooling via PgBouncer

**Horizontal Scaling (Future):**
- Read replicas for queries
- Write-ahead-log (WAL) for replication
- Sharding by user_id if needed

### File Storage Scaling

**Local Storage (Development):**
- `/uploads/` directory
- Limited by disk space

**Cloud Storage (Production):**
```
AWS S3:
  Bucket: ai-research-assistant-uploads
  Structure: s3://bucket/{user_id}/{document_id}/{file}
  Auto-scaling: Unlimited
  CDN: CloudFront for faster retrieval
```

### Caching Strategy

**Redis Cache Layers:**
```
┌────────────────────────────────────────┐
│ Level 1: Query Cache                   │
│ Key: hash(query, document_ids)         │
│ TTL: 1 hour                            │
│ Hit rate: 30-50% (same documents)      │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│ Level 2: Embedding Cache               │
│ Key: hash(query_text)                  │
│ TTL: 24 hours                          │
│ Saves: 100ms embedding generation      │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│ Level 3: Rate Limit Cache              │
│ Key: {user_id}:{endpoint}              │
│ TTL: 1 hour (sliding)                  │
│ Prevents: API abuse                    │
└────────────────────────────────────────┘
```

### Async Processing with Celery

**When to use Celery:**
```
Synchronous (HTTP response):
  • User login/logout
  • Document metadata query
  • Chat history retrieval

Asynchronous (Background task):
  • Document upload & indexing
  • PDF text extraction
  • Embedding generation
  • Vector index updates
```

**Task Queue Structure:**
```
User uploads document
    ↓
HTTP 202 Accepted (immediately)
    ↓
Task queued in Redis
    ↓
Worker processes:
  1. Extract text
  2. Generate chunks
  3. Create embeddings
  4. Update FAISS index
  5. Update database
    ↓
User notified via WebSocket
```

---

## Performance Optimization

### Query Response Times

**Target Latencies:**
```
API Request Breakdown (3-6 second total):
  1. Token validation        ~5ms
  2. Query embedding         ~100ms
  3. FAISS search           ~50ms
  4. BM25 search            ~30ms
  5. RRF fusion             ~5ms
  6. Cross-encoder reranking ~200ms
  7. Prompt building        ~10ms
  8. LLM inference          ~2-5 seconds
  9. Citation extraction    ~50ms
  10. Response formatting   ~10ms
```

**Optimization Techniques:**
- **Embedding caching** - Store frequently used query embeddings
- **Index optimization** - Tune FAISS index parameters (nprobe)
- **Prompt compression** - Use context summarization for large documents
- **Streaming** - Send tokens as they're generated (no waiting)

### Memory Management

**FAISS Index Memory:**
```
Chunks per document: 50
Average vectors: 5,000 total
Dimension: 384
Memory per vector: 384 × 4 bytes = 1.5 KB
Total: 5,000 × 1.5 KB = 7.5 MB

With 100 documents:
= 750 MB (fits in RAM)
```

**Cache Bounds:**
```
Redis Memory Limits:
  Query results: 1 GB (max 10,000 results)
  Embeddings: 500 MB
  Rate limits: 50 MB
  Session data: 100 MB
  Total: ~2 GB available
```

### Database Query Optimization

**Key Indexes:**
```sql
-- Document lookup (fast)
CREATE INDEX idx_documents_owner_id ON documents(owner_id);

-- Chunk search (critical for RAG)
CREATE INDEX idx_chunks_document_id ON chunks(document_id);

-- Chat history (frequent queries)
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);

-- User authentication
CREATE UNIQUE INDEX idx_users_email ON users(email);
```

**Query Optimization Example:**
```python
# ❌ SLOW: N+1 query problem
for doc in documents:
    chunks = db.query(Chunk).filter(Chunk.document_id == doc.id)  # Extra queries!
    
# ✅ FAST: Join query
chunks = db.query(Chunk).join(Document).filter(
    Document.owner_id == user_id
).all()
```

---

## Data Architecture

### Entity Relationships

```
User 1 ──┐
         │ owns
         └──→ Document N
              │ contains
              └──→ Chunk N
                   │ referenced by
                   └──→ Citation N
                        │ in
                        └──→ Message

User 1 ──┐
         │ creates
         └──→ Conversation N
              │ contains
              └──→ Message N
                   │ references
                   └──→ Citation N
```

### Data Consistency Strategy

**ACID Guarantees:**
- User registration: Atomic (all-or-nothing)
- Document upload: Backup on failure
- Message storage: Idempotent (duplicate protection)

**Eventual Consistency:**
- FAISS index update: Async, eventual consistency
- Cache invalidation: TTL-based

### Backup & Recovery

**Backup Strategy:**
```
Daily incremental backups:
  • Database: SQL dumps (encrypted)
  • Files: S3 cross-region replication
  • Vector index: FAISS snapshot
  
Retention: 30 days rolling window

Recovery procedure:
  1. Stop application (prevent writes)
  2. Restore from latest backup
  3. Replay transaction logs
  4. Verify data integrity
  5. Resume application
```

---

## Integration Patterns

### External Services

**Ollama (LLM Service)**
```
Connection: HTTP/REST
Endpoint: http://localhost:11434
Fallback: Graceful degradation with error message
Health check: Every 60 seconds
```

**Search Services (Optional)**
```
Tavily API:
  ├─ Purpose: Fact-checking & supporting web context
  ├─ Fallback: Return document-only answers
  └─ Rate limit: 100 calls/day (free tier)

DuckDuckGo:
  ├─ Purpose: Privacy-friendly search alternative
  ├─ No API key needed
  └─ Rate limit: 30 calls/minute
```

### Webhook Integration Pattern

**For future Slack/Teams notifications:**
```
┌──────────────┐
│  Document    │
│  Processed   │
└──────┬───────┘
       ↓
┌──────────────────────────┐
│ Event Published to Queue │
└──────┬───────────────────┘
       ↓
┌──────────────────────────┐
│ Webhook Dispatcher       │
│ (Celery task)            │
└──────┬───────────────────┘
       ├─→ Slack Notification
       ├─→ Email Alert
       └─→ User Dashboard Update
```

---

## Disaster Recovery Plan

| Scenario | RTO | RPO | Action |
|----------|-----|-----|--------|
| Database failure | 1 hour | 5 min | Restore from backup |
| Ollama down | 30 min | 0 | Use cached responses |
| Storage full | 2 hours | 0 | Archive old files |
| Security breach | 15 min | - | Revoke tokens, audit logs |
| Data corruption | 4 hours | 1 day | Point-in-time recovery |

**RTO:** Recovery Time Objective (how fast to recover)  
**RPO:** Recovery Point Objective (how much data loss tolerance)

---

## Monitoring & Observability

### Key Metrics

**Application Metrics:**
- API response times (p50, p95, p99)
- Error rates by endpoint
- LLM token usage
- Cache hit rates

**Infrastructure Metrics:**
- CPU/Memory usage
- Disk I/O
- Database connections
- Network throughput

**Business Metrics:**
- Documents indexed per day
- Queries per day
- User retention
- Average answer quality

### Logging Strategy

**Log Levels:**
```
DEBUG: Detailed diagnostic info (development only)
INFO: Normal operations
WARNING: Recoverable errors
ERROR: Request failures
CRITICAL: System failures requiring immediate attention
```

**Structured Logging:**
```json
{
  "timestamp": "2026-03-14T10:35:00Z",
  "level": "ERROR",
  "service": "query_service",
  "user_id": "user-uuid",
  "message": "LLM inference timeout",
  "duration_ms": 5000,
  "document_ids": ["doc-1", "doc-2"],
  "status_code": 503
}
```

---

## Future Enhancements

### Short Term (1-3 months)
- [ ] Multi-language support
- [ ] Document templates
- [ ] Advanced search filters
- [ ] User role-based document access

### Medium Term (3-6 months)
- [ ] Fine-tuned models for domains
- [ ] Real-time collaborative editing
- [ ] Mobile app (React Native)
- [ ] Advanced analytics dashboard

### Long Term (6-12 months)
- [ ] Multi-modal (images, tables, audio)
- [ ] Federated learning for privacy
- [ ] Knowledge graph for relationships
- [ ] On-premise deployment option

---

**Document Version:** 1.0  
**Reviewed By:** Architecture Team  
**Status:** Approved for Production  
**Next Review:** Q2 2026
