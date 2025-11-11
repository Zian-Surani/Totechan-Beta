import uuid
import os
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from pydantic import BaseModel
import structlog
from datetime import datetime

from app.config.database import get_db
from app.config.settings import settings
from app.models.user import User
from app.models.document import Document
from app.models.document_schemas import (
    DocumentType, IngestionStatus, DocumentResponse, DocumentUploadResponse,
    DocumentListResponse, DocumentSearchRequest, IngestionJob, DocumentProcessingStats
)
from app.services.document_processor import DocumentProcessor
from app.services.embeddings import EmbeddingService
from app.services.vectordb import VectorDBService
from app.utils.auth import get_current_active_user
from app.utils.exceptions import ValidationError, NotFoundError, DocumentProcessingError

logger = structlog.get_logger()
router = APIRouter()

# Global job tracking (in production, use Redis or database)
ingestion_jobs: Dict[str, Dict[str, Any]] = {}


class IngestionManager:
    """Manages document ingestion jobs"""

    def __init__(self):
        self.jobs = ingestion_jobs

    def create_job(self, document_id: uuid.UUID) -> str:
        """Create a new ingestion job"""
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {
            "id": job_id,
            "document_id": str(document_id),
            "status": IngestionStatus.PENDING,
            "progress": 0.0,
            "current_step": "Queued",
            "total_steps": 5,  # Upload -> Process -> Embed -> Index -> Complete
            "error_message": None,
            "started_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "completed_at": None
        }
        return job_id

    def update_job(self, job_id: str, **kwargs):
        """Update job status"""
        if job_id in self.jobs:
            self.jobs[job_id].update(kwargs)
            self.jobs[job_id]["updated_at"] = datetime.utcnow()

    def complete_job(self, job_id: str, success: bool = True, error_message: str = None):
        """Mark job as completed"""
        if job_id in self.jobs:
            self.jobs[job_id]["status"] = IngestionStatus.COMPLETED if success else IngestionStatus.FAILED
            self.jobs[job_id]["progress"] = 100.0 if success else self.jobs[job_id]["progress"]
            self.jobs[job_id]["completed_at"] = datetime.utcnow()
            if error_message:
                self.jobs[job_id]["error_message"] = error_message

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status"""
        return self.jobs.get(job_id)


ingestion_manager = IngestionManager()


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    access_level: str = Form("private"),
    tags: str = Form(""),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload and process a document"""
    try:
        # Validate file
        if not file.filename:
            raise ValidationError("No file provided")

        # Check file type
        file_extension = file.filename.lower().split('.')[-1]
        if file_extension not in ['pdf', 'docx', 'html', 'txt']:
            raise ValidationError("Unsupported file type. Supported types: PDF, DOCX, HTML, TXT")

        document_type = DocumentType(file_extension)

        # Check file size
        file_size = 0
        file_content = None
        content = await file.read()
        file_size = len(content)
        file_content = content

        max_size = 50 * 1024 * 1024  # 50MB
        if file_size > max_size:
            raise ValidationError(f"File too large. Maximum size is 50MB")

        # Generate unique filename
        file_id = str(uuid.uuid4())
        safe_filename = f"{file_id}_{file.filename}"
        file_path = os.path.join(settings.upload_dir, safe_filename)

        # Ensure upload directory exists
        os.makedirs(settings.upload_dir, exist_ok=True)

        # Save file
        with open(file_path, "wb") as f:
            f.write(file_content)

        # Create document record
        document = Document(
            user_id=current_user.id,
            filename=safe_filename,
            original_filename=file.filename,
            file_type=document_type,
            file_size=file_size,
            file_path=file_path,
            title=title or file.filename,
            description=description,
            access_level=access_level,
            tags=[tag.strip() for tag in tags.split(",") if tag.strip()] if tags else [],
            ingestion_status=IngestionStatus.PENDING
        )

        db.add(document)
        await db.commit()
        await db.refresh(document)

        # Create ingestion job
        job_id = ingestion_manager.create_job(document.id)

        # Start background processing
        background_tasks.add_task(
            process_document_background,
            str(document.id),
            job_id,
            str(current_user.id)
        )

        logger.info(
            "document_upload_started",
            document_id=str(document.id),
            filename=file.filename,
            user_id=str(current_user.id),
            job_id=job_id
        )

        return DocumentUploadResponse(
            message="Document uploaded successfully. Processing started.",
            document_id=document.id,
            ingestion_job_id=job_id,
            status=IngestionStatus.PENDING
        )

    except ValidationError:
        raise
    except Exception as e:
        logger.error("document_upload_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to upload document")


async def process_document_background(
    document_id: str,
    job_id: str,
    user_id: str
):
    """Background task to process document"""
    from app.config.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            # Get document
            stmt = select(Document).where(Document.id == document_id)
            result = await db.execute(stmt)
            document = result.scalar_one_or_none()

            if not document:
                ingestion_manager.complete_job(job_id, False, "Document not found")
                return

            # Update status to processing
            document.ingestion_status = IngestionStatus.PROCESSING
            await db.commit()
            ingestion_manager.update_job(
                job_id,
                status=IngestionStatus.PROCESSING,
                progress=20.0,
                current_step="Processing document"
            )

            # Initialize services
            processor = DocumentProcessor()
            embedding_service = EmbeddingService()
            vector_db = VectorDBService()

            # Process document
            processing_result = await processor.process_document(
                document.file_path,
                document.file_type,
                {
                    "doc_id": str(document.id),
                    "filename": document.original_filename,
                    "file_type": document.file_type.value,
                    "user_id": user_id,
                    "created_at": document.created_at.isoformat()
                }
            )

            ingestion_manager.update_job(
                job_id,
                progress=40.0,
                current_step="Generating embeddings"
            )

            # Generate embeddings
            chunks_with_embeddings = await embedding_service.create_embeddings_with_metadata(
                processing_result["chunks"]
            )

            ingestion_manager.update_job(
                job_id,
                progress=60.0,
                current_step="Storing in vector database"
            )

            # Prepare vectors for Pinecone
            vectors = []
            for chunk in chunks_with_embeddings:
                vector_id = f"{document.id}_{chunk['metadata']['chunk_index']}"
                vector_data = {
                    "id": vector_id,
                    "embedding": chunk["embedding"],
                    "metadata": {
                        **chunk["metadata"],
                        "doc_id": str(document.id),
                        "user_id": user_id
                    }
                }
                vectors.append(vector_data)

            # Store in vector database
            if vectors:
                vector_result = await vector_db.upsert_vectors(vectors)
                logger.info(
                    "vectors_stored",
                    document_id=document_id,
                    vectors_stored=vector_result["upserted_count"]
                )

            ingestion_manager.update_job(
                job_id,
                progress=80.0,
                current_step="Finalizing"
            )

            # Update document record
            document.ingestion_status = IngestionStatus.COMPLETED
            document.chunk_count = len(chunks_with_embeddings)
            document.is_indexed = True
            document.indexed_at = datetime.utcnow()

            # Update metadata
            document.metadata.update({
                "processing_stats": {
                    "total_chars": processing_result.get("total_chars", 0),
                    "chunk_count": len(chunks_with_embeddings),
                    "pages": processing_result.get("pages", []),
                    "processing_time": datetime.utcnow().isoformat()
                }
            })

            await db.commit()

            # Complete job
            ingestion_manager.complete_job(job_id, True)

            logger.info(
                "document_processing_completed",
                document_id=document_id,
                chunk_count=len(chunks_with_embeddings),
                job_id=job_id
            )

        except Exception as e:
            logger.error(
                "document_processing_failed",
                document_id=document_id,
                job_id=job_id,
                error=str(e)
            )

            # Update document status
            if document:
                document.ingestion_status = IngestionStatus.FAILED
                document.processing_error = str(e)
                await db.commit()

            # Fail job
            ingestion_manager.complete_job(job_id, False, str(e))


@router.get("/status/{job_id}")
async def get_ingestion_status(
    job_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get status of document ingestion job"""
    try:
        job = ingestion_manager.get_job(job_id)
        if not job:
            raise NotFoundError("Job not found")

        # Convert to response model
        return IngestionJob(**job)

    except NotFoundError:
        raise HTTPException(status_code=404, detail="Job not found")
    except Exception as e:
        logger.error("ingestion_status_check_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get job status")


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    page: int = 1,
    page_size: int = 20,
    file_type: Optional[DocumentType] = None,
    status: Optional[IngestionStatus] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's documents with filtering and pagination"""
    try:
        # Build query
        conditions = [Document.user_id == current_user.id]

        if file_type:
            conditions.append(Document.file_type == file_type)
        if status:
            conditions.append(Document.ingestion_status == status)
        if search:
            conditions.append(
                Document.title.ilike(f"%{search}%") |
                Document.original_filename.ilike(f"%{search}%")
            )

        # Get total count
        count_stmt = select(func.count(Document.id)).where(and_(*conditions))
        total_result = await db.execute(count_stmt)
        total = total_result.scalar()

        # Get documents
        offset = (page - 1) * page_size
        stmt = (
            select(Document)
            .where(and_(*conditions))
            .order_by(Document.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        documents = result.scalars().all()

        total_pages = (total + page_size - 1) // page_size

        return DocumentListResponse(
            documents=documents,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except Exception as e:
        logger.error("document_listing_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list documents")


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific document"""
    try:
        stmt = select(Document).where(
            and_(
                Document.id == document_id,
                Document.user_id == current_user.id
            )
        )
        result = await db.execute(stmt)
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        return document

    except HTTPException:
        raise
    except Exception as e:
        logger.error("document_retrieval_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve document")


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a document and its associated vectors"""
    try:
        # Get document
        stmt = select(Document).where(
            and_(
                Document.id == document_id,
                Document.user_id == current_user.id
            )
        )
        result = await db.execute(stmt)
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Delete vectors from Pinecone
        try:
            vector_db = VectorDBService()
            await vector_db.delete_vectors(
                filter_dict={
                    "doc_id": document_id,
                    "user_id": str(current_user.id)
                }
            )
            logger.info("document_vectors_deleted", document_id=document_id)
        except Exception as e:
            logger.warning("vector_deletion_failed", document_id=document_id, error=str(e))

        # Delete file from filesystem
        try:
            if os.path.exists(document.file_path):
                os.remove(document.file_path)
                logger.info("document_file_deleted", file_path=document.file_path)
        except Exception as e:
            logger.warning("file_deletion_failed", file_path=document.file_path, error=str(e))

        # Delete document record
        await db.delete(document)
        await db.commit()

        logger.info("document_deleted", document_id=document_id)
        return {"message": "Document deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("document_deletion_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete document")


@router.get("/stats")
async def get_ingestion_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get document ingestion statistics"""
    try:
        # Get document counts by status
        status_counts = {}
        for status in IngestionStatus:
            stmt = select(func.count(Document.id)).where(
                and_(
                    Document.user_id == current_user.id,
                    Document.ingestion_status == status
                )
            )
            result = await db.execute(stmt)
            status_counts[status.value] = result.scalar() or 0

        # Get total documents and size
        total_stmt = select(func.count(Document.id)).where(Document.user_id == current_user.id)
        total_result = await db.execute(total_stmt)
        total_documents = total_result.scalar() or 0

        size_stmt = select(func.coalesce(func.sum(Document.file_size), 0)).where(Document.user_id == current_user.id)
        size_result = await db.execute(size_stmt)
        total_size = size_result.scalar() or 0

        # Get total chunks
        chunks_stmt = select(func.coalesce(func.sum(Document.chunk_count), 0)).where(Document.user_id == current_user.id)
        chunks_result = await db.execute(chunks_stmt)
        total_chunks = chunks_result.scalar() or 0

        return DocumentProcessingStats(
            total_documents=total_documents,
            pending_documents=status_counts.get("pending", 0),
            processing_documents=status_counts.get("processing", 0),
            completed_documents=status_counts.get("completed", 0),
            failed_documents=status_counts.get("failed", 0),
            total_chunks=total_chunks,
            total_size_mb=round(total_size / (1024 * 1024), 2)
        )

    except Exception as e:
        logger.error("ingestion_stats_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get statistics")


@router.post("/reprocess/{document_id}")
async def reprocess_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Reprocess a document"""
    try:
        # Get document
        stmt = select(Document).where(
            and_(
                Document.id == document_id,
                Document.user_id == current_user.id
            )
        )
        result = await db.execute(stmt)
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Reset document status
        document.ingestion_status = IngestionStatus.PENDING
        document.processing_error = None
        await db.commit()

        # Create new ingestion job
        job_id = ingestion_manager.create_job(document.id)

        # Start background processing
        background_tasks.add_task(
            process_document_background,
            str(document.id),
            job_id,
            str(current_user.id)
        )

        logger.info("document_reprocess_started", document_id=document_id, job_id=job_id)

        return {
            "message": "Document reprocessing started",
            "job_id": job_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("document_reprocess_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to start reprocessing")


@router.get("/")
async def health_check():
    """Ingest router health check"""
    logger.info("ingest_router_health_check")
    return {"status": "healthy", "service": "ingest router"}