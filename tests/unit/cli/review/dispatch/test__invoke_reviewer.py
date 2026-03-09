"""Tests for _invoke_reviewer stub."""

from agentic_devtools.cli.review.dispatch import _invoke_reviewer


class TestInvokeReviewer:
    """Tests for _invoke_reviewer stub."""

    def test_returns_true_on_success(self):
        """Stub always returns True (simulated success)."""
        result = _invoke_reviewer(pr_id=123, model_id="claude-opus-4-6", role="primary")
        assert result is True

    def test_with_single_retry(self):
        """Works with retry_count=1."""
        result = _invoke_reviewer(pr_id=123, model_id="claude-opus-4-6", role="primary", retry_count=1)
        assert result is True

    def test_uses_ascii_marker_without_emoji(self, capsys):
        """Uses [OK] marker when use_emoji=False."""
        _invoke_reviewer(pr_id=123, model_id="claude-opus-4-6", role="primary", use_emoji=False)
        captured = capsys.readouterr()
        assert "[OK]" in captured.out

    def test_uses_emoji_marker_with_emoji(self, capsys):
        """Uses ✓ marker when use_emoji=True."""
        _invoke_reviewer(pr_id=123, model_id="claude-opus-4-6", role="primary", use_emoji=True)
        captured = capsys.readouterr()
        assert "✓" in captured.out
