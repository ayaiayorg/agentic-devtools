"""Tests for build_distribution function."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.release.helpers import ReleaseError, build_distribution


class TestBuildDistribution:
    """Tests for build_distribution function."""

    def test_calls_python_build(self):
        """Should invoke python -m build via run_safe."""
        mock_result = MagicMock(returncode=0)

        with patch(
            "agentic_devtools.cli.release.helpers.run_safe",
            return_value=mock_result,
        ) as mock_run:
            build_distribution()

        args = mock_run.call_args[0][0]
        assert "build" in args

    def test_uses_default_dist_dir(self):
        """Should use 'dist' as the default output directory."""
        mock_result = MagicMock(returncode=0)

        with patch(
            "agentic_devtools.cli.release.helpers.run_safe",
            return_value=mock_result,
        ) as mock_run:
            build_distribution()

        args = mock_run.call_args[0][0]
        assert "dist" in args

    def test_uses_custom_dist_dir(self):
        """Should pass the custom dist_dir to the build command."""
        mock_result = MagicMock(returncode=0)

        with patch(
            "agentic_devtools.cli.release.helpers.run_safe",
            return_value=mock_result,
        ) as mock_run:
            build_distribution(dist_dir="custom-dist")

        args = mock_run.call_args[0][0]
        assert "custom-dist" in args

    def test_raises_release_error_on_nonzero_return_code(self):
        """Should raise ReleaseError when the build command fails."""
        mock_result = MagicMock(returncode=1, stderr="build failed", stdout="")

        with patch(
            "agentic_devtools.cli.release.helpers.run_safe",
            return_value=mock_result,
        ):
            with pytest.raises(ReleaseError):
                build_distribution()
