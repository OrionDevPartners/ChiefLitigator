"""Tests for case persistence endpoints.

Uses sqlite+aiosqlite as the async test database so no external
PostgreSQL instance is required.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database import get_db
from src.database.engine import Base
from src.database.models import Case, Deadline, Message, User  # noqa: F401

# ---------------------------------------------------------------------------
# Test database setup (sqlite+aiosqlite, in-memory)
# ---------------------------------------------------------------------------

_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
_TEST_JWT_SECRET = "test-secret-key-for-case-tests-32ch"


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set required env vars for the test suite."""
    monkeypatch.setenv("JWT_SECRET_KEY", _TEST_JWT_SECRET)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", _TEST_DB_URL)


def _make_token(sub: str | None = None) -> str:
    if sub is None:
        sub = str(uuid.uuid4())
    now = int(time.time())
    return jwt.encode(
        {"sub": sub, "iat": now, "exp": now + 3600},
        _TEST_JWT_SECRET,
        algorithm="HS256",
    )


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(_TEST_DB_URL, echo=False)

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


async def _create_test_user(session: AsyncSession) -> User:
    """Helper to create a user required by the FK constraint on cases."""
    user = User(
        id=uuid.uuid4(),
        email=f"test-{uuid.uuid4().hex[:8]}@cyphergy.ai",
        password_hash="$2b$12$fakehashfortesting000000000000000000000000000000",
        name="Test User",
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def client(db_engine) -> AsyncIterator[AsyncClient]:
    """Provide an async test client with the DB session overridden."""
    from src.api import app

    session_factory = async_sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /api/v1/cases — create case
# ---------------------------------------------------------------------------


class TestCreateCase:
    @pytest.mark.asyncio
    async def test_create_case_success(self, client: AsyncClient, db_session: AsyncSession) -> None:
        user = await _create_test_user(db_session)
        await db_session.commit()
        token = _make_token(str(user.id))

        resp = await client.post(
            "/api/v1/cases",
            json={"name": "Smith v. Jones"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Smith v. Jones"
        assert data["user_id"] == str(user.id)
        assert data["status"] == "active"
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_case_with_jurisdiction(self, client: AsyncClient, db_session: AsyncSession) -> None:
        user = await _create_test_user(db_session)
        await db_session.commit()
        token = _make_token(str(user.id))

        resp = await client.post(
            "/api/v1/cases",
            json={"name": "Case A", "jurisdiction": "federal"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        assert resp.json()["jurisdiction"] == "federal"

    @pytest.mark.asyncio
    async def test_create_case_missing_name_returns_422(self, client: AsyncClient, db_session: AsyncSession) -> None:
        user = await _create_test_user(db_session)
        await db_session.commit()
        token = _make_token(str(user.id))

        resp = await client.post(
            "/api/v1/cases",
            json={"jurisdiction": "federal"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_case_empty_name_returns_422(self, client: AsyncClient, db_session: AsyncSession) -> None:
        user = await _create_test_user(db_session)
        await db_session.commit()
        token = _make_token(str(user.id))

        resp = await client.post(
            "/api/v1/cases",
            json={"name": ""},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_case_no_auth_returns_401(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/cases",
            json={"name": "Unauthorized"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/cases — list user cases
# ---------------------------------------------------------------------------


class TestListCases:
    @pytest.mark.asyncio
    async def test_list_cases_empty(self, client: AsyncClient, db_session: AsyncSession) -> None:
        user = await _create_test_user(db_session)
        await db_session.commit()
        token = _make_token(str(user.id))

        resp = await client.get(
            "/api/v1/cases",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_cases_returns_own_cases(self, client: AsyncClient, db_session: AsyncSession) -> None:
        user = await _create_test_user(db_session)
        await db_session.commit()
        token = _make_token(str(user.id))

        await client.post(
            "/api/v1/cases",
            json={"name": "Case 1"},
            headers={"Authorization": f"Bearer {token}"},
        )
        await client.post(
            "/api/v1/cases",
            json={"name": "Case 2"},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = await client.get(
            "/api/v1/cases",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        cases = resp.json()
        assert len(cases) == 2

    @pytest.mark.asyncio
    async def test_list_cases_does_not_return_other_users(self, client: AsyncClient, db_session: AsyncSession) -> None:
        user_a = await _create_test_user(db_session)
        user_b = await _create_test_user(db_session)
        await db_session.commit()

        await client.post(
            "/api/v1/cases",
            json={"name": "User A case"},
            headers={"Authorization": f"Bearer {_make_token(str(user_a.id))}"},
        )
        resp = await client.get(
            "/api/v1/cases",
            headers={"Authorization": f"Bearer {_make_token(str(user_b.id))}"},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_cases_no_auth_returns_401(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/cases")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/cases/{id} — get case with messages
# ---------------------------------------------------------------------------


class TestGetCase:
    @pytest.mark.asyncio
    async def test_get_case_with_messages(self, client: AsyncClient, db_session: AsyncSession) -> None:
        user = await _create_test_user(db_session)
        await db_session.commit()
        token = _make_token(str(user.id))

        create_resp = await client.post(
            "/api/v1/cases",
            json={"name": "Detail case"},
            headers={"Authorization": f"Bearer {token}"},
        )
        case_id = create_resp.json()["id"]

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

    @pytest.mark.asyncio
    async def test_get_case_not_found(self, client: AsyncClient, db_session: AsyncSession) -> None:
        user = await _create_test_user(db_session)
        await db_session.commit()
        token = _make_token(str(user.id))

        fake_id = str(uuid.uuid4())
        resp = await client.get(
            f"/api/v1/cases/{fake_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_case_other_user_returns_404(self, client: AsyncClient, db_session: AsyncSession) -> None:
        user_a = await _create_test_user(db_session)
        user_b = await _create_test_user(db_session)
        await db_session.commit()

        create_resp = await client.post(
            "/api/v1/cases",
            json={"name": "Private case"},
            headers={"Authorization": f"Bearer {_make_token(str(user_a.id))}"},
        )
        case_id = create_resp.json()["id"]

        resp = await client.get(
            f"/api/v1/cases/{case_id}",
            headers={"Authorization": f"Bearer {_make_token(str(user_b.id))}"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/cases/{id}/messages — add message
# ---------------------------------------------------------------------------


class TestAddMessage:
    @pytest.mark.asyncio
    async def test_add_message_success(self, client: AsyncClient, db_session: AsyncSession) -> None:
        user = await _create_test_user(db_session)
        await db_session.commit()
        token = _make_token(str(user.id))

        create_resp = await client.post(
            "/api/v1/cases",
            json={"name": "Msg case"},
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

    @pytest.mark.asyncio
    async def test_add_message_to_nonexistent_case(self, client: AsyncClient, db_session: AsyncSession) -> None:
        user = await _create_test_user(db_session)
        await db_session.commit()
        token = _make_token(str(user.id))

        fake_id = str(uuid.uuid4())
        resp = await client.post(
            f"/api/v1/cases/{fake_id}/messages",
            json={"role": "user", "content": "Hello"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_add_message_missing_content_returns_422(self, client: AsyncClient, db_session: AsyncSession) -> None:
        user = await _create_test_user(db_session)
        await db_session.commit()
        token = _make_token(str(user.id))

        create_resp = await client.post(
            "/api/v1/cases",
            json={"name": "Validation case"},
            headers={"Authorization": f"Bearer {token}"},
        )
        case_id = create_resp.json()["id"]

        resp = await client.post(
            f"/api/v1/cases/{case_id}/messages",
            json={"role": "user"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_add_message_other_user_returns_404(self, client: AsyncClient, db_session: AsyncSession) -> None:
        user_a = await _create_test_user(db_session)
        user_b = await _create_test_user(db_session)
        await db_session.commit()

        create_resp = await client.post(
            "/api/v1/cases",
            json={"name": "Private msg case"},
            headers={"Authorization": f"Bearer {_make_token(str(user_a.id))}"},
        )
        case_id = create_resp.json()["id"]

        resp = await client.post(
            f"/api/v1/cases/{case_id}/messages",
            json={"role": "user", "content": "Intruder"},
            headers={"Authorization": f"Bearer {_make_token(str(user_b.id))}"},
        )
        assert resp.status_code == 404
