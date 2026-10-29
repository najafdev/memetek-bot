"""HTML Page routes for MEMETEK Admin Dashboard."""

import logging
from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from memetek.config import settings, BRAND_DEFAULT_WELCOME, BRAND_DEFAULT_RULES
from memetek.database.session import get_session
from memetek.database.models import Chat
from memetek.database.crud import (
    get_community_stats,
    get_recent_moderation_actions,
    get_memes,
    review_meme,
    clear_warnings,
    record_moderation_action,
    get_or_create_chat,
    update_chat_settings,
    get_allowed_domains,
    add_allowed_domain,
    remove_allowed_domain,
    record_audit_event,
    get_audit_events,
)
from memetek.web.auth import (
    create_access_token,
    COOKIE_NAME,
    get_current_admin_or_none,
)
from pathlib import Path
from memetek.services.cache import cache

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(include_in_schema=False)


# -----------------------------------------------------------------------------
# Auth Routes
# -----------------------------------------------------------------------------
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Render login screen."""
    if get_current_admin_or_none(request):
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": None},
    )


@router.post("/login", response_class=HTMLResponse)
async def handle_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_session),
):
    """Verify admin credentials and set session cookie."""
    if username == settings.DASHBOARD_USERNAME and password == settings.DASHBOARD_PASSWORD:
        token = create_access_token(username=username)
        response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        response.set_cookie(
            key=COOKIE_NAME,
            value=token,
            httponly=True,
            samesite="lax",
            max_age=12 * 3600,
        )
        client_ip = request.client.host if request.client else None
        await record_audit_event(
            session=session,
            admin_user_id=username,
            action="login_success",
            details="Admin successfully logged in to dashboard",
            ip_address=client_ip,
        )
        return response

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": "Invalid administrative credentials. Access denied."},
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


@router.get("/logout")
async def handle_logout(request: Request, session: AsyncSession = Depends(get_session)):
    """Clear session cookie."""
    username = get_current_admin_or_none(request) or "Unknown"
    client_ip = request.client.host if request.client else None
    await record_audit_event(
        session=session,
        admin_user_id=username,
        action="logout",
        details="Admin logged out",
        ip_address=client_ip,
    )
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(COOKIE_NAME)
    return response


# -----------------------------------------------------------------------------
# Dashboard Pages (Protected)
# -----------------------------------------------------------------------------
@router.get("/", response_class=HTMLResponse)
async def dashboard_overview(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Render dashboard overview."""
    username = get_current_admin_or_none(request)
    if not username:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    stats = await get_community_stats(session)
    recent_actions = await get_recent_moderation_actions(session, limit=8)

    db_engine = "SQLite" if "sqlite" in settings.DATABASE_URL else "PostgreSQL"
    cache_backend = "Redis" if cache.is_redis else "In-Memory"

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "active_page": "dashboard",
            "admin_username": username,
            "stats": stats,
            "recent_actions": recent_actions,
            "db_status": f"{db_engine} (Connected)",
            "cache_backend": cache_backend,
        },
    )


@router.get("/moderation", response_class=HTMLResponse)
async def moderation_page(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Render moderation logs and warning tools."""
    username = get_current_admin_or_none(request)
    if not username:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    actions = await get_recent_moderation_actions(session, limit=50)

    return templates.TemplateResponse(
        request=request,
        name="moderation.html",
        context={
            "active_page": "moderation",
            "admin_username": username,
            "actions": actions,
            "success_msg": None,
            "error_msg": None,
        },
    )


@router.post("/moderation/clearwarns")
async def handle_clearwarns_web(
    request: Request,
    chat_id: int = Form(...),
    user_id: int = Form(...),
    session: AsyncSession = Depends(get_session),
):
    """Clear warnings via web dashboard."""
    username = get_current_admin_or_none(request)
    if not username:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    cleared = await clear_warnings(session, chat_id=chat_id, user_id=user_id)
    await record_moderation_action(
        session=session,
        chat_id=chat_id,
        target_user_id=user_id,
        moderator_user_id=None,
        action_type="web_clearwarns",
        reason=f"Cleared {cleared} warnings via web dashboard by {username}",
    )
    await record_audit_event(
        session=session,
        admin_user_id=username,
        action="clear_warnings",
        details=f"Cleared {cleared} warnings for user {user_id} in chat {chat_id}",
        ip_address=request.client.host if request.client else None,
    )

    actions = await get_recent_moderation_actions(session, limit=50)
    return templates.TemplateResponse(
        request=request,
        name="moderation.html",
        context={
            "active_page": "moderation",
            "admin_username": username,
            "actions": actions,
            "success_msg": f"Successfully cleared {cleared} active warnings for user {user_id}.",
            "error_msg": None,
        },
    )


@router.get("/memes", response_class=HTMLResponse)
async def memes_page(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Render meme approval queue and approved vault."""
    username = get_current_admin_or_none(request)
    if not username:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    pending_memes = await get_memes(session, status="pending", limit=50)
    approved_memes = await get_memes(session, status="approved", limit=50)

    return templates.TemplateResponse(
        request=request,
        name="memes.html",
        context={
            "active_page": "memes",
            "admin_username": username,
            "pending_memes": pending_memes,
            "approved_memes": approved_memes,
            "success_msg": None,
        },
    )


@router.post("/memes/{meme_id}/review")
async def handle_meme_review(
    meme_id: int,
    request: Request,
    decision: str = Form(...),
    session: AsyncSession = Depends(get_session),
):
    """Approve or reject a submitted meme."""
    username = get_current_admin_or_none(request)
    if not username:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    is_approved = (decision == "approve")
    await review_meme(session, meme_id=meme_id, approve=is_approved)

    await record_audit_event(
        session=session,
        admin_user_id=username,
        action=f"meme_{'approved' if is_approved else 'rejected'}",
        details=f"Meme #{meme_id} marked as {decision} by {username}",
        ip_address=request.client.host if request.client else None,
    )

    return RedirectResponse(url="/memes", status_code=status.HTTP_302_FOUND)


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Render settings editor."""
    username = get_current_admin_or_none(request)
    if not username:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    # Get first chat or default
    result = await session.execute(select(Chat).limit(1))
    chat = result.scalar_one_or_none()
    domains = await get_allowed_domains(session, chat_id=chat.chat_id if chat else None)

    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "active_page": "settings",
            "admin_username": username,
            "chat": chat,
            "domains": domains,
            "default_welcome": BRAND_DEFAULT_WELCOME,
            "default_rules": BRAND_DEFAULT_RULES,
            "success_msg": None,
            "error_msg": None,
        },
    )


@router.post("/settings", response_class=HTMLResponse)
async def handle_save_settings(
    request: Request,
    chat_id: int = Form(...),
    anti_spam_enabled: str = Form(...),
    welcome_enabled: str = Form(...),
    welcome_delete_seconds: int = Form(...),
    welcome_text: str = Form(...),
    rules_text: str = Form(...),
    official_contract_address: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_session),
):
    """Save community settings for a chat."""
    username = get_current_admin_or_none(request)
    if not username:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    chat = await get_or_create_chat(session, chat_id=chat_id)
    await update_chat_settings(
        session=session,
        chat_id=chat_id,
        anti_spam_enabled=(anti_spam_enabled == "true"),
        welcome_enabled=(welcome_enabled == "true"),
        welcome_delete_seconds=max(0, welcome_delete_seconds),
        welcome_text=welcome_text.strip(),
        rules_text=rules_text.strip(),
        official_contract_address=official_contract_address.strip() if official_contract_address else None,
    )

    await record_audit_event(
        session=session,
        admin_user_id=username,
        action="update_settings",
        details=f"Updated community settings for chat {chat_id}",
        ip_address=request.client.host if request.client else None,
    )

    domains = await get_allowed_domains(session, chat_id=chat_id)

    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "active_page": "settings",
            "admin_username": username,
            "chat": chat,
            "domains": domains,
            "default_welcome": BRAND_DEFAULT_WELCOME,
            "default_rules": BRAND_DEFAULT_RULES,
            "success_msg": "Community settings updated and synced with Telegram bot!",
            "error_msg": None,
        },
    )


@router.post("/settings/domains/add")
async def handle_add_domain(
    request: Request,
    domain: str = Form(...),
    session: AsyncSession = Depends(get_session),
):
    """Add a domain to allowlist."""
    username = get_current_admin_or_none(request)
    if not username:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    await add_allowed_domain(session, domain=domain)
    await record_audit_event(
        session=session,
        admin_user_id=username,
        action="add_allowed_domain",
        details=f"Added domain '{domain}' to allowlist",
        ip_address=request.client.host if request.client else None,
    )
    return RedirectResponse(url="/settings", status_code=status.HTTP_302_FOUND)


@router.post("/settings/domains/remove")
async def handle_remove_domain(
    request: Request,
    domain: str = Form(...),
    session: AsyncSession = Depends(get_session),
):
    """Remove a domain from allowlist."""
    username = get_current_admin_or_none(request)
    if not username:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    await remove_allowed_domain(session, domain=domain)
    await record_audit_event(
        session=session,
        admin_user_id=username,
        action="remove_allowed_domain",
        details=f"Removed domain '{domain}' from allowlist",
        ip_address=request.client.host if request.client else None,
    )
    return RedirectResponse(url="/settings", status_code=status.HTTP_302_FOUND)


@router.get("/logs", response_class=HTMLResponse)
async def audit_logs_page(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Render audit logs."""
    username = get_current_admin_or_none(request)
    if not username:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    events = await get_audit_events(session, limit=50)

    return templates.TemplateResponse(
        request=request,
        name="logs.html",
        context={
            "active_page": "logs",
            "admin_username": username,
            "events": events,
        },
    )
