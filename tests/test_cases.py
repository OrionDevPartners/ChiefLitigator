"""Tests for case persistence endpoints.

Uses sqlite+aiosqlite as the async test database so no external
PostgreSQL instance is required.
"""

from __future__ import annotations

import time
from typing import AsyncIterator

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database import Base, get_session
from src.database.models import Case, Message  # noqa: F401 — ensure models are registered

# ---------------------------------------------------------------------------
# Test database setup (sqlite+aiosqlite, in-memory)
# ---------------------------------------------------------------------------

_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
_TEST_JWT_SECRET = "test-secret-key-for-case-tests"


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set required env vars for the test suite."""
    monkeypatch.setenv("JWT_SECRET_KEY", _TEST_JWT_SECRET)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", _TEST_DB_URL)


def _make_token(sub: str = "user1") -> str:
    now = int(time.time())
    return jwt.encode(
        {"sub": sub, "iat": now, "exp": now + 3600},
        _TEST_JWT_SECRET,
        algorithm="HS256",
    )


@pytest.fixture()
async def db_engine():
    engine = create_async_engine(_TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture()
async def db_session(db_engine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture()
async def client(db_engine) -> AsyncIterator[AsyncClient]:
    """Provide an async test client with the DB session overridden."""
    from src.api import app

    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = _override_get_session

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /api/v1/cases — create case
# ---------------------------------------------------------------------------


class TestCreateCase:
    async def test_create_case_success(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/cases",
            json={"title": "Smith v. Jones", "description": "Contract dispute"},
            headers={"Authorization": f"Bearer {_make_token()}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Smith v. Jones"
        assert data["description"] == "Contract dispute"
        assert data["user_id"] == "user1"
        assert data["status"] == "open"
        assert "id" in data
        assert "created_at" in data

    async def test_create_case_with_jurisdiction(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/cases",
            json={"title": "Case A", "jurisdiction": "federal"},
            headers={"Authorization": f"Bearer {_make_token()}"},
        )
        assert resp.status_code == 201
        assert resp.json()["jurisdiction"] == "federal"

    async def test_create_case_missing_title_returns_422(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/cases",
            json={"description": "no title"},
            headers={"Authorization": f"Bearer {_make_token()}"},
        )
        assert resp.status_code == 422

    async def test_create_case_empty_title_returns_422(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/cases",
            json={"title": ""},
            headers={"Authorization": f"Bearer {_make_token()}"},
        )
        assert resp.status_code == 422

    async def test_create_case_no_auth_returns_401(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/cases",
            json={"title": "Unauthorized"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/cases — list user cases
# ---------------------------------------------------------------------------


class TestListCases:
    async def test_list_cases_empty(self, client: AsyncClient) -> None:
        resp = await client.get(
            "/api/v1/cases",
            headers={"Authorization": f"Bearer {_make_token()}"},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_cases_returns_own_cases(self, client: AsyncClient) -> None:
        token = _make_token("user_a")
        # Create two cases
        await client.post(
            "/api/v1/cases",
            json={"title": "Case 1"},
            headers={"Authorization": f"Bearer {token}"},
        )
        await client.post(
            "/api/v1/cases",
            json={"title": "Case 2"},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = await client.get(
            "/api/v1/cases",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        cases = resp.json()
        assert len(cases) == 2

    async def test_list_cases_does_not_return_other_users(self, client: AsyncClient) -> None:
        # user_a creates a case
        await client.post(
            "/api/v1/cases",
            json={"title": "User A's case"},
            headers={"Authorization": f"Bearer {_make_token('user_a')}"},
        )
        # user_b sees nothing
        resp = await client.get(
            "/api/v1/cases",
            headers={"Authorization": f"Bearer {_make_token('user_b')}"},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_cases_no_auth_returns_401(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/cases")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/cases/{id} — get case with messages
# ---------------------------------------------------------------------------


class TestGetCase:
    async def test_get_case_with_messages(self, client: AsyncClient) -> None:
        token = _make_token()
        # Create a case
        create_resp = await client.post(
            "/api/v1/cases",
            json={"title": "Detail case"},
            headers={"Authorization": f"Bearer {token}"},
        )
        case_id = create_resp.json()["id"]

        # Add a message
        await client.post(
            f"/api/v1/cases/{case_id}/messages",
            json={"role": "user", "content": "Hello"},
            headers={"Authorization": f"Bearer {token}"},
        )

        resp = await client.get(
            f"/api/v1/cases/{case_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == case_id
        assert len(data["messages"]) == 1
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][0]["content"] == "Hello"

    async def test_get_case_not_found(self, client: AsyncClient) -> None:
        resp = await client.get(
            "/api/v1/cases/nonexistent-id",
            headers={"Authorization": f"Bearer {_make_token()}"},
        )
        assert resp.status_code == 404

    async def test_get_case_other_user_returns_404(self, client: AsyncClient) -> None:
        # user_a creates a case
        create_resp = await client.post(
            "/api/v1/cases",
            json={"title": "Private case"},
            headers={"Authorization": f"Bearer {_make_token('user_a')}"},
        )
        case_id = create_resp.json()["id"]

        # user_b cannot access it
        resp = await client.get(
            f"/api/v1/cases/{case_id}",
            headers={"Authorization": f"Bearer {_make_token('user_b')}"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/cases/{id}/messages — add message
# ---------------------------------------------------------------------------


class TestAddMessage:
    async def test_add_message_success(self, client: AsyncClient) -> None:
        token = _make_token()
        create_resp = await client.post(
            "/api/v1/cases",
            json={"title": "Msg case"},
            headers={"Authorization": f"Bearer {token}"},
        )
        case_id = create_resp.json()["id"]

        resp = await client.post(
            f"/api/v1/cases/{case_id}/messages",
            json={"role": "user", "content": "What are my options?"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["role"] == "user"
        assert data["content"] == "What are my options?"
        assert data["case_id"] == case_id

    async def test_add_message_to_nonexistent_case(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/cases/nonexistent-id/messages",
            json={"role": "user", "content": "Hello"},
            headers={"Authorization": f"Bearer {_make_token()}"},
        )
        assert resp.status_code == 404

    async def test_add_message_missing_content_returns_422(self, client: AsyncClient) -> None:
        token = _make_token()
        create_resp = await client.post(
            "/api/v1/cases",
            json={"title": "Validation case"},
            headers={"Authorization": f"Bearer {token}"},
        )
        case_id = create_resp.json()["id"]

        resp = await client.post(
            f"/api/v1/cases/{case_id}/messages",
            json={"role": "user"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    async def test_add_message_other_user_returns_404(self, client: AsyncClient) -> None:
        # user_a creates a case
        create_resp = await client.post(
            "/api/v1/cases",
            json={"title": "Private msg case"},
            headers={"Authorization": f"Bearer {_make_token('user_a')}"},
        )
        case_id = create_resp.json()["id"]

        # user_b cannot add messages
        resp = await client.post(
            f"/api/v1/cases/{case_id}/messages",
            json={"role": "user", "content": "Intruder"},
            headers={"Authorization": f"Bearer {_make_token('user_b')}"},
        )
        assert resp.status_code == 404
