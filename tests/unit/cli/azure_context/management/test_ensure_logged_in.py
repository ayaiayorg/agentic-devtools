"""Tests for ensure_logged_in function."""

from unittest.mock import patch

from agentic_devtools.cli.azure_context.config import AzureContext
from agentic_devtools.cli.azure_context.management import ensure_logged_in


class TestEnsureLoggedIn:
    """Tests for ensure_logged_in function."""

    def test_returns_true_and_prints_when_already_logged_in(self, capsys):
        """Should return True and print confirmation when already logged in."""
        with patch(
            "agentic_devtools.cli.azure_context.management.check_login_status",
            return_value=(True, "user@company.com", None),
        ):
            result = ensure_logged_in(AzureContext.DEVOPS)

        assert result is True
        captured = capsys.readouterr()
        assert "user@company.com" in captured.out

    def test_returns_false_when_not_logged_in_and_login_fails(self, capsys):
        """Should return False when not logged in and subsequent login fails."""
        import subprocess

        with patch(
            "agentic_devtools.cli.azure_context.management.check_login_status",
            side_effect=[(False, None, "Not logged in"), (False, None, "Still not in")],
        ):
            with patch("subprocess.run", return_value=type("R", (), {"returncode": 1})()):
                result = ensure_logged_in(AzureContext.DEVOPS)

        assert result is False
