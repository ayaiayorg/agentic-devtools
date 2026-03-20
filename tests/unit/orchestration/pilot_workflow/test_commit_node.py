"""Tests for commit_node stub function."""

from agentic_devtools.orchestration.pilot_workflow import commit_node


class TestCommitNode:
    def test_returns_step_commit(self):
        result = commit_node({})
        assert result["step"] == "commit"

    def test_appends_event(self):
        result = commit_node({})
        assert len(result["events"]) == 1
        assert result["events"][0]["event"] == "commit_completed"

    def test_event_has_timestamp(self):
        result = commit_node({})
        assert "timestamp" in result["events"][0]
