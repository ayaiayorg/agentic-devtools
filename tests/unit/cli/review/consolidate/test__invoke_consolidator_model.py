"""Tests for _invoke_consolidator_model stub."""

from agentic_devtools.cli.review.consolidate import _invoke_consolidator_model


class TestInvokeConsolidatorModel:
    """Tests for _invoke_consolidator_model stub."""

    def test_returns_mock_resolution(self):
        """Stub returns mock resolution dict."""
        result = _invoke_consolidator_model(model_id="claude-opus-4-6", prompt="test")
        assert "resolution" in result
        assert result["resolution"] == "mock"
