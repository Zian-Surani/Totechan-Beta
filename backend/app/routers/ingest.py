from fastapi import APIRouter
import structlog

logger = structlog.get_logger()
router = APIRouter()


@router.get("/")
async def health_check():
    """Ingest router health check"""
    logger.info("ingest_router_health_check")
    return {"status": "healthy", "service": "ingest router"}