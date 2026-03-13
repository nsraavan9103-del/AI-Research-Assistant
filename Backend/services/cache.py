"""
Redis semantic cache for LLM responses.
Key: embedding hash; Value: {embedding, response, citations}
TTL: 1 hour (configurable)

Falls back gracefully if Redis is unavailable.
"""
import hashlib
import json
from typing import Optional

import numpy as np

from core.config import settings

_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    if not settings.REDIS_ENABLED:
        return None
    try:
        import redis as redis_lib  # type: ignore
        _redis_client = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
        _redis_client.ping()
        return _redis_client
    except Exception:
        return None


def _cosine_similarity(a: list, b: list) -> float:
    va, vb = np.array(a), np.array(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


async def get_cached_response(
    query_embedding: list[float],
) -> Optional[dict]:
    """Check Redis for a semantically similar cached response."""
    redis = _get_redis()
    if redis is None:
        return None

    try:
        keys = redis.keys("llm_cache:*")
        for key in keys:
            raw = redis.get(key)
            if not raw:
                continue
            cached = json.loads(raw)
            sim = _cosine_similarity(query_embedding, cached["embedding"])
            if sim >= settings.LLM_CACHE_SIMILARITY:
                return cached["response"]
    except Exception:
        pass
    return None


async def set_cached_response(
    query_embedding: list[float],
    response: dict,
) -> None:
    """Store response in Redis with TTL."""
    redis = _get_redis()
    if redis is None:
        return

    try:
        cache_key = f"llm_cache:{hashlib.md5(str(query_embedding[:5]).encode()).hexdigest()}"
        redis.setex(
            cache_key,
            settings.LLM_CACHE_TTL,
            json.dumps({"embedding": query_embedding, "response": response}),
        )
    except Exception:
        pass
