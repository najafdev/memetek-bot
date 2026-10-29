"""Tests for FastAPI Web Dashboard & REST API."""

import pytest
from fastapi.testclient import TestClient

from memetek.web.app import create_app
from memetek.config import settings
from memetek.web.auth import create_access_token, COOKIE_NAME
from memetek.database.crud import create_meme
from memetek.database.session import async_session_factory


@pytest.fixture
def client():
    """Test client for FastAPI app with lifecycle context."""
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_health_check_endpoint(client):
    """Verify /health returns 200 with system statuses."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert "version" in data
    assert "database" in data
    assert "cache" in data


def test_login_flow(client):
    """Test admin login validation and cookie assignment."""
    # 1. Invalid login
    bad_login = client.post(
        "/login",
        data={"username": "wrong", "password": "wrong_password"},
    )
    assert bad_login.status_code == 401
    assert "Invalid administrative credentials" in bad_login.text

    # 2. Valid login
    good_login = client.post(
        "/login",
        data={
            "username": settings.DASHBOARD_USERNAME,
            "password": settings.DASHBOARD_PASSWORD,
        },
        follow_redirects=False,
    )
    assert good_login.status_code == 302
    assert COOKIE_NAME in good_login.cookies


def test_protected_page_redirect_without_auth(client):
    """Verify unauthenticated access to dashboard redirects to /login."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert "/login" in response.headers.get("location", "")


def test_dashboard_with_authenticated_session(client):
    """Verify authenticated session can view the dashboard."""
    token = create_access_token(settings.DASHBOARD_USERNAME)
    response = client.get("/", cookies={COOKIE_NAME: token})
    assert response.status_code == 200
    assert "Community Overview" in response.text
    assert "MEMETEK" in response.text


def test_rest_api_auth_and_stats(client):
    """Verify /api/stats requires authentication."""
    # Unauthorized
    unauth = client.get("/api/stats")
    assert unauth.status_code == 401

    # Authorized via header
    token = create_access_token(settings.DASHBOARD_USERNAME)
    headers = {"Authorization": f"Bearer {token}"}
    auth_resp = client.get("/api/stats", headers=headers)
    assert auth_resp.status_code == 200
    data = auth_resp.json()
    assert "tracked_members" in data
    assert "total_messages" in data
    assert "approved_memes" in data


@pytest.mark.asyncio
async def test_api_meme_review(client):
    """Verify approving meme via REST API."""
    async with async_session_factory() as session:
        meme = await create_meme(
            session=session,
            caption="Test meme for API review",
            status="pending",
        )
        meme_id = meme.id

    token = create_access_token(settings.DASHBOARD_USERNAME)
    headers = {"Authorization": f"Bearer {token}"}

    # Review via API
    resp = client.post(
        f"/api/memes/{meme_id}/review",
        headers=headers,
        json={"approve": True},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
