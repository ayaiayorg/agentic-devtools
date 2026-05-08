"""Tests for install_package."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.setup.script_generators.required_setup import install_package


class TestInstallPackage:
    """Tests for install_package."""

    def test_success(self):
        """Successful pip install returns (True, output)."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Successfully installed"
        mock_result.stderr = ""
        with patch(
            "agentic_devtools.cli.setup.script_generators.required_setup.subprocess.run",
            return_value=mock_result,
        ):
            ok, output = install_package()
            assert ok is True
            assert "Successfully installed" in output

    def test_failure(self):
        """Failed pip install returns (False, output)."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "ERROR: Could not install"
        with patch(
            "agentic_devtools.cli.setup.script_generators.required_setup.subprocess.run",
            return_value=mock_result,
        ):
            ok, output = install_package()
            assert ok is False
            assert "ERROR" in output
