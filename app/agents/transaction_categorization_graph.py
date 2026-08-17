"""Simple batch LangGraph workflow for the MVP Transaction Agent."""

from typing import Literal

from langgraph.graph import END, START, StateGraph
from sqlalchemy.exc import SQLAlchemyError

from app.agents.state import TransactionCategorizationState
from app.schemas.transaction_categorization import CategoryAssignment
from app.services.llm_service import TransactionCategorizationLlm
from app.services.merchant_categorization_rules import match_merchant_rule
from app.services.transaction_categorization_service import approved_categories_only, validate_llm_batch_response
from app.tools.transaction_categorization_tools import TransactionCategorizationTools


def build_transaction_categorization_graph(
    tools: TransactionCategorizationTools,
    llm: TransactionCategorizationLlm,
    max_batches: int,
):
    graph = StateGraph(TransactionCategorizationState)

    def load_categories(state: TransactionCategorizationState):
        return {"approved_categories": approved_categories_only(tools.get_approved_categories())}

    def load_batch(state: TransactionCategorizationState):
        batch = tools.get_uncategorized_transaction_batch(
            state["user_id"], state["batch_size"], state.get("processed_transaction_ids", set())
        )
        return {"current_batch": batch, "deterministic_matches": {}, "llm_transactions": [], "llm_batch_response": None}

    def apply_rules(state: TransactionCategorizationState):
        categories = {category.name for category in state["approved_categories"]}
        deterministic: dict = {}
        ambiguous = []
        for transaction in state["current_batch"]:
            match = match_merchant_rule(transaction.description, transaction.transaction_type)
            if match and match.category_name in categories:
                deterministic[transaction.id] = match.category_name
            else:
                ambiguous.append(transaction)
        return {"deterministic_matches": deterministic, "llm_transactions": ambiguous}

    def save_deterministic(state: TransactionCategorizationState):
        by_name = {category.name: category for category in state["approved_categories"]}
        by_id = {category.id: category for category in state["approved_categories"]}
        assignments = [CategoryAssignment(transaction_id=transaction_id, category_id=by_name[name].id) for transaction_id, name in state["deterministic_matches"].items()]
        try:
            saved = tools.save_category_assignments(state["user_id"], assignments, by_id)
            tools.commit()
            return {"saved_transaction_ids": state.get("saved_transaction_ids", []) + saved}
        except SQLAlchemyError:
            tools.rollback()
            return {"sanitized_errors": state.get("sanitized_errors", []) + ["deterministic_save_failed"]}

    def call_groq(state: TransactionCategorizationState):
        try:
            response = llm.categorize_batch(state["llm_transactions"], state["approved_categories"])
            return {"llm_batch_response": response}
        except Exception:
            for transaction in state["llm_transactions"]:
                tools.record_categorization_event(state["user_id"], transaction.id, "transaction_categorization_failed", "groq_request_failed")
            tools.commit()
            failures = [{"transaction_id": str(transaction.id), "code": "groq_request_failed"} for transaction in state["llm_transactions"]]
            return {"failed_transactions": state.get("failed_transactions", []) + failures, "sanitized_errors": state.get("sanitized_errors", []) + ["groq_request_failed"]}

    def validate_response(state: TransactionCategorizationState):
        if state.get("llm_batch_response") is None:
            return {}
        assignments, needs_review, failures = validate_llm_batch_response(state["llm_batch_response"], state["llm_transactions"], state["approved_categories"], state["confidence_threshold"])
        if failures:
            tools.record_categorization_event(state["user_id"], None, "transaction_categorization_failed", "invalid_llm_output")
            tools.commit()
        return {"validated_assignments": assignments, "needs_review_transactions": state.get("needs_review_transactions", []) + needs_review, "failed_transactions": state.get("failed_transactions", []) + failures}

    def save_llm(state: TransactionCategorizationState):
        assignments = state.get("validated_assignments", [])
        if not assignments:
            return {}
        by_id = {category.id: category for category in state["approved_categories"]}
        try:
            saved = tools.save_category_assignments(state["user_id"], assignments, by_id)
            tools.commit()
            return {"saved_transaction_ids": state.get("saved_transaction_ids", []) + saved}
        except SQLAlchemyError:
            tools.rollback()
            return {"sanitized_errors": state.get("sanitized_errors", []) + ["llm_save_failed"]}

    def advance(state: TransactionCategorizationState):
        processed = state.get("processed_transaction_ids", set()) | {transaction.id for transaction in state["current_batch"]}
        return {"processed_transaction_ids": processed, "batches_processed": state.get("batches_processed", 0) + 1, "batch_cursor": state.get("batch_cursor", 0) + len(state["current_batch"])}

    def has_batch(state: TransactionCategorizationState) -> Literal["rules", "end"]:
        return "rules" if state.get("current_batch") else "end"

    def needs_llm(state: TransactionCategorizationState) -> Literal["groq", "advance"]:
        return "groq" if state.get("llm_transactions") else "advance"

    def more_batches(state: TransactionCategorizationState) -> Literal["batch", "end"]:
        return "batch" if state["batches_processed"] < max_batches else "end"

    graph.add_node("load_categories", load_categories)
    graph.add_node("load_batch", load_batch)
    graph.add_node("apply_rules", apply_rules)
    graph.add_node("save_deterministic", save_deterministic)
    graph.add_node("call_groq", call_groq)
    graph.add_node("validate_response", validate_response)
    graph.add_node("save_llm", save_llm)
    graph.add_node("advance", advance)
    graph.add_edge(START, "load_categories")
    graph.add_edge("load_categories", "load_batch")
    graph.add_conditional_edges("load_batch", has_batch, {"rules": "apply_rules", "end": END})
    graph.add_edge("apply_rules", "save_deterministic")
    graph.add_conditional_edges("save_deterministic", needs_llm, {"groq": "call_groq", "advance": "advance"})
    graph.add_edge("call_groq", "validate_response")
    graph.add_edge("validate_response", "save_llm")
    graph.add_edge("save_llm", "advance")
    graph.add_conditional_edges("advance", more_batches, {"batch": "load_batch", "end": END})
    return graph.compile()
