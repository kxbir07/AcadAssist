"""API routes for assistant chat history."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.chat import ChatMessage, Conversation
from app.models.shared import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.azure.agent import AcadAssistAgentService

router = APIRouter(prefix="/chat", tags=["Assistant Chat"])


class ChatMessageRequest(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    text: str = Field(..., min_length=1)
    conversation_id: Optional[str] = None


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    text: str
    time: str


@router.get("/history", response_model=List[ChatMessageResponse])
def get_chat_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve chat history belonging strictly to the authenticated user."""
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == current_user.user_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return [
        ChatMessageResponse(
            id=m.message_id,
            role=m.role,
            text=m.text,
            time=m.created_at.strftime("%I:%M %p") if m.created_at else "",
        )
        for m in messages
    ]


@router.post("/message", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
def append_chat_message(
    payload: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Persist an assistant or user message scoped to the current user."""
    # Ensure active conversation exists
    conv = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.user_id)
        .order_by(Conversation.updated_at.desc())
        .first()
    )
    if not conv:
        conv = Conversation(user_id=current_user.user_id, title="Study Session")
        db.add(conv)
        db.commit()
        db.refresh(conv)

    msg = ChatMessage(
        conversation_id=conv.conversation_id,
        user_id=current_user.user_id,
        role=payload.role,
        text=payload.text,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    return ChatMessageResponse(
        id=msg.message_id,
        role=msg.role,
        text=msg.text,
        time=msg.created_at.strftime("%I:%M %p") if msg.created_at else "",
    )


@router.delete("/history")
def clear_chat_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Clear all chat messages belonging to the current user."""
    db.query(ChatMessage).filter(ChatMessage.user_id == current_user.user_id).delete()
    db.query(Conversation).filter(Conversation.user_id == current_user.user_id).delete()
    db.commit()
    return {"status": "success", "message": "Chat history cleared."}


@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK, operation_id="chat_endpoint_api_chat_post")
@router.post("/", response_model=ChatResponse, status_code=status.HTTP_200_OK, include_in_schema=False)
def chat_endpoint(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    """Process student query through AcadAssist Agent with zero-trust identity and message persistence."""
    clean_message = request.message.strip()
    if not clean_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The 'message' field must not be empty.",
        )

    # Legacy client compatibility: if user_id is sent, it MUST match authenticated user
    if request.user_id is not None:
        clean_user_id = request.user_id.strip()
        if not clean_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The 'user_id' field must not be empty.",
            )
        if clean_user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Cannot execute chat as another user",
            )

    authoritative_user_id = current_user.user_id

    # Execute agent
    agent_service = AcadAssistAgentService()
    response = agent_service.chat(
        user_id=authoritative_user_id,
        message=clean_message,
        document_id=request.document_id,
        course_id=request.course_id,
        subject_id=request.subject_id,
        db=db,
    )

    # Persist message history
    conv = (
        db.query(Conversation)
        .filter(Conversation.user_id == authoritative_user_id)
        .order_by(Conversation.updated_at.desc())
        .first()
    )
    if not conv:
        conv = Conversation(user_id=authoritative_user_id, title="Study Session")
        db.add(conv)
        db.commit()
        db.refresh(conv)

    user_msg = ChatMessage(
        conversation_id=conv.conversation_id,
        user_id=authoritative_user_id,
        role="user",
        text=clean_message,
    )
    asst_msg = ChatMessage(
        conversation_id=conv.conversation_id,
        user_id=authoritative_user_id,
        role="assistant",
        text=response.message,
    )
    db.add(user_msg)
    db.add(asst_msg)
    db.commit()

    return response


__all__ = ["router"]
