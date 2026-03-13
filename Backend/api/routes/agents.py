"""
Agents route: /agents/research — multi-doc research mode.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from core.database import get_db
from core.models import User, Message, Conversation
from api.dependencies.auth import get_current_user

router = APIRouter(prefix="/agents", tags=["agents"])


class ResearchRequest(BaseModel):
    query: str
    document_ids: list[str] = []
    conversation_id: Optional[str] = None
    mode: str = "standard"          # "standard" | "research" | "multi_doc"
    use_web_search: bool = False


@router.post("/research")
async def research(
    req: ResearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from agents.orchestrator import run_research_agent
    from sqlalchemy import select

    # Get or create conversation
    conv = None
    if req.conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == req.conversation_id,
                Conversation.user_id == current_user.id,
            )
        )
        conv = result.scalar_one_or_none()

    if not conv:
        conv = Conversation(
            user_id=current_user.id,
            title=f"Research: {req.query[:50]}",
            mode=req.mode,
        )
        db.add(conv)
        await db.flush()

    # Run research agent
    result = await run_research_agent(
        query=req.query,
        document_ids=req.document_ids,
        mode=req.mode,
        use_web_search=req.use_web_search,
    )

    # Save user message
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=req.query,
    )
    db.add(user_msg)

    # Save assistant message with agent trace
    assistant_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=result["answer"],
        citations=result["citations"],
        agent_trace=result["agent_trace"],
    )
    db.add(assistant_msg)
    await db.flush()

    return {
        "answer": result["answer"],
        "citations": result["citations"],
        "agent_trace": result["agent_trace"],
        "conversation_id": conv.id,
        "message_id": assistant_msg.id,
        "mode": result["mode"],
    }
