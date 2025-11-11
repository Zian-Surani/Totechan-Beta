from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import List, Dict, Any, Optional
import uuid
import json
import asyncio
import structlog
from datetime import datetime

from app.config.database import get_db
from app.models.user import User
from app.models.chat import ChatSession, Message
from app.models.chat_schemas import (
    ChatQuery, ChatResponse, ChatSessionCreate, ChatSessionUpdate,
    ChatSessionResponse, MessageResponse, ChatHistoryResponse,
    SessionListResponse, RetrievalConfig, MessageUpdate, WebSocketMessage
)
from app.services.retrieval import RetrievalService
from app.services.llm_client import LLMClient
from app.utils.auth import get_current_active_user
from app.utils.exceptions import ValidationError, NotFoundError

logger = structlog.get_logger()
router = APIRouter()

# Global WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_text(json.dumps(message))

manager = ConnectionManager()


@router.post("/ask", response_model=ChatResponse)
async def ask_question(
    query: ChatQuery,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Ask a question with RAG retrieval and LLM generation"""
    try:
        # Validate query
        if not query.query.strip():
            raise ValidationError("Query cannot be empty")

        logger.info(
            "chat_query_started",
            user_id=str(current_user.id),
            query=query.query[:100],
            session_id=str(query.session_id) if query.session_id else None
        )

        # Get or create session
        session = await _get_or_create_session(db, current_user.id, query.session_id)

        # Store user message
        user_message = Message(
            session_id=session.id,
            role="user",
            content=query.query,
            token_count=len(query.query.split()),
            status="completed"
        )
        db.add(user_message)
        await db.commit()

        # Initialize services
        retrieval_service = RetrievalService()
        llm_client = LLMClient()

        # Retrieve relevant chunks
        retrieval_config = query.retrieval_config or RetrievalConfig()
        source_citations = await retrieval_service.retrieve_relevant_chunks(
            query=query.query,
            user_id=str(current_user.id),
            config=retrieval_config
        )

        # Get conversation history
        history = await _get_conversation_history(db, session.id, limit=5)

        # Format context for LLM
        context = await retrieval_service.get_context_for_query(
            query=query.query,
            user_id=str(current_user.id),
            config=retrieval_config
        )

        # Generate LLM response
        llm_response = await llm_client.generate_with_sources(
            query=query.query,
            context_chunks=context["context_chunks"],
            conversation_history=history
        )

        # Store assistant message
        assistant_message = Message(
            session_id=session.id,
            role="assistant",
            content=llm_response["content"],
            sources=[source.dict() for source in llm_response.get("sources", [])],
            model_used=llm_response["model"],
            token_count=llm_response["usage"]["completion_tokens"],
            cost_estimate=llm_response["cost_estimate"],
            retrieval_config=retrieval_config.dict(),
            status="completed"
        )
        db.add(assistant_message)

        # Update session
        session.updated_at = datetime.utcnow()
        session.last_message_at = datetime.utcnow()
        session.total_messages = session.total_messages + 2  # +2 for user and assistant messages
        session.total_tokens_used += (user_message.token_count or 0) + (assistant_message.token_count or 0)

        await db.commit()
        await db.refresh(session)

        logger.info(
            "chat_query_completed",
            user_id=str(current_user.id),
            session_id=str(session.id),
            sources_count=len(source_citations),
            tokens_used=llm_response["usage"]["total_tokens"]
        )

        return ChatResponse(
            answer=llm_response["content"],
            sources=source_citations,
            session_id=session.id,
            message_id=assistant_message.id,
            confidence_score=None,  # Could be calculated from reranking scores
            retrieval_config=retrieval_config,
            usage=llm_response["usage"],
            model_used=llm_response["model"]
        )

    except ValidationError as e:
        raise
    except Exception as e:
        logger.error("chat_query_failed", user_id=str(current_user.id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to process query")


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint for real-time chat"""
    await manager.connect(websocket, session_id)

    try:
        # Verify session exists and user is authenticated
        # Note: WebSocket auth would require token in query params or message
        logger.info("websocket_connected", session_id=session_id)

        while True:
            # Receive message
            data = await websocket.receive_text()
            message_data = json.loads(data)

            if message_data.get("type") == "query":
                await _handle_websocket_query(websocket, session_id, message_data, db)
            elif message_data.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect:
        manager.disconnect(session_id)
        logger.info("websocket_disconnected", session_id=session_id)
    except Exception as e:
        logger.error("websocket_error", session_id=session_id, error=str(e))
        manager.disconnect(session_id)


async def _handle_websocket_query(
    websocket: WebSocket,
    session_id: str,
    message_data: dict,
    db: AsyncSession
):
    """Handle incoming WebSocket query"""
    try:
        query = message_data.get("query", "")
        retrieval_config = RetrievalConfig(**message_data.get("retrieval_config", {}))

        if not query.strip():
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Query cannot be empty"
            }))
            return

        # Send typing indicator
        await websocket.send_text(json.dumps({
            "type": "status",
            "status": "thinking"
        }))

        # Initialize services
        retrieval_service = RetrievalService()
        llm_client = LLMClient()

        # Retrieve relevant chunks
        source_citations = await retrieval_service.retrieve_relevant_chunks(
            query=query,
            user_id=session_id,  # Would need proper user auth here
            config=retrieval_config
        )

        # Get conversation history
        history = await _get_conversation_history(db, uuid.UUID(session_id), limit=5)

        # Get context for LLM
        context = await retrieval_service.get_context_for_query(
            query=query,
            user_id=session_id,
            config=retrieval_config
        )

        # Send retrieved sources
        await websocket.send_text(json.dumps({
            "type": "sources",
            "sources": [source.dict() for source in source_citations]
        }))

        # Generate streaming response
        full_response = ""
        async for chunk in llm_client._generate_streaming_response(
            prompt=await llm_client.prompt_builder.build_rag_prompt(
                query=query,
                context=context["formatted_context"],
                conversation_history=history
            ),
            max_tokens=2000
        ):
            full_response += chunk
            await websocket.send_text(json.dumps({
                "type": "message_chunk",
                "content": chunk
            }))

        # Send completion message
        await websocket.send_text(json.dumps({
            "type": "complete",
            "content": full_response,
            "sources": [source.dict() for source in source_citations]
        }))

    except Exception as e:
        logger.error("websocket_query_failed", error=str(e))
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "Failed to process query"
        }))


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_session(
    session_data: ChatSessionCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new chat session"""
    try:
        session = ChatSession(
            user_id=current_user.id,
            title=session_data.title,
            description=session_data.description,
            is_active=True,
            total_messages=0,
            total_tokens_used=0
        )

        db.add(session)
        await db.commit()
        await db.refresh(session)

        logger.info("chat_session_created", session_id=str(session.id), user_id=str(current_user.id))
        return session

    except Exception as e:
        logger.error("session_creation_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create session")


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's chat sessions"""
    try:
        # Get total count
        count_stmt = select(func.count(ChatSession.id)).where(ChatSession.user_id == current_user.id)
        total_result = await db.execute(count_stmt)
        total = total_result.scalar()

        # Get sessions
        offset = (page - 1) * page_size
        stmt = (
            select(ChatSession)
            .where(ChatSession.user_id == current_user.id)
            .order_by(ChatSession.updated_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        sessions = result.scalars().all()

        total_pages = (total + page_size - 1) // page_size

        return SessionListResponse(
            sessions=sessions,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except Exception as e:
        logger.error("session_listing_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list sessions")


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific chat session"""
    try:
        session = await _get_user_session(db, current_user.id, session_id)
        return session

    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.error("session_retrieval_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve session")


@router.put("/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_session(
    session_id: str,
    session_update: ChatSessionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a chat session"""
    try:
        session = await _get_user_session(db, current_user.id, session_id)

        # Update fields
        if session_update.title is not None:
            session.title = session_update.title
        if session_update.description is not None:
            session.description = session_update.description
        if session_update.is_active is not None:
            session.is_active = session_update.is_active

        session.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(session)

        logger.info("chat_session_updated", session_id=session_id)
        return session

    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.error("session_update_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update session")


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a chat session"""
    try:
        session = await _get_user_session(db, current_user.id, session_id)

        # Delete session (cascade will delete messages)
        await db.delete(session)
        await db.commit()

        logger.info("chat_session_deleted", session_id=session_id)
        return {"message": "Session deleted successfully"}

    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.error("session_deletion_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete session")


@router.get("/sessions/{session_id}/history", response_model=ChatHistoryResponse)
async def get_session_history(
    session_id: str,
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get chat history for a session"""
    try:
        session = await _get_user_session(db, current_user.id, session_id)

        # Get messages
        offset = (page - 1) * page_size
        stmt = (
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        messages = result.scalars().all()

        # Get total count
        count_stmt = select(func.count(Message.id)).where(Message.session_id == session_id)
        count_result = await db.execute(count_stmt)
        total = count_result.scalar()

        return ChatHistoryResponse(
            session=session,
            messages=messages,
            total=total
        )

    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.error("history_retrieval_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve history")


@router.put("/messages/{message_id}/feedback")
async def update_message_feedback(
    message_id: str,
    feedback: MessageUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update feedback for a message"""
    try:
        # Get message with session to verify ownership
        stmt = (
            select(Message)
            .join(ChatSession)
            .where(and_(
                Message.id == message_id,
                ChatSession.user_id == current_user.id
            ))
        )
        result = await db.execute(stmt)
        message = result.scalar_one_or_none()

        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        # Update feedback
        if feedback.feedback is not None:
            message.feedback = feedback.feedback
        if feedback.feedback_comment is not None:
            message.feedback_comment = feedback.feedback_comment

        message.updated_at = datetime.utcnow()

        await db.commit()

        logger.info("message_feedback_updated", message_id=message_id)
        return {"message": "Feedback updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("feedback_update_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update feedback")


@router.get("/stats")
async def get_chat_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get chat usage statistics"""
    try:
        # Get user's chat statistics
        sessions_stmt = (
            select(func.count(ChatSession.id))
            .where(ChatSession.user_id == current_user.id)
        )
        sessions_count = await db.scalar(sessions_stmt)

        messages_stmt = (
            select(func.count(Message.id))
            .join(ChatSession)
            .where(ChatSession.user_id == current_user.id)
        )
        messages_count = await db.scalar(messages_stmt)

        tokens_stmt = (
            select(func.coalesce(func.sum(Message.token_count), 0))
            .join(ChatSession)
            .where(ChatSession.user_id == current_user.id)
        )
        total_tokens = await db.scalar(tokens_stmt) or 0

        return {
            "total_sessions": sessions_count or 0,
            "total_messages": messages_count or 0,
            "total_tokens_used": total_tokens,
            "average_messages_per_session": (messages_count / sessions_count) if sessions_count > 0 else 0
        }

    except Exception as e:
        logger.error("stats_retrieval_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


# Helper functions
async def _get_or_create_session(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: Optional[str]
) -> ChatSession:
    """Get existing session or create new one"""
    if session_id:
        stmt = select(ChatSession).where(
            and_(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id
            )
        )
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        if session:
            return session

    # Create new session
    session = ChatSession(
        user_id=user_id,
        title=f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        is_active=True
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def _get_user_session(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: str
) -> ChatSession:
    """Get user's session with error handling"""
    stmt = select(ChatSession).where(
        and_(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id
        )
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise NotFoundError("Session not found")

    return session


async def _get_conversation_history(
    db: AsyncSession,
    session_id: uuid.UUID,
    limit: int = 5
) -> List[Dict[str, str]]:
    """Get conversation history for context"""
    stmt = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(limit * 2)  # Get more than needed, will be filtered
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()

    # Convert to format expected by LLM and reverse to chronological order
    history = []
    for message in reversed(messages[-limit:]):
        if message.role in ["user", "assistant"]:
            history.append({
                "role": message.role,
                "content": message.content
            })

    return history


@router.get("/")
async def health_check():
    """Chat router health check"""
    logger.info("chat_router_health_check")
    return {"status": "healthy", "service": "chat router"}