"""
Smoke tests for AgentGo Biz API.
Run: pytest tests/test_api_smoke.py -v
Requires: running FastAPI app or use httpx AsyncClient with ASGI transport.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_health():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_docs_available():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/docs")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_login_invalid_credentials():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/auth/login", json={
            "email": "nonexistent@test.com",
            "password": "wrongpassword"
        })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_no_token():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/users/me")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_protected_route_invalid_token():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/users/me",
            headers={"Authorization": "Bearer invalidtoken"}
        )
    assert response.status_code == 401
