"""Tests for agentic_devtools.submission_processor._validate_suggestions."""

import pytest

from agentic_devtools.submission_processor import _validate_suggestions


class TestValidateSuggestions:
    """Tests for _validate_suggestions helper."""

    def test_valid_suggestions_pass(self):
        """Fully-specified suggestion dicts pass validation without error."""
        suggestions = [
            {"line": 1, "severity": "high", "content": "Fix this"},
            {"line": 5, "severity": "medium", "content": "Rename", "end_line": 10},
        ]
        _validate_suggestions(suggestions)  # should not raise

    def test_missing_single_key_raises(self):
        """Missing 'severity' raises ValueError naming the missing key."""
        suggestions = [{"line": 1, "content": "Fix this"}]
        with pytest.raises(ValueError, match="severity"):
            _validate_suggestions(suggestions)

    def test_missing_multiple_keys_reports_all(self):
        """Empty dict reports all three missing keys."""
        suggestions = [{}]
        with pytest.raises(ValueError, match="line.*severity.*content"):
            _validate_suggestions(suggestions)

    def test_empty_list_passes(self):
        """Empty suggestion list is valid (no suggestions to validate)."""
        _validate_suggestions([])  # should not raise

    def test_second_item_invalid(self):
        """Validation error references correct index when second item is bad."""
        suggestions = [
            {"line": 1, "severity": "high", "content": "OK"},
            {"line": 2},  # missing severity and content
        ]
        with pytest.raises(ValueError, match="index 1.*severity.*content"):
            _validate_suggestions(suggestions)
