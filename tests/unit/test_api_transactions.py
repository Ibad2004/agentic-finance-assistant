"""Unit and integration tests for transactions API endpoints (import, list, categorize)."""

from io import BytesIO
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.transaction_categorization import (
    CategorizationRunResult,
    LlmBatchCategorizationResponse,
    LlmCategorizationResult,
)

client = TestClient(app)

SAMPLE_CSV = b"""transaction_date,description,debit,credit,balance,reference,currency
2026-04-06,ACME PAYROLL LTD,,2850.00,2850.00,SALARY-APR-2026,GBP
2026-04-09,TESCO STORES 1234,63.28,,2786.72,TESCO-1234-0409,GBP
"""


def register_and_create_account(email_prefix: str = "tx_user") -> tuple[dict[str, str], str]:
    email = f"{email_prefix}_{uuid4().hex[:8]}@example.com"
    password = "StrongPassword2026!"
    reg_res = client.post("/auth/register", json={"email": email, "password": password})
    assert reg_res.status_code == 201

    login_res = client.post("/auth/login", json={"email": email, "password": password})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    acc_res = client.post(
        "/accounts",
        headers=headers,
        json={"account_name": "Test Account", "account_type": "current", "currency_code": "GBP"},
    )
    assert acc_res.status_code == 201
    account_id = acc_res.json()["id"]
    return headers, account_id


def test_import_transactions_requires_auth() -> None:
    fake_account_id = uuid4()
    response = client.post(
        f"/accounts/{fake_account_id}/transactions/import",
        files={"file": ("test.csv", BytesIO(SAMPLE_CSV), "text/csv")},
    )
    assert response.status_code == 401


def test_import_transactions_success_on_owned_account() -> None:
    headers, account_id = register_and_create_account("import_user")
    response = client.post(
        f"/accounts/{account_id}/transactions/import",
        headers=headers,
        files={"file": ("test.csv", BytesIO(SAMPLE_CSV), "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["rows_read"] == 2
    assert data["rows_imported"] == 2
    assert data["duplicate_rows"] == 0
    assert len(data["imported_transaction_ids"]) == 2


def test_import_transactions_rejects_cross_user_access() -> None:
    headers_a, account_a = register_and_create_account("owner_a")
    headers_b, _ = register_and_create_account("attacker_b")

    # User B attempts to import into User A's account
    response = client.post(
        f"/accounts/{account_a}/transactions/import",
        headers=headers_b,
        files={"file": ("test.csv", BytesIO(SAMPLE_CSV), "text/csv")},
    )
    assert response.status_code == 404
    assert "not found or access unauthorized" in response.json()["detail"].lower()


def test_import_empty_file_returns_400() -> None:
    headers, account_id = register_and_create_account("empty_csv_user")
    response = client.post(
        f"/accounts/{account_id}/transactions/import",
        headers=headers,
        files={"file": ("empty.csv", BytesIO(b""), "text/csv")},
    )
    assert response.status_code == 400


def test_list_transactions_returns_safe_fields_only() -> None:
    headers, account_id = register_and_create_account("list_user")
    # Import transactions
    client.post(
        f"/accounts/{account_id}/transactions/import",
        headers=headers,
        files={"file": ("test.csv", BytesIO(SAMPLE_CSV), "text/csv")},
    )

    response = client.get(f"/accounts/{account_id}/transactions", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 2
    assert len(data["transactions"]) == 2
    first_tx = data["transactions"][0]
    # Check safe fields
    assert "id" in first_tx
    assert "transaction_date" in first_tx
    assert "description" in first_tx
    assert "amount" in first_tx
    assert "transaction_type" in first_tx
    assert "category" in first_tx
    assert "source" in first_tx
    assert "is_reviewed" in first_tx
    # Ensure sensitive / internal fields are not exposed in transaction items
    assert "user_id" not in first_tx
    assert "account_id" not in first_tx
    assert "source_reference" not in first_tx


def test_list_transactions_rejects_cross_user_access() -> None:
    headers_a, account_a = register_and_create_account("list_owner_a")
    headers_b, _ = register_and_create_account("list_attacker_b")

    response = client.get(f"/accounts/{account_a}/transactions", headers=headers_b)
    assert response.status_code == 404


def test_categorize_transactions_runs_agent_with_mocked_llm() -> None:
    headers, account_id = register_and_create_account("cat_user")
    # Import 2 transactions (Acme Payroll LTD, Tesco Stores 1234)
    client.post(
        f"/accounts/{account_id}/transactions/import",
        headers=headers,
        files={"file": ("test.csv", BytesIO(SAMPLE_CSV), "text/csv")},
    )

    # Mock the LLM to prevent live network/Groq calls during unit test
    mock_llm = MagicMock()
    mock_llm.categorize_batch.return_value = LlmBatchCategorizationResponse(results=[])

    with patch("app.agents.transaction_agent.GroqTransactionCategorizationLlm", return_value=mock_llm):
        response = client.post(f"/accounts/{account_id}/transactions/categorize", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "batches_processed" in data
    assert "saved_transaction_ids" in data
    # Both transactions match deterministic merchant rules (Payroll -> Salary, Tesco -> Food)
    assert len(data["saved_transaction_ids"]) == 2


def test_categorize_transactions_rejects_cross_user_access() -> None:
    headers_a, account_a = register_and_create_account("cat_owner_a")
    headers_b, _ = register_and_create_account("cat_attacker_b")

    response = client.post(f"/accounts/{account_a}/transactions/categorize", headers=headers_b)
    assert response.status_code == 404
