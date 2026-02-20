"""Tests for GenerateWorkflowBranchName."""

from agentic_devtools.cli.workflows.worktree_setup import (
    generate_workflow_branch_name,
)


class TestGenerateWorkflowBranchName:
    """Tests for generate_workflow_branch_name function."""

    def test_task_issue_type(self):
        """Test branch name generation for Task issue type."""
        result = generate_workflow_branch_name(
            issue_key="DFLY-1234",
            issue_type="Task",
            workflow_name="create-task",
        )
        assert result == "task/DFLY-1234/create-task"

    def test_epic_issue_type(self):
        """Test branch name generation for Epic issue type."""
        result = generate_workflow_branch_name(
            issue_key="DFLY-5678",
            issue_type="Epic",
            workflow_name="create-epic",
        )
        assert result == "epic/DFLY-5678/create-epic"

    def test_bug_issue_type(self):
        """Test branch name generation for Bug issue type."""
        result = generate_workflow_branch_name(
            issue_key="DFLY-9999",
            issue_type="Bug",
            workflow_name="create-bug",
        )
        assert result == "bug/DFLY-9999/create-bug"

    def test_story_issue_type(self):
        """Test branch name generation for Story issue type."""
        result = generate_workflow_branch_name(
            issue_key="DFLY-1111",
            issue_type="Story",
            workflow_name="create-story",
        )
        assert result == "story/DFLY-1111/create-story"

    def test_subtask_with_parent_key(self):
        """Test branch name generation for Sub-task with parent key."""
        result = generate_workflow_branch_name(
            issue_key="DFLY-2222",
            issue_type="Sub-task",
            workflow_name="create-subtask",
            parent_key="DFLY-1000",
        )
        assert result == "subtask/DFLY-1000/DFLY-2222/create-subtask"

    def test_subtask_without_parent_key(self):
        """Test branch name for Sub-task without parent key (edge case)."""
        result = generate_workflow_branch_name(
            issue_key="DFLY-3333",
            issue_type="Sub-task",
            workflow_name="create-subtask",
        )
        # Without parent key, should fall back to standard pattern
        assert result == "subtask/DFLY-3333/create-subtask"

    def test_case_insensitive_issue_type(self):
        """Test that issue type matching is case-insensitive."""
        result = generate_workflow_branch_name(
            issue_key="DFLY-4444",
            issue_type="TASK",
            workflow_name="create-task",
        )
        assert result == "task/DFLY-4444/create-task"

    def test_unknown_issue_type_uses_type_name(self):
        """Test that unknown issue types use their lowercased name as prefix."""
        result = generate_workflow_branch_name(
            issue_key="DFLY-5555",
            issue_type="Spike",
            workflow_name="some-workflow",
        )
        # Custom types use the type name lowercased
        assert result == "spike/DFLY-5555/create-spike"

    def test_update_workflow_uses_update_action(self):
        """Test branch name with update workflow uses update action."""
        result = generate_workflow_branch_name(
            issue_key="DFLY-6666",
            issue_type="Task",
            workflow_name="update-task",
        )
        assert result == "task/DFLY-6666/update-task"

    def test_sub_task_with_hyphen(self):
        """Test branch name for 'Sub-task' issue type (with hyphen)."""
        result = generate_workflow_branch_name(
            issue_key="DFLY-7777",
            issue_type="Sub-task",
            workflow_name="create-subtask",
            parent_key="DFLY-7000",
        )
        assert result == "subtask/DFLY-7000/DFLY-7777/create-subtask"

    def test_improvement_issue_type(self):
        """Test branch name generation for Improvement issue type."""
        result = generate_workflow_branch_name(
            issue_key="DFLY-8888",
            issue_type="Improvement",
            workflow_name="create-improvement",
        )
        assert result == "improvement/DFLY-8888/create-improvement"
