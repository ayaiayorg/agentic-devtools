"""Tests for Copilot reviewer login constants."""

from agentic_devtools.cli.ci.models import (
    COPILOT_COMMENT_LOGINS,
    COPILOT_LOGINS,
    COPILOT_REVIEWER_LOGIN,
)


class TestCopilotReviewerLogin:
    """Tests for Copilot reviewer login constants in CI models."""

    def test_canonical_login_value(self) -> None:
        assert COPILOT_REVIEWER_LOGIN == "copilot-pull-request-reviewer[bot]"

    def test_canonical_login_in_copilot_login_sets(self) -> None:
        assert COPILOT_REVIEWER_LOGIN in COPILOT_LOGINS
        assert COPILOT_REVIEWER_LOGIN in COPILOT_COMMENT_LOGINS
