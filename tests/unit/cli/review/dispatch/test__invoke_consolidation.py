"""Tests for _invoke_consolidation stub."""

from agentic_devtools.cli.review.dispatch import _invoke_consolidation


class TestInvokeConsolidation:
    """Tests for _invoke_consolidation stub."""

    def test_returns_true_on_success(self):
        """Stub always returns True (simulated success)."""
        result = _invoke_consolidation(pr_id=123, model_id="claude-opus-4-6")
        assert result is True

    def test_with_single_retry(self):
        """Works with retry_count=1."""
        result = _invoke_consolidation(pr_id=123, model_id="claude-opus-4-6", retry_count=1)
        assert result is True

    def test_uses_ascii_marker_without_emoji(self, capsys):
        """Uses [OK] marker when use_emoji=False."""
        _invoke_consolidation(pr_id=123, model_id="claude-opus-4-6", use_emoji=False)
        captured = capsys.readouterr()
        assert "[OK]" in captured.out
