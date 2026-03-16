"""Database layer tests for Cyphergy.

Uses an async SQLite in-memory database for fast, isolated testing.
Each test gets a fresh database with all tables created.
"""

from __future__ import annotations

import uuid
from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database import crud
from src.database.engine import Base

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db_engine():
    """Create an async SQLite engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # Enable foreign key enforcement for SQLite
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
# User Tests
# ---------------------------------------------------------------------------


class TestUserCRUD:
    """Tests for user creation and retrieval."""

    @pytest.mark.asyncio
    async def test_create_user(self, db_session: AsyncSession) -> None:
        """Creating a user should return a User with a valid UUID and correct fields."""
        user = await crud.create_user(
            db_session,
            email="test@cyphergy.ai",
            password_hash="$2b$12$fakehashfortesting000000000000000000000000000000",
            name="Test User",
        )
        await db_session.commit()

        assert user.id is not None
        assert isinstance(user.id, uuid.UUID)
        assert user.email == "test@cyphergy.ai"
        assert user.name == "Test User"
        assert user.is_active is True

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, db_session: AsyncSession) -> None:
        """Looking up a user by email should return the correct user."""
        await crud.create_user(
            db_session,
            email="lookup@cyphergy.ai",
            password_hash="$2b$12$fakehashfortesting000000000000000000000000000000",
            name="Lookup User",
        )
        await db_session.commit()

        found = await crud.get_user_by_email(db_session, email="lookup@cyphergy.ai")
        assert found is not None
        assert found.email == "lookup@cyphergy.ai"
        assert found.name == "Lookup User"

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, db_session: AsyncSession) -> None:
        """Looking up a nonexistent email should return None."""
        found = await crud.get_user_by_email(db_session, email="nobody@cyphergy.ai")
        assert found is None

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, db_session: AsyncSession) -> None:
        """Looking up a user by UUID should return the correct user."""
        user = await crud.create_user(
            db_session,
            email="byid@cyphergy.ai",
            password_hash="$2b$12$fakehashfortesting000000000000000000000000000000",
            name="By ID User",
        )
        await db_session.commit()

        found = await crud.get_user_by_id(db_session, user_id=user.id)
        assert found is not None
        assert found.id == user.id
        assert found.email == "byid@cyphergy.ai"


# ---------------------------------------------------------------------------
# Case Tests
# ---------------------------------------------------------------------------


class TestCaseCRUD:
    """Tests for case creation and listing."""

    @pytest.mark.asyncio
    async def test_create_case(self, db_session: AsyncSession) -> None:
        """Creating a case should return a Case linked to the user."""
        user = await crud.create_user(
            db_session,
            email="cases@cyphergy.ai",
            password_hash="$2b$12$fakehashfortesting000000000000000000000000000000",
            name="Case User",
        )
        await db_session.commit()

        case = await crud.create_case(
            db_session,
            user_id=user.id,
            name="Smith v. Jones",
            jurisdiction="federal",
        )
        await db_session.commit()

        assert case.id is not None
        assert isinstance(case.id, uuid.UUID)
        assert case.name == "Smith v. Jones"
        assert case.jurisdiction == "federal"
        assert case.status == "active"
        assert case.user_id == user.id

    @pytest.mark.asyncio
    async def test_get_cases_for_user(self, db_session: AsyncSession) -> None:
        """Listing cases for a user should return all their cases."""
        user = await crud.create_user(
            db_session,
            email="multicases@cyphergy.ai",
            password_hash="$2b$12$fakehashfortesting000000000000000000000000000000",
            name="Multi Case User",
        )
        await db_session.commit()

        await crud.create_case(db_session, user_id=user.id, name="Case Alpha")
        await crud.create_case(db_session, user_id=user.id, name="Case Beta")
        await crud.create_case(
            db_session,
            user_id=user.id,
            name="Case Gamma",
            jurisdiction="california",
        )
        await db_session.commit()

        cases = await crud.get_cases_for_user(db_session, user_id=user.id)
        assert len(cases) == 3
        names = {c.name for c in cases}
        assert names == {"Case Alpha", "Case Beta", "Case Gamma"}

    @pytest.mark.asyncio
    async def test_get_cases_for_user_empty(self, db_session: AsyncSession) -> None:
        """A user with no cases should return an empty list."""
        user = await crud.create_user(
            db_session,
            email="nocases@cyphergy.ai",
            password_hash="$2b$12$fakehashfortesting000000000000000000000000000000",
            name="No Cases User",
        )
        await db_session.commit()

        cases = await crud.get_cases_for_user(db_session, user_id=user.id)
        assert cases == []

    @pytest.mark.asyncio
    async def test_get_case_by_id(self, db_session: AsyncSession) -> None:
        """Looking up a case by UUID should return the correct case."""
        user = await crud.create_user(
            db_session,
            email="caseid@cyphergy.ai",
            password_hash="$2b$12$fakehashfortesting000000000000000000000000000000",
            name="Case ID User",
        )
        await db_session.commit()

        case = await crud.create_case(db_session, user_id=user.id, name="Specific Case")
        await db_session.commit()

        found = await crud.get_case_by_id(db_session, case_id=case.id)
        assert found is not None
        assert found.id == case.id
        assert found.name == "Specific Case"


# ---------------------------------------------------------------------------
# Message Tests
# ---------------------------------------------------------------------------


class TestMessageCRUD:
    """Tests for message creation and retrieval."""

    @pytest.mark.asyncio
    async def test_create_message_user(self, db_session: AsyncSession) -> None:
        """Creating a user message should store it with role='user'."""
        user = await crud.create_user(
            db_session,
            email="msguser@cyphergy.ai",
            password_hash="$2b$12$fakehashfortesting000000000000000000000000000000",
            name="Msg User",
        )
        await db_session.commit()

        case = await crud.create_case(db_session, user_id=user.id, name="Message Case")
        await db_session.commit()

        msg = await crud.create_message(
            db_session,
            case_id=case.id,
            role="user",
            content="What is the statute of limitations in California?",
        )
        await db_session.commit()

        assert msg.id is not None
        assert msg.role == "user"
        assert msg.content == "What is the statute of limitations in California?"
        assert msg.agent_id is None
        assert msg.confidence is None
        assert msg.citations is None

    @pytest.mark.asyncio
    async def test_create_message_assistant(self, db_session: AsyncSession) -> None:
        """Creating an assistant message should store agent_id, confidence, and citations."""
        user = await crud.create_user(
            db_session,
            email="msgasst@cyphergy.ai",
            password_hash="$2b$12$fakehashfortesting000000000000000000000000000000",
            name="Msg Asst User",
        )
        await db_session.commit()

        case = await crud.create_case(db_session, user_id=user.id, name="Assistant Message Case")
        await db_session.commit()

        citations = ["Cal. Civ. Proc. Code 335.1", "28 U.S.C. 1332"]
        msg = await crud.create_message(
            db_session,
            case_id=case.id,
            role="assistant",
            content="The statute of limitations for personal injury in California is two years.",
            agent_id="lead_counsel",
            confidence=0.92,
            citations=citations,
        )
        await db_session.commit()

        assert msg.role == "assistant"
        assert msg.agent_id == "lead_counsel"
        assert msg.confidence == 0.92
        assert msg.citations == citations

    @pytest.mark.asyncio
    async def test_get_messages_for_case(self, db_session: AsyncSession) -> None:
        """Retrieving messages should return all messages for the case in order."""
        user = await crud.create_user(
            db_session,
            email="msglist@cyphergy.ai",
            password_hash="$2b$12$fakehashfortesting000000000000000000000000000000",
            name="Msg List User",
        )
        await db_session.commit()

        case = await crud.create_case(db_session, user_id=user.id, name="List Message Case")
        await db_session.commit()

        await crud.create_message(
            db_session,
            case_id=case.id,
            role="user",
            content="First question",
        )
        await crud.create_message(
            db_session,
            case_id=case.id,
            role="assistant",
            content="First answer",
            agent_id="lead_counsel",
            confidence=0.88,
        )
        await crud.create_message(
            db_session,
            case_id=case.id,
            role="user",
            content="Follow-up question",
        )
        await db_session.commit()

        messages = await crud.get_messages_for_case(db_session, case_id=case.id)
        assert len(messages) == 3
        assert messages[0].role == "user"
        assert messages[0].content == "First question"
        assert messages[1].role == "assistant"
        assert messages[2].content == "Follow-up question"


# ---------------------------------------------------------------------------
# Deadline Tests
# ---------------------------------------------------------------------------


class TestDeadlineCRUD:
    """Tests for deadline creation and retrieval."""

    @pytest.mark.asyncio
    async def test_create_deadline(self, db_session: AsyncSession) -> None:
        """Creating a deadline should store all fields correctly."""
        user = await crud.create_user(
            db_session,
            email="deadline@cyphergy.ai",
            password_hash="$2b$12$fakehashfortesting000000000000000000000000000000",
            name="Deadline User",
        )
        await db_session.commit()

        case = await crud.create_case(db_session, user_id=user.id, name="Deadline Case")
        await db_session.commit()

        deadline = await crud.create_deadline(
            db_session,
            case_id=case.id,
            title="Answer to Complaint",
            deadline_date=date(2026, 5, 15),
            deadline_type="answer",
            jurisdiction="federal",
            rule_citation="FRCP Rule 12(a)(1)(A)(i)",
        )
        await db_session.commit()

        assert deadline.id is not None
        assert isinstance(deadline.id, uuid.UUID)
        assert deadline.title == "Answer to Complaint"
        assert deadline.deadline_date == date(2026, 5, 15)
        assert deadline.deadline_type == "answer"
        assert deadline.jurisdiction == "federal"
        assert deadline.rule_citation == "FRCP Rule 12(a)(1)(A)(i)"
        assert deadline.status == "pending"

    @pytest.mark.asyncio
    async def test_deadline_days_remaining(self, db_session: AsyncSession) -> None:
        """The days_remaining property should compute correctly."""
        user = await crud.create_user(
            db_session,
            email="daysrem@cyphergy.ai",
            password_hash="$2b$12$fakehashfortesting000000000000000000000000000000",
            name="Days Remaining User",
        )
        await db_session.commit()

        case = await crud.create_case(db_session, user_id=user.id, name="Days Remaining Case")
        await db_session.commit()

        # Use a date far in the future to ensure positive days_remaining
        future_date = date(2099, 12, 31)
        deadline = await crud.create_deadline(
            db_session,
            case_id=case.id,
            title="Far Future Deadline",
            deadline_date=future_date,
            deadline_type="motion",
            jurisdiction="california",
            rule_citation="CCP 1005(b)",
        )
        await db_session.commit()

        assert deadline.days_remaining > 0

    @pytest.mark.asyncio
    async def test_get_deadlines_for_case(self, db_session: AsyncSession) -> None:
        """Retrieving deadlines should return all deadlines for the case ordered by date."""
        user = await crud.create_user(
            db_session,
            email="dllist@cyphergy.ai",
            password_hash="$2b$12$fakehashfortesting000000000000000000000000000000",
            name="Deadline List User",
        )
        await db_session.commit()

        case = await crud.create_case(db_session, user_id=user.id, name="Deadline List Case")
        await db_session.commit()

        # Create in non-chronological order to verify sorting
        await crud.create_deadline(
            db_session,
            case_id=case.id,
            title="Later Deadline",
            deadline_date=date(2026, 8, 1),
            deadline_type="trial",
            jurisdiction="federal",
            rule_citation="FRCP Rule 16",
        )
        await crud.create_deadline(
            db_session,
            case_id=case.id,
            title="Earlier Deadline",
            deadline_date=date(2026, 4, 15),
            deadline_type="answer",
            jurisdiction="federal",
            rule_citation="FRCP Rule 12(a)(1)(A)(i)",
        )
        await db_session.commit()

        deadlines = await crud.get_deadlines_for_case(db_session, case_id=case.id)
        assert len(deadlines) == 2
        # Should be ordered by deadline_date ascending
        assert deadlines[0].title == "Earlier Deadline"
        assert deadlines[1].title == "Later Deadline"

    @pytest.mark.asyncio
    async def test_get_deadlines_for_case_empty(self, db_session: AsyncSession) -> None:
        """A case with no deadlines should return an empty list."""
        user = await crud.create_user(
            db_session,
            email="nodl@cyphergy.ai",
            password_hash="$2b$12$fakehashfortesting000000000000000000000000000000",
            name="No Deadlines User",
        )
        await db_session.commit()

        case = await crud.create_case(db_session, user_id=user.id, name="No Deadlines Case")
        await db_session.commit()

        deadlines = await crud.get_deadlines_for_case(db_session, case_id=case.id)
        assert deadlines == []


# ---------------------------------------------------------------------------
# Model property tests
# ---------------------------------------------------------------------------


class TestModelProperties:
    """Tests for model __repr__ and computed properties."""

    @pytest.mark.asyncio
    async def test_user_repr(self, db_session: AsyncSession) -> None:
        """User __repr__ should contain id and email."""
        user = await crud.create_user(
            db_session,
            email="repr@cyphergy.ai",
            password_hash="$2b$12$fakehashfortesting000000000000000000000000000000",
            name="Repr User",
        )
        await db_session.commit()

        repr_str = repr(user)
        assert "repr@cyphergy.ai" in repr_str
        assert "User" in repr_str

    @pytest.mark.asyncio
    async def test_case_repr(self, db_session: AsyncSession) -> None:
        """Case __repr__ should contain id and name."""
        user = await crud.create_user(
            db_session,
            email="caserepr@cyphergy.ai",
            password_hash="$2b$12$fakehashfortesting000000000000000000000000000000",
            name="Case Repr User",
        )
        await db_session.commit()

        case = await crud.create_case(db_session, user_id=user.id, name="Repr Case")
        await db_session.commit()

        repr_str = repr(case)
        assert "Repr Case" in repr_str
        assert "Case" in repr_str
