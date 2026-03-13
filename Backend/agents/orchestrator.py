"""
Multi-agent orchestrator using LangChain tools.

Agents:
  - research_tool:    Hybrid RAG retrieval + synthesis
  - web_search_tool:  Tavily / DuckDuckGo (when gaps found)
  - fact_check_tool:  Cross-reference claims via reranker

All agent steps stored in MESSAGES.agent_trace as JSONB.
"""
import asyncio
from typing import Optional


def _get_llm():
    from langchain_ollama import OllamaLLM
    from core.config import settings
    return OllamaLLM(
        model=settings.LLM_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
    )


# ── Tool definitions ──────────────────────────────────────────────────────────
async def _research_tool_fn(query: str, document_ids: list[str]) -> str:
    from services.retrieval.hybrid import hybrid_search
    from services.retrieval.reranker import rerank
    from services.rag_chain import build_context_block

    if not document_ids and not query:
        return "No documents provided to research."
        
    chunks = await hybrid_search(query, document_ids=document_ids)
    if not chunks:
        return "No relevant content found."
        
    reranked = await rerank(query, chunks, top_n=5)
    if not reranked:
        return "No relevant content found."
    return build_context_block(reranked)


async def _web_search_tool_fn(query: str) -> str:
    try:
        from services.web_search import web_search
        results = await web_search(query, max_results=5)
        return "\n\n".join(
            f"[WEB SOURCE: {r['url']}]\n{r['title']}\n{r['content']}"
            for r in results
        )
    except Exception as e:
        return f"Web search unavailable: {e}"


async def _fact_check_tool_fn(claim: str, context: str) -> dict:
    """Score how well the context supports the claim."""
    from services.retrieval.reranker import _cosine_similarity_score
    score = _cosine_similarity_score(claim, context)
    return {
        "claim": claim,
        "support_score": round(score, 3),
        "verdict": "supported" if score > 0.3 else "insufficient evidence",
    }


# ── Multi-doc synthesis ───────────────────────────────────────────────────────
MULTI_DOC_PROMPT = """\
You are analyzing {n} research documents simultaneously.

Documents:
{document_summaries}

Task: Provide a structured synthesis covering:
1. CONSENSUS: Points all documents agree on
2. CONTRADICTIONS: Claims where documents disagree (cite both positions)
3. UNIQUE INSIGHTS: Important points found in only one document
4. GAPS: Questions raised but not answered by any document

Format each point as: [CLAIM] → [Source 1: agree/disagree] [Source 2: agree/disagree]
"""


async def run_research_agent(
    query: str,
    document_ids: list[str],
    mode: str = "standard",
    use_web_search: bool = False,
) -> dict:
    """
    Run multi-agent research pipeline.

    Returns:
        {answer, citations, agent_trace: [{step, tool, input, output}]}
    """
    agent_trace = []

    # Step 1: Research tool if documents are selected
    context = ""
    if document_ids:
        agent_trace.append({"step": 1, "tool": "research_tool", "input": query})
        context = await _research_tool_fn(query, document_ids)
        agent_trace[-1]["output"] = context[:500] + "..."
    else:
        context = "No internal research documents provided."

    # Step 2: Web search if no content
    if "No relevant content" in context and use_web_search:
        agent_trace.append({"step": 2, "tool": "web_search_tool", "input": query})
        web_context = await _web_search_tool_fn(query)
        context = context + "\n\n" + web_context
        agent_trace[-1]["output"] = web_context[:500] + "..."

    # Step 3: LLM synthesis
    from services.rag_chain import CITATION_SYSTEM_PROMPT, extract_citations
    import asyncio

    if mode == "multi_doc" and len(document_ids) > 1:
        # Get document summaries for multi-doc mode
        summaries = []
        for i, doc_id in enumerate(document_ids[:5]):
            doc_context = await _research_tool_fn(f"Summarize this document", [doc_id])
            summaries.append(f"Document {i+1} (ID: {doc_id[:8]}...):\n{doc_context[:300]}")

        prompt = MULTI_DOC_PROMPT.format(
            n=len(document_ids),
            document_summaries="\n\n".join(summaries),
        ) + f"\n\nSpecific question: {query}"
    else:
        if "No internal research documents provided" in context and not use_web_search:
            # Fallback to general LLM chat
            prompt = f"You are a helpful AI assistant. Answer the following question: {query}"
        else:
            prompt = (
                CITATION_SYSTEM_PROMPT.format(context=context)
                + f"\n\nQuestion: {query}\n\nAnswer:"
            )

    try:
        llm = _get_llm()
        loop = asyncio.get_event_loop()
        answer = await loop.run_in_executor(None, llm.invoke, prompt)
        agent_trace.append({"step": 3, "tool": "llm_synthesis", "output": str(answer)[:200]})
    except Exception as e:
        answer = f"Agent LLM error: {e}"
        agent_trace.append({"step": 3, "tool": "llm_synthesis", "error": str(e)})

    citations = extract_citations(str(answer))

    return {
        "answer": str(answer),
        "citations": citations,
        "agent_trace": agent_trace,
        "mode": mode,
    }
