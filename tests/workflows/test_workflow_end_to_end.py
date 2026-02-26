"""
End-to-end integration tests for complete workflow lifecycles.

These tests exercise multiple workflow steps in sequence to verify that:
- State transitions happen correctly across multiple steps
- Events trigger the correct advancement logic
- Deferred transitions (via pending_transition) resolve correctly
- Complete workflows reach "completed" status

Unlike unit tests that isolate individual functions, these tests
exercise complete workflows with real state management and template rendering.

Adding Tests for a New Workflow
--------------------------------
1. Place the test class in this file (or a new file under tests/workflows/).
2. Decide whether the workflow is "registered" (has event-driven transitions in
   WORKFLOW_REGISTRY) or "simple" (single-step, just calls initiate_workflow).
3. For registered workflows — test each event-driven transition and any deferred
   transitions via get_next_workflow_prompt (see TestWorkOnJiraIssueWorkflowEndToEnd).
4. For simple workflows — test initiation sets the correct state and that
   notify_workflow_event returns triggered=False (see TestCreateJiraIssueWorkflowEndToEnd).
5. Use the shared fixtures from tests/workflows/conftest.py:
   - temp_state_dir: isolated state dir (tmp_path/state/); clear_state() only
     wipes this subdir and never touches temp_output_dir or temp_prompts_dir
   - temp_output_dir: redirects all prompt/temp file writes away from scripts/temp/
   - clear_state_before: wipes state before each test (depends on temp_state_dir)
   - mock_jira_issue_response: realistic Jira Story API payload
   - mock_preflight_pass: preflight check always passes (correct worktree assumed)
   - mock_workflow_state_clearing: no-op for clear_state — prefer passing values
     via _argv instead (see "Notes on mock_workflow_state_clearing" in conftest.py)
6. For tests that call advancement helpers that render prompts for the
   pull-request-review workflow, patch get_queue_status to avoid reading
   the real queue.json from scripts/temp/:
       with patch("agentic_devtools.cli.azure_devops.file_review_commands.get_queue_status",
                  return_value=<queue_dict>):
           result = advancement.try_advance_workflow_after_pr_review()
"""

from unittest.mock import MagicMock, patch

from agentic_devtools import state
from agentic_devtools.cli.workflows import advancement, commands
from agentic_devtools.cli.workflows.manager import (
    PromptStatus,
    WorkflowEvent,
    get_next_workflow_prompt,
    notify_workflow_event,
)


class TestWorkOnJiraIssueWorkflowEndToEnd:
    """End-to-end integration tests for the work-on-jira-issue workflow."""

    def test_event_driven_chain_planning_to_implementation_review(
        self, temp_state_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test event-driven advancement from planning through to implementation-review.

        Exercises three consecutive immediate transitions:
        - planning -> checklist-creation (JIRA_COMMENT_ADDED)
        - checklist-creation -> implementation (CHECKLIST_CREATED)
        - implementation -> implementation-review (CHECKLIST_COMPLETE)
        """
        # Start at planning step (simulating post-initiation state)
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="planning",
            context={"jira_issue_key": "DFLY-1234"},
        )

        # Step 1: planning -> checklist-creation (Jira planning comment added)
        result1 = advancement.try_advance_workflow_after_jira_comment()
        assert result1 is True
        workflow = state.get_workflow_state()
        assert workflow["step"] == "checklist-creation"

        # Step 2: checklist-creation -> implementation (checklist created)
        result2 = notify_workflow_event(WorkflowEvent.CHECKLIST_CREATED)
        assert result2.triggered is True
        assert result2.immediate_advance is True
        assert result2.new_step == "implementation"
        workflow = state.get_workflow_state()
        assert workflow["step"] == "implementation"

        # Step 3: implementation -> implementation-review (all checklist items done)
        result3 = notify_workflow_event(WorkflowEvent.CHECKLIST_COMPLETE)
        assert result3.triggered is True
        assert result3.immediate_advance is True
        assert result3.new_step == "implementation-review"
        workflow = state.get_workflow_state()
        assert workflow["step"] == "implementation-review"

        # Verify workflow is still in-progress (not yet completed)
        assert workflow["status"] == "in-progress"

        # Verify all three steps were captured in the output
        captured = capsys.readouterr()
        assert "checklist-creation" in captured.out
        assert "implementation" in captured.out
        assert "implementation-review" in captured.out

    def test_deferred_transition_commit_to_pull_request(self, temp_state_dir, temp_output_dir, clear_state_before):
        """Test deferred transition: commit step -> pull-request via get_next_workflow_prompt.

        The GIT_COMMIT_CREATED event sets a pending_transition (because the transition
        requires background task completion). get_next_workflow_prompt then resolves it.
        """
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="commit",
            context={"jira_issue_key": "DFLY-1234", "branch_name": "feature/DFLY-1234/test"},
        )

        # Fire GIT_COMMIT_CREATED - sets pending_transition, does NOT immediately advance
        result = advancement.try_advance_workflow_after_commit(branch_name="feature/DFLY-1234/test")
        assert result is True
        workflow = state.get_workflow_state()
        # Step is still "commit" — the transition is deferred
        assert workflow["step"] == "commit"
        assert workflow["context"]["pending_transition"]["to_step"] == "pull-request"
        assert "agdt-git-commit" in workflow["context"]["pending_transition"]["required_tasks"]

        # Now resolve the pending transition via get_next_workflow_prompt
        with patch(
            "agentic_devtools.cli.workflows.manager.get_active_tasks",
            return_value=[],
        ), patch(
            "agentic_devtools.cli.workflows.manager._render_step_prompt",
            return_value="# Pull Request Step\n\nCreate your pull request.",
        ):
            prompt_result = get_next_workflow_prompt()

        assert prompt_result.status == PromptStatus.SUCCESS
        assert prompt_result.step == "pull-request"
        assert "Pull Request" in prompt_result.content

        # Verify workflow state was updated to pull-request
        workflow = state.get_workflow_state()
        assert workflow["step"] == "pull-request"
        assert workflow["status"] == "in-progress"
        # pending_transition should be cleared
        assert workflow["context"].get("pending_transition") is None

    def test_deferred_transition_pull_request_to_completion(self, temp_state_dir, temp_output_dir, clear_state_before):
        """Test deferred transition: pull-request step -> completion via get_next_workflow_prompt.

        The PR_CREATED event sets a pending_transition. get_next_workflow_prompt resolves it
        and sets the workflow status to 'completed'.
        """
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="pull-request",
            context={"jira_issue_key": "DFLY-1234", "branch_name": "feature/DFLY-1234/test"},
        )

        # Fire PR_CREATED event - sets pending_transition
        result = advancement.try_advance_workflow_after_pr_creation(
            pull_request_id=42,
            pull_request_url="https://example.com/pr/42",
        )
        assert result is True
        workflow = state.get_workflow_state()
        # Step is still "pull-request" — transition is deferred
        assert workflow["step"] == "pull-request"
        pending = workflow["context"]["pending_transition"]
        assert pending["to_step"] == "completion"
        # Verify PR data was captured in context
        assert workflow["context"]["pull_request_id"] == 42
        assert workflow["context"]["pull_request_url"] == "https://example.com/pr/42"

        # Resolve the pending transition
        with patch(
            "agentic_devtools.cli.workflows.manager.get_active_tasks",
            return_value=[],
        ), patch(
            "agentic_devtools.cli.workflows.manager._render_step_prompt",
            return_value="# Workflow Complete\n\nCongratulations!",
        ):
            prompt_result = get_next_workflow_prompt()

        assert prompt_result.status == PromptStatus.SUCCESS
        assert prompt_result.step == "completion"

        # Verify workflow reached completed status
        workflow = state.get_workflow_state()
        assert workflow["step"] == "completion"
        assert workflow["status"] == "completed"

    def test_complete_workflow_planning_to_completion(self, temp_state_dir, temp_output_dir, clear_state_before):
        """Test the full work-on-jira-issue workflow lifecycle from planning to completion.

        This exercises all steps in order:
        planning -> checklist-creation -> implementation -> implementation-review
        -> verification -> commit -> [pending] -> pull-request -> [pending] -> completion
        """
        # Start at planning (simulating successful initiation with preflight pass)
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="planning",
            context={"jira_issue_key": "DFLY-1234", "issue_summary": "Add new feature"},
        )

        # planning -> checklist-creation
        advancement.try_advance_workflow_after_jira_comment()
        assert state.get_workflow_state()["step"] == "checklist-creation"

        # checklist-creation -> implementation
        notify_workflow_event(WorkflowEvent.CHECKLIST_CREATED)
        assert state.get_workflow_state()["step"] == "implementation"

        # implementation -> implementation-review
        notify_workflow_event(WorkflowEvent.CHECKLIST_COMPLETE)
        assert state.get_workflow_state()["step"] == "implementation-review"

        # implementation-review -> verification (manual advance via command)
        commands.advance_work_on_jira_issue_workflow()
        assert state.get_workflow_state()["step"] == "verification"

        # verification -> commit (manual advance via command)
        commands.advance_work_on_jira_issue_workflow()
        assert state.get_workflow_state()["step"] == "commit"

        # commit -> [pending] pull-request (GIT_COMMIT_CREATED, deferred)
        advancement.try_advance_workflow_after_commit(branch_name="feature/DFLY-1234/test")
        workflow = state.get_workflow_state()
        assert workflow["step"] == "commit"  # Still commit, transition is pending
        assert workflow["context"]["pending_transition"]["to_step"] == "pull-request"

        # Resolve pending commit transition -> pull-request
        with patch(
            "agentic_devtools.cli.workflows.manager.get_active_tasks",
            return_value=[],
        ), patch(
            "agentic_devtools.cli.workflows.manager._render_step_prompt",
            return_value="# Pull Request Step",
        ):
            result = get_next_workflow_prompt()
        assert result.step == "pull-request"
        assert state.get_workflow_state()["step"] == "pull-request"

        # pull-request -> [pending] completion (PR_CREATED, deferred)
        advancement.try_advance_workflow_after_pr_creation(
            pull_request_id=99,
            pull_request_url="https://dev.azure.com/org/project/_git/repo/pullrequest/99",
        )
        workflow = state.get_workflow_state()
        assert workflow["step"] == "pull-request"  # Still pull-request, pending
        assert workflow["context"]["pending_transition"]["to_step"] == "completion"

        # Resolve pending PR transition -> completion
        with patch(
            "agentic_devtools.cli.workflows.manager.get_active_tasks",
            return_value=[],
        ), patch(
            "agentic_devtools.cli.workflows.manager._render_step_prompt",
            return_value="# Workflow Complete",
        ):
            result = get_next_workflow_prompt()
        assert result.step == "completion"

        # Verify final workflow state
        workflow = state.get_workflow_state()
        assert workflow["step"] == "completion"
        assert workflow["status"] == "completed"
        # PR data preserved in context
        assert workflow["context"]["pull_request_id"] == 99

    def test_get_next_workflow_prompt_returns_waiting_when_background_tasks_active(
        self, temp_state_dir, temp_output_dir, clear_state_before
    ):
        """Test that get_next_workflow_prompt returns WAITING when background tasks are running.

        Even if there is a pending transition, the workflow waits for background tasks
        to complete before advancing.
        """
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="commit",
            context={
                "jira_issue_key": "DFLY-1234",
                "pending_transition": {
                    "to_step": "pull-request",
                    "required_tasks": ["agdt-git-commit"],
                },
            },
        )

        # Simulate a running background task
        mock_task = MagicMock()
        mock_task.id = "task-git-abc-123"
        mock_task.command = "agdt-git-commit"
        mock_task.status = MagicMock()
        mock_task.status.value = "running"

        with patch(
            "agentic_devtools.cli.workflows.manager.get_active_tasks",
            return_value=[mock_task],
        ):
            result = get_next_workflow_prompt()

        assert result.status == PromptStatus.WAITING
        assert result.step == "commit"
        assert result.pending_task_ids == ["task-git-abc-123"]
        # Step should not have advanced
        assert state.get_workflow_state()["step"] == "commit"

    def test_context_preserved_across_event_driven_transitions(
        self, temp_state_dir, temp_output_dir, clear_state_before
    ):
        """Test that workflow context is preserved and accumulated across transitions.

        Each event can add context updates, and the context should accumulate
        across multiple transitions rather than being overwritten.
        """
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="planning",
            context={"jira_issue_key": "DFLY-1234", "issue_summary": "Test feature"},
        )

        # Advance with context update
        notify_workflow_event(
            WorkflowEvent.JIRA_COMMENT_ADDED,
            context_updates={"plan_comment_id": "comment-1"},
        )
        workflow = state.get_workflow_state()
        # Original context preserved
        assert workflow["context"]["jira_issue_key"] == "DFLY-1234"
        assert workflow["context"]["issue_summary"] == "Test feature"
        # New context added
        assert workflow["context"]["plan_comment_id"] == "comment-1"
        assert workflow["step"] == "checklist-creation"

        # Another advance with more context
        notify_workflow_event(
            WorkflowEvent.CHECKLIST_CREATED,
            context_updates={"checklist_item_count": 5},
        )
        workflow = state.get_workflow_state()
        # All previous context still there
        assert workflow["context"]["jira_issue_key"] == "DFLY-1234"
        assert workflow["context"]["plan_comment_id"] == "comment-1"
        # Plus new context
        assert workflow["context"]["checklist_item_count"] == 5
        assert workflow["step"] == "implementation"


class TestPullRequestReviewWorkflowEndToEnd:
    """End-to-end integration tests for the pull-request-review workflow."""

    def test_pr_reviewed_event_loops_in_file_review(self, temp_state_dir, temp_output_dir, clear_state_before, capsys):
        """Test that PR_REVIEWED event keeps the workflow in the file-review step.

        When PR_REVIEWED fires while reviewing files, the workflow stays in
        file-review (transitions from file-review -> file-review) until all files
        are reviewed.
        """
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="file-review",
            context={"pull_request_id": "123"},
        )

        # Fire PR_REVIEWED - should stay in file-review (more files to review)
        result = advancement.try_advance_workflow_after_pr_review()
        assert result is True

        workflow = state.get_workflow_state()
        assert workflow["step"] == "file-review"  # Stays in file-review

        # Fire it again (reviewing another file)
        result2 = advancement.try_advance_workflow_after_pr_review()
        assert result2 is True
        workflow = state.get_workflow_state()
        assert workflow["step"] == "file-review"

        # Verify WORKFLOW ADVANCED was printed (file-review -> file-review is immediate)
        captured = capsys.readouterr()
        assert "WORKFLOW ADVANCED" in captured.out

    def test_complete_pull_request_review_workflow(self, temp_state_dir, temp_output_dir, clear_state_before):
        """Test the full pull-request-review workflow lifecycle from initiate to completion.

        Exercises all steps in order:
        initiate -> file-review -> (file-review loop) -> summary -> decision -> completion
        """
        # Set state for the PR
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="initiate",
            context={"pull_request_id": "123", "jira_issue_key": "DFLY-5678"},
        )
        state.set_value("pull_request_id", "123")

        pending_queue = {
            "all_complete": False,
            "completed_count": 0,
            "pending_count": 3,
            "total_count": 3,
            "current_file": "src/module.py",
            "prompt_file_path": "/tmp/prompt.md",
        }

        # initiate -> file-review (manual advance)
        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands.get_queue_status",
            return_value=pending_queue,
        ):
            commands.advance_pull_request_review_workflow()
        assert state.get_workflow_state()["step"] == "file-review"

        # file-review -> file-review (PR_REVIEWED events while files still pending)
        notify_workflow_event(WorkflowEvent.PR_REVIEWED)
        assert state.get_workflow_state()["step"] == "file-review"
        notify_workflow_event(WorkflowEvent.PR_REVIEWED)
        assert state.get_workflow_state()["step"] == "file-review"

        complete_queue = {
            "all_complete": True,
            "completed_count": 3,
            "pending_count": 0,
            "total_count": 3,
            "current_file": None,
            "prompt_file_path": None,
        }

        # file-review -> summary (all files reviewed, manual advance)
        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands.get_queue_status",
            return_value=complete_queue,
        ):
            commands.advance_pull_request_review_workflow()
        assert state.get_workflow_state()["step"] == "summary"

        # summary -> decision (manual advance)
        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands.get_queue_status",
            return_value=complete_queue,
        ):
            commands.advance_pull_request_review_workflow()
        assert state.get_workflow_state()["step"] == "decision"

        # decision -> completion (manual advance)
        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands.get_queue_status",
            return_value=complete_queue,
        ):
            commands.advance_pull_request_review_workflow()
        assert state.get_workflow_state()["step"] == "completion"

        # Verify final workflow state
        workflow = state.get_workflow_state()
        assert workflow["status"] == "completed"

    def test_pr_review_waiting_when_tasks_pending_during_transition(
        self, temp_state_dir, temp_output_dir, clear_state_before
    ):
        """Test that the review workflow waits when background tasks are running.

        When there's a pending transition AND active background tasks,
        get_next_workflow_prompt returns WAITING rather than advancing.
        """
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="summary",
            context={
                "pull_request_id": "123",
                "pending_transition": {
                    "to_step": "decision",
                    "required_tasks": ["agdt-generate-pr-summary"],
                },
            },
        )

        mock_task = MagicMock()
        mock_task.id = "task-summary-xyz-456"
        mock_task.command = "agdt-generate-pr-summary"
        mock_task.status = MagicMock()
        mock_task.status.value = "running"

        with patch(
            "agentic_devtools.cli.workflows.manager.get_active_tasks",
            return_value=[mock_task],
        ):
            result = get_next_workflow_prompt()

        assert result.status == PromptStatus.WAITING
        assert result.step == "summary"
        assert "agdt-generate-pr-summary" in result.content
        # Workflow should not have advanced
        assert state.get_workflow_state()["step"] == "summary"

    def test_no_effect_when_pr_reviewed_in_wrong_step(self, temp_state_dir, temp_output_dir, clear_state_before):
        """Test that PR_REVIEWED event has no effect when not in the file-review step.

        Events should only advance workflows when the current step matches
        the transition's from_step.
        """
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="decision",
            context={"pull_request_id": "123"},
        )

        result = notify_workflow_event(WorkflowEvent.PR_REVIEWED)

        # Should not trigger any transition from the decision step
        assert result.triggered is False
        assert state.get_workflow_state()["step"] == "decision"


class TestCreateJiraIssueWorkflowEndToEnd:
    """End-to-end integration tests for the create-jira-issue workflow.

    The create-jira-issue workflow is a "simple" workflow: it is NOT registered in
    WORKFLOW_REGISTRY, so notify_workflow_event() always returns triggered=False and
    no automatic step transitions occur. The AI agent calls initiate_workflow once,
    reads the rendered prompt, then uses Jira API commands to populate the issue.
    """

    def test_initiation_sets_workflow_state(
        self,
        temp_state_dir,
        temp_output_dir,
        clear_state_before,
        mock_preflight_pass,
    ):
        """Test that initiating the workflow sets the expected state.

        Simulates an AI agent calling agdt-initiate-create-jira-issue-workflow
        in continuation mode. Values are passed via _argv (--project-key,
        --issue-key) so the command parses and validates its own inputs —
        representative of real CLI usage. Because temp_state_dir patches
        get_state_dir() to a dedicated subdir, clear_state_for_workflow_initiation()
        does not wipe temp_output_dir, so no mock_workflow_state_clearing needed.
        """
        commands.initiate_create_jira_issue_workflow(_argv=["--issue-key", "DFLY-1234", "--project-key", "DFLY"])

        workflow = state.get_workflow_state()
        assert workflow is not None
        assert workflow["active"] == "create-jira-issue"
        assert workflow["step"] == "initiate"
        assert workflow["status"] == "initiated"

    def test_no_auto_transitions_for_simple_workflow(self, temp_state_dir, temp_output_dir, clear_state_before):
        """Test that JIRA_ISSUE_CREATED event does not trigger any transition.

        Simple workflows (not in WORKFLOW_REGISTRY) do not participate in
        event-driven advancement. Verifies the boundary between simple and
        registered workflows so future additions know which pattern to use.
        """
        state.set_workflow_state(
            name="create-jira-issue",
            status="initiated",
            step="initiate",
            context={"jira_project_key": "DFLY"},
        )

        result = notify_workflow_event(WorkflowEvent.JIRA_ISSUE_CREATED)

        assert result.triggered is False
        # State must not have changed
        workflow = state.get_workflow_state()
        assert workflow["step"] == "initiate"
        assert workflow["status"] == "initiated"

    def test_no_auto_transitions_for_jira_issue_updated_event(
        self, temp_state_dir, temp_output_dir, clear_state_before
    ):
        """Test that JIRA_ISSUE_UPDATED event also returns triggered=False.

        Neither creation nor update events drive the simple workflow forward.
        """
        state.set_workflow_state(
            name="create-jira-issue",
            status="initiated",
            step="initiate",
            context={"jira_project_key": "DFLY"},
        )

        result = notify_workflow_event(WorkflowEvent.JIRA_ISSUE_UPDATED)

        assert result.triggered is False
        assert state.get_workflow_state()["step"] == "initiate"

    def test_jira_issue_retrieved_event_has_no_side_effects_on_simple_workflow(
        self,
        temp_state_dir,
        temp_output_dir,
        clear_state_before,
        mock_preflight_pass,
        mock_jira_issue_response,
    ):
        """Test that try_advance_workflow_after_jira_issue_retrieved has no side effects.

        For simple (non-registry) workflows, notify_workflow_event() returns early
        with triggered=False and never applies context_updates.  This test verifies
        that after an AI agent calls the Jira retrieval advancement helper the
        workflow step and context are completely unchanged.

        Values are provided via _argv so the command validates its own required inputs.
        Because temp_state_dir patches get_state_dir() to a dedicated subdir,
        clear_state_for_workflow_initiation() does not wipe temp_output_dir.
        """
        from agentic_devtools.cli.workflows.advancement import try_advance_workflow_after_jira_issue_retrieved

        commands.initiate_create_jira_issue_workflow(_argv=["--issue-key", "DFLY-1234", "--project-key", "DFLY"])

        # Capture state immediately after initiation
        initial_workflow = state.get_workflow_state()
        initial_step = initial_workflow["step"]

        # Simulate the AI agent passing Jira issue data through the helper.
        # For a simple (non-registry) workflow this must NOT trigger and must NOT
        # apply context_updates — no side effects on workflow state.
        triggered = try_advance_workflow_after_jira_issue_retrieved(issue_data=mock_jira_issue_response)
        assert triggered is False

        # Workflow state is completely unchanged: same step, no injected fields
        workflow = state.get_workflow_state()
        assert workflow["step"] == initial_step
        assert "issue_summary" not in workflow["context"]
        assert "issue_type" not in workflow["context"]


class TestMockAgentBehavior:
    """Tests that simulate end-to-end AI agent interactions across all major workflows.

    Each test mimics the sequence of CLI commands an AI agent would issue when
    working through a workflow. External services (Jira, ADO, Git) are replaced
    with lightweight mocks so no real network calls are made.

    These tests are the reference implementation for the acceptance criterion
    "Tests verify CLI commands execute workflows properly".
    """

    def test_agent_works_through_jira_issue_planning_step(
        self, temp_state_dir, temp_output_dir, clear_state_before, mock_jira_issue_response, capsys
    ):
        """Simulate an AI agent advancing from planning to checklist-creation.

        Mimics the agent behavior:
        1. Workflow is already at 'planning' (set up externally by initiation).
        2. Agent posts a planning comment to Jira.
        3. Advancement helper fires JIRA_COMMENT_ADDED → immediate transition.
        4. Agent reads the new step via get_workflow_state().
        """
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="planning",
            context={
                "jira_issue_key": "DFLY-1234",
                "issue_summary": mock_jira_issue_response["fields"]["summary"],
            },
        )

        # Step 1: agent posts Jira planning comment (advancement helper fires the event)
        triggered = advancement.try_advance_workflow_after_jira_comment()
        assert triggered is True

        # Step 2: agent reads new workflow step
        workflow = state.get_workflow_state()
        assert workflow["step"] == "checklist-creation"
        assert workflow["context"]["jira_issue_key"] == "DFLY-1234"

        # The console output includes the WORKFLOW ADVANCED banner
        captured = capsys.readouterr()
        assert "WORKFLOW ADVANCED" in captured.out
        assert "checklist-creation" in captured.out

    def test_agent_resolves_pending_transition_by_polling(self, temp_state_dir, temp_output_dir, clear_state_before):
        """Simulate an AI agent polling get_next_workflow_prompt after a deferred transition.

        Mimics the agent behavior:
        1. Agent saves work (git commit/push) — sets pending_transition.
        2. Agent polls get_next_workflow_prompt until background tasks finish.
        3. First poll: background task still running → WAITING.
        4. Second poll: task complete → SUCCESS, workflow advances to pull-request.
        """
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="commit",
            context={"jira_issue_key": "DFLY-1234", "branch_name": "feature/DFLY-1234/test"},
        )

        # Agent fires commit event (creates pending_transition)
        advancement.try_advance_workflow_after_commit(branch_name="feature/DFLY-1234/test")
        assert state.get_workflow_state()["step"] == "commit"  # Still at commit

        # First poll: background task is running → agent gets WAITING response
        mock_running_task = MagicMock()
        mock_running_task.id = "task-git-abc"
        mock_running_task.command = "agdt-git-commit"
        mock_running_task.status = MagicMock()
        mock_running_task.status.value = "running"

        with patch("agentic_devtools.cli.workflows.manager.get_active_tasks", return_value=[mock_running_task]):
            first_poll = get_next_workflow_prompt()

        assert first_poll.status == PromptStatus.WAITING
        assert first_poll.step == "commit"
        assert "task-git-abc" in first_poll.pending_task_ids

        # Second poll: task finished → agent gets SUCCESS response with pull-request prompt
        with patch(
            "agentic_devtools.cli.workflows.manager.get_active_tasks",
            return_value=[],
        ), patch(
            "agentic_devtools.cli.workflows.manager._render_step_prompt",
            return_value="# Pull Request Step\n\nCreate your pull request.",
        ):
            second_poll = get_next_workflow_prompt()

        assert second_poll.status == PromptStatus.SUCCESS
        assert second_poll.step == "pull-request"
        assert state.get_workflow_state()["step"] == "pull-request"

    def test_agent_performs_pr_review_file_loop(self, temp_state_dir, temp_output_dir, clear_state_before):
        """Simulate an AI agent reviewing multiple files in the PR review workflow.

        Mimics the agent behavior:
        1. Workflow is already at 'file-review'.
        2. Agent reviews file 1 → PR_REVIEWED event → stays in file-review.
        3. Agent reviews file 2 → PR_REVIEWED event → stays in file-review.
        4. All files done → agent manually advances to summary.
        """
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="file-review",
            context={"pull_request_id": "456"},
        )
        state.set_value("pull_request_id", "456")

        in_progress_queue = {
            "all_complete": False,
            "completed_count": 0,
            "pending_count": 2,
            "total_count": 2,
            "current_file": "file1",
            "prompt_file_path": "/dev/null",
        }

        # Agent reviews file 1
        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands.get_queue_status",
            return_value=in_progress_queue,
        ):
            result1 = advancement.try_advance_workflow_after_pr_review()
        assert result1 is True
        assert state.get_workflow_state()["step"] == "file-review"

        # Agent reviews file 2
        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands.get_queue_status",
            return_value=in_progress_queue,
        ):
            result2 = advancement.try_advance_workflow_after_pr_review()
        assert result2 is True
        assert state.get_workflow_state()["step"] == "file-review"

        # All files reviewed — agent advances to summary
        complete_queue = {
            "all_complete": True,
            "completed_count": 2,
            "pending_count": 0,
            "total_count": 2,
            "current_file": None,
            "prompt_file_path": None,
        }
        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands.get_queue_status",
            return_value=complete_queue,
        ):
            commands.advance_pull_request_review_workflow()

        assert state.get_workflow_state()["step"] == "summary"

    def test_agent_receives_no_workflow_response_when_inactive(
        self, temp_state_dir, temp_output_dir, clear_state_before
    ):
        """Test that get_next_workflow_prompt returns NO_WORKFLOW when no workflow is active.

        Simulates an AI agent calling the command without having initiated a workflow first.
        The agent should receive a clear error message with instructions.
        """
        # No workflow is active (state is clean)
        result = get_next_workflow_prompt()

        assert result.status == PromptStatus.NO_WORKFLOW
        assert "agdt-initiate" in result.content
