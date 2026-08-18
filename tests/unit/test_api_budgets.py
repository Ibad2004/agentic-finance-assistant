"""Tests for the budget management API endpoints."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def register_user(prefix: str = "budget_user") -> dict[str, str]:
    """Register a user and return auth headers."""
    email = f"{prefix}_{uuid4().hex[:8]}@example.com"
    password = "BudgetTest123!"
    reg = client.post("/auth/register", json={"email": email, "password": password})
    assert reg.status_code == 201
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def get_food_category_id() -> str:
    """Return the Food category ID (seeded by seed_categories)."""
    from app.db.session import SessionLocal
    from app.db.models import TransactionCategory

    db = SessionLocal()
    try:
        cat = db.query(TransactionCategory).filter_by(name="Food").first()
        assert cat is not None, "Food category must be seeded"
        return str(cat.id)
    finally:
        db.close()


def get_transport_category_id() -> str:
    """Return the Transport category ID (seeded by seed_categories)."""
    from app.db.session import SessionLocal
    from app.db.models import TransactionCategory

    db = SessionLocal()
    try:
        cat = db.query(TransactionCategory).filter_by(name="Transport").first()
        assert cat is not None, "Transport category must be seeded"
        return str(cat.id)
    finally:
        db.close()


def create_budget(headers: dict, category_id: str, amount: str, start: str, end: str) -> dict:
    """Helper to create a budget and return the response JSON."""
    res = client.post(
        "/budgets",
        headers=headers,
        json={
            "category_id": category_id,
            "budget_amount": amount,
            "period_start": start,
            "period_end": end,
        },
    )
    return res


def import_transactions(headers: dict, account_id: str, csv_content: bytes) -> None:
    """Helper to import transactions into an account."""
    from io import BytesIO

    res = client.post(
        f"/accounts/{account_id}/transactions/import",
        headers=headers,
        files={"file": ("test.csv", BytesIO(csv_content), "text/csv")},
    )
    assert res.status_code == 200


def create_account(headers: dict) -> str:
    """Helper to create an account and return its ID."""
    res = client.post(
        "/accounts",
        headers=headers,
        json={"account_name": "Budget Test Account", "account_type": "current", "currency_code": "GBP"},
    )
    assert res.status_code == 201
    return res.json()["id"]


# --- CREATE BUDGET TESTS ---

def test_create_budget_success() -> None:
    headers = register_user("bcreate")
    category_id = get_food_category_id()
    res = create_budget(headers, category_id, "500.00", "2026-04-01", "2026-04-30")
    assert res.status_code == 201
    data = res.json()
    assert data["budget_amount"] == 500.0
    assert data["category_name"] == "Food"
    assert data["status"] == "under_budget"
    assert data["actual_spending"] == 0.0
    assert data["remaining"] == 500.0
    assert data["percentage_used"] == 0.0
    assert data["transaction_count"] == 0


def test_create_budget_duplicate_returns_409() -> None:
    headers = register_user("bdup")
    category_id = get_food_category_id()
    res1 = create_budget(headers, category_id, "500.00", "2026-05-01", "2026-05-31")
    assert res1.status_code == 201
    res2 = create_budget(headers, category_id, "600.00", "2026-05-01", "2026-05-31")
    assert res2.status_code == 409


def test_create_budget_zero_amount_rejected() -> None:
    headers = register_user("bzero")
    category_id = get_food_category_id()
    res = create_budget(headers, category_id, "0.00", "2026-04-01", "2026-04-30")
    assert res.status_code == 422


def test_create_budget_negative_amount_rejected() -> None:
    headers = register_user("bneg")
    category_id = get_food_category_id()
    res = create_budget(headers, category_id, "-100.00", "2026-04-01", "2026-04-30")
    assert res.status_code == 422


def test_create_budget_end_before_start_rejected() -> None:
    headers = register_user("bdate")
    category_id = get_food_category_id()
    res = create_budget(headers, category_id, "500.00", "2026-04-30", "2026-04-01")
    assert res.status_code == 409


def test_create_budget_requires_auth() -> None:
    res = client.post(
        "/budgets",
        json={
            "category_id": str(uuid4()),
            "budget_amount": "100.00",
            "period_start": "2026-04-01",
            "period_end": "2026-04-30",
        },
    )
    assert res.status_code == 401


# --- LIST BUDGETS TESTS ---

def test_list_budgets_empty() -> None:
    headers = register_user("blist_empty")
    res = client.get("/budgets", headers=headers)
    assert res.status_code == 200
    assert res.json() == []


def test_list_budgets_returns_all() -> None:
    headers = register_user("blist_all")
    food_id = get_food_category_id()
    transport_id = get_transport_category_id()
    create_budget(headers, food_id, "400.00", "2026-04-01", "2026-04-30")
    create_budget(headers, transport_id, "200.00", "2026-04-01", "2026-04-30")
    res = client.get("/budgets", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2


def test_list_budgets_user_isolation() -> None:
    headers_a = register_user("blist_iso_a")
    headers_b = register_user("blist_iso_b")
    food_id = get_food_category_id()
    create_budget(headers_a, food_id, "300.00", "2026-06-01", "2026-06-30")
    create_budget(headers_b, food_id, "250.00", "2026-06-01", "2026-06-30")

    res_a = client.get("/budgets", headers=headers_a)
    res_b = client.get("/budgets", headers=headers_b)
    assert len(res_a.json()) == 1
    assert len(res_b.json()) == 1
    assert res_a.json()[0]["budget_amount"] == 300.0
    assert res_b.json()[0]["budget_amount"] == 250.0


# --- GET BUDGET TESTS ---

def test_get_budget_success() -> None:
    headers = register_user("bget")
    food_id = get_food_category_id()
    create_res = create_budget(headers, food_id, "500.00", "2026-07-01", "2026-07-31")
    budget_id = create_res.json()["id"]
    res = client.get(f"/budgets/{budget_id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["id"] == budget_id


def test_get_budget_not_found() -> None:
    headers = register_user("bget_nf")
    res = client.get(f"/budgets/{uuid4()}", headers=headers)
    assert res.status_code == 404


def test_get_budget_cross_user_denied() -> None:
    headers_a = register_user("bget_xa")
    headers_b = register_user("bget_xb")
    food_id = get_food_category_id()
    create_res = create_budget(headers_a, food_id, "500.00", "2026-08-01", "2026-08-31")
    budget_id = create_res.json()["id"]
    res = client.get(f"/budgets/{budget_id}", headers=headers_b)
    assert res.status_code == 404


# --- UPDATE BUDGET TESTS ---

def test_update_budget_amount() -> None:
    headers = register_user("bupd_amt")
    food_id = get_food_category_id()
    create_res = create_budget(headers, food_id, "500.00", "2026-09-01", "2026-09-30")
    budget_id = create_res.json()["id"]
    res = client.patch(
        f"/budgets/{budget_id}",
        headers=headers,
        json={"budget_amount": "750.00"},
    )
    assert res.status_code == 200
    assert res.json()["budget_amount"] == 750.0


def test_update_budget_not_found() -> None:
    headers = register_user("bupd_nf")
    res = client.patch(
        f"/budgets/{uuid4()}",
        headers=headers,
        json={"budget_amount": "100.00"},
    )
    assert res.status_code == 404


def test_update_budget_cross_user_denied() -> None:
    headers_a = register_user("bupd_xa")
    headers_b = register_user("bupd_xb")
    food_id = get_food_category_id()
    create_res = create_budget(headers_a, food_id, "500.00", "2026-10-01", "2026-10-31")
    budget_id = create_res.json()["id"]
    res = client.patch(
        f"/budgets/{budget_id}",
        headers=headers_b,
        json={"budget_amount": "999.00"},
    )
    assert res.status_code == 404


# --- DELETE BUDGET TESTS ---

def test_delete_budget_success() -> None:
    headers = register_user("bdel")
    food_id = get_food_category_id()
    create_res = create_budget(headers, food_id, "500.00", "2026-11-01", "2026-11-30")
    budget_id = create_res.json()["id"]
    res = client.delete(f"/budgets/{budget_id}", headers=headers)
    assert res.status_code == 204
    # Verify deleted
    get_res = client.get(f"/budgets/{budget_id}", headers=headers)
    assert get_res.status_code == 404


def test_delete_budget_not_found() -> None:
    headers = register_user("bdel_nf")
    res = client.delete(f"/budgets/{uuid4()}", headers=headers)
    assert res.status_code == 404


def test_delete_budget_cross_user_denied() -> None:
    headers_a = register_user("bdel_xa")
    headers_b = register_user("bdel_xb")
    food_id = get_food_category_id()
    create_res = create_budget(headers_a, food_id, "500.00", "2026-12-01", "2026-12-31")
    budget_id = create_res.json()["id"]
    res = client.delete(f"/budgets/{budget_id}", headers=headers_b)
    assert res.status_code == 404


# --- SPENDING AGGREGATION TESTS ---

def test_budget_with_zero_spending() -> None:
    headers = register_user("bspend_zero")
    food_id = get_food_category_id()
    create_account(headers)
    res = create_budget(headers, food_id, "500.00", "2026-04-01", "2026-04-30")
    data = res.json()
    assert data["actual_spending"] == 0.0
    assert data["remaining"] == 500.0
    assert data["transaction_count"] == 0
    assert data["status"] == "under_budget"


def test_budget_with_spending_under_80_percent() -> None:
    headers = register_user("bspend_under80")
    food_id = get_food_category_id()
    account_id = create_account(headers)
    csv = b"transaction_date,description,debit,credit,balance,reference,currency\n2026-04-10,TESCO,100.00,,400.00,T1,GBP\n"
    import_transactions(headers, account_id, csv)
    # Categorize so spending is tracked
    from unittest.mock import MagicMock, patch

    mock_llm = MagicMock()
    mock_llm.categorize_batch.return_value = None
    with patch("app.agents.transaction_agent.GroqTransactionCategorizationLlm", return_value=mock_llm):
        client.post(f"/accounts/{account_id}/transactions/categorize", headers=headers)

    res = create_budget(headers, food_id, "500.00", "2026-04-01", "2026-04-30")
    data = res.json()
    assert data["actual_spending"] == 100.0
    assert data["status"] == "under_budget"


def test_budget_with_spending_near_limit() -> None:
    headers = register_user("bspend_near")
    food_id = get_food_category_id()
    account_id = create_account(headers)
    # Spend 450 of 500 = 90% -> near_limit
    csv = b"transaction_date,description,debit,credit,balance,reference,currency\n2026-04-10,TESCO,450.00,,50.00,T1,GBP\n"
    import_transactions(headers, account_id, csv)
    from unittest.mock import MagicMock, patch

    mock_llm = MagicMock()
    mock_llm.categorize_batch.return_value = None
    with patch("app.agents.transaction_agent.GroqTransactionCategorizationLlm", return_value=mock_llm):
        client.post(f"/accounts/{account_id}/transactions/categorize", headers=headers)

    res = create_budget(headers, food_id, "500.00", "2026-04-01", "2026-04-30")
    data = res.json()
    assert data["actual_spending"] == 450.0
    assert data["status"] == "near_limit"


def test_budget_over_budget() -> None:
    headers = register_user("bspend_over")
    food_id = get_food_category_id()
    account_id = create_account(headers)
    csv = b"transaction_date,description,debit,credit,balance,reference,currency\n2026-04-10,TESCO,600.00,,-100.00,T1,GBP\n"
    import_transactions(headers, account_id, csv)
    from unittest.mock import MagicMock, patch

    mock_llm = MagicMock()
    mock_llm.categorize_batch.return_value = None
    with patch("app.agents.transaction_agent.GroqTransactionCategorizationLlm", return_value=mock_llm):
        client.post(f"/accounts/{account_id}/transactions/categorize", headers=headers)

    res = create_budget(headers, food_id, "500.00", "2026-04-01", "2026-04-30")
    data = res.json()
    assert data["actual_spending"] == 600.0
    assert data["status"] == "over_budget"
    assert data["remaining"] == -100.0


def test_budget_spending_date_boundary_no_transactions_outside_range() -> None:
    headers = register_user("bspend_boundary")
    food_id = get_food_category_id()
    account_id = create_account(headers)
    # Transaction outside budget period
    csv = b"transaction_date,description,debit,credit,balance,reference,currency\n2026-05-05,TESCO,200.00,,300.00,T1,GBP\n"
    import_transactions(headers, account_id, csv)
    from unittest.mock import MagicMock, patch

    mock_llm = MagicMock()
    mock_llm.categorize_batch.return_value = None
    with patch("app.agents.transaction_agent.GroqTransactionCategorizationLlm", return_value=mock_llm):
        client.post(f"/accounts/{account_id}/transactions/categorize", headers=headers)

    res = create_budget(headers, food_id, "500.00", "2026-04-01", "2026-04-30")
    data = res.json()
    assert data["actual_spending"] == 0.0
    assert data["transaction_count"] == 0
    assert data["status"] == "under_budget"


def test_budget_multiple_transactions_aggregated() -> None:
    headers = register_user("bspend_multi")
    food_id = get_food_category_id()
    account_id = create_account(headers)
    csv = (
        b"transaction_date,description,debit,credit,balance,reference,currency\n"
        b"2026-04-10,TESCO,50.00,,450.00,T1,GBP\n"
        b"2026-04-15,TESCO,75.00,,375.00,T2,GBP\n"
        b"2026-04-20,TESCO,30.00,,345.00,T3,GBP\n"
    )
    import_transactions(headers, account_id, csv)
    from unittest.mock import MagicMock, patch

    mock_llm = MagicMock()
    mock_llm.categorize_batch.return_value = None
    with patch("app.agents.transaction_agent.GroqTransactionCategorizationLlm", return_value=mock_llm):
        client.post(f"/accounts/{account_id}/transactions/categorize", headers=headers)

    res = create_budget(headers, food_id, "200.00", "2026-04-01", "2026-04-30")
    data = res.json()
    assert data["actual_spending"] == 155.0
    assert data["transaction_count"] == 3
    assert data["remaining"] == 45.0
    assert data["status"] == "under_budget"


def test_budget_percentage_used_calculation() -> None:
    headers = register_user("bspend_pct")
    food_id = get_food_category_id()
    account_id = create_account(headers)
    csv = b"transaction_date,description,debit,credit,balance,reference,currency\n2026-04-10,TESCO,400.00,,100.00,T1,GBP\n"
    import_transactions(headers, account_id, csv)
    from unittest.mock import MagicMock, patch

    mock_llm = MagicMock()
    mock_llm.categorize_batch.return_value = None
    with patch("app.agents.transaction_agent.GroqTransactionCategorizationLlm", return_value=mock_llm):
        client.post(f"/accounts/{account_id}/transactions/categorize", headers=headers)

    res = create_budget(headers, food_id, "500.00", "2026-04-01", "2026-04-30")
    data = res.json()
    assert data["percentage_used"] == 0.8
    assert data["status"] == "near_limit"
