"""Tests for _check_login_in_response helper."""

from agentic_devtools.cli.github.request_copilot_review import (
    COPILOT_REVIEWER_LOGIN,
    _check_login_in_response,
)


class TestCheckLoginInResponse:
    """Tests for _check_login_in_response."""

    def test_found_in_users(self):
        """Returns True when bot is in users array."""
        data = {"users": [{"login": COPILOT_REVIEWER_LOGIN}]}
        assert _check_login_in_response(data) is True

    def test_found_in_teams_slug(self):
        """Returns True when bot slug is in teams array."""
        data = {"users": [], "teams": [{"slug": COPILOT_REVIEWER_LOGIN}]}
        assert _check_login_in_response(data) is True

    def test_not_found_in_either(self):
        """Returns False when bot is in neither array."""
        data = {"users": [{"login": "other"}], "teams": [{"slug": "other-team"}]}
        assert _check_login_in_response(data) is False

    def test_empty_arrays(self):
        """Returns False for empty arrays."""
        data = {"users": [], "teams": []}
        assert _check_login_in_response(data) is False

    def test_missing_keys(self):
        """Returns False when keys are missing."""
        assert _check_login_in_response({}) is False

    def test_users_checked_before_teams(self):
        """Returns True from users even when teams also has a match."""
        data = {
            "users": [{"login": COPILOT_REVIEWER_LOGIN}],
            "teams": [{"slug": COPILOT_REVIEWER_LOGIN}],
        }
        assert _check_login_in_response(data) is True
