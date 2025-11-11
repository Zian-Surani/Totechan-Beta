from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.config.database import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Session information
    title = Column(String(255))
    description = Column(Text)
    is_active = Column(Boolean, default=True)

    # Session metadata
    session_metadata = Column(JSONB, default={})
    total_messages = Column(Integer, default=0)
    total_tokens_used = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_message_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ChatSession(id='{self.id}', title='{self.title}', messages={self.total_messages})>"


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False, index=True)

    # Message content
    role = Column(String(50), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    content_type = Column(String(50), default="text")  # text, markdown, json

    # RAG-specific information
    sources = Column(JSONB)  # Array of source citations
    retrieval_config = Column(JSONB)  # Retrieval parameters used
    retrieval_results = Column(JSONB)  # Raw retrieval results
    confidence_score = Column(String(10))  # High, Medium, Low

    # LLM information
    model_used = Column(String(100))
    token_count = Column(Integer)
    cost_estimate = Column(String(50))  # Estimated cost in USD

    # User feedback
    feedback = Column(String(20))  # helpful, not_helpful, inappropriate
    feedback_comment = Column(Text)

    # Message status
    status = Column(String(50), default="completed")  # pending, completed, failed
    error_message = Column(Text)

    # Metadata
    metadata = Column(JSONB, default={})

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    session = relationship("ChatSession", back_populates="messages")

    def __repr__(self):
        return f"<Message(role='{self.role}', tokens={self.token_count})>"


# Add relationships to User model
from app.models.user import User
User.chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")