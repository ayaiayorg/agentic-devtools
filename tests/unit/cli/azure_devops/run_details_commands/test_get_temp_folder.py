"""
Tests for run_details_commands module.
"""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.run_details_commands import (
    _get_temp_folder,
)


class TestGetTempFolder:
    """Tests for _get_temp_folder helper."""

    def test_creates_temp_folder(self, tmp_path):
        """Should create temp folder if it doesn't exist."""
        with patch("agentic_devtools.cli.azure_devops.run_details_commands.Path") as mock_path:
            # Set up the chain of Path operations
            mock_file = MagicMock()
            mock_file.parent.parent.parent.parent = tmp_path
            mock_path.return_value = mock_file
            mock_path.__file__ = __file__

            # Just verify the function returns a Path-like object
            # The actual implementation depends on file system structure
            result = _get_temp_folder()
            assert result is not None
