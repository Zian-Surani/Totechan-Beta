from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.config.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # File information
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # pdf, docx, html, txt
    file_size = Column(Integer, nullable=False)
    file_path = Column(String(500), nullable=False)
    mime_type = Column(String(100))

    # Processing status
    ingestion_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    chunk_count = Column(Integer, default=0)
    processing_error = Column(Text)

    # Content metadata
    title = Column(String(500))
    description = Column(Text)
    author = Column(String(255))
    created_date = Column(DateTime(timezone=True))
    language = Column(String(10), default="en")

    # Access control
    access_level = Column(String(50), default="private")  # public, private, restricted
    tags = Column(JSONB, default=[])
    categories = Column(JSONB, default=[])

    # Search and indexing
    is_indexed = Column(Boolean, default=False)
    search_vector = Column(JSONB)  # For full-text search
    metadata = Column(JSONB, default={})

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    indexed_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", back_populates="documents")

    def __repr__(self):
        return f"<Document(filename='{self.filename}', status='{self.ingestion_status}')>"


# Add relationship to User model
from app.models.user import User
User.documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")