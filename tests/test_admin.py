"""Tests for the admin system.

Uses an async SQLite in-memory database for fast, isolated testing.
Each test gets a fresh database with all tables created.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.auth.admin import (
    admin_login,
    invite_beta_user,
    revoke_user,
    system_health,
)
from src.auth.signup import hash_password
from src.database.engine import Base
from src.database.models import BetaInvite, User

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_TEST_SECRET = "test-secret-key-for-admin-tests"
_ADMIN_PASSWORD = "AdminPass123"
_USER_PASSWORD = "UserPass1234"


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


async def _create_admin(db: AsyncSession) -> User:
    """Helper: create an admin user in the database."""
    admin = User(
        id=uuid.uuid4(),
        email="admin@cyphergy.ai",
        password_hash=hash_password(_ADMIN_PASSWORD),
        name="Admin User",
        is_admin=True,
    )
    db.add(admin)
    await db.flush()
    await db.refresh(admin)
    return admin


async def _create_regular_user(db: AsyncSession) -> User:
    """Helper: create a regular (non-admin) user in the database."""
    user = User(
        id=uuid.uuid4(),
        email="regular@cyphergy.ai",
        password_hash=hash_password(_USER_PASSWORD),
        name="Regular User",
        is_admin=False,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAdmin:
    """Tests for admin authentication and management."""

    @pytest.mark.asyncio
    async def test_admin_login_works(self, db_session: AsyncSession) -> None:
        """An admin user should receive a JWT on successful login."""
        await _create_admin(db_session)
        await db_session.commit()

        result = await admin_login(db_session, email="admin@cyphergy.ai", password=_ADMIN_PASSWORD)

        assert result is not None
        assert result["email"] == "admin@cyphergy.ai"
        assert result["name"] == "Admin User"
        assert result["is_admin"] == "true"
        assert len(result["token"]) > 0

    @pytest.mark.asyncio
    async def test_non_admin_blocked(self, db_session: AsyncSession) -> None:
        """A non-admin user should be denied admin login."""
        await _create_regular_user(db_session)
        await db_session.commit()

        result = await admin_login(db_session, email="regular@cyphergy.ai", password=_USER_PASSWORD)

        assert result is None

    @pytest.mark.asyncio
    async def test_invite_user_creates_beta_invite(self, db_session: AsyncSession) -> None:
        """invite_beta_user should create a BetaInvite record with a unique code."""
        invite = await invite_beta_user(db_session, email="newbeta@cyphergy.ai")
        await db_session.commit()

        assert invite.id is not None
        assert isinstance(invite.id, uuid.UUID)
        assert invite.email == "newbeta@cyphergy.ai"
        assert invite.is_approved is True
        assert invite.is_revoked is False
        assert invite.locked_ip is None
        assert len(invite.invite_code) > 0

    @pytest.mark.asyncio
    async def test_revoke_user_works(self, db_session: AsyncSession) -> None:
        """revoke_user should deactivate the user and revoke their beta invite."""
        user = await _create_regular_user(db_session)
        await db_session.commit()

        # Also create a beta invite for the user
        invite = BetaInvite(
            id=uuid.uuid4(),
            email=user.email,
            invite_code="test-code-for-revoke",
            is_approved=True,
        )
        db_session.add(invite)
        await db_session.commit()

        revoked = await revoke_user(db_session, email=user.email)
        await db_session.commit()

        assert revoked is True
        # Refresh to see updated state
        await db_session.refresh(user)
        await db_session.refresh(invite)
        assert user.is_active is False
        assert invite.is_revoked is True

    def test_system_health_returns_status(self) -> None:
        """system_health should return a dict with operational status."""
        health = system_health()

        assert health["status"] == "operational"
        assert health["database"] == "connected"
        assert health["llm_provider"] == "available"
        assert health["agents"] == 5
        assert health["beta_gate"] == "active"
