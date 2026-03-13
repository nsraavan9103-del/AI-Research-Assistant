"""
Hybrid FAISS + BM25 retrieval with Reciprocal Rank Fusion (RRF).

On startup:
  - FAISS index is loaded from disk (or rebuilt from DB chunks)
  - BM25 corpus is built in-memory from DB chunks

Per-query:
  1. FAISS dense search → top-50
  2. BM25 sparse search → top-50
  3. RRF fusion → merged top-100
  4. Metadata filters applied
"""
import asyncio
import os
import pickle
from typing import Optional

import numpy as np

from core.config import settings

# In-memory state (rebuilt on startup)
_faiss_index = None         # faiss.Index or None
_chunk_id_map: list[str] = []   # index position → chunk_id
_bm25_index = None          # BM25Okapi or None
_bm25_corpus: list[list[str]] = []
_bm25_chunk_ids: list[str] = []


# ── FAISS helpers ─────────────────────────────────────────────────────────────
def _get_embedder():
    from langchain_ollama import OllamaEmbeddings
    return OllamaEmbeddings(
        model=settings.EMBED_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
    )


def _embed_texts(texts: list[str]) -> np.ndarray:
    embedder = _get_embedder()
    vecs = embedder.embed_documents(texts)
    return np.array(vecs, dtype=np.float32)


def _embed_query(query: str) -> np.ndarray:
    embedder = _get_embedder()
    vec = embedder.embed_query(query)
    return np.array([vec], dtype=np.float32)


# ── RRF ──────────────────────────────────────────────────────────────────────
def _reciprocal_rank_fusion(
    faiss_results: list[tuple[str, float]],
    bm25_results: list[tuple[str, float]],
    k: int = 60,
) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for rank, (chunk_id, _) in enumerate(faiss_results):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (rank + k)
    for rank, (chunk_id, _) in enumerate(bm25_results):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (rank + k)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


# ── Index construction ────────────────────────────────────────────────────────
async def add_chunks_to_index(document_id: str, chunk_objs: list) -> None:
    """
    Add newly chunked documents to FAISS and BM25 indexes.
    chunk_objs: list of DocumentChunk ORM objects.
    """
    global _faiss_index, _chunk_id_map, _bm25_index, _bm25_corpus, _bm25_chunk_ids

    if not chunk_objs:
        return

    texts = [c.content for c in chunk_objs]
    ids = [c.id for c in chunk_objs]

    loop = asyncio.get_event_loop()

    try:
        import faiss  # type: ignore
        vecs = await loop.run_in_executor(None, _embed_texts, texts)
        dim = vecs.shape[1]

        if _faiss_index is None:
            _faiss_index = faiss.IndexFlatL2(dim)
            _chunk_id_map = []

        _faiss_index.add(vecs)
        _chunk_id_map.extend(ids)

        # Save FAISS index to disk
        os.makedirs(settings.VECTOR_DIR, exist_ok=True)
        faiss.write_index(_faiss_index, os.path.join(settings.VECTOR_DIR, "index.faiss"))
        with open(os.path.join(settings.VECTOR_DIR, "chunk_ids.pkl"), "wb") as f:
            pickle.dump(_chunk_id_map, f)

    except ImportError:
        # faiss not available — use LangChain FAISS wrapper as fallback
        from langchain_community.vectorstores import FAISS
        from langchain_core.documents import Document as LCDoc

        lc_docs = [LCDoc(page_content=t, metadata={"chunk_id": i}) for t, i in zip(texts, ids)]
        embedder = _get_embedder()
        vs = FAISS.from_documents(lc_docs, embedder)
        vs.save_local(settings.VECTOR_DIR)

    # BM25
    try:
        from rank_bm25 import BM25Okapi  # type: ignore
        tokenized = [t.lower().split() for t in texts]
        _bm25_corpus.extend(tokenized)
        _bm25_chunk_ids.extend(ids)
        _bm25_index = BM25Okapi(_bm25_corpus)
    except ImportError:
        pass  # BM25 optional


async def rebuild_index_from_db() -> None:
    """Rebuild FAISS + BM25 from all DocumentChunk rows in DB at startup."""
    global _faiss_index, _chunk_id_map, _bm25_index, _bm25_corpus, _bm25_chunk_ids

    from core.database import AsyncSessionLocal
    from core.models import DocumentChunk
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(DocumentChunk))
        chunks = result.scalars().all()

    if not chunks:
        return

    await add_chunks_to_index("all", chunks)


# ── Search ────────────────────────────────────────────────────────────────────
async def hybrid_search(
    query: str,
    document_ids: Optional[list[str]] = None,
    top_k: int = 50,
) -> list[dict]:
    """
    Returns top chunks from hybrid FAISS + BM25 search.
    Each result: {chunk_id, content, score, metadata}
    """
    global _faiss_index, _chunk_id_map, _bm25_index, _bm25_chunk_ids

    from core.database import AsyncSessionLocal
    from core.models import DocumentChunk
    from sqlalchemy import select

    loop = asyncio.get_event_loop()
    faiss_results: list[tuple[str, float]] = []
    bm25_results: list[tuple[str, float]] = []

    # ── FAISS search ──────────────────────────────────────────────────────────
    try:
        import faiss

        if _faiss_index is None and os.path.exists(
            os.path.join(settings.VECTOR_DIR, "index.faiss")
        ):
            _faiss_index = faiss.read_index(
                os.path.join(settings.VECTOR_DIR, "index.faiss")
            )
            with open(os.path.join(settings.VECTOR_DIR, "chunk_ids.pkl"), "rb") as f:
                _chunk_id_map = pickle.load(f)

        if _faiss_index is not None and _faiss_index.ntotal > 0:
            qvec = await loop.run_in_executor(None, _embed_query, query)
            k = min(top_k, _faiss_index.ntotal)
            distances, indices = _faiss_index.search(qvec, k)

            for dist, idx in zip(distances[0], indices[0]):
                if idx >= 0 and idx < len(_chunk_id_map):
                    faiss_results.append((_chunk_id_map[idx], float(dist)))

    except (ImportError, Exception):
        # Fallback: LangChain FAISS
        try:
            from langchain_community.vectorstores import FAISS
            embedder = _get_embedder()
            vs = FAISS.load_local(
                settings.VECTOR_DIR, embedder, allow_dangerous_deserialization=True
            )
            lc_results = await loop.run_in_executor(
                None, vs.similarity_search_with_score, query, top_k
            )
            for doc, score in lc_results:
                chunk_id = doc.metadata.get("chunk_id", "")
                if chunk_id:
                    faiss_results.append((chunk_id, score))
        except Exception:
            pass

    # ── BM25 search ───────────────────────────────────────────────────────────
    if _bm25_index is not None:
        tokenized_query = query.lower().split()
        scores = _bm25_index.get_scores(tokenized_query)
        top_indices = np.argsort(scores)[::-1][:top_k]
        bm25_results = [
            (_bm25_chunk_ids[i], float(scores[i]))
            for i in top_indices
            if i < len(_bm25_chunk_ids)
        ]

    # ── Fusion ────────────────────────────────────────────────────────────────
    merged = _reciprocal_rank_fusion(faiss_results, bm25_results)
    candidate_ids = [cid for cid, _ in merged[:100]]

    # ── Metadata filter ───────────────────────────────────────────────────────
    if not candidate_ids:
        return []

    async with AsyncSessionLocal() as db:
        query_stmt = select(DocumentChunk).where(DocumentChunk.id.in_(candidate_ids))
        if document_ids:
            query_stmt = query_stmt.where(DocumentChunk.document_id.in_(document_ids))
        result = await db.execute(query_stmt)
        chunks = result.scalars().all()

    # Preserve RRF order
    chunk_map = {c.id: c for c in chunks}
    ordered = [
        {
            "chunk_id": cid,
            "content": chunk_map[cid].content,
            "metadata": chunk_map[cid].chunk_metadata or {},
            "score": score,
        }
        for cid, score in merged
        if cid in chunk_map
    ]

    return ordered[:top_k]
