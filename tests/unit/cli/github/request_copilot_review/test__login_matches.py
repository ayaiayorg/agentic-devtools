"""Tests for _login_matches helper."""

from agentic_devtools.cli.github.request_copilot_review import (
    COPILOT_REVIEWER_LOGIN,
    _login_matches,
)


class TestLoginMatches:
    """Tests for _login_matches."""

    def test_exact_match(self):
        """Returns True for exact bot login."""
        assert _login_matches(COPILOT_REVIEWER_LOGIN) is True

    def test_case_insensitive(self):
        """Returns True for different casing."""
        assert _login_matches("Copilot-Pull-Request-Reviewer[bot]") is True

    def test_uppercase(self):
        """Returns True for all-uppercase."""
        assert _login_matches("COPILOT-PULL-REQUEST-REVIEWER[BOT]") is True

    def test_non_matching(self):
        """Returns False for non-matching login."""
        assert _login_matches("other-user") is False

    def test_empty_string(self):
        """Returns False for empty string."""
        assert _login_matches("") is False

    def test_partial_match(self):
        """Returns False for partial match."""
        assert _login_matches("copilot-pull-request-reviewer") is False
