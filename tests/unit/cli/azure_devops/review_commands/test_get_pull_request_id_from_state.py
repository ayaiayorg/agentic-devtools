"""Tests for get_pull_request_id_from_state function."""


class TestGetPullRequestIdFromState:
    """Tests for _get_pull_request_id_from_state function."""

    def test_returns_int_from_valid_value(self):
        """Test returns integer when valid number in state."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.azure_devops.review_commands import _get_pull_request_id_from_state

        with patch("agdt_ai_helpers.cli.azure_devops.review_commands.get_value", return_value="123"):
            result = _get_pull_request_id_from_state()

        assert result == 123

    def test_returns_none_when_not_set(self):
        """Test returns None when not in state."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.azure_devops.review_commands import _get_pull_request_id_from_state

        with patch("agdt_ai_helpers.cli.azure_devops.review_commands.get_value", return_value=None):
            result = _get_pull_request_id_from_state()

        assert result is None

    def test_returns_none_for_invalid_value(self):
        """Test returns None for non-numeric value."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.azure_devops.review_commands import _get_pull_request_id_from_state

        with patch("agdt_ai_helpers.cli.azure_devops.review_commands.get_value", return_value="not-a-number"):
            result = _get_pull_request_id_from_state()

        assert result is None
