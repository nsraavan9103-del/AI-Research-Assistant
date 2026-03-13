"""
Web search integration: Tavily (primary) → DuckDuckGo (fallback).
Only called when:
  - Retrieval returns 0 results above threshold, OR
  - User explicitly enables web search toggle.
"""
import asyncio
from typing import Optional

from core.config import settings


async def web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the web. Returns [{title, url, content}].
    Falls back to DuckDuckGo if Tavily fails or API key not set.
    """
    loop = asyncio.get_event_loop()

    if settings.TAVILY_API_KEY:
        try:
            result = await loop.run_in_executor(None, _tavily_search, query, max_results)
            if result:
                return result
        except Exception:
            pass

    # DuckDuckGo fallback (no API key required)
    try:
        return await loop.run_in_executor(None, _ddg_search, query, max_results)
    except Exception:
        return []


def _tavily_search(query: str, max_results: int) -> list[dict]:
    from tavily import TavilyClient  # type: ignore
    client = TavilyClient(api_key=settings.TAVILY_API_KEY)
    results = client.search(query, max_results=max_results)
    return [
        {"title": r["title"], "url": r["url"], "content": r["content"]}
        for r in results.get("results", [])
    ]


def _ddg_search(query: str, max_results: int) -> list[dict]:
    from duckduckgo_search import DDGS  # type: ignore
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "content": r.get("body", ""),
            }
            for r in results
        ]
