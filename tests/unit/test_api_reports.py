"""Tests for the financial report generation and retrieval API endpoints."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def register_user(prefix: str = "report_user") -> dict[str, str]:
    email = f"{prefix}_{uuid4().hex[:8]}@example.com"
    password = "ReportTest123!"
    reg = client.post("/auth/register", json={"email": email, "password": password})
    assert reg.status_code == 201
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def create_account(headers: dict) -> str:
    res = client.post(
        "/accounts",
        headers=headers,
        json={"account_name": "Report Test Account", "account_type": "current", "currency_code": "GBP"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def import_transactions(headers: dict, account_id: str, csv_content: bytes) -> None:
    res = client.post(
        f"/accounts/{account_id}/transactions/import",
        headers=headers,
        files={"file": ("test.csv", BytesIO(csv_content), "text/csv")},
    )
    assert res.status_code == 200


def categorize_transactions(headers: dict, account_id: str) -> None:
    mock_llm = MagicMock()
    mock_llm.categorize_batch.return_value = None
    with patch("app.agents.transaction_agent.GroqTransactionCategorizationLlm", return_value=mock_llm):
        client.post(f"/accounts/{account_id}/transactions/categorize", headers=headers)


SAMPLE_CSV = b"""transaction_date,description,debit,credit,balance,reference,currency
2026-04-06,ACME PAYROLL LTD,,3000.00,3000.00,SALARY-APR,GBP
2026-04-10,TESCO STORES,150.00,,2850.00,TESCO-1,GBP
2026-04-15,OCTOPUS ENERGY,95.00,,2755.00,ENERGY-1,GBP
2026-04-20,TFL TRAVEL CHARGE,45.00,,2710.00,TFL-1,GBP
"""


# --- GENERATE REPORT TESTS ---

def test_generate_report_empty_period() -> None:
    headers = register_user("rpt_empty")
    res = client.post(
        "/reports/generate",
        headers=headers,
        json={
            "report_type": "monthly_summary",
            "period_start": "2026-01-01",
            "period_end": "2026-01-31",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["report_type"] == "monthly_summary"
    assert data["total_income"] == 0.0
    assert data["total_expenses"] == 0.0
    assert data["net_amount"] == 0.0
    assert data["transaction_count"] == 0
    assert data["file_format"] == "pdf"


def test_generate_report_with_transactions() -> None:
    headers = register_user("rpt_with_tx")
    account_id = create_account(headers)
    import_transactions(headers, account_id, SAMPLE_CSV)
    categorize_transactions(headers, account_id)

    res = client.post(
        "/reports/generate",
        headers=headers,
        json={
            "report_type": "monthly_summary",
            "period_start": "2026-04-01",
            "period_end": "2026-04-30",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["total_income"] == 3000.0
    assert data["total_expenses"] == 290.0
    assert data["net_amount"] == 2710.0
    assert data["transaction_count"] == 4
    assert "Food" in data["category_breakdown"]
    assert "Utilities" in data["category_breakdown"]
    assert "Transport" in data["category_breakdown"]
    assert data["category_breakdown"]["Food"] == 150.0


def test_generate_report_invalid_date_range() -> None:
    headers = register_user("rpt_bad_date")
    res = client.post(
        "/reports/generate",
        headers=headers,
        json={
            "report_type": "monthly_summary",
            "period_start": "2026-04-30",
            "period_end": "2026-04-01",
        },
    )
    assert res.status_code == 400


def test_generate_report_invalid_type() -> None:
    headers = register_user("rpt_bad_type")
    res = client.post(
        "/reports/generate",
        headers=headers,
        json={
            "report_type": "invalid_type",
            "period_start": "2026-04-01",
            "period_end": "2026-04-30",
        },
    )
    assert res.status_code == 422


def test_generate_report_requires_auth() -> None:
    res = client.post(
        "/reports/generate",
        json={
            "report_type": "monthly_summary",
            "period_start": "2026-04-01",
            "period_end": "2026-04-30",
        },
    )
    assert res.status_code == 401


def test_generate_report_user_isolation() -> None:
    headers_a = register_user("rpt_iso_a")
    headers_b = register_user("rpt_iso_b")
    account_a = create_account(headers_a)
    import_transactions(headers_a, account_a, SAMPLE_CSV)
    categorize_transactions(headers_a, account_a)

    client.post(
        "/reports/generate",
        headers=headers_a,
        json={
            "report_type": "monthly_summary",
            "period_start": "2026-04-01",
            "period_end": "2026-04-30",
        },
    )

    res_a = client.get("/reports", headers=headers_a)
    res_b = client.get("/reports", headers=headers_b)
    assert len(res_a.json()) == 1
    assert len(res_b.json()) == 0


# --- LIST REPORTS TESTS ---

def test_list_reports_empty() -> None:
    headers = register_user("rpt_list_empty")
    res = client.get("/reports", headers=headers)
    assert res.status_code == 200
    assert res.json() == []


def test_list_reports_returns_generated() -> None:
    headers = register_user("rpt_list_gen")
    client.post(
        "/reports/generate",
        headers=headers,
        json={
            "report_type": "monthly_summary",
            "period_start": "2026-03-01",
            "period_end": "2026-03-31",
        },
    )
    client.post(
        "/reports/generate",
        headers=headers,
        json={
            "report_type": "expense_summary",
            "period_start": "2026-04-01",
            "period_end": "2026-04-30",
        },
    )
    res = client.get("/reports", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) == 2


# --- GET REPORT TESTS ---

def test_get_report_success() -> None:
    headers = register_user("rpt_get")
    gen_res = client.post(
        "/reports/generate",
        headers=headers,
        json={
            "report_type": "monthly_summary",
            "period_start": "2026-02-01",
            "period_end": "2026-02-28",
        },
    )
    report_id = gen_res.json()["id"]
    res = client.get(f"/reports/{report_id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["id"] == report_id


def test_get_report_not_found() -> None:
    headers = register_user("rpt_get_nf")
    res = client.get(f"/reports/{uuid4()}", headers=headers)
    assert res.status_code == 404


def test_get_report_cross_user_denied() -> None:
    headers_a = register_user("rpt_get_xa")
    headers_b = register_user("rpt_get_xb")
    gen_res = client.post(
        "/reports/generate",
        headers=headers_a,
        json={
            "report_type": "monthly_summary",
            "period_start": "2026-01-01",
            "period_end": "2026-01-31",
        },
    )
    report_id = gen_res.json()["id"]
    res = client.get(f"/reports/{report_id}", headers=headers_b)
    assert res.status_code == 404


# --- PDF CONTENT VALIDATION ---

def test_generate_report_creates_pdf_file() -> None:
    headers = register_user("rpt_pdf_file")
    res = client.post(
        "/reports/generate",
        headers=headers,
        json={
            "report_type": "monthly_summary",
            "period_start": "2026-04-01",
            "period_end": "2026-04-30",
        },
    )
    assert res.status_code == 201
    storage_path = res.json()["storage_path"]
    import os
    assert os.path.exists(storage_path)
    with open(storage_path, "rb") as f:
        content = f.read()
    assert content[:4] == b"%PDF"
    assert len(content) > 100
    os.remove(storage_path)


def test_generate_report_with_zero_transactions_returns_valid_pdf() -> None:
    headers = register_user("rpt_zero_pdf")
    res = client.post(
        "/reports/generate",
        headers=headers,
        json={
            "report_type": "monthly_summary",
            "period_start": "2026-06-01",
            "period_end": "2026-06-30",
        },
    )
    assert res.status_code == 201
    storage_path = res.json()["storage_path"]
    import os
    assert os.path.exists(storage_path)
    with open(storage_path, "rb") as f:
        content = f.read()
    assert content[:4] == b"%PDF"
    assert res.json()["transaction_count"] == 0
    assert res.json()["category_breakdown"] == {}
    os.remove(storage_path)
