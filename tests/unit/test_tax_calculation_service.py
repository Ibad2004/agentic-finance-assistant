"""Unit tests for TaxCalculationService and TaxCalculationRepository."""

from decimal import Decimal
from uuid import UUID, uuid4

from app.db.models import TaxCalculation
from app.services.tax_calculation_service import TaxCalculationService
from app.tax.uk.england.tax_year_2026_27.schemas import TaxCalculationResult


class FakeTaxCalculationRepository:
    def __init__(self) -> None:
        self.calculations: list[TaxCalculation] = []
        self.committed = False

    def save_tax_calculation(self, user_id: UUID, result: TaxCalculationResult) -> TaxCalculation:
        calc = TaxCalculation(
            id=uuid4(),
            user_id=user_id,
            tax_year=result.tax_year,
            rules_version=result.rules_version,
            total_income=result.total_income,
            total_allowances=result.total_allowances,
            taxable_income=result.taxable_income,
            income_tax_due=result.income_tax_due,
            assumptions=result.assumptions,
            limitations=result.limitations,
            calculation_details=result.calculation_details,
        )
        self.calculations.append(calc)
        return calc

    def get_by_id(self, calculation_id: UUID, user_id: UUID) -> TaxCalculation | None:
        for c in self.calculations:
            if c.id == calculation_id and c.user_id == user_id:
                return c
        return None

    def list_for_user(self, user_id: UUID) -> list[TaxCalculation]:
        return [c for c in self.calculations if c.user_id == user_id]

    def commit(self) -> None:
        self.committed = True


def test_tax_service_calculate_and_save() -> None:
    repo = FakeTaxCalculationRepository()
    service = TaxCalculationService(repo)  # type: ignore[arg-type]
    user_id = uuid4()

    saved = service.calculate_and_save(user_id=user_id, total_income=Decimal("50000.00"))

    assert repo.committed is True
    assert saved.user_id == user_id
    assert saved.tax_year == "2026/27"
    assert saved.rules_version == "2026_27_england_v1"
    assert saved.total_income == Decimal("50000.00")
    assert saved.taxable_income == Decimal("37430.00")
    assert saved.income_tax_due == Decimal("7486.00")


def test_tax_service_user_scoping() -> None:
    repo = FakeTaxCalculationRepository()
    service = TaxCalculationService(repo)  # type: ignore[arg-type]
    user_a = uuid4()
    user_b = uuid4()

    calc_a = service.calculate_and_save(user_id=user_a, total_income=Decimal("40000.00"))

    assert service.get_calculation(calc_a.id, user_a) is not None
    assert service.get_calculation(calc_a.id, user_b) is None
    assert len(service.list_calculations(user_a)) == 1
    assert len(service.list_calculations(user_b)) == 0


def test_tax_service_pure_estimate_without_repo() -> None:
    service = TaxCalculationService()
    result = service.calculate_estimate(total_income=Decimal("35000.00"))
    assert result.tax_year == "2026/27"
    assert result.total_income == Decimal("35000.00")
    assert result.income_tax_due == Decimal("4486.00")
