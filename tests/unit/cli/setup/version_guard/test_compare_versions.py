"""Tests for ``compare_versions`` in ``version_guard``."""

from unittest.mock import patch

import pytest

from agentic_devtools.cli.setup.version_guard import compare_versions


class TestCompareVersions:
    """Tests for PEP 440-based version comparison with fallback."""

    def test_equal_versions(self) -> None:
        assert compare_versions("0.2.69", "0.2.69") == 0

    def test_newer_version(self) -> None:
        assert compare_versions("0.2.70", "0.2.69") == 1

    def test_older_version(self) -> None:
        assert compare_versions("0.2.64", "0.2.69") == -1

    def test_prerelease_dev_is_older_than_release(self) -> None:
        assert compare_versions("0.2.69.dev1", "0.2.69") == -1

    def test_prerelease_rc_is_older_than_release(self) -> None:
        assert compare_versions("1.0.0rc1", "1.0.0") == -1

    def test_post_release_is_newer(self) -> None:
        assert compare_versions("1.0.0.post1", "1.0.0") == 1

    def test_fallback_on_import_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        """When packaging is unavailable, fallback is used and warning emitted."""
        original_import = __import__

        def _block_packaging(name, *args, **kwargs):
            if name == "packaging.version":
                raise ImportError("mocked: packaging unavailable")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=_block_packaging):
            result = compare_versions("0.2.70", "0.2.69")

        assert result == 1
        err = capsys.readouterr().err
        assert "packaging library not available" in err

    def test_fallback_on_invalid_version(self, capsys: pytest.CaptureFixture[str]) -> None:
        """When version strings are not PEP 440 compliant, falls back to segment-based comparison."""
        result = compare_versions("0.2.70", "0.2.69-custom-build")
        assert result == 1
        err = capsys.readouterr().err
        assert "falling back to segment-based comparison" in err
