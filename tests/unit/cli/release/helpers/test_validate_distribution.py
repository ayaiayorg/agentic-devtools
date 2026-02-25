"""Tests for validate_distribution function."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.release.helpers import ReleaseError, validate_distribution


class TestValidateDistribution:
    """Tests for validate_distribution function."""

    def test_calls_twine_check(self):
        """Should invoke python -m twine check via run_safe."""
        mock_result = MagicMock(returncode=0)

        with patch(
            "agentic_devtools.cli.release.helpers.run_safe",
            return_value=mock_result,
        ) as mock_run:
            validate_distribution()

        args = mock_run.call_args[0][0]
        assert "twine" in args
        assert "check" in args

    def test_uses_default_dist_dir(self):
        """Should include dist/* glob in the twine check command by default."""
        mock_result = MagicMock(returncode=0)

        with patch(
            "agentic_devtools.cli.release.helpers.run_safe",
            return_value=mock_result,
        ) as mock_run:
            validate_distribution()

        args = mock_run.call_args[0][0]
        # The dist pattern should appear somewhere in the args
        assert any("dist" in str(a) for a in args)

    def test_uses_custom_dist_dir(self):
        """Should pass custom dist_dir glob to the twine check command."""
        mock_result = MagicMock(returncode=0)

        with patch(
            "agentic_devtools.cli.release.helpers.run_safe",
            return_value=mock_result,
        ) as mock_run:
            validate_distribution(dist_dir="my-dist")

        args = mock_run.call_args[0][0]
        assert any("my-dist" in str(a) for a in args)

    def test_raises_release_error_on_failure(self):
        """Should raise ReleaseError when twine check returns non-zero."""
        mock_result = MagicMock(returncode=1, stderr="check failed", stdout="")

        with patch(
            "agentic_devtools.cli.release.helpers.run_safe",
            return_value=mock_result,
        ):
            with pytest.raises(ReleaseError):
                validate_distribution()
