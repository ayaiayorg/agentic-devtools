"""
Shared fixtures for workflow integration tests.

These fixtures provide common mocks for AI agent behavior tests:
- External service responses (Jira, Azure DevOps)
- Preflight check results
- Workflow state helpers

Pattern for new workflow tests:
    def test_my_workflow(temp_state_dir, temp_output_dir, clear_state_before,
                         mock_preflight_pass):
        # Pass all required values via _argv so state-clearing in the command
        # does not wipe values you set before the call.
        commands.initiate_my_workflow(_argv=["--issue-key", "DFLY-1234",
                                             "--project-key", "DFLY"])
        workflow = state.get_workflow_state()
        assert workflow["active"] == "my-workflow"

Notes on mock_workflow_state_clearing:
    This fixture disables the clear_state() call that every initiation command
    makes at startup. Two valid use cases:

    1. Fixture isolation: clear_state_for_workflow_initiation() calls
       clear_temp_folder(), which deletes everything inside get_state_dir()
       including the temp/ subdirectory created by temp_output_dir. Use this
       fixture to prevent that deletion when the test also exercises prompt
       saving (save_to_temp=True). Always pass required values via _argv in
       combination with this fixture to keep the test representative.

    2. Legacy tests: When a test must pre-set state values before calling the
       command and _argv support is absent, this fixture prevents the pre-set
       state from being wiped.
"""

from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.prompts import loader


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def temp_output_dir(tmp_path):
    """Redirect all prompt/temp file writes away from scripts/temp/ during tests."""
    output_dir = tmp_path / "temp"
    output_dir.mkdir()
    with patch.object(loader, "get_temp_output_dir", return_value=output_dir), patch(
        "agentic_devtools.cli.workflows.manager.get_temp_output_dir", return_value=output_dir
    ):
        yield output_dir


@pytest.fixture
def clear_state_before(temp_state_dir):
    """Clear state file before each test."""
    state.clear_state()
    yield


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
def temp_prompts_dir(tmp_path):
    """Temporary prompts directory with get_prompts_dir patched at fixture time.

    Tests that call workflow initiation commands (which call load_and_render_prompt)
    need both this fixture and temp_output_dir so that:
    - get_prompts_dir() returns a writable tmp directory
    - get_temp_output_dir() returns a writable tmp directory

    Usage::

        def test_my_workflow(temp_state_dir, temp_prompts_dir, temp_output_dir,
                             clear_state_before, mock_preflight_pass):
            workflow_dir = temp_prompts_dir / "my-workflow"
            workflow_dir.mkdir()
            (workflow_dir / "default-initiate-prompt.md").write_text("...", encoding="utf-8")
            commands.initiate_my_workflow(_argv=["--issue-key", "DFLY-1234"])
    """
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    with patch.object(loader, "get_prompts_dir", return_value=prompts_dir):
        yield prompts_dir


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

    Prefer passing required values via _argv instead of using this fixture —
    that keeps tests more representative of real CLI usage. Only use this
    fixture for edge cases where _argv support is absent.
    """
    with patch(
        "agentic_devtools.cli.workflows.commands.clear_state_for_workflow_initiation",
        autospec=True,
        return_value=None,
    ):
        yield
