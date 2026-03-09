"""Tests for _apply_resolution stub."""

from agentic_devtools.cli.review.consolidate import _apply_resolution


class TestApplyResolution:
    """Tests for _apply_resolution stub."""

    def test_does_not_raise(self):
        """Stub completes without error."""
        _apply_resolution(pr_id=123, resolution={"resolution": "mock"})
