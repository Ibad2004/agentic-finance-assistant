"""End-to-end MVP pipeline test: CSV import -> Transaction Agent -> Category Verification."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.agents.transaction_agent import create_groq_transaction_agent
from app.db.models import FinancialAccount, Transaction, TransactionCategory, User
from app.db.session import SessionLocal
from app.tools.csv_import_tool import import_csv_transactions
from scripts.seed_categories import seed_categories


def run_e2e_test() -> dict:
    session: Session = SessionLocal()
    try:
        # Step 1: Ensure categories are seeded
        seed_stats = seed_categories(session)
        print(f"[1/5] Categories verified in DB (Total: {seed_stats['total']})")

        # Step 2: Create test user and GBP financial account
        test_email = "e2e_test_user@example.com"
        user = session.scalar(select(User).where(User.email == test_email))
        if user is None:
            user = User(
                email=test_email,
                password_hash="test_hash_not_for_production",
                full_name="E2E Test User",
                is_active=True,
            )
            session.add(user)
            session.flush()

        account = session.scalar(
            select(FinancialAccount).where(
                FinancialAccount.user_id == user.id,
                FinancialAccount.account_name == "E2E Main Account",
            )
        )
        if account is None:
            account = FinancialAccount(
                user_id=user.id,
                account_name="E2E Main Account",
                account_type="current",
                currency_code="GBP",
            )
            session.add(account)
            session.flush()

        # Clean previous test transactions for idempotency
        session.execute(delete(Transaction).where(Transaction.account_id == account.id))
        session.commit()
        print(f"[2/5] Setup User: {user.id} ({user.email}) | Account: {account.id} ({account.account_name})")

        # Step 3: Import sample UK transactions CSV
        csv_path = Path("data/sample_uk_transactions.csv")
        csv_bytes = csv_path.read_bytes()
        import_result = import_csv_transactions(
            session=session,
            authenticated_user_id=user.id,
            selected_account_id=account.id,
            csv_content=csv_bytes,
        )
        print(
            f"[3/5] CSV Import Completed: {import_result.rows_imported}/{import_result.rows_read} rows imported, "
            f"{import_result.duplicate_rows} duplicates, {len(import_result.validation_errors)} errors."
        )

        session.refresh(account)
        print(f"      Account Balance updated to: GBP {account.current_balance}")

        # Step 4: Run the Groq Transaction Agent
        print("[4/5] Running Transaction Agent with Groq...")
        agent = create_groq_transaction_agent(session)
        agent_result = agent.run(user_id=user.id)
        print(
            f"      Agent Execution: {agent_result.batches_processed} batches processed, "
            f"{len(agent_result.saved_transaction_ids)} categorized & saved, "
            f"{len(agent_result.needs_review_transaction_ids)} needs review, "
            f"{len(agent_result.failed_transactions)} failed."
        )

        # Step 5: Verify all transactions in PostgreSQL
        print("[5/5] Verifying categorized transactions in database:")
        transactions = list(
            session.scalars(
                select(Transaction)
                .where(Transaction.account_id == account.id)
                .order_by(Transaction.transaction_date, Transaction.id)
            )
        )

        categories_by_id = {
            cat.id: cat for cat in session.scalars(select(TransactionCategory))
        }

        results_summary = []
        uncategorized_count = 0
        for tx in transactions:
            cat = categories_by_id.get(tx.category_id) if tx.category_id else None
            cat_name = cat.name if cat else "UNCATEGORIZED"
            cat_type = cat.category_type if cat else "N/A"
            if cat is None:
                uncategorized_count += 1
            print(
                f"  - {tx.transaction_date} | {tx.description:<32} | {tx.transaction_type:<7} | "
                f"£{tx.amount:>7.2f} -> [{cat_name}] ({cat_type})"
            )
            results_summary.append({
                "date": str(tx.transaction_date),
                "description": tx.description,
                "type": tx.transaction_type,
                "amount": float(tx.amount),
                "category": cat_name,
                "category_type": cat_type,
            })

        return {
            "total_transactions": len(transactions),
            "uncategorized": uncategorized_count,
            "saved_by_agent": len(agent_result.saved_transaction_ids),
            "transactions": results_summary,
            "account_balance": float(account.current_balance) if account.current_balance else None,
            "agent_errors": agent_result.sanitized_errors,
        }
    finally:
        session.close()


if __name__ == "__main__":
    summary = run_e2e_test()
    print("\n--- E2E Summary ---")
    print(f"Total Transactions: {summary['total_transactions']}")
    print(f"Categorized: {summary['total_transactions'] - summary['uncategorized']}")
    print(f"Uncategorized: {summary['uncategorized']}")
    print(f"Account Balance: £{summary['account_balance']}")
