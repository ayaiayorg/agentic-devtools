"""Tests for pass_e2.validator — _parse_tasks_from_content."""

from agentic_devtools.cli.speckit.pass_e2.validator import _parse_tasks_from_content


class TestParseTasksFromContent:
    """Verify task parsing from tasks.md content."""

    def test_non_continuation_line_flushes_current_task(self) -> None:
        """A non-indented, non-task line after a task flushes the current task.

        When the parser encounters a line that is neither a new task header
        nor an indented continuation, it terminates the active task.
        """
        content = "- [ ] T001 First task description\nSome non-indented non-task line\n- [ ] T002 Second task\n"
        tasks = _parse_tasks_from_content(content)
        assert len(tasks) == 2
        assert tasks[0] == ("T001", "First task description")
        assert tasks[1] == ("T002", "Second task")

    def test_blank_line_does_not_flush_current_task(self) -> None:
        """A blank line is skipped; the next task header triggers the flush."""
        content = "- [ ] T001 Task one\n\n- [ ] T002 Task two\n"
        tasks = _parse_tasks_from_content(content)
        assert len(tasks) == 2
        assert tasks[0] == ("T001", "Task one")
        assert tasks[1] == ("T002", "Task two")

    def test_non_task_text_before_first_task(self) -> None:
        """Non-task lines before first task don't crash (current_task_id is None)."""
        content = "# Heading\nSome preamble text\n- [ ] T001 The only task\n"
        tasks = _parse_tasks_from_content(content)
        assert len(tasks) == 1
        assert tasks[0] == ("T001", "The only task")

    def test_blank_line_then_indented_continuation_retained(self) -> None:
        """Blank line between task header and indented continuation is preserved.

        Ensures continuation lines after a blank line within an active task
        are joined into the task description rather than being dropped.
        """
        content = (
            "- [ ] T051 First part of description\n"
            "\n"
            "    Indented continuation with FR-001 ref\n"
            "    Another continuation line\n"
            "- [ ] T052 Next task\n"
        )
        tasks = _parse_tasks_from_content(content)
        assert len(tasks) == 2
        assert tasks[0] == (
            "T051",
            "First part of description Indented continuation with FR-001 ref Another continuation line",
        )
        assert tasks[1] == ("T052", "Next task")
