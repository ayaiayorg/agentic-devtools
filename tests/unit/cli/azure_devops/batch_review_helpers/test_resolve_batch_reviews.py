"""Tests for agentic_devtools.cli.azure_devops.batch_review_helpers.resolve_batch_reviews."""

from agentic_devtools.cli.azure_devops.batch_review_helpers import resolve_batch_reviews


class TestResolveBatchReviews:
    """Tests for resolve_batch_reviews."""

    def test_applies_default_outcome(self):
        """Items without outcome get the default."""
        payload = {
            "default_outcome": "approve",
            "items": [{"file_path": "/a.ts"}],
        }
        result = resolve_batch_reviews(payload)
        assert result[0]["outcome"] == "approve"

    def test_applies_default_summary(self):
        """Items without summary get the default."""
        payload = {
            "default_summary": "LGTM",
            "items": [{"file_path": "/a.ts"}],
        }
        result = resolve_batch_reviews(payload)
        assert result[0]["summary"] == "LGTM"

    def test_per_item_outcome_overrides_default(self):
        """Per-item outcome takes precedence over default."""
        payload = {
            "default_outcome": "approve",
            "items": [{"file_path": "/a.ts", "outcome": "request-changes"}],
        }
        result = resolve_batch_reviews(payload)
        assert result[0]["outcome"] == "request-changes"

    def test_per_item_summary_overrides_default(self):
        """Per-item summary takes precedence over default."""
        payload = {
            "default_summary": "Default summary",
            "items": [{"file_path": "/a.ts", "summary": "Custom summary"}],
        }
        result = resolve_batch_reviews(payload)
        assert result[0]["summary"] == "Custom summary"

    def test_default_outcome_defaults_to_approve(self):
        """When no default_outcome is provided, 'approve' is used."""
        payload = {"items": [{"file_path": "/a.ts"}]}
        result = resolve_batch_reviews(payload)
        assert result[0]["outcome"] == "approve"

    def test_empty_items_returns_empty(self):
        """Empty items list returns empty resolved list."""
        payload = {"items": []}
        result = resolve_batch_reviews(payload)
        assert result == []

    def test_suggestions_preserved(self):
        """Suggestions from items are preserved in output."""
        payload = {
            "items": [
                {
                    "file_path": "/a.ts",
                    "outcome": "request-changes",
                    "suggestions": [{"line": 10, "content": "Fix"}],
                },
            ],
        }
        result = resolve_batch_reviews(payload)
        assert result[0]["suggestions"] == [{"line": 10, "content": "Fix"}]

    def test_multiple_items_resolved(self):
        """Multiple items are all resolved correctly."""
        payload = {
            "default_outcome": "approve",
            "default_summary": "LGTM",
            "items": [
                {"file_path": "/a.ts"},
                {"file_path": "/b.ts", "summary": "Custom"},
            ],
        }
        result = resolve_batch_reviews(payload)
        assert len(result) == 2
        assert result[0]["summary"] == "LGTM"
        assert result[1]["summary"] == "Custom"

    def test_outcome_normalized_to_lowercase(self):
        """Outcome strings are lowercased."""
        payload = {"items": [{"file_path": "/a.ts", "outcome": "Approve"}]}
        result = resolve_batch_reviews(payload)
        assert result[0]["outcome"] == "approve"

    def test_empty_string_outcome_uses_default(self):
        """Empty string outcome falls back to default."""
        payload = {
            "default_outcome": "approve",
            "items": [{"file_path": "/a.ts", "outcome": ""}],
        }
        result = resolve_batch_reviews(payload)
        assert result[0]["outcome"] == "approve"

    def test_empty_string_summary_uses_default(self):
        """Empty string summary falls back to default."""
        payload = {
            "default_summary": "Default",
            "items": [{"file_path": "/a.ts", "summary": ""}],
        }
        result = resolve_batch_reviews(payload)
        assert result[0]["summary"] == "Default"

    def test_whitespace_only_summary_uses_default(self):
        """Whitespace-only summary falls back to default."""
        payload = {
            "default_summary": "Default",
            "items": [{"file_path": "/a.ts", "summary": "   "}],
        }
        result = resolve_batch_reviews(payload)
        assert result[0]["summary"] == "Default"

    def test_does_not_mutate_original_items(self):
        """Resolve creates copies, not mutating original items."""
        items = [{"file_path": "/a.ts"}]
        payload = {"default_outcome": "approve", "items": items}
        resolve_batch_reviews(payload)
        assert "outcome" not in items[0]

    def test_non_dict_item_passed_through(self):
        """Non-dict items are passed through for validation to catch."""
        payload = {"items": ["not a dict", 42]}
        result = resolve_batch_reviews(payload)
        assert result == ["not a dict", 42]

    def test_falsy_non_string_outcome_not_replaced(self):
        """Non-string falsy outcome (e.g., False, 0) is preserved, not replaced by default."""
        payload = {
            "default_outcome": "approve",
            "items": [{"file_path": "/a.ts", "outcome": False}],
        }
        result = resolve_batch_reviews(payload)
        # False is preserved so validation can catch the type error
        assert result[0]["outcome"] is False

    def test_falsy_non_string_summary_not_replaced(self):
        """Non-string falsy summary (e.g., 0) is preserved, not replaced by default."""
        payload = {
            "default_summary": "Default",
            "items": [{"file_path": "/a.ts", "summary": 0}],
        }
        result = resolve_batch_reviews(payload)
        # 0 is preserved so validation can catch the type error
        assert result[0]["summary"] == 0

    def test_items_null_returns_empty(self):
        """payload with items=null resolves to empty list (no crash)."""
        payload = {"items": None}
        result = resolve_batch_reviews(payload)
        assert result == []

    def test_items_non_list_wrapped(self):
        """Non-list items value is wrapped so validation can surface error."""
        payload = {"items": "not-a-list"}
        result = resolve_batch_reviews(payload)
        assert result == ["not-a-list"]

    def test_items_missing_returns_empty(self):
        """Missing items key resolves to empty list."""
        payload = {}
        result = resolve_batch_reviews(payload)
        assert result == []
