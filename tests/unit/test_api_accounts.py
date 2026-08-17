"""Unit and integration tests for accounts API endpoints (/accounts)."""

from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def register_and_get_auth_header(email_prefix: str = "account_user") -> dict[str, str]:
    email = f"{email_prefix}_{uuid4().hex[:8]}@example.com"
    password = "Password123!"
    reg_res = client.post("/auth/register", json={"email": email, "password": password})
    assert reg_res.status_code == 201

    login_res = client.post("/auth/login", json={"email": email, "password": password})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_account_success_without_exposing_user_id() -> None:
    headers = register_and_get_auth_header("create_acc")
    response = client.post(
        "/accounts",
        headers=headers,
        json={
            "account_name": "Main Checking Account",
            "account_type": "current",
            "currency_code": "GBP",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["account_name"] == "Main Checking Account"
    assert data["account_type"] == "current"
    assert data["currency_code"] == "GBP"
    assert "id" in data
    assert "created_at" in data
    assert "user_id" not in data  # Ownership is in JWT, user_id is never exposed


def test_create_account_invalid_currency_rejected() -> None:
    headers = register_and_get_auth_header("invalid_curr")
    response = client.post(
        "/accounts",
        headers=headers,
        json={
            "account_name": "USD Account",
            "account_type": "current",
            "currency_code": "USD",
        },
    )
    assert response.status_code == 422


def test_create_account_invalid_type_rejected() -> None:
    headers = register_and_get_auth_header("invalid_type")
    response = client.post(
        "/accounts",
        headers=headers,
        json={
            "account_name": "Crypto Account",
            "account_type": "crypto",
            "currency_code": "GBP",
        },
    )
    assert response.status_code == 422


def test_list_accounts_enforces_user_isolation() -> None:
    headers_a = register_and_get_auth_header("user_a")
    headers_b = register_and_get_auth_header("user_b")

    # User A creates 2 accounts
    res_a1 = client.post(
        "/accounts",
        headers=headers_a,
        json={"account_name": "User A Current", "account_type": "current", "currency_code": "GBP"},
    )
    res_a2 = client.post(
        "/accounts",
        headers=headers_a,
        json={"account_name": "User A Savings", "account_type": "savings", "currency_code": "GBP"},
    )
    assert res_a1.status_code == 201
    assert res_a2.status_code == 201

    # User B creates 1 account
    res_b1 = client.post(
        "/accounts",
        headers=headers_b,
        json={"account_name": "User B Current", "account_type": "current", "currency_code": "GBP"},
    )
    assert res_b1.status_code == 201

    # User A lists accounts
    list_a = client.get("/accounts", headers=headers_a)
    assert list_a.status_code == 200
    names_a = [acc["account_name"] for acc in list_a.json()]
    assert "User A Current" in names_a
    assert "User A Savings" in names_a
    assert "User B Current" not in names_a

    # User B lists accounts
    list_b = client.get("/accounts", headers=headers_b)
    assert list_b.status_code == 200
    names_b = [acc["account_name"] for acc in list_b.json()]
    assert "User B Current" in names_b
    assert "User A Current" not in names_b
    assert "User A Savings" not in names_b
