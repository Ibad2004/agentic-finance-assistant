"""Public entry point for the single MVP Transaction Agent."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.agents.transaction_categorization_graph import build_transaction_categorization_graph
from app.config import Settings, get_settings
from app.db.repositories.transaction_categorization_repository import TransactionCategorizationRepository
from app.schemas.transaction_categorization import CategorizationFailure, CategorizationRunResult
from app.services.groq_llm_provider import GroqTransactionCategorizationLlm
from app.services.llm_service import TransactionCategorizationLlm
from app.tools.transaction_categorization_tools import TransactionCategorizationTools


class TransactionAgent:
    def __init__(self, session: Session, llm: TransactionCategorizationLlm, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._graph = build_transaction_categorization_graph(
            TransactionCategorizationTools(TransactionCategorizationRepository(session)),
            llm,
            self._settings.transaction_agent_max_batches_per_run,
        )

    def run(self, user_id: UUID) -> CategorizationRunResult:
        final_state = self._graph.invoke({
            "user_id": user_id,
            "batch_size": self._settings.transaction_agent_batch_size,
            "confidence_threshold": self._settings.transaction_agent_confidence_threshold,
            "batch_cursor": 0,
            "batches_processed": 0,
            "saved_transaction_ids": [],
            "needs_review_transactions": [],
            "failed_transactions": [],
            "sanitized_errors": [],
            "processed_transaction_ids": set(),
        })
        return CategorizationRunResult(
            saved_transaction_ids=final_state.get("saved_transaction_ids", []),
            needs_review_transaction_ids=final_state.get("needs_review_transactions", []),
            failed_transactions=[CategorizationFailure(**failure) for failure in final_state.get("failed_transactions", [])],
            sanitized_errors=final_state.get("sanitized_errors", []),
            batches_processed=final_state.get("batches_processed", 0),
        )


def create_groq_transaction_agent(session: Session) -> TransactionAgent:
    settings = get_settings()
    return TransactionAgent(session, GroqTransactionCategorizationLlm(settings), settings)
