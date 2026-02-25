"""
Shared fixtures for workflow integration tests.

These fixtures provide common mocks for AI agent behavior tests:
- External service responses (Jira, Azure DevOps)
- Preflight check results
- Workflow state helpers

Pattern for new workflow tests:
    def test_my_workflow(temp_state_dir, temp_output_dir, clear_state_before,
                         mock_preflight_pass, mock_workflow_state_clearing):
        state.set_value("jira.issue_key", "DFLY-1234")
        commands.initiate_my_workflow(_argv=["--issue-key", "DFLY-1234"])
        workflow = state.get_workflow_state()
        assert workflow["active"] == "my-workflow"
"""

from unittest.mock import patch

import pytest

from agentic_devtools import state


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def mock_jira_issue_response():
    """Mock Jira API response representing a typical Story issue.

    Simulates the AI agent receiving a Jira issue payload after calling
    the Jira REST API. Use this fixture to set up realistic test data
    without making real network calls.
    """
    return {
        "id": "123456",
        "key": "DFLY-1234",
        "self": "https://jira.example.com/rest/api/2/issue/123456",
        "fields": {
            "summary": "Add workflow tests mocking AI agent behavior",
            "description": "As a developer, I want workflow tests...",
            "issuetype": {"name": "Story", "subtask": False},
            "status": {"name": "In Progress"},
            "priority": {"name": "Medium"},
            "labels": ["ai-tooling", "testing"],
            "assignee": {"displayName": "Test User", "name": "testuser"},
            "reporter": {"displayName": "Reporter", "name": "reporter"},
            "project": {"key": "DFLY", "name": "Dragonfly"},
            "customfield_10008": None,  # Epic link
        },
    }


@pytest.fixture
def mock_jira_created_issue_response():
    """Mock Jira API response after creating a new issue.

    Simulates the payload returned by Jira when an AI agent successfully
    creates a new issue via the REST API.
    """
    return {
        "id": "789012",
        "key": "DFLY-5678",
        "self": "https://jira.example.com/rest/api/2/issue/789012",
    }


@pytest.fixture
def mock_preflight_pass():
    """Mock preflight check that always passes.

    Simulates the AI agent already being in the correct worktree/branch
    context. Use when testing workflow logic without needing to set up a
    real git worktree.
    """
    from agentic_devtools.cli.workflows.preflight import PreflightResult

    passing_result = PreflightResult(
        folder_valid=True,
        branch_valid=True,
        folder_name="DFLY-1234",
        branch_name="feature/DFLY-1234/implementation",
        issue_key="DFLY-1234",
    )
    with patch(
        "agentic_devtools.cli.workflows.preflight.check_worktree_and_branch",
        return_value=passing_result,
    ):
        yield passing_result


@pytest.fixture
def mock_workflow_state_clearing():
    """Mock clear_state_for_workflow_initiation to be a no-op.

    Workflow initiation commands clear all state at the start to ensure
    a fresh workflow. This fixture prevents that clearing so tests can
    set up state (e.g., jira.issue_key) before calling the command.
    """
    with patch("agentic_devtools.cli.workflows.commands.clear_state_for_workflow_initiation"):
        yield
