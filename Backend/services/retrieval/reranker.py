"""
BGE-Reranker cross-encoder for precise relevance scoring.
Model: BAAI/bge-reranker-v2-m3 (via FlagEmbedding)

Falls back to simple cosine-similarity scoring if FlagEmbedding is not installed.
"""
import asyncio
from typing import Optional

from core.config import settings

_reranker = None


def _load_reranker():
    global _reranker
    if _reranker is not None:
        return _reranker
    try:
        from FlagEmbedding import FlagReranker  # type: ignore
        _reranker = FlagReranker("BAAI/bge-reranker-v2-m3", use_fp16=True)
        return _reranker
    except (ImportError, Exception):
        return None


def _cosine_similarity_score(query: str, chunk_content: str) -> float:
    """Simple keyword-overlap fallback when reranker is unavailable."""
    q_words = set(query.lower().split())
    c_words = set(chunk_content.lower().split())
    if not q_words or not c_words:
        return 0.0
    intersection = q_words & c_words
    return len(intersection) / (len(q_words) + len(c_words) - len(intersection))


async def rerank(
    query: str,
    chunks: list[dict],
    top_n: int = 5,
    score_threshold: float = 0.0,  # Lowered from 0.3 — BGE not always available
) -> list[dict]:
    """
    Cross-encoder reranking of retrieved chunks.

    Args:
        query:           User query string
        chunks:          List of {chunk_id, content, metadata, score}
        top_n:           Number of top results to return
        score_threshold: Minimum score to include (0.0 = return all top_n)

    Returns:
        Sorted list of chunks with an added 'rerank_score' field.
    """
    if not chunks:
        return []

    loop = asyncio.get_event_loop()

    def _do_rerank():
        reranker = _load_reranker()

        if reranker is not None:
            pairs = [[query, chunk["content"]] for chunk in chunks]
            try:
                scores = reranker.compute_score(pairs, normalize=True)
                if not isinstance(scores, list):
                    scores = [scores]
            except Exception:
                scores = [_cosine_similarity_score(query, c["content"]) for c in chunks]
        else:
            # Keyword fallback
            scores = [_cosine_similarity_score(query, c["content"]) for c in chunks]

        ranked = sorted(
            zip(chunks, scores),
            key=lambda x: x[1],
            reverse=True,
        )

        results = []
        for chunk, score in ranked[:top_n]:
            if score >= score_threshold:
                results.append({**chunk, "rerank_score": score})

        # If nothing passes threshold, return top-1 with warning
        if not results and ranked:
            top_chunk, top_score = ranked[0]
            results = [{**top_chunk, "rerank_score": top_score, "low_confidence": True}]

        return results

    return await loop.run_in_executor(None, _do_rerank)
