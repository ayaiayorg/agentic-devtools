"""Tests for ``_fallback_compare`` in ``version_guard``."""

from unittest.mock import patch

from agentic_devtools.cli.setup.version_guard import _fallback_compare


class TestFallbackCompare:
    """Tests for the segment-based fallback comparison."""

    def test_equal_versions(self) -> None:
        assert _fallback_compare("0.2.69", "0.2.69") == 0

    def test_running_newer(self) -> None:
        assert _fallback_compare("0.2.70", "0.2.69") == 1

    def test_running_older(self) -> None:
        assert _fallback_compare("0.2.64", "0.2.69") == -1

    def test_different_length_segments(self) -> None:
        # 0.2 vs 0.2.1 — running is older
        assert _fallback_compare("0.2", "0.2.1") == -1

    def test_prerelease_dev_is_older(self) -> None:
        assert _fallback_compare("0.2.69dev1", "0.2.69") == -1

    def test_prerelease_alpha_is_older(self) -> None:
        assert _fallback_compare("1.0.0alpha1", "1.0.0") == -1

    def test_prerelease_rc_is_older(self) -> None:
        assert _fallback_compare("1.0.0rc1", "1.0.0") == -1

    def test_post_release_is_newer(self) -> None:
        assert _fallback_compare("1.0.0post1", "1.0.0") == 1

    def test_strips_local_metadata(self) -> None:
        assert _fallback_compare("0.2.69+local", "0.2.69") == 0

    def test_strips_local_metadata_both(self) -> None:
        assert _fallback_compare("0.2.70+abc", "0.2.69+xyz") == 1

    def test_empty_running_fails_open(self) -> None:
        assert _fallback_compare("", "0.2.69") == 0

    def test_empty_pinned_fails_open(self) -> None:
        assert _fallback_compare("0.2.69", "") == 0

    def test_garbage_input_fails_open(self) -> None:
        # Non-numeric segments with same length fail-open
        assert _fallback_compare("abc", "def") == 0

    def test_major_version_difference(self) -> None:
        assert _fallback_compare("2.0.0", "1.0.0") == 1
        assert _fallback_compare("1.0.0", "2.0.0") == -1

    def test_prerelease_rc1_vs_rc2(self) -> None:
        """Regression: different prerelease numbers must not be treated as equal."""
        assert _fallback_compare("1.0.0rc1", "1.0.0rc2") == -1
        assert _fallback_compare("1.0.0rc2", "1.0.0rc1") == 1

    def test_prerelease_dev1_vs_dev2(self) -> None:
        """Regression: different dev numbers must not be treated as equal."""
        assert _fallback_compare("0.2.69dev1", "0.2.69dev2") == -1
        assert _fallback_compare("0.2.69dev2", "0.2.69dev1") == 1

    def test_pure_prerelease_dev_segment_older(self) -> None:
        """0.2.69.dev1 (split into '0','2','69','dev1') is older than 0.2.69."""
        assert _fallback_compare("0.2.69.dev1", "0.2.69") == -1

    def test_pure_prerelease_rc_segment_older(self) -> None:
        assert _fallback_compare("1.0.0.rc1", "1.0.0") == -1

    def test_pure_prerelease_dev1_vs_dev2_segment(self) -> None:
        """Regression: 0.2.69.dev1 < 0.2.69.dev2."""
        assert _fallback_compare("0.2.69.dev1", "0.2.69.dev2") == -1
        assert _fallback_compare("0.2.69.dev2", "0.2.69.dev1") == 1

    def test_unexpected_exception_fails_open(self) -> None:
        """Exception during comparison fails open (returns 0)."""
        with patch(
            "agentic_devtools.cli.setup.version_guard._segment_value",
            side_effect=TypeError("unexpected"),
        ):
            assert _fallback_compare("1.0.0", "2.0.0") == 0
