"""Tests for the transaction filtering endpoint."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

CSV_MULTI = b"""transaction_date,description,debit,credit,balance,reference,currency
2026-04-06,ACME PAYROLL LTD,,3000.00,3000.00,SAL-APR,GBP
2026-04-07,TESCO STORES 1234,63.28,,2936.72,TESCO-1,GBP
2026-04-10,TFL TRAVEL CHARGE,8.50,,2928.22,TFL-1,GBP
2026-04-15,OCTOPUS ENERGY,92.00,,2836.22,ENERGY-1,GBP
2026-04-18,M&S FOODHALL,34.70,,2801.52,MS-1,GBP
2026-04-20,NETFLIX.COM,10.99,,2790.53,NET-1,GBP
2026-05-05,TESCO STORES 5678,45.00,,2745.53,TESCO-2,GBP
"""


def register_user(prefix: str = "txfilt") -> dict[str, str]:
    email = f"{prefix}_{uuid4().hex[:8]}@example.com"
    password = "FilterTest123!"
    reg = client.post("/auth/register", json={"email": email, "password": password})
    assert reg.status_code == 201
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def create_account(headers: dict) -> str:
    res = client.post(
        "/accounts",
        headers=headers,
        json={"account_name": "Filter Test Account", "account_type": "current", "currency_code": "GBP"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def import_and_categorize(headers: dict, account_id: str, csv: bytes = CSV_MULTI) -> None:
    res = client.post(
        f"/accounts/{account_id}/transactions/import",
        headers=headers,
        files={"file": ("test.csv", BytesIO(csv), "text/csv")},
    )
    assert res.status_code == 200
    mock_llm = MagicMock()
    mock_llm.categorize_batch.return_value = None
    with patch("app.agents.transaction_agent.GroqTransactionCategorizationLlm", return_value=mock_llm):
        client.post(f"/accounts/{account_id}/transactions/categorize", headers=headers)


def list_tx(headers: dict, account_id: str, **params) -> dict:
    res = client.get(f"/accounts/{account_id}/transactions", headers=headers, params=params)
    assert res.status_code == 200
    return res.json()


# --- NO FILTER (baseline) ---

def test_list_no_filters_returns_all() -> None:
    headers = register_user("nfilt")
    account_id = create_account(headers)
    import_and_categorize(headers, account_id)
    data = list_tx(headers, account_id)
    assert data["total_count"] == 7


# --- START_DATE FILTER ---

def test_start_date_filters_correctly() -> None:
    headers = register_user("sdate")
    account_id = create_account(headers)
    import_and_categorize(headers, account_id)
    data = list_tx(headers, account_id, start_date="2026-04-10")
    assert data["total_count"] == 5
    for tx in data["transactions"]:
        assert tx["transaction_date"] >= "2026-04-10"


def test_start_date_no_matches() -> None:
    headers = register_user("sdate_nomatch")
    account_id = create_account(headers)
    import_and_categorize(headers, account_id)
    data = list_tx(headers, account_id, start_date="2027-01-01")
    assert data["total_count"] == 0
    assert data["transactions"] == []


# --- END_DATE FILTER ---

def test_end_date_filters_correctly() -> None:
    headers = register_user("edate")
    account_id = create_account(headers)
    import_and_categorize(headers, account_id)
    data = list_tx(headers, account_id, end_date="2026-04-30")
    assert data["total_count"] == 6
    for tx in data["transactions"]:
        assert tx["transaction_date"] <= "2026-04-30"


def test_end_date_no_matches() -> None:
    headers = register_user("edate_nomatch")
    account_id = create_account(headers)
    import_and_categorize(headers, account_id)
    data = list_tx(headers, account_id, end_date="2026-03-01")
    assert data["total_count"] == 0


# --- DATE RANGE COMBINED ---

def test_date_range_combined() -> None:
    headers = register_user("drange")
    account_id = create_account(headers)
    import_and_categorize(headers, account_id)
    data = list_tx(headers, account_id, start_date="2026-04-10", end_date="2026-04-18")
    assert data["total_count"] == 3
    for tx in data["transactions"]:
        assert "2026-04-10" <= tx["transaction_date"] <= "2026-04-18"


# --- TRANSACTION TYPE FILTER ---

def test_filter_income_only() -> None:
    headers = register_user("ttype_inc")
    account_id = create_account(headers)
    import_and_categorize(headers, account_id)
    data = list_tx(headers, account_id, transaction_type="income")
    assert data["total_count"] == 1
    assert data["transactions"][0]["transaction_type"] == "income"


def test_filter_expense_only() -> None:
    headers = register_user("ttype_exp")
    account_id = create_account(headers)
    import_and_categorize(headers, account_id)
    data = list_tx(headers, account_id, transaction_type="expense")
    assert data["total_count"] == 6
    for tx in data["transactions"]:
        assert tx["transaction_type"] == "expense"


# --- AMOUNT FILTERS ---

def test_min_amount_filter() -> None:
    headers = register_user("min_amt")
    account_id = create_account(headers)
    import_and_categorize(headers, account_id)
    data = list_tx(headers, account_id, min_amount="90.00")
    assert data["total_count"] == 2
    for tx in data["transactions"]:
        assert float(tx["amount"]) >= 90.0


def test_max_amount_filter() -> None:
    headers = register_user("max_amt")
    account_id = create_account(headers)
    import_and_categorize(headers, account_id)
    data = list_tx(headers, account_id, max_amount="15.00")
    assert data["total_count"] == 2
    for tx in data["transactions"]:
        assert float(tx["amount"]) <= 15.0


def test_amount_range_combined() -> None:
    headers = register_user("amt_range")
    account_id = create_account(headers)
    import_and_categorize(headers, account_id)
    data = list_tx(headers, account_id, min_amount="30.00", max_amount="100.00")
    assert data["total_count"] == 4
    for tx in data["transactions"]:
        assert 30.0 <= float(tx["amount"]) <= 100.0


# --- CATEGORY FILTER ---

def test_category_filter() -> None:
    headers = register_user("cat_filt")
    account_id = create_account(headers)
    import_and_categorize(headers, account_id)

    from app.db.session import SessionLocal
    from app.db.models import TransactionCategory

    db = SessionLocal()
    try:
        food_cat = db.query(TransactionCategory).filter_by(name="Food").first()
        food_id = str(food_cat.id)
    finally:
        db.close()

    data = list_tx(headers, account_id, category=food_id)
    assert data["total_count"] == 2
    for tx in data["transactions"]:
        assert tx["category"] == "Food"


# --- COMBINATION FILTERS ---

def test_multiple_filters_combined() -> None:
    headers = register_user("combo")
    account_id = create_account(headers)
    import_and_categorize(headers, account_id)
    data = list_tx(
        headers,
        account_id,
        start_date="2026-04-01",
        end_date="2026-04-30",
        transaction_type="expense",
        max_amount="50.00",
    )
    assert data["total_count"] == 3
    for tx in data["transactions"]:
        assert tx["transaction_type"] == "expense"
        assert float(tx["amount"]) <= 50.0
        assert "2026-04-01" <= tx["transaction_date"] <= "2026-04-30"


def test_filter_with_limit_offset() -> None:
    headers = register_user("filt_page")
    account_id = create_account(headers)
    import_and_categorize(headers, account_id)
    data = list_tx(
        headers,
        account_id,
        transaction_type="expense",
        limit=2,
        offset=0,
    )
    assert data["total_count"] == 6
    assert len(data["transactions"]) == 2


# --- PRESERVES EXISTING BEHAVIOR ---

def test_auth_required_for_filtered_requests() -> None:
    res = client.get(f"/accounts/{uuid4()}/transactions", params={"start_date": "2026-04-01"})
    assert res.status_code == 401


def test_cross_user_cannot_filter() -> None:
    headers_a = register_user("filt_xa")
    headers_b = register_user("filt_xb")
    account_a = create_account(headers_a)
    import_and_categorize(headers_a, account_a)
    res = client.get(
        f"/accounts/{account_a}/transactions",
        headers=headers_b,
        params={"start_date": "2026-04-01"},
    )
    assert res.status_code == 404
