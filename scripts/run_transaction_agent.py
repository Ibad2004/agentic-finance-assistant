"""Explicit development entry point for running the Transaction Agent for one user."""

import argparse
from uuid import UUID

from app.agents.transaction_agent import create_groq_transaction_agent
from app.db.session import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Transaction Agent for one explicit user.")
    parser.add_argument("--user-id", required=True, type=UUID)
    args = parser.parse_args()
    session = SessionLocal()
    try:
        result = create_groq_transaction_agent(session).run(args.user_id)
    finally:
        session.close()
    print({
        "batches_processed": result.batches_processed,
        "saved_transactions": len(result.saved_transaction_ids),
        "needs_review": len(result.needs_review_transaction_ids),
        "failures": len(result.failed_transactions),
    })


if __name__ == "__main__":
    main()
