"""Tests for pull-request-review file-review prompt template rendering."""

from agentic_devtools.prompts import loader


class TestPrReviewFileReviewPromptRendering:
    """Tests for the default-file-review-prompt.md template in pull-request-review workflow."""

    def _render(self, **kwargs):
        """Render the actual PR review file-review template with the given variables."""
        template = loader.load_prompt_template("pull-request-review", "file-review")
        return loader.substitute_variables(template, kwargs)

    def _base_variables(self):
        return {
            "pull_request_id": "42",
            "completed_count": "3",
            "pending_count": "2",
            "total_count": "5",
            "current_file": "src/app.ts",
            "prompt_file_path": "/tmp/prompts/file-abc123.md",
        }

    def test_renders_without_error(self):
        """Template renders without exceptions with all base variables."""
        result = self._render(**self._base_variables())
        assert result is not None
        assert len(result) > 0

    def test_pull_request_id_rendered(self):
        """Pull request ID appears in rendered output."""
        result = self._render(**self._base_variables())
        assert "42" in result

    def test_queue_progress_rendered(self):
        """Completed and pending counts appear in rendered output."""
        result = self._render(**self._base_variables())
        assert "3" in result
        assert "2" in result

    def test_current_file_section_present_when_set(self):
        """Current file section renders when current_file is provided."""
        result = self._render(**self._base_variables())
        assert "## Current File" in result
        assert "src/app.ts" in result

    def test_current_file_section_absent_when_empty(self):
        """Current file section does NOT render when current_file is empty."""
        variables = self._base_variables()
        variables["current_file"] = ""
        result = self._render(**variables)
        assert "## Current File" not in result

    def test_strategy_a_commands_absent_when_current_file_empty(self):
        """Strategy A commands do NOT render --file-path with empty value."""
        variables = self._base_variables()
        variables["current_file"] = ""
        result = self._render(**variables)
        assert '--file-path ""' not in result
        assert "## Strategy A" not in result

    def test_current_file_section_absent_when_omitted(self):
        """Current file section does NOT render when current_file is omitted."""
        variables = self._base_variables()
        del variables["current_file"]
        result = self._render(**variables)
        assert "## Current File" not in result

    def test_strategy_a_commands_absent_when_current_file_omitted(self):
        """Strategy A commands do NOT render when current_file is omitted."""
        variables = self._base_variables()
        del variables["current_file"]
        result = self._render(**variables)
        assert '--file-path ""' not in result
        assert "## Strategy A" not in result

    def test_review_process_absent_when_current_file_empty(self):
        """Review Process section does NOT render when current_file is empty."""
        variables = self._base_variables()
        variables["current_file"] = ""
        result = self._render(**variables)
        assert "## Review Process" not in result

    def test_review_process_present_when_current_file_set(self):
        """Review Process section renders when current_file is provided."""
        result = self._render(**self._base_variables())
        assert "## Review Process" in result

    def test_strategy_a_commands_present(self):
        """Strategy A single-file commands appear when current_file is set."""
        result = self._render(**self._base_variables())
        assert "## Strategy A" in result
        assert "agdt-approve-file" in result
        assert "agdt-request-changes" in result
        assert "agdt-request-changes-with-suggestion" in result

    def test_strategy_b_commands_present(self):
        """Strategy B batch commands appear in rendered output."""
        result = self._render(**self._base_variables())
        assert "agdt-approve-files" in result
        assert "agdt-submit-reviews" in result

    def test_strategy_b_commands_present_when_current_file_empty(self):
        """Strategy B batch commands still appear when current_file is empty."""
        variables = self._base_variables()
        variables["current_file"] = ""
        result = self._render(**variables)
        assert "## Strategy B" in result
        assert "agdt-approve-files" in result
        assert "agdt-submit-reviews" in result

    def test_batch_defaults_schema_example_present(self):
        """Batch defaults schema keys appear in an example."""
        result = self._render(**self._base_variables())
        assert "default_outcome" in result
        assert "default_summary" in result

    def test_no_agdt_task_wait_reference(self):
        """agdt-task-wait does NOT appear anywhere in rendered output."""
        result = self._render(**self._base_variables())
        assert "agdt-task-wait" not in result

    def test_no_agdt_task_wait_when_current_file_empty(self):
        """agdt-task-wait does NOT appear when current_file is empty."""
        variables = self._base_variables()
        variables["current_file"] = ""
        result = self._render(**variables)
        assert "agdt-task-wait" not in result

    def test_no_wait_poll_instructions(self):
        """No wait/poll instructions for API completion remain."""
        result = self._render(**self._base_variables())
        assert "Wait for the review to post" not in result
        assert "wait for the review to post" not in result

    def test_submission_strategies_section_present(self):
        """A section describing when to use Strategy A vs B exists."""
        result = self._render(**self._base_variables())
        assert "Submission Strategies" in result
        assert "Strategy A" in result
        assert "Strategy B" in result

    def test_workflow_status_footer_present(self):
        """The workflow status line at the bottom still renders."""
        result = self._render(**self._base_variables())
        assert "Workflow Status" in result
        assert "3" in result
        assert "5" in result

    def test_batch_request_changes_command_present(self):
        """agdt-request-changes-batch command appears in rendered output."""
        result = self._render(**self._base_variables())
        assert "agdt-request-changes-batch" in result

    def test_async_processing_note_present(self):
        """After Submitting section mentions async processing."""
        result = self._render(**self._base_variables())
        assert "asynchronously" in result

    def test_prompt_file_path_rendered(self):
        """Prompt file path appears in rendered output."""
        result = self._render(**self._base_variables())
        assert "/tmp/prompts/file-abc123.md" in result
