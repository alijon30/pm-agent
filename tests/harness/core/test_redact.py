from app.harness.core.redact import redact


def test_known_secret_shapes_are_redacted_but_surrounding_text_survives() -> None:
    text = (
        "slack xoxb-123-abc failed; linear lin_api_ABC123; notion ntn_ZZZ; "
        "fathom whsec_QUJDMTIz; google AIzaSyABCDEFGHIJKLMNOPQRSTUVWX; Bearer eyJhbGciOi.xx; "
        "github ghp_ABC123def; github_pat_11ABCDE_xyz"
    )
    out = redact(text)
    for token in ("xoxb-123-abc", "lin_api_ABC123", "ntn_ZZZ", "whsec_QUJDMTIz",
                  "AIzaSyABCDEFGHIJKLMNOPQRSTUVWX", "eyJhbGciOi.xx", "ghp_ABC123def",
                  "github_pat_11ABCDE_xyz"):
        assert token not in out
    assert "slack" in out and "failed" in out and "[redacted]" in out


def test_ordinary_text_is_unchanged() -> None:
    assert redact("INV-142 moved to In Progress") == "INV-142 moved to In Progress"


def test_words_that_merely_start_like_a_token_survive() -> None:
    assert redact("the ghost_writer branch and a ghastly bug") == (
        "the ghost_writer branch and a ghastly bug")
