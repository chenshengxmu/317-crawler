"""
Health check endpoints.
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException
from loguru import logger

from api.models import HealthResponse
from storage import es_client
from config import settings

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns service status and Elasticsearch health.
    """
    try:
        # Check Elasticsearch health
        es_health = es_client.health_check()

        return HealthResponse(
            status="healthy" if es_health.get("status") != "error" else "unhealthy",
            elasticsearch=es_health,
            version=settings.api_version,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")
