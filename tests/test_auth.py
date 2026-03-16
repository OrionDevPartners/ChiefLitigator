"""Tests for JWT authentication handler and middleware."""

from __future__ import annotations

import time

import jwt
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.auth.jwt_handler import JWTHandler
from src.auth.middleware import JWTAuthMiddleware

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_TEST_SECRET = "test-secret-key-for-unit-tests"


@pytest.fixture(autouse=True)
def _set_jwt_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure JWT_SECRET_KEY is set for every test."""
    monkeypatch.setenv("JWT_SECRET_KEY", _TEST_SECRET)


@pytest.fixture()
def handler() -> JWTHandler:
    return JWTHandler()


@pytest.fixture()
def app() -> FastAPI:
    """Minimal FastAPI app with JWT middleware and test routes."""
    _app = FastAPI()
    _app.add_middleware(JWTAuthMiddleware)

    @_app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @_app.get("/health/ready")
    async def health_ready() -> dict[str, str]:
        return {"ready": "true"}

    @_app.get("/api/v1/protected")
    async def protected(request: Request) -> dict[str, object]:
        payload = getattr(request.state, "jwt_payload", {})
        return {"message": "authorized", "sub": payload.get("sub")}

    @_app.post("/api/v1/action")
    async def action() -> dict[str, str]:
        return {"result": "done"}

    @_app.get("/other")
    async def other() -> dict[str, str]:
        return {"page": "public"}

    return _app


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# JWTHandler — token creation
# ---------------------------------------------------------------------------


class TestJWTHandlerCreate:
    def test_create_token_returns_string(self, handler: JWTHandler) -> None:
        token = handler.create_token({"sub": "user1"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_token_contains_claims(self, handler: JWTHandler) -> None:
        token = handler.create_token({"sub": "user1", "role": "admin"})
        decoded = jwt.decode(token, _TEST_SECRET, algorithms=["HS256"])
        assert decoded["sub"] == "user1"
        assert decoded["role"] == "admin"
        assert "iat" in decoded
        assert "exp" in decoded

    def test_create_token_exp_defaults_to_30_min(self, handler: JWTHandler) -> None:
        token = handler.create_token({"sub": "u"})
        decoded = jwt.decode(token, _TEST_SECRET, algorithms=["HS256"])
        assert decoded["exp"] - decoded["iat"] == 1800

    def test_create_token_custom_expiry(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JWT_EXPIRY_SECONDS", "600")
        h = JWTHandler()
        token = h.create_token({"sub": "u"})
        decoded = jwt.decode(token, _TEST_SECRET, algorithms=["HS256"])
        assert decoded["exp"] - decoded["iat"] == 600


# ---------------------------------------------------------------------------
# JWTHandler — token verification
# ---------------------------------------------------------------------------


class TestJWTHandlerVerify:
    def test_verify_valid_token(self, handler: JWTHandler) -> None:
        token = handler.create_token({"sub": "user1"})
        payload = handler.verify_token(token)
        assert payload["sub"] == "user1"

    def test_verify_expired_token_raises(self, handler: JWTHandler) -> None:
        expired_payload = {
            "sub": "user1",
            "iat": int(time.time()) - 7200,
            "exp": int(time.time()) - 3600,
        }
        token = jwt.encode(expired_payload, _TEST_SECRET, algorithm="HS256")
        with pytest.raises(jwt.ExpiredSignatureError):
            handler.verify_token(token)

    def test_verify_invalid_signature_raises(self, handler: JWTHandler) -> None:
        token = jwt.encode(
            {"sub": "user1", "exp": int(time.time()) + 3600},
            "wrong-secret",
            algorithm="HS256",
        )
        with pytest.raises(jwt.InvalidTokenError):
            handler.verify_token(token)

    def test_verify_malformed_token_raises(self, handler: JWTHandler) -> None:
        with pytest.raises(jwt.InvalidTokenError):
            handler.verify_token("not.a.jwt")

    def test_verify_empty_token_raises(self, handler: JWTHandler) -> None:
        with pytest.raises(jwt.InvalidTokenError):
            handler.verify_token("")


# ---------------------------------------------------------------------------
# JWTHandler — configuration errors
# ---------------------------------------------------------------------------


class TestJWTHandlerConfig:
    def test_missing_secret_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
            JWTHandler()

    def test_invalid_expiry_falls_back_to_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JWT_EXPIRY_SECONDS", "not-a-number")
        h = JWTHandler()
        token = h.create_token({"sub": "u"})
        decoded = jwt.decode(token, _TEST_SECRET, algorithms=["HS256"])
        assert decoded["exp"] - decoded["iat"] == 1800


# ---------------------------------------------------------------------------
# Middleware — public routes (no token required)
# ---------------------------------------------------------------------------


class TestMiddlewarePublicRoutes:
    def test_health_endpoint_is_public(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_health_ready_endpoint_is_public(self, client: TestClient) -> None:
        resp = client.get("/health/ready")
        assert resp.status_code == 200

    def test_non_api_v1_route_is_public(self, client: TestClient) -> None:
        resp = client.get("/other")
        assert resp.status_code == 200
        assert resp.json()["page"] == "public"


# ---------------------------------------------------------------------------
# Middleware — protected routes (token required)
# ---------------------------------------------------------------------------


class TestMiddlewareProtectedRoutes:
    def test_missing_auth_header_returns_401(self, client: TestClient) -> None:
        resp = client.get("/api/v1/protected")
        assert resp.status_code == 401
        assert "Missing Authorization header" in resp.json()["error"]

    def test_malformed_auth_header_returns_401(self, client: TestClient) -> None:
        resp = client.get("/api/v1/protected", headers={"Authorization": "Token abc"})
        assert resp.status_code == 401
        assert "Invalid Authorization header format" in resp.json()["error"]

    def test_bearer_only_no_token_returns_401(self, client: TestClient) -> None:
        resp = client.get("/api/v1/protected", headers={"Authorization": "Bearer"})
        assert resp.status_code == 401

    def test_expired_token_returns_401(self, client: TestClient) -> None:
        expired = jwt.encode(
            {"sub": "u", "iat": int(time.time()) - 7200, "exp": int(time.time()) - 3600},
            _TEST_SECRET,
            algorithm="HS256",
        )
        resp = client.get("/api/v1/protected", headers={"Authorization": f"Bearer {expired}"})
        assert resp.status_code == 401
        assert "expired" in resp.json()["error"].lower()

    def test_invalid_token_returns_401(self, client: TestClient) -> None:
        resp = client.get(
            "/api/v1/protected",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401
        assert "Invalid token" in resp.json()["error"]

    def test_valid_token_passes_through(self, client: TestClient, handler: JWTHandler) -> None:
        token = handler.create_token({"sub": "user42"})
        resp = client.get("/api/v1/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "authorized"
        assert data["sub"] == "user42"

    def test_valid_token_on_post_route(self, client: TestClient, handler: JWTHandler) -> None:
        token = handler.create_token({"sub": "user1"})
        resp = client.post("/api/v1/action", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["result"] == "done"

    def test_options_request_passes_without_token(self, client: TestClient) -> None:
        resp = client.options("/api/v1/protected")
        # OPTIONS should not be blocked by auth
        assert resp.status_code != 401
