"""
Document routes: upload (202 + background indexing), list, get, delete, SSE progress.
"""
import asyncio
import json
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.models import Document, User
from core.config import settings
from api.dependencies.auth import get_current_user
from api.dependencies.file_validator import validate_upload

router = APIRouter(prefix="/documents", tags=["documents"])

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


class DocumentOut(BaseModel):
    id: str
    filename: str
    original_filename: str
    status: str
    total_chunks: int
    file_size_bytes: int
    created_at: str

    class Config:
        from_attributes = True


# ── Upload ────────────────────────────────────────────────────────────────────
@router.post("/upload", status_code=202)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload and begin indexing a document.
    Returns 202 immediately with {document_id, task_id}.
    Indexing happens in background (Celery if enabled, else synchronous).
    """
    content, sha256 = await validate_upload(file)

    # Dedup: return existing document if same hash
    existing = await db.execute(
        select(Document).where(
            Document.file_hash == sha256,
            Document.owner_id == current_user.id,
        )
    )
    existing_doc = existing.scalar_one_or_none()
    if existing_doc:
        return {"document_id": existing_doc.id, "task_id": None, "status": "duplicate"}

    # Sanitize filename
    from werkzeug.utils import secure_filename
    safe_name = secure_filename(file.filename or "upload.bin")
    unique_name = f"{sha256[:8]}_{safe_name}"
    storage_path = os.path.join(settings.UPLOAD_DIR, unique_name)

    # Write to disk
    with open(storage_path, "wb") as f:
        f.write(content)

    # Create DB record
    doc = Document(
        owner_id=current_user.id,
        filename=unique_name,
        original_filename=file.filename or safe_name,
        file_hash=sha256,
        file_size_bytes=len(content),
        status="pending",
        storage_path=storage_path,
    )
    db.add(doc)
    await db.flush()

    doc_id = doc.id

    # Trigger indexing
    task_id = None
    if settings.CELERY_ENABLED:
        from tasks.indexing import index_document_task
        task = index_document_task.delay(doc_id)
        task_id = task.id
    else:
        # Synchronous indexing in background asyncio task
        asyncio.create_task(_index_sync(doc_id))

    return {"document_id": doc_id, "task_id": task_id, "status": "pending"}


async def _index_sync(doc_id: str) -> None:
    """Lightweight synchronous fallback indexer (no Celery)."""
    from core.database import AsyncSessionLocal
    from services.chunking import chunk_and_index_document

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(Document).where(Document.id == doc_id))
            doc = result.scalar_one_or_none()
            if not doc:
                return

            doc.status = "indexing"
            await db.commit()

            await chunk_and_index_document(doc, db)

            # Reload doc to update
            await db.refresh(doc)
            doc.status = "ready"
            await db.commit()
        except Exception as e:
            async with AsyncSessionLocal() as db2:
                result = await db2.execute(select(Document).where(Document.id == doc_id))
                doc = result.scalar_one_or_none()
                if doc:
                    doc.status = "failed"
                    await db2.commit()
            print(f"[Indexing ERROR] {doc_id}: {e}")


# ── List ──────────────────────────────────────────────────────────────────────
@router.get("/", response_model=list[DocumentOut])
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document).where(Document.owner_id == current_user.id)
    )
    return result.scalars().all()


# ── Get ───────────────────────────────────────────────────────────────────────
@router.get("/{document_id}")
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.owner_id == current_user.id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


# ── SSE Progress ──────────────────────────────────────────────────────────────
@router.get("/{document_id}/progress")
async def indexing_progress(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Server-Sent Events stream for real-time indexing progress."""

    async def event_stream():
        from core.database import AsyncSessionLocal
        max_polls = 120  # 3 minutes max

        for _ in range(max_polls):
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Document).where(Document.id == document_id)
                )
                doc = result.scalar_one_or_none()
                if not doc:
                    yield f"data: {json.dumps({'error': 'Document not found'})}\n\n"
                    break

                status_payload = {
                    "document_id": doc.id,
                    "status": doc.status,
                    "total_chunks": doc.total_chunks,
                }
                yield f"data: {json.dumps(status_payload)}\n\n"

                if doc.status in ("ready", "failed"):
                    break

            await asyncio.sleep(1.5)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
