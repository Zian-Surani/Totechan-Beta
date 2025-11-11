from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FeedbackType(str, Enum):
    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"
    INAPPROPRIATE = "inappropriate"


class RetrievalConfig(BaseModel):
    k: int = Field(8, ge=1, le=50)
    rerank: bool = True
    filters: Optional[Dict[str, Any]] = None
    threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    hybrid_search: bool = False


class SourceCitation(BaseModel):
    document_id: uuid.UUID
    filename: str
    page_number: Optional[int]
    chunk_index: int
    chunk_text: str
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    url: Optional[str]
    snippet: str

    class Config:
        from_attributes = True


class ChatSessionBase(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None


class ChatSessionCreate(ChatSessionBase):
    pass


class ChatSessionUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ChatSessionResponse(ChatSessionBase):
    id: uuid.UUID
    user_id: uuid.UUID
    is_active: bool
    total_messages: int
    total_tokens_used: int
    created_at: datetime
    updated_at: datetime
    last_message_at: Optional[datetime]

    class Config:
        from_attributes = True


class MessageBase(BaseModel):
    content: str
    content_type: str = "text"


class MessageCreate(MessageBase):
    session_id: uuid.UUID
    retrieval_config: Optional[RetrievalConfig] = None


class MessageUpdate(BaseModel):
    feedback: Optional[FeedbackType] = None
    feedback_comment: Optional[str] = None


class MessageResponse(MessageBase):
    id: uuid.UUID
    session_id: uuid.UUID
    role: MessageRole
    sources: Optional[List[SourceCitation]]
    retrieval_config: Optional[RetrievalConfig]
    confidence_score: Optional[ConfidenceLevel]
    model_used: Optional[str]
    token_count: Optional[int]
    cost_estimate: Optional[str]
    feedback: Optional[FeedbackType]
    feedback_comment: Optional[str]
    status: MessageStatus
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[uuid.UUID] = None
    retrieval_config: Optional[RetrievalConfig] = None

    @validator('query')
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError('Query cannot be empty')
        return v.strip()


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceCitation]
    session_id: uuid.UUID
    message_id: uuid.UUID
    confidence_score: Optional[ConfidenceLevel]
    retrieval_config: RetrievalConfig
    usage: Dict[str, Any]
    model_used: str


class ChatHistoryResponse(BaseModel):
    session: ChatSessionResponse
    messages: List[MessageResponse]
    total: int


class SessionListResponse(BaseModel):
    sessions: List[ChatSessionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ChatStats(BaseModel):
    """Chat usage statistics"""
    total_sessions: int
    total_messages: int
    total_tokens_used: int
    average_messages_per_session: float
    total_cost_estimate: str


class WebSocketMessage(BaseModel):
    """WebSocket message schema"""
    type: str  # message, status, error, typing
    session_id: uuid.UUID
    data: Dict[str, Any]
    timestamp: datetime