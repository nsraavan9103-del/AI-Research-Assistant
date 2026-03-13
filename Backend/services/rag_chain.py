"""
RAG chain: citation-aware prompting + LangChain streaming.

Pipeline:
  1. Hybrid search (FAISS + BM25 + RRF)
  2. BGE reranker
  3. Citation-annotated context block
  4. Ollama LLM (streaming or blocking)
  5. Citation extractor
"""
import re
from typing import AsyncIterator, Optional

from core.config import settings

# ── Citation prompt ───────────────────────────────────────────────────────────
CITATION_SYSTEM_PROMPT = """\
You are a precise research assistant. You MUST follow these rules absolutely:

1. ONLY use information from the provided context chunks below.
2. After EVERY factual claim, add a citation in the format [Source: {{doc_title}}, p.{{page}}].
3. If the context does not contain enough information, respond EXACTLY:
   "I cannot find sufficient information in the provided documents to answer this question."
4. Do NOT use any prior knowledge beyond what is in the context.
5. Do NOT speculate or extrapolate beyond what the sources state.

Context:
{context}
"""

CITATION_PATTERN = re.compile(
    r"\[Source:\s*(?P<doc>[^,\]]+),\s*p\.(?P<page>\d+)\]"
)


def build_context_block(chunks: list[dict]) -> str:
    """Format retrieved chunks into a numbered context block."""
    blocks = []
    for i, chunk in enumerate(chunks):
        meta = chunk.get("metadata") or {}
        page = meta.get("page_num", "N/A")
        filename = meta.get("filename", "document")
        blocks.append(
            f"[CHUNK {i+1}] Source: {filename}, Page: {page}\n{chunk['content']}"
        )
    return "\n\n---\n\n".join(blocks)


def extract_citations(response: str) -> list[dict]:
    """Parse [Source: ..., p.N] patterns from LLM response."""
    return [
        {"document": m.group("doc").strip(), "page": int(m.group("page"))}
        for m in CITATION_PATTERN.finditer(response)
    ]


def _get_llm(streaming: bool = False):
    """Get Ollama LLM instance."""
    from langchain_ollama import OllamaLLM
    return OllamaLLM(
        model=settings.LLM_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        streaming=streaming,
    )


# ── Standard (blocking) pipeline ──────────────────────────────────────────────
async def run_rag_pipeline(
    question: str,
    document_ids: Optional[list[str]] = None,
    user_id: Optional[str] = None,
    use_web_search: bool = False,
) -> dict:
    """
    Full RAG pipeline (non-streaming).

    Returns:
        {answer, citations, cached: bool}
    """
    import asyncio
    from services.retrieval.hybrid import hybrid_search
    from services.retrieval.reranker import rerank

    # 1. Hybrid retrieval
    raw_chunks = await hybrid_search(question, document_ids=document_ids)

    # 2. Web search supplement (if enabled and no chunks found)
    if use_web_search and len(raw_chunks) == 0:
        try:
            from services.web_search import web_search
            web_results = await web_search(question)
            for i, r in enumerate(web_results):
                raw_chunks.append({
                    "chunk_id": f"web_{i}",
                    "content": r["content"],
                    "metadata": {"filename": r.get("url", "web"), "page_num": 1},
                    "score": 0.5,
                })
        except Exception:
            pass

    # 3. Rerank
    reranked = await rerank(question, raw_chunks, top_n=5)

    # 4. Build context
    if not reranked:
        return {
            "answer": "I cannot find sufficient information in the provided documents to answer this question.",
            "citations": [],
            "cached": False,
        }

    context = build_context_block(reranked)
    prompt_text = (
        CITATION_SYSTEM_PROMPT.format(context=context)
        + f"\n\nQuestion: {question}\n\nAnswer:"
    )

    # 5. LLM
    try:
        llm = _get_llm(streaming=False)
        loop = asyncio.get_event_loop()
        answer = await loop.run_in_executor(None, llm.invoke, prompt_text)
    except Exception as e:
        answer = f"LLM error: {str(e)}. Please ensure Ollama is running with the `{settings.LLM_MODEL}` model."

    citations = extract_citations(str(answer))
    return {"answer": str(answer), "citations": citations, "cached": False}


# ── Streaming pipeline ────────────────────────────────────────────────────────
async def run_rag_pipeline_stream(
    question: str,
    document_ids: Optional[list[str]] = None,
    user_id: Optional[str] = None,
    use_web_search: bool = False,
) -> AsyncIterator[dict]:
    """
    Streaming RAG pipeline — yields:
      {"type": "stage", "content": "Searching documents..."}
      {"type": "token", "content": "<token>"}
      {"type": "citations", "content": [...]}
    """
    from services.retrieval.hybrid import hybrid_search
    from services.retrieval.reranker import rerank

    context = ""
    reranked = None
    if document_ids:
        yield {"type": "stage", "content": "Searching documents..."}
        raw_chunks = await hybrid_search(question, document_ids=document_ids)
    
        yield {"type": "stage", "content": "Reranking results..."}
        reranked = await rerank(question, raw_chunks, top_n=5)
    
        if reranked:
            context = build_context_block(reranked)

    if use_web_search and not context:
        yield {"type": "stage", "content": "Searching web..."}
        from services.web_search import web_search
        web_results = await web_search(question)
        if web_results:
            context = "\n\n".join(
                f"[WEB SOURCE: {r['url']}]\n{r['title']}\n{r['content']}"
                for r in web_results
            )

    if context:
        prompt_text = (
            CITATION_SYSTEM_PROMPT.format(context=context)
            + f"\n\nQuestion: {question}\n\nAnswer:"
        )
    else:
        prompt_text = f"You are a helpful AI assistant. Answer the following question: {question}"

    yield {"type": "stage", "content": "Synthesizing answer..."}

    try:
        llm = _get_llm(streaming=True)
        full_response = []

        # Stream from Ollama
        import asyncio
        loop = asyncio.get_event_loop()

        def _stream_sync():
            tokens = []
            for chunk in llm.stream(prompt_text):
                tokens.append(chunk)
            return tokens

        all_tokens = await loop.run_in_executor(None, _stream_sync)
        for token in all_tokens:
            full_response.append(str(token))
            yield {"type": "token", "content": str(token)}

        full_text = "".join(full_response)
        citations = extract_citations(full_text)
        yield {"type": "citations", "content": citations}

    except Exception as e:
        yield {"type": "token", "content": f"LLM error: {str(e)}. Please ensure Ollama is running."}
        yield {"type": "citations", "content": []}
