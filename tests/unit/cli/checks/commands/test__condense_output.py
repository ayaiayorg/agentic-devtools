"""Tests for _condense_output helper."""

from agentic_devtools.cli.checks.commands import _condense_output


class TestCondenseOutput:
    """Tests for _condense_output stripping noise from check output."""

    def test_strips_passed_test_lines(self):
        raw = (
            "tests/unit/foo/test_bar.py::TestBar::test_one PASSED\n"
            "tests/unit/foo/test_bar.py::TestBar::test_two PASSED\n"
            "FAIL: coverage < 100%\n"
        )
        result = _condense_output(raw)
        assert "PASSED" not in result
        assert "FAIL: coverage < 100%" in result

    def test_strips_platform_metadata(self):
        raw = (
            "platform win32 -- Python 3.13.8\n"
            "cachedir: .pytest_cache\n"
            "rootdir: C:\\repos\\test\n"
            "configfile: pyproject.toml\n"
            "plugins: cov-6.0\n"
            "collecting ... collected 5 items\n"
            "collected 5 items\n"
            "FAIL: something broke\n"
        )
        result = _condense_output(raw)
        assert "platform" not in result
        assert "cachedir" not in result
        assert "rootdir" not in result
        assert "configfile" not in result
        assert "plugins" not in result
        assert "collecting" not in result
        assert "collected" not in result
        assert "FAIL: something broke" in result

    def test_collapses_consecutive_blank_lines(self):
        raw = "line1\n\n\n\nline2\n"
        result = _condense_output(raw)
        assert result == "line1\n\nline2"

    def test_removes_trailing_blank_lines(self):
        raw = "content\n\n\n"
        result = _condense_output(raw)
        assert result == "content"

    def test_keeps_non_passed_lines(self):
        raw = (
            "-- source.py -> tests/unit/source --\n"
            "FAIL: missing coverage\n"
            "E   AssertionError: expected True\n"
            "> assert False\n"
        )
        result = _condense_output(raw)
        assert "-- source.py" in result
        assert "FAIL:" in result
        assert "E   AssertionError" in result
        assert "> assert False" in result

    def test_empty_input(self):
        assert _condense_output("") == ""

    def test_keeps_passed_without_double_colon(self):
        """Lines ending in PASSED but without :: are kept (not test results)."""
        raw = "All checks PASSED\n"
        result = _condense_output(raw)
        assert "All checks PASSED" in result
