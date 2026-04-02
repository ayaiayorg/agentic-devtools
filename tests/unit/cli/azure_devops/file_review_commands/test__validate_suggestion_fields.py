"""Tests for _validate_suggestion_fields shared validator."""

from agentic_devtools.cli.azure_devops.file_review_commands import _validate_suggestion_fields


class TestValidateSuggestionFields:
    """Tests for the shared suggestion field validator."""

    def test_valid_suggestion_returns_empty_list(self):
        """A valid suggestion should produce no errors."""
        s = {"content": "Fix this", "line": 10, "severity": "high"}
        assert _validate_suggestion_fields(s, 0) == []

    def test_normalizes_severity_to_lowercase(self):
        """Severity should be normalized to lowercase in-place."""
        s = {"content": "Fix", "line": 10, "severity": " High "}
        errors = _validate_suggestion_fields(s, 0)
        assert errors == []
        assert s["severity"] == "high"

    def test_rejects_invalid_severity_value(self):
        """Severity not in {high, medium, low} should be rejected."""
        s = {"content": "Fix", "line": 10, "severity": "critical"}
        errors = _validate_suggestion_fields(s, 0)
        assert len(errors) == 1
        assert "invalid severity" in errors[0]

    def test_rejects_empty_content(self):
        """Empty content should be rejected."""
        s = {"content": "", "line": 10, "severity": "high"}
        errors = _validate_suggestion_fields(s, 0)
        assert len(errors) == 1
        assert "non-empty string" in errors[0]

    def test_rejects_non_string_content(self):
        """Non-string content should be rejected."""
        s = {"content": 123, "line": 10, "severity": "high"}
        errors = _validate_suggestion_fields(s, 0)
        assert len(errors) == 1
        assert "non-empty string" in errors[0]

    def test_rejects_missing_content(self):
        """Missing content key should be rejected."""
        s = {"line": 10, "severity": "high"}
        errors = _validate_suggestion_fields(s, 0)
        assert len(errors) == 1
        assert "content" in errors[0]

    def test_rejects_missing_line(self):
        """Missing 'line' key should be rejected with 'required and missing' message."""
        s = {"content": "Fix", "severity": "high"}
        errors = _validate_suggestion_fields(s, 0)
        assert len(errors) == 1
        assert "required and missing" in errors[0]

    def test_rejects_null_line(self):
        """Null line should be rejected with specific message."""
        s = {"content": "Fix", "line": None, "severity": "high"}
        errors = _validate_suggestion_fields(s, 0)
        assert len(errors) == 1
        assert "must not be null" in errors[0]

    def test_rejects_bool_line(self):
        """Boolean line should be rejected."""
        s = {"content": "Fix", "line": True, "severity": "high"}
        errors = _validate_suggestion_fields(s, 0)
        assert len(errors) == 1
        assert "expected integer" in errors[0]

    def test_rejects_string_line(self):
        """String line should be rejected."""
        s = {"content": "Fix", "line": "10", "severity": "high"}
        errors = _validate_suggestion_fields(s, 0)
        assert len(errors) == 1
        assert "expected integer" in errors[0]

    def test_rejects_line_less_than_1(self):
        """Line < 1 should be rejected."""
        s = {"content": "Fix", "line": 0, "severity": "high"}
        errors = _validate_suggestion_fields(s, 0)
        assert len(errors) == 1
        assert ">= 1" in errors[0]

    def test_rejects_empty_severity(self):
        """Empty severity should be rejected."""
        s = {"content": "Fix", "line": 10, "severity": ""}
        errors = _validate_suggestion_fields(s, 0)
        assert len(errors) == 1
        assert "severity" in errors[0]

    def test_rejects_non_string_severity(self):
        """Non-string severity should be rejected."""
        s = {"content": "Fix", "line": 10, "severity": 42}
        errors = _validate_suggestion_fields(s, 0)
        assert len(errors) == 1
        assert "severity" in errors[0]

    # --- Optional field: end_line ---

    def test_valid_end_line(self):
        """Valid end_line >= line should pass."""
        s = {"content": "Fix", "line": 10, "severity": "high", "end_line": 15}
        assert _validate_suggestion_fields(s, 0) == []

    def test_null_end_line_removed(self):
        """Null end_line should be removed from suggestion."""
        s = {"content": "Fix", "line": 10, "severity": "high", "end_line": None}
        assert _validate_suggestion_fields(s, 0) == []
        assert "end_line" not in s

    def test_rejects_string_end_line(self):
        """String end_line should be rejected."""
        s = {"content": "Fix", "line": 10, "severity": "high", "end_line": "15"}
        errors = _validate_suggestion_fields(s, 0)
        assert len(errors) == 1
        assert "end_line" in errors[0]
        assert "integer" in errors[0]

    def test_rejects_bool_end_line(self):
        """Boolean end_line should be rejected."""
        s = {"content": "Fix", "line": 10, "severity": "high", "end_line": True}
        errors = _validate_suggestion_fields(s, 0)
        assert len(errors) == 1
        assert "end_line" in errors[0]

    def test_rejects_end_line_less_than_1(self):
        """end_line < 1 should be rejected."""
        s = {"content": "Fix", "line": 10, "severity": "high", "end_line": 0}
        errors = _validate_suggestion_fields(s, 0)
        assert len(errors) == 1
        assert "end_line" in errors[0]
        assert ">= 1" in errors[0]

    def test_rejects_end_line_less_than_line(self):
        """end_line < line should be rejected."""
        s = {"content": "Fix", "line": 10, "severity": "high", "end_line": 5}
        errors = _validate_suggestion_fields(s, 0)
        assert len(errors) == 1
        assert "end_line" in errors[0]

    # --- Optional field: out_of_scope ---

    def test_valid_out_of_scope_bool(self):
        """Boolean out_of_scope should pass."""
        s = {"content": "Fix", "line": 10, "severity": "high", "out_of_scope": True}
        assert _validate_suggestion_fields(s, 0) == []

    def test_rejects_non_bool_out_of_scope(self):
        """Non-boolean out_of_scope should be rejected."""
        s = {"content": "Fix", "line": 10, "severity": "high", "out_of_scope": "yes"}
        errors = _validate_suggestion_fields(s, 0)
        assert len(errors) == 1
        assert "out_of_scope" in errors[0]
        assert "boolean" in errors[0]

    # --- Optional field: link_text ---

    def test_valid_link_text(self):
        """Non-empty string link_text should pass."""
        s = {"content": "Fix", "line": 10, "severity": "high", "link_text": "see here"}
        assert _validate_suggestion_fields(s, 0) == []

    def test_null_link_text_removed(self):
        """Null link_text should be removed from suggestion."""
        s = {"content": "Fix", "line": 10, "severity": "high", "link_text": None}
        assert _validate_suggestion_fields(s, 0) == []
        assert "link_text" not in s

    def test_blank_link_text_removed(self):
        """Whitespace-only link_text should be removed."""
        s = {"content": "Fix", "line": 10, "severity": "high", "link_text": "   "}
        assert _validate_suggestion_fields(s, 0) == []
        assert "link_text" not in s

    def test_rejects_non_string_link_text(self):
        """Non-string link_text should be rejected."""
        s = {"content": "Fix", "line": 10, "severity": "high", "link_text": 42}
        errors = _validate_suggestion_fields(s, 0)
        assert len(errors) == 1
        assert "link_text" in errors[0]

    # --- Conditional: replacement_code ---

    def test_replacement_code_validated_for_suggest_outcome(self):
        """replacement_code must be present for request-changes-with-suggestion."""
        s = {"content": "Fix", "line": 10, "severity": "high"}
        errors = _validate_suggestion_fields(s, 0, outcome="request-changes-with-suggestion")
        assert len(errors) == 1
        assert "replacement_code" in errors[0]

    def test_replacement_code_not_required_for_changes_outcome(self):
        """replacement_code should not be required for request-changes."""
        s = {"content": "Fix", "line": 10, "severity": "high"}
        errors = _validate_suggestion_fields(s, 0, outcome="request-changes")
        assert errors == []

    def test_valid_replacement_code(self):
        """Valid replacement_code should pass."""
        s = {"content": "Fix", "line": 10, "severity": "high", "replacement_code": "fixed code"}
        errors = _validate_suggestion_fields(s, 0, outcome="request-changes-with-suggestion")
        assert errors == []

    # --- context_prefix ---

    def test_context_prefix_in_error_message(self):
        """Errors should include the context_prefix."""
        s = {"content": "", "line": 10, "severity": "high"}
        errors = _validate_suggestion_fields(s, 0, context_prefix="Review at index 3 (foo.ts): ")
        assert errors[0].startswith("Review at index 3 (foo.ts): ")
