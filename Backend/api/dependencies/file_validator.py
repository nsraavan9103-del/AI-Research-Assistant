"""
File upload validator FastAPI dependency.

Checks (in order):
  1. File size ≤ 10 MB (Content-Length header fast-path, then full read)
  2. MIME type via magic bytes (python-magic or fallback to extension)
  3. SHA-256 hash for duplicate detection
"""
import hashlib
import os
from typing import Optional

from fastapi import HTTPException, UploadFile

from core.config import settings

ALLOWED_MIMES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/octet-stream",  # some text files on Windows
}

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}


def _get_mime(content: bytes) -> str:
    """Best-effort MIME detection: tries python-magic first, falls back to header sniff."""
    try:
        import magic as _magic  # type: ignore
        return _magic.from_buffer(content[:2048], mime=True)
    except ImportError:
        # python-magic not available (optional) — check PDF magic bytes manually
        if content[:4] == b"%PDF":
            return "application/pdf"
        # Try decoding as UTF-8 text
        try:
            content[:512].decode("utf-8")
            return "text/plain"
        except UnicodeDecodeError:
            return "application/octet-stream"


def _check_extension(filename: str) -> None:
    ext = os.path.splitext(filename.lower())[1]
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Extension '{ext}' not permitted. Allowed: {ALLOWED_EXTENSIONS}",
        )


async def validate_upload(file: UploadFile) -> tuple[bytes, str]:
    """
    Validate the uploaded file.

    Returns:
        (content_bytes, sha256_hex)

    Raises:
        413 if file exceeds MAX_UPLOAD_SIZE_MB
        415 if MIME type or extension is not allowed
    """
    max_bytes = settings.max_upload_bytes

    # Guard 1: Size from Content-Length header (early rejection)
    if file.size and file.size > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit",
        )

    # Guard 2: Extension check
    _check_extension(file.filename or "unknown.bin")

    # Read full content (one extra byte to catch edge case)
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit",
        )

    # Guard 3: MIME via magic bytes
    mime = _get_mime(content)
    if mime not in ALLOWED_MIMES:
        raise HTTPException(
            status_code=415,
            detail=f"File type '{mime}' not permitted",
        )

    # Guard 4: SHA-256 hash for dedup
    sha256 = hashlib.sha256(content).hexdigest()

    return content, sha256
