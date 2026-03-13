"""
Query routes: single-document Q&A and streaming Q&A.
Orchestrates: hybrid retrieval → reranking → citation prompting → LLM.
"""
import asyncio
import json
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.models import User, Conversation, Message, Document
from api.dependencies.auth import get_current_user

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    question: str
    document_ids: list[str] = []
    conversation_id: Optional[str] = None
    use_web_search: bool = False
    model: Optional[str] = None  # e.g. "qwen2.5:3b", "phi3:mini"


class QueryResponse(BaseModel):
    answer: str
    citations: list[dict]
    conversation_id: str
    message_id: str
    cached: bool = False
    latency_ms: float = 0


# ── Helpers ───────────────────────────────────────────────────────────────────
async def _get_or_create_conversation(
    user: User,
    conversation_id: Optional[str],
    db: AsyncSession,
) -> Conversation:
    if conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user.id,
            )
        )
        conv = result.scalar_one_or_none()
        if conv:
            return conv

    # Create new conversation
    conv = Conversation(user_id=user.id, title="New Conversation")
    db.add(conv)
    await db.flush()
    return conv


# ── Standard Q&A ─────────────────────────────────────────────────────────────
@router.post("/", response_model=QueryResponse)
async def query(
    req: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from services.rag_chain import run_rag_pipeline

    start = time.monotonic()
    conv = await _get_or_create_conversation(current_user, req.conversation_id, db)

    # Save user message
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=req.question,
    )
    db.add(user_msg)
    await db.flush()

    # Run RAG
    result = await run_rag_pipeline(
        question=req.question,
        document_ids=req.document_ids,
        user_id=current_user.id,
        use_web_search=req.use_web_search,
        model=req.model,
    )

    latency = (time.monotonic() - start) * 1000

    # Save assistant message
    assistant_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=result["answer"],
        citations=result["citations"],
        latency_ms=latency,
    )
    db.add(assistant_msg)
    await db.flush()

    return QueryResponse(
        answer=result["answer"],
        citations=result["citations"],
        conversation_id=conv.id,
        message_id=assistant_msg.id,
        cached=result.get("cached", False),
        latency_ms=latency,
    )


# ── Streaming Q&A ─────────────────────────────────────────────────────────────
@router.post("/stream")
async def query_stream(
    req: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Streams the LLM response token-by-token via Server-Sent Events.
    Yields: data: {"token": "..."}\n\n
    Final: data: {"done": true, "citations": [...]}\n\n
    """
    from services.rag_chain import run_rag_pipeline_stream

    conv = await _get_or_create_conversation(current_user, req.conversation_id, db)
    conv_id = conv.id

    async def event_stream():
        full_answer = []
        citations = []
        try:
            async for chunk in run_rag_pipeline_stream(
                question=req.question,
                document_ids=req.document_ids,
                user_id=current_user.id,
                use_web_search=req.use_web_search,
                model=req.model,
            ):
                if chunk.get("type") == "stage":
                    yield f"data: {json.dumps({'stage': chunk['content']})}\n\n"
                elif chunk.get("type") == "token":
                    full_answer.append(chunk["content"])
                    yield f"data: {json.dumps({'token': chunk['content']})}\n\n"
                elif chunk.get("type") == "citations":
                    citations = chunk["content"]

            # Persist after streaming
            from core.database import AsyncSessionLocal
            from services.rag_chain import extract_citations
            answer_text = "".join(full_answer)

            async with AsyncSessionLocal() as save_db:
                asst_msg = Message(
                    conversation_id=conv_id,
                    role="assistant",
                    content=answer_text,
                    citations=citations,
                )
                save_db.add(asst_msg)
                await save_db.commit()

            yield f"data: {json.dumps({'done': True, 'citations': citations, 'conversation_id': conv_id})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── History ───────────────────────────────────────────────────────────────────
@router.get("/conversations")
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id, Conversation.is_archived == False)
        .order_by(Conversation.updated_at.desc())
    )
    return result.scalars().all()


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    return msg_result.scalars().all()
