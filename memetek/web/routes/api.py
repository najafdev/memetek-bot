"""REST API endpoints for monitoring, health check, and integrations."""

import logging
from typing import Dict, Any, List, Optional
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
from memetek.services.pumpfun import pumpfun_service, DEFAULT_TRACKED_WHALES
from memetek.database.models import Chat
from sqlalchemy import select
from aiogram import Bot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["API"])


class WhaleBuyPayload(BaseModel):
    token_symbol: str = "MEMETEK"
    token_name: str = "MEMETEK Token"
    contract_address: str = "8kG8M3M3T3KpumpFUNmoonCOINtokenCA123456789pump"
    sol_amount: float = 2.5
    usd_amount: Optional[float] = None
    tokens_bought: Optional[float] = None
    market_cap_usd: Optional[float] = None
    buyer: Optional[str] = "@slingoor"
    tx_hash: Optional[str] = None
    chat_id: Optional[int] = None
    media_url: Optional[str] = None
    extra_whales: Optional[List[str]] = None


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


# -----------------------------------------------------------------------------
# Pump.fun Whale Buy Webhook Endpoint
# -----------------------------------------------------------------------------
@router.post("/whale-buy", tags=["Pump.fun Whale Tracker"])
async def trigger_whale_buy_webhook(
    payload: WhaleBuyPayload,
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """Receive on-chain Pump.fun whale buy event and broadcast alert to Telegram."""
    alert_text = pumpfun_service.format_buy_alert(
        token_symbol=payload.token_symbol,
        token_name=payload.token_name,
        contract_address=payload.contract_address,
        sol_amount=payload.sol_amount,
        usd_amount=payload.usd_amount,
        tokens_bought=payload.tokens_bought,
        market_cap_usd=payload.market_cap_usd,
        buyer_handle=payload.buyer,
        tx_hash=payload.tx_hash,
        extra_whales=payload.extra_whales,
    )

    sent_count = 0
    bot = None
    try:
        from memetek.bot.instance import create_bot
        bot = create_bot()

        target_chat_ids: List[int] = []
        if payload.chat_id:
            target_chat_ids.append(payload.chat_id)
        else:
            # Broadcast to active community chats
            stmt = select(Chat.chat_id).where(
                Chat.is_active.is_(True),
            )
            result = await session.execute(stmt)
            target_chat_ids = [row[0] for row in result.all()]

            # Fallback to configured admin if no chats stored yet
            if not target_chat_ids and settings.admin_ids_list:
                target_chat_ids.append(settings.admin_ids_list[0])

        for cid in target_chat_ids:
            ok = await pumpfun_service.broadcast_buy_alert(
                bot=bot,
                chat_id=cid,
                alert_text=alert_text,
                media_url=payload.media_url,
            )
            if ok:
                sent_count += 1

    except Exception as e:
        logger.error("Error broadcasting whale buy via webhook: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Broadcast error: {e}",
        )
    finally:
        if bot and bot.session:
            await bot.session.close()

    return {
        "success": True,
        "broadcast_chats": sent_count,
        "token": payload.token_symbol,
        "sol_amount": payload.sol_amount,
        "buyer": payload.buyer,
        "tagged_whales": pumpfun_service.tracked_whales,
    }


@router.get("/tracked-whales", tags=["Pump.fun Whale Tracker"])
async def get_tracked_whales() -> Dict[str, Any]:
    """Retrieve list of currently tracked Pump.fun alpha whales."""
    return {
        "success": True,
        "tracked_whales": pumpfun_service.tracked_whales,
        "count": len(pumpfun_service.tracked_whales),
    }
