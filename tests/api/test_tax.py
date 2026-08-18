"""Tests for the tax API endpoints."""

from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def register_user(email_prefix: str = "tax_user") -> dict[str, str]:
    """Register a user and return the auth header."""
    email = f"{email_prefix}_{uuid4().hex[:8]}@example.com"
    password = "securepassword123"
    reg_res = client.post("/auth/register", json={"email": email, "password": password})
    assert reg_res.status_code == 201, f"Registration failed: {reg_res.text}"
    login_res = client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_estimate_tax_success() -> None:
    """Test successful tax estimation."""
    headers = register_user("estimate_success")
    payload = {
        "total_income": "50000.00",
        "custom_allowance": "0.00",
    }
    response = client.post("/tax/estimate", json=payload, headers=headers)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["total_income"] == 50000.0
    # With custom_allowance=0, personal allowance is 0, so taxable income is 50000
    # Tax: 37700*0.2 + (50000-37700)*0.4 = 7540 + 4920 = 12460
    assert data["income_tax_due"] == 12460.0
    assert data["total_allowances"] == 0.0
    assert data["taxable_income"] == 50000.0
    assert data["id"] is not None
    assert data["user_id"] is not None
    assert data["calculated_at"] is not None
    # Check that the calculation is persisted (we can't directly check without repo, but we trust the agent)
    # Check that the response includes the required fields
    assert len(data["band_breakdown"]) == 3


def test_estimate_tax_missing_jwt() -> None:
    """Test endpoint without JWT."""
    payload = {
        "total_income": "50000.00",
        "custom_allowance": "0.00",
    }
    response = client.post("/tax/estimate", json=payload)
    assert response.status_code == 401


def test_estimate_tax_invalid_jwt() -> None:
    """Test endpoint with invalid JWT."""
    headers = {"Authorization": "Bearer invalidtoken"}
    payload = {
        "total_income": "50000.00",
        "custom_allowance": "0.00",
    }
    response = client.post("/tax/estimate", json=payload, headers=headers)
    assert response.status_code == 401


def test_estimate_tax_invalid_income() -> None:
    """Test endpoint with invalid income (negative)."""
    headers = register_user("invalid_income")
    payload = {
        "total_income": "-100.00",
        "custom_allowance": "0.00",
    }
    response = client.post("/tax/estimate", json=payload, headers=headers)
    assert response.status_code == 422  # Validation error


def test_estimate_tax_custom_allowance() -> None:
    """Test TaxAgent with a custom allowance."""
    headers = register_user("custom_allowance")
    payload = {
        "total_income": "30000.00",
        "custom_allowance": "15000.00",
    }
    response = client.post("/tax/estimate", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_allowances"] == 15000.0
    # Taxable income = 30000 - 15000 = 15000
    # Tax = 15000 * 0.2 = 3000.00
    assert data["income_tax_due"] == 3000.0
    assert data["taxable_income"] == 15000.0


def test_list_tax_calculations() -> None:
    """Test listing tax calculations for the user."""
    headers = register_user("list_calcs")
    # Create two calculations
    payload1 = {"total_income": "50000.00", "custom_allowance": "0.00"}
    payload2 = {"total_income": "60000.00", "custom_allowance": "0.00"}
    response1 = client.post("/tax/estimate", json=payload1, headers=headers)
    assert response1.status_code == 200
    response2 = client.post("/tax/estimate", json=payload2, headers=headers)
    assert response2.status_code == 200
    # Now list
    response = client.get("/tax/calculations", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    # Check that the calculations belong to the user
    user_id = data[0]["user_id"]
    assert all(calc["user_id"] == user_id for calc in data)
    # Check the amounts
    amounts = {calc["total_income"] for calc in data}
    assert amounts == {50000.0, 60000.0}


def test_get_tax_calculation() -> None:
    """Test getting a specific tax calculation."""
    headers = register_user("get_calc")
    # Create a calculation
    payload = {"total_income": "50000.00", "custom_allowance": "0.00"}
    response = client.post("/tax/estimate", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    calc_id = data["id"]
    # Get the calculation
    response = client.get(f"/tax/calculations/{calc_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == calc_id
    assert data["total_income"] == 50000.0


def test_get_tax_calculation_not_found() -> None:
    """Test getting a non-existent calculation."""
    headers = register_user("not_found")
    random_id = uuid4()
    response = client.get(f"/tax/calculations/{random_id}", headers=headers)
    assert response.status_code == 404


def test_get_tax_calculation_wrong_user() -> None:
    """Test that a user cannot access another user's calculation."""
    # Create two users
    headers_a = register_user("user_a")
    headers_b = register_user("user_b")
    # User A creates a calculation
    payload = {"total_income": "50000.00", "custom_allowance": "0.00"}
    response = client.post("/tax/estimate", json=payload, headers=headers_a)
    assert response.status_code == 200
    calc_id = response.json()["id"]
    # User A can see their calculation
    response = client.get(f"/tax/calculations/{calc_id}", headers=headers_a)
    assert response.status_code == 200
    # User B cannot see user A's calculation
    response = client.get(f"/tax/calculations/{calc_id}", headers=headers_b)
    assert response.status_code == 404


def test_tax_result_includes_disclaimer() -> None:
    """Test that the tax result includes assumptions, limitations, and rules_version."""
    headers = register_user("disclaimer")
    payload = {"total_income": "50000.00", "custom_allowance": "0.00"}
    response = client.post("/tax/estimate", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "assumptions" in data
    assert "limitations" in data
    assert "rules_version" in data
    assert data["rules_version"] == "2026_27_england_v1"
    assert isinstance(data["assumptions"], str)
    assert len(data["assumptions"]) > 0
    assert isinstance(data["limitations"], str)
    assert len(data["limitations"]) > 0
    # Check that the assumptions and limitations are from the engine
    assert "UK resident" in data["assumptions"]
    assert "NOT constitute an official HMRC tax determination" in data["limitations"]