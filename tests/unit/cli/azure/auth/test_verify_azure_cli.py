"""Tests for verify_azure_cli function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure.auth import verify_azure_cli


class TestVerifyAzureCli:
    """Tests for verify_azure_cli function."""

    def test_returns_true_when_az_is_available(self):
        """Should return True when the az version command succeeds."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch(
            "agentic_devtools.cli.azure.auth.run_safe",
            return_value=mock_result,
        ):
            result = verify_azure_cli()

        assert result is True

    def test_returns_false_when_az_is_not_available(self):
        """Should return False when the az version command fails."""
        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch(
            "agentic_devtools.cli.azure.auth.run_safe",
            return_value=mock_result,
        ):
            result = verify_azure_cli()

        assert result is False

    def test_calls_az_version(self):
        """Should call az version to verify the CLI is installed."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch(
            "agentic_devtools.cli.azure.auth.run_safe",
            return_value=mock_result,
        ) as mock_run:
            verify_azure_cli()

        call_args = mock_run.call_args[0][0]
        assert "az" in call_args
        assert "version" in call_args
