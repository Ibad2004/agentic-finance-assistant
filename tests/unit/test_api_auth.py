"""Unit and integration tests for authentication endpoints (/auth/register, /auth/login)."""

from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_register_success_returns_201_and_never_exposes_password_hash() -> None:
    unique_email = f"user_{uuid4().hex[:8]}@example.com"
    response = client.post(
        "/auth/register",
        json={
            "email": unique_email,
            "password": "SecurePassword123!",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == unique_email.lower()
    assert data["full_name"] == "Test User"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data
    assert "password_hash" not in data
    assert "password" not in data


def test_register_duplicate_email_returns_409_conflict() -> None:
    unique_email = f"duplicate_{uuid4().hex[:8]}@example.com"
    payload = {
        "email": unique_email,
        "password": "SecurePassword123!",
        "full_name": "First User",
    }
    first_res = client.post("/auth/register", json=payload)
    assert first_res.status_code == 201

    second_res = client.post("/auth/register", json=payload)
    assert second_res.status_code == 409
    assert "already exists" in second_res.json()["detail"].lower()


def test_register_invalid_email_or_short_password_returns_422() -> None:
    # Invalid email format
    res1 = client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": "validpassword123"},
    )
    assert res1.status_code == 422

    # Short password (< 8 chars)
    res2 = client.post(
        "/auth/register",
        json={"email": "valid@example.com", "password": "short"},
    )
    assert res2.status_code == 422


def test_login_success_returns_bearer_jwt_token() -> None:
    unique_email = f"login_test_{uuid4().hex[:8]}@example.com"
    password = "MyStrongPassword2026!"
    reg_res = client.post(
        "/auth/register",
        json={"email": unique_email, "password": password, "full_name": "Login User"},
    )
    assert reg_res.status_code == 201

    login_res = client.post(
        "/auth/login",
        json={"email": unique_email, "password": password},
    )
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert len(token_data["access_token"]) > 20


def test_login_invalid_password_returns_401() -> None:
    unique_email = f"wrong_pw_{uuid4().hex[:8]}@example.com"
    client.post(
        "/auth/register",
        json={"email": unique_email, "password": "CorrectPassword123!"},
    )
    login_res = client.post(
        "/auth/login",
        json={"email": unique_email, "password": "WrongPassword123!"},
    )
    assert login_res.status_code == 401
    assert "invalid email or password" in login_res.json()["detail"].lower()


def test_login_nonexistent_email_returns_401() -> None:
    login_res = client.post(
        "/auth/login",
        json={"email": "nobody_exists_here@example.com", "password": "SomePassword123!"},
    )
    assert login_res.status_code == 401


def test_protected_route_without_token_returns_401() -> None:
    res = client.get("/accounts")
    assert res.status_code == 401


def test_protected_route_with_invalid_token_returns_401() -> None:
    res = client.get("/accounts", headers={"Authorization": "Bearer invalid.jwt.token"})
    assert res.status_code == 401
