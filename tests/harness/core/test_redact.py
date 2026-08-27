from app.harness.core.redact import redact


def test_known_secret_shapes_are_redacted_but_surrounding_text_survives() -> None:
    text = (
        "slack xoxb-123-abc failed; linear lin_api_ABC123; notion ntn_ZZZ; "
        "fathom whsec_QUJDMTIz; google AIzaSyABCDEFGHIJKLMNOPQRSTUVWX; Bearer eyJhbGciOi.xx"
    )
    out = redact(text)
    for token in ("xoxb-123-abc", "lin_api_ABC123", "ntn_ZZZ", "whsec_QUJDMTIz",
                  "AIzaSyABCDEFGHIJKLMNOPQRSTUVWX", "eyJhbGciOi.xx"):
        assert token not in out
    assert "slack" in out and "failed" in out and "[redacted]" in out


def test_ordinary_text_is_unchanged() -> None:
    assert redact("INV-142 moved to In Progress") == "INV-142 moved to In Progress"
