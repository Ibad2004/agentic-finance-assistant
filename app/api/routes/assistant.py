"""AI Financial Assistant chat endpoint."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.config import Settings, get_settings
from app.db.models import User
from app.services.groq_chat_llm import GroqChatLlm

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["AI Assistant"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    response: str


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Chat with the AI Financial Assistant",
)
def chat(
    payload: ChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChatResponse:
    """Send a message to the AI Financial Assistant and receive a response.

    The assistant uses the FinancialAssistant agent which:
    1. Gathers verified financial data from the database (deterministic)
    2. Passes verified context to the LLM (AI reasoning)
    3. Returns a natural language response grounded in real data

    All financial numbers come from backend calculations, never from the LLM.
    This is an estimation tool, not an official financial advisor.
    """
    try:
        llm = GroqChatLlm(settings)
    except RuntimeError as exc:
        logger.error("LLM provider not configured: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI assistant is not configured. Please contact the administrator.",
        ) from exc

    from app.agents.financial_assistant import FinancialAssistant

    assistant = FinancialAssistant(session=db, llm=llm)

    try:
        response_text = assistant.chat(
            user_id=current_user.id,
            user_name=current_user.full_name or current_user.email,
            message=payload.message,
        )
    except Exception as exc:
        logger.error("LLM call failed for assistant chat: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI assistant is temporarily unavailable. Please try again later.",
        ) from exc

    return ChatResponse(response=response_text)
