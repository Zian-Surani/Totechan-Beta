from fastapi import APIRouter
import structlog

logger = structlog.get_logger()
router = APIRouter()


@router.get("/")
async def health_check():
    """Chat router health check"""
    logger.info("chat_router_health_check")
    return {"status": "healthy", "service": "chat router"}