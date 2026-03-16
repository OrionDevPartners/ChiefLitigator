"""Tests for the beta gate access control system.

Uses an async SQLite in-memory database for fast, isolated testing.
Each test gets a fresh database with all tables created.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.database.engine import Base
from src.security.beta_gate import (
    BetaGateMiddleware,
    approve_beta_user,
    check_ip,
    lock_ip,
    reset_beta_ip,
    revoke_beta_access,
    send_beta_invite_email,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_TEST_SECRET = "test-secret-key-for-beta-gate-tests"


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set required environment variables for all tests."""
    monkeypatch.setenv("JWT_SECRET_KEY", _TEST_SECRET)


@pytest_asyncio.fixture
async def db_engine():
    """Create an async SQLite engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

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
async def db_session(db_engine):
    """Yield a request-scoped async session for testing."""
    session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBetaGate:
    """Tests for beta gate access control."""

    @pytest.mark.asyncio
    async def test_approve_user_creates_account(self, db_session: AsyncSession) -> None:
        """Approving a beta user should create both a User and a BetaInvite record."""
        user, invite = await approve_beta_user(
            db_session,
            email="beta@cyphergy.ai",
            name="Beta User",
            password="SecurePass1",
        )
        await db_session.commit()

        assert user.id is not None
        assert isinstance(user.id, uuid.UUID)
        assert user.email == "beta@cyphergy.ai"
        assert user.name == "Beta User"
        assert user.is_active is True

        assert invite.id is not None
        assert invite.email == "beta@cyphergy.ai"
        assert invite.is_approved is True
        assert invite.is_revoked is False
        assert invite.locked_ip is None
        assert len(invite.invite_code) > 0

    @pytest.mark.asyncio
    async def test_first_login_locks_ip(self, db_session: AsyncSession) -> None:
        """First login should lock the beta invite to the connecting IP address."""
        await approve_beta_user(
            db_session,
            email="lockip@cyphergy.ai",
            name="Lock IP User",
            password="SecurePass1",
        )
        await db_session.commit()

        invite = await lock_ip(db_session, email="lockip@cyphergy.ai", ip_address="192.168.1.100")
        await db_session.commit()

        assert invite is not None
        assert invite.locked_ip == "192.168.1.100"

    @pytest.mark.asyncio
    async def test_same_ip_passes(self, db_session: AsyncSession) -> None:
        """Requests from the same locked IP should pass the beta gate check."""
        await approve_beta_user(
            db_session,
            email="sameip@cyphergy.ai",
            name="Same IP User",
            password="SecurePass1",
        )
        await db_session.commit()

        await lock_ip(db_session, email="sameip@cyphergy.ai", ip_address="10.0.0.1")
        await db_session.commit()

        allowed = await check_ip(db_session, email="sameip@cyphergy.ai", ip_address="10.0.0.1")
        assert allowed is True

    @pytest.mark.asyncio
    async def test_different_ip_blocked(self, db_session: AsyncSession) -> None:
        """Requests from a different IP than the locked IP should be blocked."""
        await approve_beta_user(
            db_session,
            email="diffip@cyphergy.ai",
            name="Diff IP User",
            password="SecurePass1",
        )
        await db_session.commit()

        await lock_ip(db_session, email="diffip@cyphergy.ai", ip_address="10.0.0.1")
        await db_session.commit()

        allowed = await check_ip(db_session, email="diffip@cyphergy.ai", ip_address="10.0.0.99")
        assert allowed is False

    @pytest.mark.asyncio
    async def test_revoke_blocks_access(self, db_session: AsyncSession) -> None:
        """Revoking beta access should block all further IP checks."""
        await approve_beta_user(
            db_session,
            email="revoke@cyphergy.ai",
            name="Revoke User",
            password="SecurePass1",
        )
        await db_session.commit()

        await lock_ip(db_session, email="revoke@cyphergy.ai", ip_address="10.0.0.1")
        await db_session.commit()

        revoked = await revoke_beta_access(db_session, email="revoke@cyphergy.ai")
        await db_session.commit()
        assert revoked is True

        allowed = await check_ip(db_session, email="revoke@cyphergy.ai", ip_address="10.0.0.1")
        assert allowed is False

    @pytest.mark.asyncio
    async def test_reset_ip_allows_relogin(self, db_session: AsyncSession) -> None:
        """Resetting the locked IP should allow re-login from a new IP address."""
        await approve_beta_user(
            db_session,
            email="resetip@cyphergy.ai",
            name="Reset IP User",
            password="SecurePass1",
        )
        await db_session.commit()

        await lock_ip(db_session, email="resetip@cyphergy.ai", ip_address="10.0.0.1")
        await db_session.commit()

        # Before reset, different IP is blocked
        allowed = await check_ip(db_session, email="resetip@cyphergy.ai", ip_address="10.0.0.2")
        assert allowed is False

        # Reset the IP
        reset = await reset_beta_ip(db_session, email="resetip@cyphergy.ai")
        await db_session.commit()
        assert reset is True

        # After reset, any IP passes (not yet locked)
        allowed = await check_ip(db_session, email="resetip@cyphergy.ai", ip_address="10.0.0.2")
        assert allowed is True

        # Lock to new IP
        invite = await lock_ip(db_session, email="resetip@cyphergy.ai", ip_address="10.0.0.2")
        await db_session.commit()
        assert invite is not None
        assert invite.locked_ip == "10.0.0.2"

    def test_middleware_blocks_wrong_ip(self) -> None:
        """BetaGateMiddleware should return 403 when client IP does not match locked IP."""
        app = FastAPI()

        # BetaGateMiddleware (inner — checks state)
        app.add_middleware(BetaGateMiddleware)

        # Inject middleware (outer — runs first, sets request state)
        class _InjectBetaState(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
                request.state.jwt_payload = {
                    "email": "test@cyphergy.ai",
                    "sub": "user1",
                }
                request.state.client_ip = "10.0.0.99"
                request.state.beta_locked_ip = "10.0.0.1"
                return await call_next(request)

        app.add_middleware(_InjectBetaState)

        @app.get("/api/v1/protected")
        async def protected() -> dict[str, str]:
            return {"status": "ok"}

        client = TestClient(app)
        resp = client.get("/api/v1/protected")
        assert resp.status_code == 403
        body = resp.json()
        assert "denied" in body["error"].lower() or "IP" in body["error"]

    def test_email_function_sends_invite(self) -> None:
        """send_beta_invite_email should return metadata with sent status."""
        result = send_beta_invite_email("invited@cyphergy.ai", "test-invite-code-123")

        assert result["to"] == "invited@cyphergy.ai"
        assert result["invite_code"] == "test-invite-code-123"
        assert result["status"] == "sent"
        assert "subject" in result
