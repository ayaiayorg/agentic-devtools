"""Tests for _config_to_dict."""

from agentic_devtools.cli.azure_devops.review_config import ReviewerConfig
from agentic_devtools.cli.review.config_commands import _config_to_dict


class TestConfigToDict:
    """Tests for _config_to_dict."""

    def test_converts_dataclass(self):
        """Converts a dataclass to dict."""
        result = _config_to_dict(ReviewerConfig(model_id="claude-opus-4-6", role="primary"))
        assert result == {"model_id": "claude-opus-4-6", "role": "primary"}

    def test_converts_list(self):
        """Converts a list of dataclasses."""
        result = _config_to_dict([ReviewerConfig(model_id="claude-opus-4-6", role="primary")])
        assert result == [{"model_id": "claude-opus-4-6", "role": "primary"}]

    def test_converts_dict(self):
        """Converts a dict with nested values."""
        result = _config_to_dict({"key": "value", "nested": {"inner": 1}})
        assert result == {"key": "value", "nested": {"inner": 1}}

    def test_passes_through_primitives(self):
        """Primitives pass through unchanged."""
        assert _config_to_dict("hello") == "hello"
        assert _config_to_dict(42) == 42
        assert _config_to_dict(True) is True
