# AI Research Assistant - Comprehensive Project Documentation

> **Project Name:** AI Research Assistant  
> **Version:** 1.0  
> **Technology Stack:** FastAPI · React · PostgreSQL/SQLite · LangChain · Ollama · Redis · Celery  
> **Document Type:** Complete Technical Specification & User Guide  
> **Last Updated:** March 2026

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Software Modules](#software-modules)
3. [System Architecture](#system-architecture)
4. [Data Flow Diagram](#data-flow-diagram)
5. [Database Design](#database-design)
6. [API Endpoints](#api-endpoints)
7. [Frontend Components](#frontend-components)
8. [RAG Pipeline Details](#rag-pipeline-details)
9. [Setup & Installation](#setup--installation)
10. [Usage Guide](#usage-guide)

---

## Project Overview

The **AI Research Assistant** is an enterprise-grade, full-stack application designed to help users upload documents and ask intelligent questions using Retrieval-Augmented Generation (RAG) technology. The system combines:

- **Advanced Document Processing:** Semantic chunking, embedding generation, and deduplication
- **Hybrid Retrieval:** Combines dense vectors (FAISS) and sparse retrieval (BM25) with Reciprocal Rank Fusion
- **Multi-Agent Orchestration:** Research, fact-checking, and web search capabilities
- **Citation-Aware Responses:** LLM generates answers with proper attribution to source documents
- **Streaming Real-Time Feedback:** Server-Sent Events (SSE) for immediate user feedback
- **User Authentication:** Secure JWT-based dual-token system

**Target Users:**
- Researchers and academics
- Business analysts
- Knowledge workers
- Students and educators

**Key Capabilities:**
- Upload multiple document formats (PDF, TXT, Markdown)
- Ask natural language questions
- Get AI-powered answers with citations
- Access chat history and conversation tracking
- Perform web searches for additional context
- Multi-user collaboration support

---

## Software Modules

The system is divided into **6 core software modules**, each performing a specific task and working together to provide the complete research assistant experience.

---

### 1. Authentication & Authorization Module

**Purpose:** Manages user registration, login, session management, and role-based access control.

**Components:**
- User registration and account creation
- Password hashing using bcrypt/argon2
- JWT token generation (Access & Refresh tokens)
- Token validation middleware
- Role-based access control (Admin, User, Viewer)
- Password reset functionality
- Session timeout management

**Key Functions:**
```
- register_user(email, password, full_name) → User
- authenticate_user(email, password) → JWT Token Pair
- validate_token(token) → User ID
- refresh_access_token(refresh_token) → New Access Token
- logout_user(token) → Session Invalidated
- assign_user_role(user_id, role) → Updated User
```

**Response Codes:**
- 200: Successful authentication
- 401: Invalid credentials
- 403: Insufficient permissions
- 409: User already exists

---

### 2. File Upload & Processing Module

**Purpose:** Handles secure document ingestion, validation, storage, and preparation for indexing.

**Components:**
- File upload handler with size validation (max 50MB)
- MIME type validation (PDF, TXT, Markdown)
- SHA-256 hashing for duplicate detection
- File storage management (local/cloud)
- Text extraction from various formats
- Semantic chunking algorithm
- Vector embedding generation

**Key Functions:**
```
- upload_file(file, user_id) → Document Record
- validate_file(file) → Validation Result
- extract_text(file_path) → Raw Text
- chunk_text(text, chunk_size, overlap) → List[Chunk]
- generate_embeddings(chunks) → List[Vector]
- detect_duplicate(file_hash) → Boolean
```

**Chunking Strategy:**
- Chunk Size: 512 tokens (~2,048 characters)
- Overlap: 50 tokens (for context continuity)
- Strategy: Recursive splitting on sentences, paragraphs, sections

**Storage Locations:**
- Local: `/uploads/` directory
- Cloud: AWS S3 / Google Cloud Storage (configurable)
- Database: Metadata and embeddings stored in PostgreSQL

---

### 3. Vector Storage & Retrieval Module

**Purpose:** Manages embedding storage, similarity search, and retrieval optimization.

**Components:**
- FAISS index creation and management
- Vector normalization and optimization
- BM25 sparse index for keyword matching
- Hybrid search with Reciprocal Rank Fusion (RRF)
- BGE-Reranker cross-encoder for result refinement
- Metadata filtering and faceted search
- Index persistence and restoration

**Key Functions:**
```
- create_faiss_index(embeddings, documents) → FAISSIndex
- semantic_search(query_embedding, k=5) → TopK Results
- bm25_search(query_text, k=5) → TopK Results
- hybrid_search(query, k=10) → Reranked Results
- add_to_index(documents, embeddings) → Updated Index
- remove_from_index(document_ids) → Updated Index
```

**Search Pipeline:**
1. Convert query to embedding (nomic-embed-text)
2. Semantic search in FAISS (top 20 candidates)
3. BM25 keyword search (top 20 candidates)
4. Combine results using RRF (Reciprocal Rank Fusion)
5. Rerank with BGE-Reranker-v2-m3
6. Return top 5-10 documents with score > threshold

---

### 4. LLM Query & Answer Generation Module (RAG Engine)

**Purpose:** Orchestrates the RAG pipeline to generate accurate, citation-aware answers.

**Components:**
- Query embedding generation
- Document retrieval and ranking
- Prompt engineering and template management
- LLM invocation (Ollama phi3)
- Token streaming for real-time feedback
- Citation extraction and formatting
- Answer validation and quality checking

**Key Functions:**
```
- generate_answer(query, documents, conversation_history) → Answer
- stream_answer(query, documents) → StreamingResponse
- extract_citations(answer, documents) → List[Citation]
- validate_answer_quality(answer, documents) → QualityScore
- format_answer_with_citations(answer, citations) → FormattedAnswer
```

**RAG Prompt Template:**
```
You are an AI Research Assistant. Answer the user's question using ONLY 
the provided documents. Cite your sources explicitly.

Documents:
{context}

Question: {query}

Instructions:
1. Use only information from the documents
2. Cite specific document sections
3. Be accurate and concise
4. If unsure, say "I don't have enough information"

Answer:
```

**Answer Format:**
- Main Answer Text
- Citation List: [Doc1: page X] [Doc2: section Y]
- Confidence Score: 0.0 - 1.0
- Source Documents: List of used document IDs

---

### 5. Chat History & Conversation Management Module

**Purpose:** Stores, retrieves, and manages user conversations and interaction history.

**Components:**
- Conversation session creation and management
- Message storage (user questions and AI responses)
- Conversation indexing for quick retrieval
- Export functionality (PDF, JSON, CSV)
- Conversation sharing and collaboration
- Analytics and usage tracking

**Key Functions:**
```
- create_conversation(user_id, title, documents) → Conversation
- save_message(conversation_id, role, content, metadata) → Message
- get_conversation_history(conversation_id) → List[Message]
- export_conversation(conversation_id, format) → File
- delete_conversation(conversation_id) → Success/Failure
- search_conversations(user_id, query) → List[Conversation]
```

**Data Structure:**
```
Conversation:
  - id: UUID
  - user_id: UUID
  - title: String
  - created_at: Timestamp
  - updated_at: Timestamp
  - documents: List[DocumentID]
  - messages: List[Message]
  - is_archived: Boolean
  - is_shared: Boolean

Message:
  - id: UUID
  - conversation_id: UUID
  - role: "user" | "assistant"
  - content: String
  - citations: List[Citation]
  - embedded_at: Timestamp
  - tokens_used: Integer
```

---

### 6. Frontend Interface Module (React + Vite)

**Purpose:** Provides responsive, modern UI for user interaction.

**Components:**
- Authentication pages (Login, Register, Password Reset)
- Document upload interface
- Chat interface with message history
- Document viewer and citation highlighting
- User dashboard and settings
- Dark mode support
- Responsive design (mobile, tablet, desktop)

**Key Pages:**
```
/auth/login          - User login
/auth/register       - User registration
/app/chat            - Main chat interface
/app/documents       - Document management
/app/settings        - User preferences
/app/history         - Chat history
```

**Key Components:**
- `ChatMessage`: Displays single message with citations
- `CitationBadge`: Interactive citation links
- `UploadZone`: Drag-and-drop file upload
- `DocumentViewer`: PDF/text preview with highlighting
- `ThinkingIndicator`: Streaming response animation
- `SidebarNav`: Navigation menu

**State Management:**
- Zustand for global state
- React Query for server state
- Context API for theme and auth

---

## System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│           Frontend Layer (React + TypeScript)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Auth Page  │  │  Chat Page   │  │ Document Mgr │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  TailwindCSS · Zustand · React Query                            │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTPS / JWT Auth
                         ↓
┌────────────────────────────────────────────────────────────────┐
│        API Gateway Layer (FastAPI Framework)                    │
│  ┌──────────────────────────────────────────────────────┐       │
│  │ /auth         /documents     /query      /agents     │       │
│  │ /chat         /search        /export     /admin      │       │
│  └──────────────────────────────────────────────────────┘       │
│  Middleware: JWT · Rate Limiting · CORS · Error Handling        │
└───┬────────────────────────────────────────────────────────────┘
    │
    ├─→ Authentication Service (JWT Validation)
    │
    ├─→ Document Processing Service
    │   ├─→ File Validator
    │   ├─→ Text Extractor
    │   └─→ Chunker
    │
    ├─→ RAG Engine Service
    │   ├─→ Query Embedder
    │   ├─→ Retrieval Engine (FAISS + BM25)
    │   ├─→ Reranker (BGE)
    │   └─→ LLM Interface (Ollama)
    │
    └─→ Data Layer
        ├─→ PostgreSQL (User, Document, Chat Data)
        ├─→ Redis Cache (LLM Responses, Rate Limits)
        ├─→ FAISS Index (Vector Storage, Local)
        └─→ File Storage (Uploaded Documents)

Background Processing:
┌───────────────────────────────────────────────────┐
│  Celery Worker + Redis Broker                     │
│  • Document Indexing Tasks                        │
│  • Embedding Generation                           │
│  • PDF Text Extraction                            │
│  • Scheduled Cache Cleanup                        │
└───────────────────────────────────────────────────┘
```

### Component Interaction Flow

```
User uploads document
         ↓
  [File Validator] - Check size, type, hash
         ↓
  [Text Extractor] - Extract text from PDF/TXT
         ↓
  [Chunking Engine] - Semantic split (512 tokens)
         ↓
  [Embedding Generator] - nomic-embed-text model
         ↓
  [FAISS Indexer] - Add vectors to index
         ↓
  [Database] - Store metadata and vectors
         ↓
  Document ready for queries

User asks a question
         ↓
  [Query Embedder] - Convert question to vector
         ↓
  [Retrieval Engine] - FAISS + BM25 search
         ↓
  [RRF Fusion] - Combine results
         ↓
  [BGE Reranker] - Rank by relevance
         ↓
  [Prompt Builder] - Construct RAG prompt
         ↓
  [LLM (Ollama)] - Generate answer
         ↓
  [Citation Extractor] - Format citations
         ↓
  [User Interface] - Display answer + sources
         ↓
  [Save to History] - Store in database
```

---

## Data Flow Diagram

### Level-0 DFD (System Overview)

```
┌──────────┐              ┌─────────────────┐              ┌──────────┐
│  User    │──Input/──→   │ AI Research     │──→ Response  │  User    │
│          │  Output      │ Assistant       │  with        │          │
└──────────┘              │ System          │  Citations   └──────────┘
                          └─────────────────┘
```

### Level-1 DFD (Detailed Process Flow)

```
                        ┌─── UPLOAD FLOW ───┐

User with Document
     ↓
[1.0] Validate File
 ├─ Check file size (max 50MB)
 ├─ Verify MIME type
 └─ Calculate SHA-256 hash
     ↓ (Valid)
[2.0] Extract Text
 ├─ Use PDFLoader for PDFs
 └─ Read raw text from TXT/MD
     ↓
[3.0] Chunk Text
 ├─ Split into 512-token chunks
 └─ Maintain 50-token overlap
     ↓
[4.0] Generate Embeddings
 ├─ nomic-embed-text model
 └─ Normalize vectors
     ↓
[5.0] Store in FAISS + Database
 ├─ Add to FAISS index
 └─ Save metadata to PostgreSQL
     ↓
Document Indexed & Ready


                        ┌── QUERY FLOW ───┐

User Query + Chat ID
     ↓
[1.0] Embed Query
 └─ nomic-embed-text model
     ↓
[2.0] Retrieve Documents (Hybrid Search)
 ├─ [2.1] FAISS Semantic Search (top 20)
 │        └─ Vector similarity
 ├─ [2.2] BM25 Keyword Search (top 20)
 │        └─ TF-IDF scoring
 └─ [2.3] Reciprocal Rank Fusion
          └─ Combine scores
     ↓
[3.0] Rerank Results
 ├─ BGE-Reranker-v2-m3
 └─ Select top 5 documents
     ↓
[4.0] Generate Answer
 ├─ Build RAG prompt
 ├─ Call Ollama (phi3)
 └─ Stream tokens
     ↓
[5.0] Extract Citations
 ├─ Identify source documents
 └─ Map to original chunks
     ↓
[6.0] Persist to Database
 ├─ Save user message
 ├─ Save AI response
 └─ Save citations
     ↓
Return Answer to User (with citations)
```

---

## Database Design

### Entity Relationship Diagram (Logical)

```
┌──────────────────────────┐
│         USERS            │
├──────────────────────────┤
│ id (UUID) [PK]          │
│ email (VARCHAR) [UK]    │
│ hashed_password         │
│ full_name               │
│ role (ENUM)             │
│ is_active (BOOLEAN)     │
│ created_at              │
│ updated_at              │
└──────────────────────────┘
         │ 1
         │ │ (has many)
         1 │
┌─────────▼──────────────────┐
│     DOCUMENTS              │
├────────────────────────────┤
│ id (UUID) [PK]            │
│ owner_id (UUID) [FK]      │
│ filename (VARCHAR)        │
│ file_hash (VARCHAR)       │
│ file_size (BIGINT)        │
│ status (ENUM)             │
│ total_chunks (INT)        │
│ metadata (JSONB)          │
│ created_at                │
│ updated_at                │
└────────────────────────────┘
         │ 1
         │ │ (has many)
         1 │
┌─────────▼──────────────────┐
│     CHUNKS                 │
├────────────────────────────┤
│ id (UUID) [PK]            │
│ document_id (UUID) [FK]   │
│ chunk_index (INT)         │
│ text (TEXT)               │
│ embedding (VECTOR)        │
│ tokens (INT)              │
│ metadata (JSONB)          │
│ created_at                │
└────────────────────────────┘

┌──────────────────────────┐
│   CONVERSATIONS          │
├──────────────────────────┤
│ id (UUID) [PK]          │
│ user_id (UUID) [FK]     │
│ title (VARCHAR)         │
│ is_archived (BOOLEAN)   │
│ created_at              │
│ updated_at              │
└──────────────────────────┘
         │ 1
         │ │ (has many)
         1 │
┌─────────▼──────────────────┐
│     MESSAGES               │
├────────────────────────────┤
│ id (UUID) [PK]            │
│ conversation_id (UUID)[FK]│
│ role (ENUM)               │
│ content (TEXT)            │
│ tokens_used (INT)         │
│ metadata (JSONB)          │
│ created_at                │
└────────────────────────────┘
         │ 1
         │ │ (has many)
         1 │
┌─────────▼──────────────────┐
│     CITATIONS              │
├────────────────────────────┤
│ id (UUID) [PK]            │
│ message_id (UUID) [FK]    │
│ chunk_id (UUID) [FK]      │
│ document_id (UUID) [FK]   │
│ citation_text (VARCHAR)   │
│ page_number (INT)         │
│ confidence (FLOAT)        │
│ created_at                │
└────────────────────────────┘
```

### Table Schema Details

#### USERS Table
| Field Name | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PRIMARY KEY | Unique user identifier |
| email | VARCHAR(255) | UNIQUE, NOT NULL | User email address |
| hashed_password | VARCHAR(255) | NOT NULL | Bcrypt/Argon2 hashed password |
| full_name | VARCHAR(255) | NOT NULL | User's full name |
| role | ENUM | DEFAULT 'user' | User role: admin \| user \| viewer |
| is_active | BOOLEAN | DEFAULT TRUE | Account activation status |
| is_verified | BOOLEAN | DEFAULT FALSE | Email verification status |
| created_at | TIMESTAMP | NOT NULL | Account creation timestamp |
| updated_at | TIMESTAMP | NOT NULL | Last update timestamp |

#### DOCUMENTS Table
| Field Name | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PRIMARY KEY | Unique document identifier |
| owner_id | UUID | FOREIGN KEY (USERS) | Document owner |
| filename | VARCHAR(255) | NOT NULL | Stored filename |
| file_hash | VARCHAR(64) | UNIQUE | SHA-256 hash for deduplication |
| file_size | BIGINT | NOT NULL | File size in bytes |
| status | ENUM | DEFAULT 'pending' | pending \| indexing \| ready \| failed |
| total_chunks | INTEGER | DEFAULT 0 | Number of chunks after indexing |
| storage_path | VARCHAR(512) | NOT NULL | Path to stored file |
| metadata | JSONB | DEFAULT '{}' | Title, authors, tags, etc. |
| created_at | TIMESTAMP | NOT NULL | Upload timestamp |
| updated_at | TIMESTAMP | NOT NULL | Last update timestamp |

#### CHUNKS Table
| Field Name | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PRIMARY KEY | Unique chunk identifier |
| document_id | UUID | FOREIGN KEY (DOCUMENTS) | Source document |
| chunk_index | INTEGER | NOT NULL | Order in document (0-based) |
| text | TEXT | NOT NULL | Chunk text content |
| embedding | VECTOR(384) | NOT NULL | nomic-embed-text vector |
| tokens | INTEGER | NOT NULL | Token count in chunk |
| metadata | JSONB | DEFAULT '{}' | Start page, section, etc. |
| embedding_model | VARCHAR(50) | DEFAULT 'nomic-embed-text' | Model used |
| created_at | TIMESTAMP | NOT NULL | Creation timestamp |

#### CONVERSATIONS Table
| Field Name | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PRIMARY KEY | Unique conversation identifier |
| user_id | UUID | FOREIGN KEY (USERS) | Conversation owner |
| title | VARCHAR(255) | NOT NULL | User-defined title |
| document_count | INTEGER | DEFAULT 0 | Number of documents in conversation |
| message_count | INTEGER | DEFAULT 0 | Number of messages exchanged |
| is_archived | BOOLEAN | DEFAULT FALSE | Archive status |
| is_shared | BOOLEAN | DEFAULT FALSE | Sharing status |
| created_at | TIMESTAMP | NOT NULL | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL | Last update timestamp |

#### MESSAGES Table
| Field Name | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PRIMARY KEY | Unique message identifier |
| conversation_id | UUID | FOREIGN KEY (CONVERSATIONS) | Parent conversation |
| role | ENUM | NOT NULL | "user" \| "assistant" |
| content | TEXT | NOT NULL | Message content |
| tokens_used | INTEGER | DEFAULT 0 | LLM tokens consumed |
| metadata | JSONB | DEFAULT '{}' | Model, temperature, etc. |
| created_at | TIMESTAMP | NOT NULL | Message timestamp |

#### CITATIONS Table
| Field Name | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PRIMARY KEY | Unique citation identifier |
| message_id | UUID | FOREIGN KEY (MESSAGES) | Cited in message |
| chunk_id | UUID | FOREIGN KEY (CHUNKS) | Source chunk |
| document_id | UUID | FOREIGN KEY (DOCUMENTS) | Source document |
| citation_text | VARCHAR(512) | NOT NULL | Citation text preview |
| page_number | INTEGER | NULLABLE | Page number if available |
| confidence | FLOAT | NOT NULL | 0.0-1.0 citation confidence |
| created_at | TIMESTAMP | NOT NULL | Creation timestamp |

---

## API Endpoints

### Authentication Endpoints

#### POST /api/v1/auth/register
Register a new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "full_name": "John Doe"
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "user",
  "created_at": "2026-03-14T10:30:00Z"
}
```

#### POST /api/v1/auth/login
Authenticate user and receive token pair.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

#### POST /api/v1/auth/refresh
Refresh access token using refresh token.

**Request:**
```json
{
  "refresh_token": "eyJhbGc..."
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Document Endpoints

#### POST /api/v1/documents/upload
Upload and index a new document.

**Request:**
- Headers: `Authorization: Bearer {token}`
- Body: Form-data with file and metadata

**Response (202):**
```json
{
  "id": "doc-uuid",
  "filename": "research.pdf",
  "status": "indexing",
  "file_size": 2048576,
  "created_at": "2026-03-14T10:30:00Z"
}
```

#### GET /api/v1/documents
List all documents owned by user.

**Query Parameters:**
- `skip`: Offset (default: 0)
- `limit`: Page size (default: 10)
- `status`: Filter by status

**Response (200):**
```json
{
  "total": 5,
  "documents": [
    {
      "id": "doc-uuid",
      "filename": "research.pdf",
      "status": "ready",
      "total_chunks": 45,
      "created_at": "2026-03-14T10:30:00Z"
    }
  ]
}
```

#### DELETE /api/v1/documents/{document_id}
Delete a document and its indexed chunks.

**Response (204):** No content

### Query Endpoints

#### POST /api/v1/query/ask
Ask a question about uploaded documents.

**Request:**
```json
{
  "query": "What are the key findings in the research?",
  "document_ids": ["doc-uuid-1", "doc-uuid-2"],
  "conversation_id": "conv-uuid",
  "stream": true
}
```

**Response (200) - Streaming JSON:**
```json
{"type": "content", "data": "The key findings "}
{"type": "content", "data": "include..."}
{"type": "citations", "data": [{"document_id": "...", "chunk_id": "...", "text": "..."}]}
{"type": "complete", "data": {"tokens_used": 150, "confidence": 0.92}}
```

#### POST /api/v1/query/search
Search documents without generating answer.

**Request:**
```json
{
  "query": "machine learning algorithms",
  "document_ids": ["doc-uuid-1"],
  "k": 10
}
```

**Response (200):**
```json
{
  "results": [
    {
      "chunk_id": "chunk-uuid",
      "document_id": "doc-uuid",
      "text": "...",
      "score": 0.87,
      "page_number": 5
    }
  ]
}
```

### Conversation Endpoints

#### POST /api/v1/conversations
Create a new conversation.

**Request:**
```json
{
  "title": "Q&A about Research Paper",
  "document_ids": ["doc-uuid-1", "doc-uuid-2"]
}
```

**Response (201):**
```json
{
  "id": "conv-uuid",
  "title": "Q&A about Research Paper",
  "created_at": "2026-03-14T10:30:00Z"
}
```

#### GET /api/v1/conversations/{conversation_id}
Get conversation details and messages.

**Response (200):**
```json
{
  "id": "conv-uuid",
  "title": "Q&A about Research Paper",
  "messages": [
    {
      "id": "msg-uuid",
      "role": "user",
      "content": "What is the main topic?",
      "created_at": "2026-03-14T10:35:00Z"
    },
    {
      "id": "msg-uuid",
      "role": "assistant",
      "content": "The main topic is...",
      "citations": [{"document_id": "...", "text": "..."}],
      "created_at": "2026-03-14T10:35:05Z"
    }
  ]
}
```

---

## Frontend Components

### Page Structure

```
App.jsx (Root)
├── AuthPage
│   ├── LoginForm
│   └── RegisterForm
├── ChatPage
│   ├── Sidebar
│   │   ├── ConversationList
│   │   └── DocumentSelector
│   ├── MainChat
│   │   ├── MessageList
│   │   │   ├── ChatMessage
│   │   │   ├── CitationBadge
│   │   │   └── ThinkingIndicator
│   │   └── QueryInput
│   │       └── UploadZone
│   └── DocumentViewer
│       └── PDFPreview / TextPreview
└── SettingsPage
    ├── UserProfile
    ├── Preferences
    └── DataManagement
```

### Key Components Details

#### ChatMessage Component
Displays individual chat messages with proper formatting.

**Props:**
- `role`: "user" | "assistant"
- `content`: Message text
- `citations`: Array of citations
- `timestamp`: Message creation time
- `streaming`: Boolean (for animation)

**Features:**
- Markdown support for assistant messages
- Citation highlighting and tooltips
- Time display
- Copy to clipboard button

#### CitationBadge Component
Renders interactive citation links.

**Props:**
- `documentId`: Reference document ID
- `chunkId`: Reference chunk ID
- `text`: Citation text preview
- `pageNumber`: Optional page reference

**Features:**
- Hover tooltip with full text
- Click to highlight in document viewer
- Confidence score display

#### UploadZone Component
Drag-and-drop file upload interface.

**Props:**
- `onUpload`: Callback function
- `maxSize`: Max file size (bytes)
- `acceptedTypes`: Accepted MIME types

**Features:**
- Drag-and-drop support
- File size validation
- Progress indicator
- Error messages

#### ThinkingIndicator Component
Animated loading state during API calls.

**Props:**
- `isActive`: Boolean
- `message`: Status message

**Features:**
- Animated dots
- Custom messages
- Smooth transitions

#### DocumentViewer Component
Preview uploaded documents.

**Props:**
- `documentId`: Document to display
- `highlightChunks`: Highlight chunks array
- `currentPage`: Current page (for PDFs)

**Features:**
- PDF rendering with PDF.js
- Text preview with syntax highlighting
- Chunk highlighting
- Page navigation
- Search functionality

---

## RAG Pipeline Details

### Query Processing Flow

```
User Query
    ↓
┌─────────────────────────────────────┐
│ 1. QUERY EMBEDDING                  │
│ ─────────────────────────────────── │
│ Input: "What is X?"                 │
│ Model: nomic-embed-text             │
│ Output: Vector (384-dim)            │
│ Process: Tokenize → Forward pass    │
│ Time: ~100ms                        │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 2. SEMANTIC SEARCH (FAISS)          │
│ ─────────────────────────────────── │
│ Index: FAISS IVF256,Flat            │
│ K: 20 (candidates)                  │
│ Metric: L2 distance                 │
│ Returns: Top 20 chunks + scores     │
│ Time: ~50ms                         │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 3. SPARSE SEARCH (BM25)             │
│ ─────────────────────────────────── │
│ Index: BM25 inverted index          │
│ K: 20 (candidates)                  │
│ Metric: TF-IDF                      │
│ Returns: Top 20 chunks + scores     │
│ Time: ~30ms                         │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 4. RECIPROCAL RANK FUSION (RRF)    │
│ ─────────────────────────────────── │
│ Combine FAISS + BM25 results       │
│ Formula: RRF(d) = Σ 1/(k+rank_d) │
│ k=60 (normalization parameter)      │
│ Returns: Top 30 fused results       │
│ Time: ~5ms                          │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 5. CROSS-ENCODER RERANKING         │
│ ─────────────────────────────────── │
│ Model: BGE-Reranker-v2-m3          │
│ Input: (query, chunk_i) pairs × 30  │
│ Output: Relevance scores (0-1)      │
│ Top: 5-10 chunks                    │
│ Time: ~200ms                        │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 6. CONTEXT ASSEMBLY                 │
│ ─────────────────────────────────── │
│ Select top 5 chunks                 │
│ Format: "Document: {text}"          │
│ Max total tokens: 2000              │
│ Returns: Context string             │
│ Time: ~10ms                         │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 7. PROMPT ENGINEERING              │
│ ─────────────────────────────────── │
│ Template: RAG prompt (see above)    │
│ Variables: query, context, history  │
│ Max prompt tokens: 3000             │
│ Returns: Final prompt               │
│ Time: ~5ms                          │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 8. LLM INFERENCE                    │
│ ─────────────────────────────────── │
│ Model: Ollama (phi3, 7B)            │
│ Endpoint: localhost:11434           │
│ Temperature: 0.7 (balanced)         │
│ Top-k: 40 (diversity)               │
│ Max tokens: 500                     │
│ Streaming: Token-by-token SSE       │
│ Time: ~2-5 seconds                  │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 9. CITATION EXTRACTION              │
│ ─────────────────────────────────── │
│ Parse answer for document refs      │
│ Match to source chunks              │
│ Extract quote excerpts              │
│ Calculate confidence scores         │
│ Returns: Citation list              │
│ Time: ~50ms                         │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 10. RESPONSE FORMATTING             │
│ ─────────────────────────────────── │
│ Structure: Answer + Citations       │
│ Markdown formatting                 │
│ HTML escaping for safety            │
│ Returns: Final response             │
│ Time: ~10ms                         │
└─────────────────────────────────────┘
    ↓
Answer sent to User with Citations
```

### Embedding Model Details

**Model:** `nomic-embed-text`
- **Embedding Dimension:** 384
- **Max Input Length:** 2048 tokens
- **Architecture:** Transformer-based
- **Training Data:** 235M+ text pairs
- **Performance:** State-of-the-art for open-source models

### Reranker Model Details

**Model:** `BGE-Reranker-v2-m3`
- **Purpose:** Cross-encoder for relevance scoring
- **Input:** (Query, Document) pairs
- **Output:** Relevance score 0.0-1.0
- **Speed:** ~200ms for 30 pairs
- **Accuracy:** Better than cosine similarity alone

### LLM Model Details

**Model:** `phi3` (via Ollama)
- **Size:** 7B parameters
- **Training:** 128K context window
- **Architecture:** Transformer decoder
- **Performance:** Fast, memory-efficient
- **Supports:** Instruction following, reasoning, code

---

## Setup & Installation

### Prerequisites

- **Python:** 3.10 or higher
- **Node.js:** 18+ (recommended v24)
- **Ollama:** Latest version running locally
- **PostgreSQL:** 14+ (or SQLite for development)
- **Redis:** Optional (for caching and Celery)

### Backend Setup

```bash
# Navigate to backend directory
cd Backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env with your configuration

# Initialize database
python -m alembic upgrade head

# Start Ollama (in separate terminal)
ollama serve

# Pull required models
ollama pull phi3
ollama pull nomic-embed-text

# Run backend server
python -m uvicorn main:app --reload --port 8000
```

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Setup environment variables
cp .env.example .env.local
# Edit .env.local with API endpoint

# Start development server
npm run dev

# Open browser
# http://localhost:5173
```

---

## Usage Guide

### For End Users

#### 1. Create Account
- Navigate to `/auth/register`
- Enter email, password, and full name
- Verify email (if configured)
- Login

#### 2. Upload Documents
- Click "Upload Documents" button
- Drag and drop or select files (PDF, TXT, Markdown)
- Wait for indexing to complete (indicated by status)
- Documents appear in document list

#### 3. Ask Questions
- Create new conversation
- Select documents to query
- Type your question
- Review AI answer and citations
- Click citations to view source content

#### 4. Manage Conversations
- View all past conversations
- Archive old conversations
- Export conversation as PDF/JSON
- Share conversations with others (if enabled)

### For Administrators

#### User Management
```
/admin/users
- View all registered users
- Reset user passwords
- Assign roles (admin, user, viewer)
- Deactivate accounts
```

#### Document Management
```
/admin/documents
- View all documents in system
- Monitor indexing status
- Delete problematic documents
- View usage statistics
```

#### System Monitoring
```
/admin/monitoring
- API request metrics
- LLM token usage
- Database query performance
- Vector search statistics
- Cache hit rates
```

### For Developers

#### API Integration

```python
import requests

# Authenticate
response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={
        "email": "user@example.com",
        "password": "password123"
    }
)
token = response.json()["access_token"]

# Ask a question
response = requests.post(
    "http://localhost:8000/api/v1/query/ask",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "query": "What is the main topic?",
        "document_ids": ["doc-uuid"],
        "stream": False
    }
)
answer = response.json()
```

#### Custom Models

To use different LLM or embedding models:

1. **Edit `.env`:**
```
LLM_MODEL=mistral
EMBEDDING_MODEL=bge-large-en
```

2. **Pull model in Ollama:**
```bash
ollama pull mistral
```

3. **Restart backend:**
```bash
python -m uvicorn main:app --reload
```

---

## Performance Metrics

### Benchmark Results

| Operation | Time | Notes |
|---|---|---|
| Document Upload & Index | 10-30 seconds | Varies by document size |
| Query Embedding | ~100ms | nomic-embed-text |
| FAISS Search | ~50ms | K=20 candidates |
| BM25 Search | ~30ms | Keyword matching |
| Reranking | ~200ms | BGE-Reranker |
| LLM Inference | 2-5 seconds | Stream per token |
| Total Query Response | 3-6 seconds | End-to-end |

### Resource Requirements

| Component | CPU | RAM | Storage |
|---|---|---|---|
| FastAPI Server | 2+ cores | 2GB | 500MB |
| Ollama (LLM) | 4+ cores | 6-8GB | 5GB |
| PostgreSQL | 2 cores | 2GB | 10GB+ |
| Redis Cache | 1 core | 1GB | 2GB |
| Vector Index | 1 core | 2-4GB | 1GB per 100K chunks |

---

## Troubleshooting

### Common Issues

**Issue:** "Connection refused" when calling Ollama
- **Solution:** Ensure Ollama is running: `ollama serve`

**Issue:** Out of memory during indexing
- **Solution:** Reduce chunk size or index documents in batches

**Issue:** Slow query responses
- **Solution:** Check FAISS index size; rebuild if fragmented

**Issue:** Failed file uploads
- **Solution:** Check file size and format; verify disk space

---

## Future Enhancements

- [ ] Multi-language support
- [ ] Queue-based document processing for large batches
- [ ] Web search integration (Tavily API)
- [ ] Multi-modal document support (images, tables)
- [ ] Collaborative editing and real-time updates
- [ ] Advanced analytics dashboard
- [ ] Fine-tuned models for domain-specific queries
- [ ] Mobile application

---

**Version:** 1.0  
**Last Updated:** March 14, 2026  
**Maintained By:** AI Research Assistant Team
