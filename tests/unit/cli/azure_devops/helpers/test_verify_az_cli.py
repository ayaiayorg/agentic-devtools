"""Tests for verify_az_cli function."""

import sys
from unittest.mock import patch

import pytest

from agentic_devtools.cli.azure_devops.helpers import verify_az_cli


class TestVerifyAzCli:
    """Tests for verify_az_cli function."""

    def test_does_not_exit_when_az_available(self):
        """Should complete without raising SystemExit when az CLI is installed."""
        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.returncode = 0

        ext_result = MagicMock()
        ext_result.returncode = 0
        ext_result.stdout = "azure-devops"

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.run_safe",
            side_effect=[mock_result, ext_result],
        ):
            verify_az_cli()  # Should not raise

    def test_exits_when_az_not_installed(self):
        """Should raise SystemExit when az CLI is not found."""
        import subprocess

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.run_safe",
            side_effect=FileNotFoundError("az not found"),
        ):
            with pytest.raises(SystemExit):
                verify_az_cli()
