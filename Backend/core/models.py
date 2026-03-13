"""
SQLAlchemy ORM models — Full production schema.
All PKs are UUIDs. Relationships use lazy="selectin" for async compatibility.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy import JSON  # fallback for SQLite

from core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


# ── Users ─────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="user")  # admin | user | viewer
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    password_reset_token: Mapped[Optional[str]] = mapped_column(String(255))
    reset_token_expires: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    documents: Mapped[list["Document"]] = relationship(back_populates="owner", lazy="selectin")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user", lazy="selectin")
    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user", lazy="selectin")


# ── Documents ─────────────────────────────────────────────────────────────────
class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), index=True)  # SHA-256
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|indexing|ready|failed
    total_chunks: Mapped[int] = mapped_column(Integer, default=0)
    storage_path: Mapped[Optional[str]] = mapped_column(String(1000))
    doc_metadata: Mapped[Optional[dict]] = mapped_column(JSON)  # title, authors, tags
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    owner: Mapped["User"] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document", lazy="selectin")


# ── Document Chunks ───────────────────────────────────────────────────────────
class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_metadata: Mapped[Optional[dict]] = mapped_column(JSON)  # page_num, section, headings
    semantic_density_score: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    document: Mapped["Document"] = relationship(back_populates="chunks")


# ── Conversations ─────────────────────────────────────────────────────────────
class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(500))
    mode: Mapped[str] = mapped_column(String(20), default="standard")  # standard|research|multi_doc
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", lazy="selectin")


# ── Messages ──────────────────────────────────────────────────────────────────
class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user|assistant|system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[Optional[dict]] = mapped_column(JSON)       # [{chunk_id, score, snippet, page}]
    agent_trace: Mapped[Optional[dict]] = mapped_column(JSON)     # [{step, tool, input, output}]
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


# ── User Sessions ─────────────────────────────────────────────────────────────
class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    jti: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)  # JWT ID
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="sessions")
