"""Tests for agentic_devtools.cli.azure_devops.batch_review_helpers.validate_batch_reviews."""

from agentic_devtools.cli.azure_devops.batch_review_helpers import validate_batch_reviews


class TestValidateBatchReviews:
    """Tests for validate_batch_reviews."""

    def test_valid_approve_item(self):
        """A valid approve item produces no errors."""
        items = [{"file_path": "/a.ts", "outcome": "approve", "summary": "LGTM"}]
        errors = validate_batch_reviews(items)
        assert errors == []

    def test_valid_request_changes_item(self):
        """A valid request-changes item produces no errors."""
        items = [
            {
                "file_path": "/a.ts",
                "outcome": "request-changes",
                "summary": "Issues found",
                "suggestions": [{"line": 10, "severity": "high", "content": "Fix"}],
            },
        ]
        errors = validate_batch_reviews(items)
        assert errors == []

    def test_missing_file_path(self):
        """Missing file_path produces an error."""
        items = [{"outcome": "approve", "summary": "ok"}]
        errors = validate_batch_reviews(items)
        assert len(errors) == 1
        assert "missing required" in errors[0]
        assert "file_path" in errors[0]

    def test_empty_file_path(self):
        """Empty file_path produces an error."""
        items = [{"file_path": "", "outcome": "approve", "summary": "ok"}]
        errors = validate_batch_reviews(items)
        assert len(errors) == 1
        assert "empty or whitespace" in errors[0]

    def test_non_string_file_path(self):
        """Non-string file_path produces a type error."""
        items = [{"file_path": 42, "outcome": "approve", "summary": "ok"}]
        errors = validate_batch_reviews(items)
        assert len(errors) == 1
        assert "must be a string" in errors[0]
        assert "int" in errors[0]

    def test_whitespace_only_file_path(self):
        """Whitespace-only file_path produces an error."""
        items = [{"file_path": "   ", "outcome": "approve", "summary": "ok"}]
        errors = validate_batch_reviews(items)
        assert len(errors) == 1
        assert "empty or whitespace" in errors[0]

    def test_unknown_outcome(self):
        """Unknown outcome produces an error."""
        items = [{"file_path": "/a.ts", "outcome": "invalid", "summary": "ok"}]
        errors = validate_batch_reviews(items)
        assert len(errors) == 1
        assert "unknown outcome" in errors[0]

    def test_missing_summary(self):
        """Missing summary (None) produces a type error."""
        items = [{"file_path": "/a.ts", "outcome": "approve", "summary": None}]
        errors = validate_batch_reviews(items)
        assert len(errors) == 1
        assert "must be a string" in errors[0]

    def test_empty_summary(self):
        """Empty summary produces an error."""
        items = [{"file_path": "/a.ts", "outcome": "approve", "summary": ""}]
        errors = validate_batch_reviews(items)
        assert len(errors) == 1
        assert "summary is required" in errors[0]

    def test_non_string_summary_integer(self):
        """Non-string summary (integer) produces a type error."""
        items = [{"file_path": "/a.ts", "outcome": "approve", "summary": 42}]
        errors = validate_batch_reviews(items)
        assert len(errors) == 1
        assert "must be a string" in errors[0]
        assert "int" in errors[0]

    def test_non_string_summary_boolean(self):
        """Non-string summary (bool) produces a type error."""
        items = [{"file_path": "/a.ts", "outcome": "approve", "summary": True}]
        errors = validate_batch_reviews(items)
        assert len(errors) == 1
        assert "must be a string" in errors[0]
        assert "bool" in errors[0]

    def test_request_changes_missing_suggestions(self):
        """request-changes without suggestions produces an error."""
        items = [
            {"file_path": "/a.ts", "outcome": "request-changes", "summary": "Issues"},
        ]
        errors = validate_batch_reviews(items)
        assert len(errors) == 1
        assert "suggestions" in errors[0]

    def test_request_changes_empty_suggestions(self):
        """request-changes with empty suggestions produces an error."""
        items = [
            {
                "file_path": "/a.ts",
                "outcome": "request-changes",
                "summary": "Issues",
                "suggestions": [],
            },
        ]
        errors = validate_batch_reviews(items)
        assert len(errors) == 1
        assert "suggestions" in errors[0]

    def test_non_dict_suggestion(self):
        """Non-dict suggestion produces an error."""
        items = [
            {
                "file_path": "/a.ts",
                "outcome": "request-changes",
                "summary": "Issues",
                "suggestions": ["not a dict"],
            },
        ]
        errors = validate_batch_reviews(items)
        assert len(errors) == 1
        assert "must be an object/dict" in errors[0]

    def test_non_dict_item(self):
        """Non-dict item produces an error."""
        items = ["not a dict"]
        errors = validate_batch_reviews(items)
        assert len(errors) == 1
        assert "not a JSON object" in errors[0]

    def test_multiple_errors(self):
        """Multiple invalid items produce multiple errors."""
        items = [
            {"file_path": "", "outcome": "approve", "summary": "ok"},
            {"file_path": "/b.ts", "outcome": "invalid", "summary": "ok"},
        ]
        errors = validate_batch_reviews(items)
        assert len(errors) == 2

    def test_non_string_outcome(self):
        """Non-string outcome produces a type error."""
        items = [{"file_path": "/a.ts", "outcome": 42, "summary": "ok"}]
        errors = validate_batch_reviews(items)
        assert len(errors) == 1
        assert "must be a string" in errors[0]

    def test_approve_does_not_require_suggestions(self):
        """Approve outcome doesn't need suggestions."""
        items = [{"file_path": "/a.ts", "outcome": "approve", "summary": "LGTM"}]
        errors = validate_batch_reviews(items)
        assert errors == []

    def test_request_changes_with_suggestion_outcome(self):
        """request-changes-with-suggestion is a valid outcome."""
        items = [
            {
                "file_path": "/a.ts",
                "outcome": "request-changes-with-suggestion",
                "summary": "Suggestions",
                "suggestions": [{"line": 5, "severity": "medium", "content": "Rename", "replacement_code": "x"}],
            },
        ]
        errors = validate_batch_reviews(items)
        assert errors == []

    def test_suggestion_missing_severity(self):
        """Suggestion missing severity produces an error."""
        items = [
            {
                "file_path": "/a.ts",
                "outcome": "request-changes",
                "summary": "Issues",
                "suggestions": [{"line": 10, "content": "Fix"}],
            },
        ]
        errors = validate_batch_reviews(items)
        assert len(errors) == 1
        assert "severity" in errors[0]

    def test_suggestion_missing_line(self):
        """Suggestion missing line produces an error."""
        items = [
            {
                "file_path": "/a.ts",
                "outcome": "request-changes",
                "summary": "Issues",
                "suggestions": [{"severity": "high", "content": "Fix"}],
            },
        ]
        errors = validate_batch_reviews(items)
        assert len(errors) == 1
        assert "line" in errors[0]

    def test_suggestion_missing_replacement_code_for_with_suggestion(self):
        """request-changes-with-suggestion without replacement_code."""
        items = [
            {
                "file_path": "/a.ts",
                "outcome": "request-changes-with-suggestion",
                "summary": "Suggestions",
                "suggestions": [{"line": 5, "severity": "medium", "content": "Rename"}],
            },
        ]
        errors = validate_batch_reviews(items)
        assert len(errors) == 1
        assert "replacement_code" in errors[0]
