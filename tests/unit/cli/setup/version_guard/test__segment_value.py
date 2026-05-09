"""Tests for ``_segment_value`` in ``version_guard``."""

from agentic_devtools.cli.setup.version_guard import _segment_value


class TestSegmentValue:
    """Tests for the segment-to-tuple conversion."""

    def test_pure_numeric(self) -> None:
        assert _segment_value("42") == (42, 0, 0)

    def test_dev_suffix_with_number(self) -> None:
        assert _segment_value("1dev3") == (1, -4, 3)

    def test_dev_suffix_without_number(self) -> None:
        assert _segment_value("1dev") == (1, -4, 0)

    def test_alpha_suffix_with_number(self) -> None:
        assert _segment_value("1alpha2") == (1, -3, 2)

    def test_a_suffix_with_number(self) -> None:
        assert _segment_value("1a5") == (1, -3, 5)

    def test_beta_suffix_with_number(self) -> None:
        assert _segment_value("1beta4") == (1, -2, 4)

    def test_b_suffix_with_number(self) -> None:
        assert _segment_value("1b7") == (1, -2, 7)

    def test_rc_suffix_with_number(self) -> None:
        assert _segment_value("1rc2") == (1, -1, 2)

    def test_c_suffix_with_number(self) -> None:
        assert _segment_value("1c3") == (1, -1, 3)

    def test_post_suffix_with_number(self) -> None:
        assert _segment_value("1post5") == (1, 1, 5)

    def test_different_rc_numbers_are_distinct(self) -> None:
        """Regression: rc1 vs rc2 must produce different tuples."""
        assert _segment_value("1rc1") != _segment_value("1rc2")
        assert _segment_value("1rc1") < _segment_value("1rc2")

    def test_different_dev_numbers_are_distinct(self) -> None:
        """Regression: dev1 vs dev2 must produce different tuples."""
        assert _segment_value("1dev1") != _segment_value("1dev2")
        assert _segment_value("1dev1") < _segment_value("1dev2")

    def test_non_numeric_segment(self) -> None:
        assert _segment_value("abc") == (0, 0, 0)

    def test_empty_segment(self) -> None:
        assert _segment_value("") == (0, 0, 0)

    def test_unknown_suffix(self) -> None:
        assert _segment_value("1xyz") == (1, 0, 0)

    def test_whitespace_stripped(self) -> None:
        assert _segment_value("  42  ") == (42, 0, 0)

    def test_suffix_number_non_digit_ignored(self) -> None:
        """Non-digit suffix remainder defaults to 0."""
        assert _segment_value("1rcfoo") == (1, -1, 0)

    def test_pure_dev_segment(self) -> None:
        """Pure 'dev1' without leading digit returns (0, -4, 1)."""
        assert _segment_value("dev1") == (0, -4, 1)

    def test_pure_dev_segment_without_number(self) -> None:
        assert _segment_value("dev") == (0, -4, 0)

    def test_pure_rc_segment(self) -> None:
        assert _segment_value("rc2") == (0, -1, 2)

    def test_pure_alpha_segment(self) -> None:
        assert _segment_value("alpha3") == (0, -3, 3)

    def test_pure_beta_segment(self) -> None:
        assert _segment_value("beta1") == (0, -2, 1)

    def test_pure_post_segment(self) -> None:
        assert _segment_value("post4") == (0, 1, 4)

    def test_pure_dev1_vs_dev2_are_distinct(self) -> None:
        """Regression: pure dev1 vs dev2 must produce different tuples."""
        assert _segment_value("dev1") < _segment_value("dev2")

    def test_pure_prerelease_less_than_release(self) -> None:
        """Pure 'dev1' sorts below '0' (release)."""
        assert _segment_value("dev1") < _segment_value("0")
