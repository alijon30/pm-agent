from app.core.keys import event_doc_id, idempotency_key, new_id


def test_new_ids_are_unique_hex_and_safe_as_firestore_doc_ids() -> None:
    a, b = new_id(), new_id()
    assert a != b
    assert len(a) == 32 and "/" not in a


def test_event_doc_id_is_deterministic_per_provider_event() -> None:
    assert event_doc_id("fathom", "msg_123") == "fathom:msg_123"
    assert event_doc_id("fathom", "msg_123") == event_doc_id("fathom", "msg_123")


def test_idempotency_key_is_stable_and_changes_with_any_input() -> None:
    k = idempotency_key("fathom:msg_123", 0, "linear.create_issue")
    assert k == idempotency_key("fathom:msg_123", 0, "linear.create_issue")
    assert len(k) == 16
    assert k != idempotency_key("fathom:msg_123", 1, "linear.create_issue")
    assert k != idempotency_key("fathom:msg_123", 0, "linear.assign")
