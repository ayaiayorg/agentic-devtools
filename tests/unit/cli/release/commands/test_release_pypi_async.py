"""Tests for release_pypi_async function."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.release.commands import release_pypi_async


class TestReleasePypiAsync:
    """Tests for release_pypi_async function."""

    def test_spawns_background_task(self):
        """Should spawn a background task for the release flow."""
        mock_task = MagicMock()
        mock_task.id = "release-task-id"
        mock_task.command = "agdt-release-pypi"

        with patch(
            "agentic_devtools.cli.release.commands.get_pypi_package_name",
            return_value="my-package",
        ):
            with patch(
                "agentic_devtools.cli.release.commands.get_pypi_version",
                return_value="1.2.3",
            ):
                with patch(
                    "agentic_devtools.cli.release.commands.run_function_in_background",
                    return_value=mock_task,
                ) as mock_bg:
                    with patch("agentic_devtools.cli.release.commands.print_task_tracking_info"):
                        release_pypi_async()

        mock_bg.assert_called_once()

    def test_exits_when_package_name_missing(self):
        """Should exit with error when pypi.package_name is not set."""
        with patch(
            "agentic_devtools.cli.release.commands.get_pypi_package_name",
            return_value=None,
        ):
            with pytest.raises(SystemExit):
                release_pypi_async()

    def test_exits_when_version_missing(self):
        """Should exit with error when pypi.version is not set."""
        with patch(
            "agentic_devtools.cli.release.commands.get_pypi_package_name",
            return_value="my-package",
        ):
            with patch(
                "agentic_devtools.cli.release.commands.get_pypi_version",
                return_value=None,
            ):
                with pytest.raises(SystemExit):
                    release_pypi_async()
