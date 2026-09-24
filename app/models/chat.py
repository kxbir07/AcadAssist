"""Conversation and ChatMessage models for user assistant history."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.database.base import Base


def generate_uuid() -> str:
    """Generate a standard UUID4 string."""
    return str(uuid.uuid4())


class Conversation(Base):
    """Conversation session belonging to an authenticated user."""

    __tablename__ = "conversations"
    __table_args__ = {"extend_existing": True}

    conversation_id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False, default="Study Session")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")


class ChatMessage(Base):
    """Individual chat message within a Conversation."""

    __tablename__ = "chat_messages"
    __table_args__ = {"extend_existing": True}

    message_id = Column(String(36), primary_key=True, default=generate_uuid)
    conversation_id = Column(
        String(36), ForeignKey("conversations.conversation_id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(String(64), nullable=False, index=True)
    role = Column(String(32), nullable=False)  # "user" or "assistant"
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    conversation = relationship("Conversation", back_populates="messages")


__all__ = ["Conversation", "ChatMessage"]
