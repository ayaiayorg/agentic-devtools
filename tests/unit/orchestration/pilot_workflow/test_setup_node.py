"""Tests for setup_node stub function."""

from agentic_devtools.orchestration.pilot_workflow import setup_node


class TestSetupNode:
    def test_returns_step_setup(self):
        result = setup_node({})
        assert result["step"] == "setup"

    def test_clears_error(self):
        result = setup_node({"error": "something"})
        assert result["error"] is None

    def test_appends_event(self):
        result = setup_node({})
        assert len(result["events"]) == 1
        assert result["events"][0]["event"] == "setup_completed"

    def test_event_has_timestamp(self):
        result = setup_node({})
        assert "timestamp" in result["events"][0]
