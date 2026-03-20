"""Tests for pull_request_node stub function."""

from agentic_devtools.orchestration.pilot_workflow import pull_request_node


class TestPullRequestNode:
    def test_returns_step_pull_request(self):
        result = pull_request_node({})
        assert result["step"] == "pull_request"

    def test_appends_event(self):
        result = pull_request_node({})
        assert len(result["events"]) == 1
        assert result["events"][0]["event"] == "pull_request_completed"

    def test_event_has_timestamp(self):
        result = pull_request_node({})
        assert "timestamp" in result["events"][0]
