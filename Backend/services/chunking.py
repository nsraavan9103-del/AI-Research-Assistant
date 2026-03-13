"""
Semantic chunking pipeline — 3-layer approach:
  Layer 1: Structural split (PDF pages / paragraph boundaries)
  Layer 2: SemanticChunker (embedding-based boundary detection)
  Layer 3: Metadata annotation per chunk

Falls back to RecursiveCharacterTextSplitter if Ollama is unavailable.
"""
import asyncio
import os
from dataclasses import dataclass, field
from typing import Optional

from core.config import settings


@dataclass
class ChunkData:
    content: str
    chunk_index: int
    token_count: int = 0
    metadata: dict = field(default_factory=dict)


def _count_tokens(text: str) -> int:
    """Approximate token count (4 chars ≈ 1 token)."""
    return len(text) // 4


# ── Text extraction ───────────────────────────────────────────────────────────
def extract_text(storage_path: str) -> tuple[str, list[dict]]:
    """
    Extract text from a file. Returns (full_text, page_metadata_list).
    page_metadata_list: [{page_num, char_start, char_end, section}]
    """
    ext = os.path.splitext(storage_path)[1].lower()

    if ext == ".pdf":
        return _extract_pdf(storage_path)
    else:
        return _extract_text(storage_path)


def _extract_pdf(path: str) -> tuple[str, list[dict]]:
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(path)
        pages = []
        offsets = []
        full_text = ""

        for i, page in enumerate(doc):
            text = page.get_text()
            start = len(full_text)
            full_text += text + "\n\n"
            offsets.append({
                "page_num": i + 1,
                "char_start": start,
                "char_end": len(full_text),
            })

        return full_text, offsets
    except ImportError:
        # Fallback: langchain PyPDFLoader
        from langchain_community.document_loaders import PyPDFLoader
        docs = PyPDFLoader(path).load()
        full_text = "\n\n".join(d.page_content for d in docs)
        offsets = [{"page_num": i + 1} for i in range(len(docs))]
        return full_text, offsets


def _extract_text(path: str) -> tuple[str, list[dict]]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    return text, [{"page_num": 1}]


# ── Chunker ───────────────────────────────────────────────────────────────────
def _semantic_split(text: str, page_offsets: list[dict]) -> list[ChunkData]:
    """
    Try SemanticChunker (requires Ollama). Falls back to RecursiveCharacterTextSplitter.
    """
    if len(text.strip()) < 100:
        # Very short document → single chunk
        return [ChunkData(content=text.strip(), chunk_index=0,
                          token_count=_count_tokens(text),
                          metadata={"page_num": 1})]

    try:
        from langchain_experimental.text_splitter import SemanticChunker
        from langchain_ollama import OllamaEmbeddings

        embedder = OllamaEmbeddings(
            model=settings.EMBED_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
        )
        chunker = SemanticChunker(
            embeddings=embedder,
            breakpoint_threshold_type="percentile",
            breakpoint_threshold_amount=85,
            add_start_index=True,
        )
        from langchain_core.documents import Document as LCDoc
        lc_docs = chunker.create_documents([text])
        return _annotate_chunks(lc_docs, page_offsets)

    except Exception:
        # Fallback to recursive splitter
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=512, chunk_overlap=50, add_start_index=True
        )
        from langchain_core.documents import Document as LCDoc
        lc_docs = splitter.create_documents([text])
        return _annotate_chunks(lc_docs, page_offsets)


def _annotate_chunks(lc_docs, page_offsets: list[dict]) -> list[ChunkData]:
    chunks = []
    for i, doc in enumerate(lc_docs):
        start_idx = doc.metadata.get("start_index", 0)

        # Find which page this chunk belongs to
        page_num = 1
        for po in reversed(page_offsets):
            if start_idx >= po.get("char_start", 0):
                page_num = po.get("page_num", 1)
                break

        chunks.append(ChunkData(
            content=doc.page_content,
            chunk_index=i,
            token_count=_count_tokens(doc.page_content),
            metadata={
                "page_num": page_num,
                "char_offset": start_idx,
            },
        ))
    return chunks


# ── Public API ────────────────────────────────────────────────────────────────
async def chunk_and_index_document(doc, db) -> None:
    """
    Full indexing pipeline:
      1. Extract text
      2. Semantic chunk
      3. Embed + build FAISS index
      4. Save DocumentChunk rows to DB
    """
    from core.models import DocumentChunk
    from sqlalchemy import delete
    from services.retrieval.hybrid import add_chunks_to_index

    # Step 1: extract
    loop = asyncio.get_event_loop()
    text, page_offsets = await loop.run_in_executor(
        None, extract_text, doc.storage_path
    )

    # Step 2: chunk
    chunks = await loop.run_in_executor(None, _semantic_split, text, page_offsets)

    # Step 3: delete old chunks if re-indexing
    await db.execute(
        delete(DocumentChunk).where(DocumentChunk.document_id == doc.id)
    )

    # Step 4: persist chunks to DB
    chunk_objs = []
    for chunk_data in chunks:
        chunk_obj = DocumentChunk(
            document_id=doc.id,
            chunk_index=chunk_data.chunk_index,
            content=chunk_data.content,
            token_count=chunk_data.token_count,
            chunk_metadata=chunk_data.metadata,
        )
        db.add(chunk_obj)
        chunk_objs.append(chunk_obj)

    await db.flush()

    # Step 5: add to FAISS + BM25 index
    await add_chunks_to_index(doc.id, chunk_objs)

    # Update document
    doc.total_chunks = len(chunk_objs)
