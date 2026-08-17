"""Financial accounts and transaction management endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.agents.transaction_agent import create_groq_transaction_agent
from app.api.dependencies import get_current_user, get_db
from app.db.models import User
from app.db.repositories.account_repository import AccountRepository
from app.db.repositories.transaction_repository import TransactionRepository
from app.schemas.account import AccountCreateRequest, AccountResponse
from app.schemas.csv_import import CsvImportResult
from app.schemas.transaction import TransactionListResponse, TransactionResponse
from app.schemas.transaction_categorization import CategorizationRunResult
from app.services.account_service import AccountService
from app.tools.csv_import_tool import import_csv_transactions

router = APIRouter(prefix="/accounts", tags=["Financial Accounts"])


@router.post(
    "",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new GBP financial account",
)
def create_account(
    payload: AccountCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AccountResponse:
    """Create a new financial account owned strictly by the authenticated user."""
    service = AccountService(AccountRepository(db))
    account = service.create_account(
        user_id=current_user.id,
        account_name=payload.account_name,
        account_type=payload.account_type,
        currency_code=payload.currency_code,
    )
    return AccountResponse.model_validate(account)


@router.get(
    "",
    response_model=list[AccountResponse],
    status_code=status.HTTP_200_OK,
    summary="List all accounts owned by authenticated user",
)
def list_accounts(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[AccountResponse]:
    """Retrieve all financial accounts belonging to the authenticated user."""
    service = AccountService(AccountRepository(db))
    accounts = service.list_accounts_for_user(user_id=current_user.id)
    return [AccountResponse.model_validate(account) for account in accounts]


@router.post(
    "/{account_id}/transactions/import",
    response_model=CsvImportResult,
    status_code=status.HTTP_200_OK,
    summary="Import normalized CSV transactions into user account",
)
async def import_transactions(
    account_id: UUID,
    file: Annotated[UploadFile, File(description="UK bank format CSV file")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CsvImportResult:
    """Import transactions from a normalized CSV file for an account owned by the user."""
    account_repo = AccountRepository(db)
    account = account_repo.get_account_for_user(account_id=account_id, user_id=current_user.id)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial account not found or access unauthorized.",
        )

    csv_content = await file.read()
    if not csv_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )

    result = import_csv_transactions(
        session=db,
        authenticated_user_id=current_user.id,
        selected_account_id=account_id,
        csv_content=csv_content,
    )
    return result


@router.post(
    "/{account_id}/transactions/categorize",
    response_model=CategorizationRunResult,
    status_code=status.HTTP_200_OK,
    summary="Trigger Transaction Agent categorization for user account",
)
def categorize_transactions(
    account_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CategorizationRunResult:
    """Run the Transaction Agent to categorize uncategorized transactions for the authenticated user."""
    account_repo = AccountRepository(db)
    account = account_repo.get_account_for_user(account_id=account_id, user_id=current_user.id)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial account not found or access unauthorized.",
        )

    agent = create_groq_transaction_agent(db)
    result = agent.run(user_id=current_user.id)
    return result


@router.get(
    "/{account_id}/transactions",
    response_model=TransactionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List transactions for an account owned by user",
)
def list_transactions(
    account_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TransactionListResponse:
    """List transactions for a financial account, verifying user ownership and returning safe fields."""
    account_repo = AccountRepository(db)
    account = account_repo.get_account_for_user(account_id=account_id, user_id=current_user.id)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial account not found or access unauthorized.",
        )

    tx_repo = TransactionRepository(db)
    transactions, total_count = tx_repo.list_transactions_for_account(
        account_id=account_id,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )

    items = [
        TransactionResponse(
            id=tx.id,
            transaction_date=tx.transaction_date,
            description=tx.description,
            amount=tx.amount,
            transaction_type=tx.transaction_type,
            category=tx.category.name if tx.category else None,
            source=tx.source,
            is_reviewed=tx.is_reviewed,
        )
        for tx in transactions
    ]

    return TransactionListResponse(
        transactions=items,
        total_count=total_count,
    )
