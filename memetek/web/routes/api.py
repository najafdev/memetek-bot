"""REST API endpoints for monitoring, health check, and integrations."""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from memetek.config import settings
from memetek.database.session import get_session
from memetek.database.crud import (
    get_community_stats,
    get_recent_moderation_actions,
    review_meme,
    record_audit_event,
)
from memetek.web.auth import require_admin_api
from memetek.services.cache import cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["API"])


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    cache_backend: str
    environment: str


class MemeReviewRequest(BaseModel):
    approve: bool


# -----------------------------------------------------------------------------
# Health Check Endpoint
# -----------------------------------------------------------------------------
@router.get("/health", response_model=HealthResponse, tags=["Monitoring"])
async def health_check(session: AsyncSession = Depends(get_session)):
    """Health check endpoint for Docker Compose, Kubernetes, and load balancers."""
    db_status = "connected"
    try:
        await session.execute(text("SELECT 1"))
    except Exception as e:
        logger.error("Healthcheck DB ping failed: %s", e)
        db_status = f"unhealthy ({type(e).__name__})"

    overall_status = "ok" if db_status == "connected" else "degraded"
    cache_backend = "redis" if cache.is_redis else "in-memory"

    return HealthResponse(
        status=overall_status,
        version="1.0.0",
        database=db_status,
        cache_backend=cache_backend,
        environment=settings.APP_ENV,
    )


# Root level /health alias
@router.get("/healthz", response_model=HealthResponse, include_in_schema=False)
async def healthz(session: AsyncSession = Depends(get_session)):
    return await health_check(session)


# -----------------------------------------------------------------------------
# Protected Admin API Endpoints
# -----------------------------------------------------------------------------
@router.get("/stats", tags=["Admin API"])
async def get_stats_api(
    admin_user: str = Depends(require_admin_api),
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """Retrieve community statistics in JSON format."""
    return await get_community_stats(session)


@router.get("/moderation/recent", tags=["Admin API"])
async def get_recent_actions_api(
    limit: int = 20,
    admin_user: str = Depends(require_admin_api),
    session: AsyncSession = Depends(get_session),
) -> List[Dict[str, Any]]:
    """Retrieve recent moderation actions in JSON format."""
    actions = await get_recent_moderation_actions(session, limit=limit)
    return [
        {
            "id": a.id,
            "chat_id": a.chat_id,
            "target_user_id": a.target_user_id,
            "action_type": a.action_type,
            "reason": a.reason,
            "is_automated": a.is_automated,
            "created_at": a.created_at.isoformat(),
        }
        for a in actions
    ]


@router.post("/memes/{meme_id}/review", tags=["Admin API"])
async def review_meme_api(
    meme_id: int,
    payload: MemeReviewRequest,
    admin_user: str = Depends(require_admin_api),
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """Approve or reject a submitted meme via API."""
    meme = await review_meme(session, meme_id=meme_id, approve=payload.approve)
    if not meme:
        raise HTTPException(status_code=404, detail="Meme not found.")

    await record_audit_event(
        session=session,
        admin_user_id=admin_user,
        action=f"api_meme_{'approved' if payload.approve else 'rejected'}",
        details=f"Meme #{meme_id} reviewed via API",
    )

    return {
        "success": True,
        "meme_id": meme.id,
        "status": meme.status,
    }
