from decimal import Decimal
from uuid import uuid4

from app.schemas.transaction_categorization import CategorySummary, TransactionForCategorization
from app.services.transaction_categorization_service import validate_llm_batch_response


food = CategorySummary(id=uuid4(), name="Food", category_type="expense")
salary = CategorySummary(id=uuid4(), name="Salary", category_type="income")
transaction = TransactionForCategorization(id=uuid4(), description="TESCO", transaction_type="expense", amount=Decimal("10.00"))


def validate(response):
    return validate_llm_batch_response(response, [transaction], [food, salary], 0.85)


def test_valid_high_confidence_result_becomes_assignment() -> None:
    assignments, review, failures = validate({"results": [{"transaction_id": str(transaction.id), "category_name": "Food", "confidence": 0.96, "reason": "Supermarket purchase."}]})
    assert assignments[0].category_id == food.id
    assert not review and not failures


def test_invalid_category_and_wrong_type_are_rejected() -> None:
    _, _, invalid_failures = validate({"results": [{"transaction_id": str(transaction.id), "category_name": "Unknown", "confidence": 0.96, "reason": "x"}]})
    _, _, type_failures = validate({"results": [{"transaction_id": str(transaction.id), "category_name": "Salary", "confidence": 0.96, "reason": "x"}]})
    assert invalid_failures[0]["code"] == "invalid_category"
    assert type_failures[0]["code"] == "wrong_category_type"


def test_invalid_or_duplicate_transaction_ids_are_rejected() -> None:
    unknown = uuid4()
    _, _, unknown_failures = validate({"results": [{"transaction_id": str(unknown), "category_name": "Food", "confidence": 0.96, "reason": "x"}]})
    _, _, duplicate_failures = validate({"results": [
        {"transaction_id": str(transaction.id), "category_name": "Food", "confidence": 0.96, "reason": "x"},
        {"transaction_id": str(transaction.id), "category_name": "Food", "confidence": 0.96, "reason": "x"},
    ]})
    assert unknown_failures[0]["code"] == "unexpected_transaction_id"
    assert any(failure["code"] == "duplicate_transaction_id" for failure in duplicate_failures)


def test_missing_low_and_invalid_confidence_results_are_not_saved() -> None:
    _, _, missing = validate({"results": []})
    _, review, _ = validate({"results": [{"transaction_id": str(transaction.id), "category_name": "Food", "confidence": 0.84, "reason": "x"}]})
    _, _, invalid = validate({"results": [{"transaction_id": str(transaction.id), "category_name": "Food", "confidence": 2, "reason": "x"}]})
    assert missing[0]["code"] == "missing_result"
    assert review == [transaction.id]
    assert invalid[0]["code"] == "invalid_llm_response"
