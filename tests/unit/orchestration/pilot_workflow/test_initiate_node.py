"""Tests for initiate_node stub function."""

from agentic_devtools.orchestration.pilot_workflow import initiate_node


class TestInitiateNode:
    def test_returns_step_initiate(self):
        result = initiate_node({})
        assert result["step"] == "initiate"

    def test_sets_status_active(self):
        result = initiate_node({})
        assert result["status"] == "active"

    def test_appends_event(self):
        result = initiate_node({})
        assert len(result["events"]) == 1
        assert result["events"][0]["event"] == "initiate_completed"

    def test_event_has_timestamp(self):
        result = initiate_node({})
        assert "timestamp" in result["events"][0]
