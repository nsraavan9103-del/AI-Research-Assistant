"""
BM25 retrieval helper — wraps rank_bm25.
Used as the sparse retrieval component in the hybrid pipeline.
"""
from __future__ import annotations

from typing import Optional


class BM25Retriever:
    """Thin wrapper around BM25Okapi for document chunk retrieval."""

    def __init__(self, corpus: list[str], chunk_ids: list[str]):
        try:
            from rank_bm25 import BM25Okapi  # type: ignore
            self._tokenized = [doc.lower().split() for doc in corpus]
            self._bm25 = BM25Okapi(self._tokenized)
            self._chunk_ids = chunk_ids
            self._available = True
        except ImportError:
            self._available = False
            self._chunk_ids = chunk_ids

    def search(self, query: str, top_k: int = 50) -> list[tuple[str, float]]:
        """Returns [(chunk_id, score)] sorted desc by score."""
        if not self._available or not self._chunk_ids:
            return []

        import numpy as np
        tokenized_q = query.lower().split()
        scores = self._bm25.get_scores(tokenized_q)
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [
            (self._chunk_ids[i], float(scores[i]))
            for i in top_indices
            if i < len(self._chunk_ids) and scores[i] > 0
        ]

    def add(self, text: str, chunk_id: str) -> None:
        """Add a new document to the BM25 index (rebuilds)."""
        if not self._available:
            return
        from rank_bm25 import BM25Okapi
        self._tokenized.append(text.lower().split())
        self._chunk_ids.append(chunk_id)
        self._bm25 = BM25Okapi(self._tokenized)
