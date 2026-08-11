from uuid import uuid4

from app.services.audit_service import record_audit_log


class RecordingSession:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, instance: object) -> None:
        self.added.append(instance)


def test_record_audit_log_only_appends_a_new_entry() -> None:
    session = RecordingSession()
    user_id = uuid4()

    audit_log = record_audit_log(
        session,  # type: ignore[arg-type]
        user_id=user_id,
        action_type="csv_imported",
        entity_type="transaction",
        metadata={"accepted_rows": 2},
    )

    assert session.added == [audit_log]
    assert audit_log.user_id == user_id
    assert audit_log.metadata_ == {"accepted_rows": 2}
