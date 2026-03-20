"""Tests for completion_node stub function."""

from agentic_devtools.orchestration.pilot_workflow import completion_node


class TestCompletionNode:
    def test_returns_step_completion(self):
        result = completion_node({})
        assert result["step"] == "completion"

    def test_sets_status_completed(self):
        result = completion_node({})
        assert result["status"] == "completed"

    def test_appends_event(self):
        result = completion_node({})
        assert len(result["events"]) == 1
        assert result["events"][0]["event"] == "completion_completed"

    def test_event_has_timestamp(self):
        result = completion_node({})
        assert "timestamp" in result["events"][0]
