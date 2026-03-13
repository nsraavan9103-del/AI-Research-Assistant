# AI Research Assistant - Complete API Reference

## API Specification v1.0

**Base URL:** `http://localhost:8000/api/v1`  
**Authentication:** Bearer Token (JWT)  
**Content-Type:** application/json  

---

## Table of Contents

1. [Authentication Endpoints](#authentication-endpoints)
2. [Document Endpoints](#document-endpoints)
3. [Query Endpoints](#query-endpoints)
4. [Conversation Endpoints](#conversation-endpoints)
5. [User Endpoints](#user-endpoints)
6. [Admin Endpoints](#admin-endpoints)
7. [Error Handling](#error-handling)
8. [Rate Limiting](#rate-limiting)

---

## Authentication Endpoints

### POST /auth/register

Create a new user account.

**Request Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "password": "SecurePassword123!@#",
  "full_name": "Jane Doe"
}
```

**Response: 201 Created**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "newuser@example.com",
  "full_name": "Jane Doe",
  "role": "user",
  "is_active": true,
  "is_verified": false,
  "created_at": "2026-03-14T10:30:00Z"
}
```

**Error Responses:**
- `400 Bad Request` - Invalid email format or weak password
- `409 Conflict` - Email already registered

**Password Requirements:**
- Minimum 8 characters
- At least one uppercase letter
- At least one number
- At least one special character

---

### POST /auth/login

Authenticate user and receive token pair.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!@#"
}
```

**Response: 200 OK**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "full_name": "Jane Doe",
    "role": "user"
  }
}
```

**Error Responses:**
- `401 Unauthorized` - Invalid credentials
- `404 Not Found` - User not found

**Token Details:**
- Access Token: Valid for 1 hour
- Refresh Token: Valid for 30 days

---

### POST /auth/refresh

Obtain new access token using refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response: 200 OK**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Error Responses:**
- `401 Unauthorized` - Refresh token expired or invalid

---

### POST /auth/logout

Invalidate user session.

**Request Headers:**
```
Authorization: Bearer {access_token}
```

**Response: 204 No Content**

---

### POST /auth/password-reset

Request password reset email.

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response: 200 OK**
```json
{
  "message": "Password reset email sent"
}
```

---

## Document Endpoints

### POST /documents/upload

Upload and index a new document.

**Request Headers:**
```
Authorization: Bearer {access_token}
Content-Type: multipart/form-data
```

**Request Body (Form-Data):**
```
file: <binary PDF/TXT file>
metadata: {"title": "Research Paper", "tags": ["AI", "ML"]}
```

**Response: 202 Accepted**
```json
{
  "id": "doc-550e8400-e29b-41d4-a716-446655440000",
  "filename": "research_paper.pdf",
  "file_size": 2048576,
  "status": "indexing",
  "file_hash": "sha256_hash_here",
  "owner_id": "user-550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2026-03-14T10:30:00Z",
  "metadata": {
    "title": "Research Paper",
    "tags": ["AI", "ML"]
  }
}
```

**Error Responses:**
- `400 Bad Request` - Invalid file format
- `413 Payload Too Large` - File exceeds 50MB
- `409 Conflict` - Duplicate file (same SHA-256)
- `401 Unauthorized` - Missing/invalid token

**Supported Formats:**
- `.pdf` - PDF documents
- `.txt` - Plain text files
- `.md` - Markdown files
- `.docx` - Word documents
- `.xlsx` - Excel spreadsheets

**File Upload Limits:**
- Max size: 50MB
- Max simultaneous uploads: 5

---

### GET /documents

List all documents for authenticated user.

**Request Headers:**
```
Authorization: Bearer {access_token}
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| skip | integer | 0 | Offset for pagination |
| limit | integer | 10 | Number of results |
| status | string | all | Filter by status: pending, indexing, ready, failed |
| search | string | empty | Search documents by filename |
| sort | string | created_at | Sort field: created_at, filename, file_size |
| order | string | desc | Sort order: asc, desc |

**Example Request:**
```
GET /documents?skip=0&limit=10&status=ready&sort=created_at&order=desc
```

**Response: 200 OK**
```json
{
  "total": 5,
  "skip": 0,
  "limit": 10,
  "documents": [
    {
      "id": "doc-550e8400-e29b-41d4-a716-446655440000",
      "filename": "research_paper.pdf",
      "file_size": 2048576,
      "status": "ready",
      "total_chunks": 45,
      "tags": ["AI", "ML"],
      "created_at": "2026-03-14T10:30:00Z",
      "updated_at": "2026-03-14T10:35:45Z"
    }
  ]
}
```

**Document Statuses:**
- `pending` - Awaiting processing
- `indexing` - Currently being processed
- `ready` - Indexed and searchable
- `failed` - Processing failed

---

### GET /documents/{document_id}

Get detailed information about a specific document.

**Request Headers:**
```
Authorization: Bearer {access_token}
```

**Response: 200 OK**
```json
{
  "id": "doc-550e8400-e29b-41d4-a716-446655440000",
  "filename": "research_paper.pdf",
  "file_size": 2048576,
  "status": "ready",
  "total_chunks": 45,
  "total_tokens": 18240,
  "owner_id": "user-550e8400-e29b-41d4-a716-446655440000",
  "storage_path": "/uploads/user-id/doc-id.pdf",
  "file_hash": "sha256_hash",
  "metadata": {
    "title": "Research Paper",
    "authors": ["John Doe"],
    "pages": 32
  },
  "created_at": "2026-03-14T10:30:00Z",
  "updated_at": "2026-03-14T10:35:45Z",
  "chunks": [
    {
      "id": "chunk-550e8400-e29b-41d4-a716-446655440000",
      "index": 0,
      "tokens": 512,
      "page": 1,
      "preview": "The research focuses on..."
    }
  ]
}
```

---

### DELETE /documents/{document_id}

Delete a document and all its chunks.

**Request Headers:**
```
Authorization: Bearer {access_token}
```

**Response: 204 No Content**

**Error Responses:**
- `404 Not Found` - Document not found
- `403 Forbidden` - User doesn't own document

---

### GET /documents/{document_id}/chunks

Get all chunks for a document.

**Query Parameters:**
| Parameter | Type | Default |
|-----------|------|---------|
| skip | integer | 0 |
| limit | integer | 20 |

**Response: 200 OK**
```json
{
  "total": 45,
  "chunks": [
    {
      "id": "chunk-550e8400-e29b-41d4-a716-446655440000",
      "document_id": "doc-550e8400-e29b-41d4-a716-446655440000",
      "index": 0,
      "text": "Full text of chunk...",
      "tokens": 512,
      "page_number": 1,
      "metadata": {
        "section": "Introduction",
        "start_position": 0
      },
      "created_at": "2026-03-14T10:35:00Z"
    }
  ]
}
```

---

## Query Endpoints

### POST /query/ask

Ask a question about indexed documents and get an AI-generated answer.

**Request Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "query": "What are the main findings of the research?",
  "document_ids": [
    "doc-550e8400-e29b-41d4-a716-446655440000",
    "doc-550e8401-e29b-41d4-a716-446655440001"
  ],
  "conversation_id": "conv-550e8400-e29b-41d4-a716-446655440000",
  "stream": true,
  "include_sources": true,
  "top_k": 5
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| query | string | Yes | User's question |
| document_ids | array[UUID] | Yes | Documents to search |
| conversation_id | UUID | No | Link to conversation |
| stream | boolean | No (def: false) | Stream response tokens |
| include_sources | boolean | No (def: true) | Include citations |
| top_k | integer | No (def: 5) | Max sources to return |

**Response: 200 OK (Non-Streaming)**
```json
{
  "answer": "The main findings include:\n1. AI improves efficiency by 40%\n2. Implementation requires careful planning\n\nThese findings are based on research conducted over 12 months.",
  "citations": [
    {
      "id": "cite-550e8400-e29b-41d4-a716-446655440000",
      "document_id": "doc-550e8400-e29b-41d4-a716-446655440000",
      "chunk_id": "chunk-550e8400-e29b-41d4-a716-446655440000",
      "text": "The study shows a 40% efficiency improvement",
      "page_number": 5,
      "confidence": 0.92
    }
  ],
  "metadata": {
    "tokens_used": 150,
    "inference_time_ms": 3500,
    "documents_used": 2,
    "model": "phi3"
  }
}
```

**Response: 200 OK (Streaming - Server-Sent Events)**
```
data: {"type": "content", "data": "The"}
data: {"type": "content", "data": " main"}
data: {"type": "content", "data": " findings"}
...
data: {"type": "citations", "data": [...citations...]}
data: {"type": "complete", "data": {"tokens_used": 150}}
```

**Error Responses:**
- `400 Bad Request` - No documents selected
- `404 Not Found` - Document not found
- `429 Too Many Requests` - Rate limit exceeded
- `503 Service Unavailable` - LLM unavailable

---

### POST /query/search

Search documents without generating an LLM answer.

**Request Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "query": "machine learning",
  "document_ids": ["doc-550e8400-e29b-41d4-a716-446655440000"],
  "k": 10,
  "search_type": "hybrid"
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| query | string | Yes | Search query |
| document_ids | array[UUID] | Yes | Documents to search |
| k | integer | No (def: 5) | Number of results |
| search_type | string | No (def: hybrid) | semantic, keyword, hybrid |

**Response: 200 OK**
```json
{
  "results": [
    {
      "chunk_id": "chunk-550e8400-e29b-41d4-a716-446655440000",
      "document_id": "doc-550e8400-e29b-41d4-a716-446655440000",
      "text": "Machine learning is a subset of artificial intelligence...",
      "score": 0.92,
      "page_number": 12,
      "search_type": "semantic",
      "position": 1
    },
    {
      "chunk_id": "chunk-550e8401-e29b-41d4-a716-446655440001",
      "document_id": "doc-550e8400-e29b-41d4-a716-446655440000",
      "text": "ML algorithms learn from data without explicit programming...",
      "score": 0.88,
      "page_number": 15,
      "search_type": "keyword",
      "position": 2
    }
  ],
  "total_results": 2,
  "search_time_ms": 125
}
```

**Search Types:**
- `semantic` - Vector similarity (FAISS)
- `keyword` - Full-text search (BM25)
- `hybrid` - Combined semantic + keyword (RRF)

---

## Conversation Endpoints

### POST /conversations

Create a new conversation.

**Request Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "title": "Q&A about AI Research Paper",
  "document_ids": [
    "doc-550e8400-e29b-41d4-a716-446655440000",
    "doc-550e8401-e29b-41d4-a716-446655440001"
  ]
}
```

**Response: 201 Created**
```json
{
  "id": "conv-550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user-550e8400-e29b-41d4-a716-446655440000",
  "title": "Q&A about AI Research Paper",
  "document_ids": [
    "doc-550e8400-e29b-41d4-a716-446655440000",
    "doc-550e8401-e29b-41d4-a716-446655440001"
  ],
  "message_count": 0,
  "is_archived": false,
  "is_shared": false,
  "created_at": "2026-03-14T10:30:00Z",
  "updated_at": "2026-03-14T10:30:00Z"
}
```

---

### GET /conversations

List all conversations for user.

**Query Parameters:**
| Parameter | Type | Default |
|-----------|------|---------|
| skip | integer | 0 |
| limit | integer | 20 |
| archived | boolean | false |

**Response: 200 OK**
```json
{
  "total": 3,
  "conversations": [
    {
      "id": "conv-550e8400-e29b-41d4-a716-446655440000",
      "title": "Q&A about AI Research",
      "message_count": 5,
      "is_archived": false,
      "preview": "What are main findings...",
      "created_at": "2026-03-14T10:30:00Z",
      "updated_at": "2026-03-14T11:15:00Z"
    }
  ]
}
```

---

### GET /conversations/{conversation_id}

Get conversation details with all messages.

**Response: 200 OK**
```json
{
  "id": "conv-550e8400-e29b-41d4-a716-446655440000",
  "title": "Q&A about AI Research",
  "document_ids": ["..."],
  "messages": [
    {
      "id": "msg-550e8400-e29b-41d4-a716-446655440000",
      "role": "user",
      "content": "What are the main findings?",
      "created_at": "2026-03-14T10:35:00Z"
    },
    {
      "id": "msg-550e8401-e29b-41d4-a716-446655440000",
      "role": "assistant",
      "content": "The main findings include...",
      "tokens_used": 150,
      "citations": [
        {
          "document_id": "doc-...",
          "text": "...",
          "confidence": 0.92
        }
      ],
      "created_at": "2026-03-14T10:35:05Z"
    }
  ],
  "created_at": "2026-03-14T10:30:00Z"
}
```

---

### DELETE /conversations/{conversation_id}

Delete a conversation.

**Response: 204 No Content**

---

### POST /conversations/{conversation_id}/export

Export conversation as file.

**Request Body:**
```json
{
  "format": "pdf"
}
```

**Supported Formats:** pdf, json, csv, markdown

**Response: 200 OK**
- Returns binary file for download

---

## User Endpoints

### GET /users/me

Get current user profile.

**Request Headers:**
```
Authorization: Bearer {access_token}
```

**Response: 200 OK**
```json
{
  "id": "user-550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "full_name": "Jane Doe",
  "role": "user",
  "is_active": true,
  "is_verified": true,
  "created_at": "2026-03-14T10:30:00Z",
  "preferences": {
    "theme": "dark",
    "notifications_enabled": true
  },
  "usage_stats": {
    "total_documents": 5,
    "total_tokens_used": 15000,
    "api_calls": 120
  }
}
```

---

### PUT /users/me

Update user profile.

**Request Body:**
```json
{
  "full_name": "Jane Smith",
  "preferences": {
    "theme": "light",
    "notifications_enabled": false
  }
}
```

**Response: 200 OK**
```json
{
  "id": "user-550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "full_name": "Jane Smith",
  "preferences": {
    "theme": "light",
    "notifications_enabled": false
  }
}
```

---

### POST /users/me/change-password

Change user password.

**Request Body:**
```json
{
  "current_password": "OldPassword123!",
  "new_password": "NewPassword456!@#"
}
```

**Response: 200 OK**
```json
{
  "message": "Password changed successfully"
}
```

**Error Responses:**
- `400 Bad Request` - Current password incorrect
- `422 Unprocessable Entity` - New password doesn't meet requirements

---

## Admin Endpoints

### GET /admin/users

List all users (admin only).

**Request Headers:**
```
Authorization: Bearer {admin_token}
```

**Query Parameters:**
| Parameter | Type |
|-----------|------|
| skip | integer |
| limit | integer |
| role | string |
| is_active | boolean |

**Response: 200 OK**
```json
{
  "total": 25,
  "users": [
    {
      "id": "user-...",
      "email": "user@example.com",
      "full_name": "Jane Doe",
      "role": "user",
      "is_active": true,
      "created_at": "2026-03-14T10:30:00Z"
    }
  ]
}
```

---

### PUT /admin/users/{user_id}/role

Change user role (admin only).

**Request Body:**
```json
{
  "role": "admin"
}
```

**Allowed Roles:** user, admin, viewer

**Response: 200 OK**

---

### POST /admin/system/cleanup

Run system maintenance task (admin only).

**Response: 200 OK**
```json
{
  "message": "Cleanup completed",
  "stats": {
    "deleted_documents": 5,
    "cleared_cache": "2.5 GB"
  }
}
```

---

## Error Handling

### Error Response Format

All errors follow this format:

```json
{
  "detail": "Description of error",
  "error_code": "ERROR_CODE",
  "status": 400,
  "timestamp": "2026-03-14T10:30:00Z"
}
```

### HTTP Status Codes

| Code | Meaning | Common Cause |
|------|---------|--------------|
| 200 | OK | Successful request |
| 201 | Created | Resource created |
| 202 | Accepted | Async task queued |
| 204 | No Content | Successful deletion |
| 400 | Bad Request | Invalid parameters |
| 401 | Unauthorized | Missing/invalid token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Duplicate resource |
| 413 | Payload Too Large | File too large |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Service down |

---

## Rate Limiting

### Limits per User

| Endpoint | Limit | Window |
|----------|-------|--------|
| /query/ask | 100 | 1 hour |
| /documents/upload | 50 | 1 day |
| /query/search | 500 | 1 hour |
| Other endpoints | 1000 | 1 hour |

### Rate Limit Headers

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1710424200
```

---

## WebSocket Endpoints

### ws://localhost:8000/ws/documents/{document_id}/status

Subscribe to document indexing status updates.

**Message Format:**
```json
{
  "status": "indexing",
  "progress": 45,
  "total_chunks": 100,
  "current_chunk": 45,
  "timestamp": "2026-03-14T10:35:00Z"
}
```

---

**API Version:** 1.0  
**Last Updated:** March 2026
