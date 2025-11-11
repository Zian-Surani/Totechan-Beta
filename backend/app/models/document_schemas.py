from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from enum import Enum


class DocumentType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    TXT = "txt"


class IngestionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AccessLevel(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    RESTRICTED = "restricted"


class DocumentBase(BaseModel):
    filename: str = Field(..., max_length=255)
    original_filename: str = Field(..., max_length=255)
    file_type: DocumentType
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    author: Optional[str] = Field(None, max_length=255)
    access_level: AccessLevel = AccessLevel.PRIVATE
    tags: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    language: str = "en"


class DocumentCreate(DocumentBase):
    file_size: int
    file_path: str


class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    access_level: Optional[AccessLevel] = None
    tags: Optional[List[str]] = None
    categories: Optional[List[str]] = None


class DocumentResponse(DocumentBase):
    id: uuid.UUID
    user_id: uuid.UUID
    file_size: int
    file_path: str
    mime_type: Optional[str]
    ingestion_status: IngestionStatus
    chunk_count: int
    processing_error: Optional[str]
    created_date: Optional[datetime]
    is_indexed: bool
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    indexed_at: Optional[datetime]

    class Config:
        from_attributes = True


class DocumentUploadResponse(BaseModel):
    message: str
    document_id: uuid.UUID
    ingestion_job_id: uuid.UUID
    status: IngestionStatus


class IngestionJob(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    status: IngestionStatus
    progress: float = Field(0.0, ge=0.0, le=100.0)
    current_step: str
    total_steps: int
    error_message: Optional[str]
    started_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DocumentSearchRequest(BaseModel):
    query: Optional[str] = None
    file_types: Optional[List[DocumentType]] = None
    access_levels: Optional[List[AccessLevel]] = None
    tags: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)

    @validator('query')
    def validate_query(cls, v):
        if v and len(v.strip()) == 0:
            return None
        return v.strip() if v else None


class DocumentChunk(BaseModel):
    """Schema for individual document chunks"""
    id: str
    document_id: uuid.UUID
    chunk_index: int
    text: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None

    class Config:
        from_attributes = True


class DocumentProcessingStats(BaseModel):
    """Statistics about document processing"""
    total_documents: int
    pending_documents: int
    processing_documents: int
    completed_documents: int
    failed_documents: int
    total_chunks: int
    total_size_mb: float