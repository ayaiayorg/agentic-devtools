"""Tests for agentic_devtools.cli.azure_devops.submit_reviews._validate_suggestion_fields."""

from agentic_devtools.cli.azure_devops.submit_reviews import _validate_suggestion_fields


class TestValidateSuggestionFields:
    """Tests for _validate_suggestion_fields."""

    # -- Valid suggestions --

    def test_valid_request_changes_suggestion(self):
        """A suggestion with all required fields produces no errors."""
        errors = _validate_suggestion_fields(
            {"line": 10, "severity": "high", "content": "Fix this"},
            item_idx=0, sg_idx=0, file_path="/a.ts", outcome="request-changes",
        )
        assert errors == []

    def test_valid_request_changes_with_suggestion(self):
        """A suggestion with replacement_code for request-changes-with-suggestion."""
        errors = _validate_suggestion_fields(
            {"line": 5, "severity": "medium", "content": "Rename", "replacement_code": "newName"},
            item_idx=0, sg_idx=0, file_path="/a.ts", outcome="request-changes-with-suggestion",
        )
        assert errors == []

    def test_severity_case_insensitive(self):
        """Severity is matched case-insensitively."""
        for sev in ("High", "MEDIUM", "Low"):
            errors = _validate_suggestion_fields(
                {"line": 1, "severity": sev, "content": "ok"},
                item_idx=0, sg_idx=0, file_path="/a.ts", outcome="request-changes",
            )
            assert errors == [], f"severity '{sev}' should be valid"

    # -- line field validation --

    def test_missing_line(self):
        """Missing line produces an error."""
        errors = _validate_suggestion_fields(
            {"severity": "high", "content": "Fix"},
            item_idx=0, sg_idx=0, file_path="/a.ts", outcome="request-changes",
        )
        assert len(errors) == 1
        assert "'line'" in errors[0]

    def test_non_integer_line(self):
        """Non-integer line produces an error."""
        errors = _validate_suggestion_fields(
            {"line": "10", "severity": "high", "content": "Fix"},
            item_idx=0, sg_idx=0, file_path="/a.ts", outcome="request-changes",
        )
        assert len(errors) == 1
        assert "'line'" in errors[0]
        assert "str" in errors[0]

    def test_boolean_line_rejected(self):
        """Boolean line is rejected (bool is subclass of int)."""
        errors = _validate_suggestion_fields(
            {"line": True, "severity": "high", "content": "Fix"},
            item_idx=0, sg_idx=0, file_path="/a.ts", outcome="request-changes",
        )
        assert len(errors) == 1
        assert "'line'" in errors[0]

    def test_zero_line(self):
        """Line 0 is invalid (must be ≥ 1)."""
        errors = _validate_suggestion_fields(
            {"line": 0, "severity": "high", "content": "Fix"},
            item_idx=0, sg_idx=0, file_path="/a.ts", outcome="request-changes",
        )
        assert len(errors) == 1
        assert "≥ 1" in errors[0]

    def test_negative_line(self):
        """Negative line is invalid."""
        errors = _validate_suggestion_fields(
            {"line": -1, "severity": "high", "content": "Fix"},
            item_idx=0, sg_idx=0, file_path="/a.ts", outcome="request-changes",
        )
        assert len(errors) == 1
        assert "≥ 1" in errors[0]

    # -- severity field validation --

    def test_missing_severity(self):
        """Missing severity produces an error."""
        errors = _validate_suggestion_fields(
            {"line": 10, "content": "Fix"},
            item_idx=0, sg_idx=0, file_path="/a.ts", outcome="request-changes",
        )
        assert len(errors) == 1
        assert "'severity'" in errors[0]

    def test_non_string_severity(self):
        """Non-string severity produces an error."""
        errors = _validate_suggestion_fields(
            {"line": 10, "severity": 42, "content": "Fix"},
            item_idx=0, sg_idx=0, file_path="/a.ts", outcome="request-changes",
        )
        assert len(errors) == 1
        assert "'severity'" in errors[0]
        assert "int" in errors[0]

    def test_unknown_severity(self):
        """Unknown severity value produces an error."""
        errors = _validate_suggestion_fields(
            {"line": 10, "severity": "critical", "content": "Fix"},
            item_idx=0, sg_idx=0, file_path="/a.ts", outcome="request-changes",
        )
        assert len(errors) == 1
        assert "unknown severity" in errors[0]

    # -- content field validation --

    def test_missing_content(self):
        """Missing content produces an error."""
        errors = _validate_suggestion_fields(
            {"line": 10, "severity": "high"},
            item_idx=0, sg_idx=0, file_path="/a.ts", outcome="request-changes",
        )
        assert len(errors) == 1
        assert "'content'" in errors[0]

    def test_non_string_content(self):
        """Non-string content produces an error."""
        errors = _validate_suggestion_fields(
            {"line": 10, "severity": "high", "content": 42},
            item_idx=0, sg_idx=0, file_path="/a.ts", outcome="request-changes",
        )
        assert len(errors) == 1
        assert "'content'" in errors[0]
        assert "int" in errors[0]

    def test_empty_content(self):
        """Empty content produces an error."""
        errors = _validate_suggestion_fields(
            {"line": 10, "severity": "high", "content": "  "},
            item_idx=0, sg_idx=0, file_path="/a.ts", outcome="request-changes",
        )
        assert len(errors) == 1
        assert "'content'" in errors[0]
        assert "empty" in errors[0]

    # -- replacement_code field validation --

    def test_replacement_code_not_required_for_request_changes(self):
        """replacement_code is not required for request-changes."""
        errors = _validate_suggestion_fields(
            {"line": 10, "severity": "high", "content": "Fix"},
            item_idx=0, sg_idx=0, file_path="/a.ts", outcome="request-changes",
        )
        assert errors == []

    def test_missing_replacement_code_for_with_suggestion(self):
        """Missing replacement_code for request-changes-with-suggestion."""
        errors = _validate_suggestion_fields(
            {"line": 10, "severity": "high", "content": "Fix"},
            item_idx=0, sg_idx=0, file_path="/a.ts", outcome="request-changes-with-suggestion",
        )
        assert len(errors) == 1
        assert "replacement_code" in errors[0]

    def test_empty_replacement_code_for_with_suggestion(self):
        """Empty replacement_code for request-changes-with-suggestion."""
        errors = _validate_suggestion_fields(
            {"line": 10, "severity": "high", "content": "Fix", "replacement_code": "  "},
            item_idx=0, sg_idx=0, file_path="/a.ts", outcome="request-changes-with-suggestion",
        )
        assert len(errors) == 1
        assert "replacement_code" in errors[0]
        assert "empty" in errors[0]

    def test_non_string_replacement_code(self):
        """Non-string replacement_code produces an error."""
        errors = _validate_suggestion_fields(
            {"line": 10, "severity": "high", "content": "Fix", "replacement_code": 42},
            item_idx=0, sg_idx=0, file_path="/a.ts", outcome="request-changes-with-suggestion",
        )
        assert len(errors) == 1
        assert "replacement_code" in errors[0]

    # -- Multiple errors --

    def test_all_fields_missing(self):
        """Missing all required fields produces multiple errors."""
        errors = _validate_suggestion_fields(
            {},
            item_idx=0, sg_idx=0, file_path="/a.ts", outcome="request-changes",
        )
        assert len(errors) == 3  # line, severity, content

    def test_all_fields_missing_with_suggestion(self):
        """Missing all fields for request-changes-with-suggestion produces 4 errors."""
        errors = _validate_suggestion_fields(
            {},
            item_idx=0, sg_idx=0, file_path="/a.ts", outcome="request-changes-with-suggestion",
        )
        assert len(errors) == 4  # line, severity, content, replacement_code

    # -- Error message formatting --

    def test_error_message_includes_item_and_suggestion_index(self):
        """Error messages include item and suggestion indices."""
        errors = _validate_suggestion_fields(
            {"line": "bad", "severity": "high", "content": "Fix"},
            item_idx=2, sg_idx=3, file_path="/x.ts", outcome="request-changes",
        )
        assert "Item 2" in errors[0]
        assert "suggestion 3" in errors[0]
        assert "/x.ts" in errors[0]
