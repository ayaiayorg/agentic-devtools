"""Tests for run_langchain_workflow runner."""

from unittest.mock import MagicMock, patch

import pytest


class TestRunLangchainWorkflowFreshInvocation:
    """Tests for fresh (non-resume) LangGraph workflow invocation."""

    def test_fresh_invocation_calls_graph_invoke(self, tmp_path, capsys):
        """Fresh invocation builds graph and invokes with initial state."""
        mock_compiled = MagicMock()
        mock_compiled.invoke.return_value = {
            "step": "completion",
            "status": "completed",
            "events": [],
        }

        with patch("agentic_devtools.orchestration.checkpointing.get_checkpointer") as mock_checkpointer:
            mock_checkpointer.return_value = MagicMock()
            with patch("agentic_devtools.orchestration.graph_builder.build_work_on_issue_graph") as mock_build:
                mock_build.return_value = mock_compiled
                from agentic_devtools.orchestration.runner import run_langchain_workflow

                run_langchain_workflow("TEST-123", interactive=True, model="gpt-4")

        # Verify graph was invoked with correct initial state
        call_args = mock_compiled.invoke.call_args
        initial_state = call_args[0][0]
        assert initial_state["issue_key"] == "TEST-123"
        assert initial_state["agent_context"]["interactive"] is True
        assert initial_state["agent_context"]["model"] == "gpt-4"

        captured = capsys.readouterr()
        assert "[langchain] Starting workflow for TEST-123" in captured.out
        assert "[langchain] Workflow completed" in captured.out

    def test_fresh_invocation_handles_graph_interrupt(self, capsys):
        """Fresh invocation handles GraphInterrupt for human-in-the-loop pause."""
        mock_compiled = MagicMock()

        # Simulate GraphInterrupt
        class GraphInterrupt(Exception):
            pass

        mock_compiled.invoke.side_effect = GraphInterrupt("Waiting for approval")

        with patch("agentic_devtools.orchestration.checkpointing.get_checkpointer") as mock_checkpointer:
            mock_checkpointer.return_value = MagicMock()
            with patch("agentic_devtools.orchestration.graph_builder.build_work_on_issue_graph") as mock_build:
                mock_build.return_value = mock_compiled
                from agentic_devtools.orchestration.runner import run_langchain_workflow

                # Should not raise, should print resume instructions
                run_langchain_workflow("TEST-456")

        captured = capsys.readouterr()
        assert "paused" in captured.err
        assert "--resume" in captured.err

    def test_fresh_invocation_non_interrupt_error_exits(self, capsys):
        """Fresh invocation with non-GraphInterrupt error exits with code 1."""
        mock_compiled = MagicMock()
        mock_compiled.invoke.side_effect = RuntimeError("Something went wrong")

        with patch("agentic_devtools.orchestration.checkpointing.get_checkpointer") as mock_checkpointer:
            mock_checkpointer.return_value = MagicMock()
            with patch("agentic_devtools.orchestration.graph_builder.build_work_on_issue_graph") as mock_build:
                mock_build.return_value = mock_compiled
                from agentic_devtools.orchestration.runner import run_langchain_workflow

                with pytest.raises(SystemExit) as exc_info:
                    run_langchain_workflow("TEST-456")

                assert exc_info.value.code == 1
                captured = capsys.readouterr()
                assert "Workflow execution failed" in captured.err


class TestRunLangchainWorkflowResume:
    """Tests for resume path in LangGraph workflow."""

    def test_resume_with_no_checkpoint_exits(self, capsys):
        """Resume with no existing checkpoint exits with error."""
        mock_checkpointer = MagicMock()
        mock_checkpointer.get.return_value = None

        mock_compiled = MagicMock()

        with patch("agentic_devtools.orchestration.checkpointing.get_checkpointer") as mock_get_cp:
            mock_get_cp.return_value = mock_checkpointer
            with patch("agentic_devtools.orchestration.graph_builder.build_work_on_issue_graph") as mock_build:
                mock_build.return_value = mock_compiled
                from agentic_devtools.orchestration.runner import run_langchain_workflow

                with pytest.raises(SystemExit) as exc_info:
                    run_langchain_workflow("TEST-789", resume=True)

                assert exc_info.value.code == 1
                captured = capsys.readouterr()
                assert "No existing checkpoint" in captured.err

    def test_resume_with_existing_checkpoint_invokes_command(self, capsys):
        """Resume with existing checkpoint invokes graph with Command(resume=True)."""
        mock_checkpointer = MagicMock()
        mock_checkpointer.get.return_value = {"some": "checkpoint"}

        mock_compiled = MagicMock()
        mock_compiled.invoke.return_value = {
            "step": "completion",
            "status": "completed",
            "events": [],
        }

        with patch("agentic_devtools.orchestration.checkpointing.get_checkpointer") as mock_get_cp:
            mock_get_cp.return_value = mock_checkpointer
            with patch("agentic_devtools.orchestration.graph_builder.build_work_on_issue_graph") as mock_build:
                mock_build.return_value = mock_compiled
                from agentic_devtools.orchestration.runner import run_langchain_workflow

                run_langchain_workflow("TEST-789", resume=True)

        captured = capsys.readouterr()
        assert "[langchain] Resuming workflow for TEST-789" in captured.out

    def test_resume_with_resume_data_passes_data_to_command(self, capsys):
        """Resume with resume_data passes structured data to Command(resume=...)."""
        mock_checkpointer = MagicMock()
        mock_checkpointer.get.return_value = {"some": "checkpoint"}

        mock_compiled = MagicMock()
        mock_compiled.invoke.return_value = {
            "step": "completion",
            "status": "completed",
            "events": [],
        }

        resume_payload = {"completed": True, "summary": "Work done"}

        with patch("agentic_devtools.orchestration.checkpointing.get_checkpointer") as mock_get_cp:
            mock_get_cp.return_value = mock_checkpointer
            with patch("agentic_devtools.orchestration.graph_builder.build_work_on_issue_graph") as mock_build:
                mock_build.return_value = mock_compiled
                from agentic_devtools.orchestration.runner import run_langchain_workflow

                run_langchain_workflow("TEST-789", resume=True, resume_data=resume_payload)

        # Verify Command was called with the resume data
        call_args = mock_compiled.invoke.call_args
        command_arg = call_args[0][0]
        # The Command object should have resume=resume_payload
        assert command_arg.resume == resume_payload

    def test_resume_failure_exits_with_error(self, capsys):
        """Resume failure exits with error code 1."""
        mock_checkpointer = MagicMock()
        mock_checkpointer.get.return_value = {"some": "checkpoint"}

        mock_compiled = MagicMock()
        mock_compiled.invoke.side_effect = RuntimeError("Resume failed")

        with patch("agentic_devtools.orchestration.checkpointing.get_checkpointer") as mock_get_cp:
            mock_get_cp.return_value = mock_checkpointer
            with patch("agentic_devtools.orchestration.graph_builder.build_work_on_issue_graph") as mock_build:
                mock_build.return_value = mock_compiled
                from agentic_devtools.orchestration.runner import run_langchain_workflow

                with pytest.raises(SystemExit) as exc_info:
                    run_langchain_workflow("TEST-789", resume=True)

                assert exc_info.value.code == 1
                captured = capsys.readouterr()
                assert "Workflow resume failed" in captured.err

    def test_resume_handles_graph_interrupt(self, capsys):
        """Resume path handles GraphInterrupt for a later gate pause."""
        mock_checkpointer = MagicMock()
        mock_checkpointer.get.return_value = {"some": "checkpoint"}

        mock_compiled = MagicMock()

        # Simulate GraphInterrupt during resume
        class GraphInterrupt(Exception):
            pass

        mock_compiled.invoke.side_effect = GraphInterrupt("Waiting for next gate")

        with patch("agentic_devtools.orchestration.checkpointing.get_checkpointer") as mock_get_cp:
            mock_get_cp.return_value = mock_checkpointer
            with patch("agentic_devtools.orchestration.graph_builder.build_work_on_issue_graph") as mock_build:
                mock_build.return_value = mock_compiled
                from agentic_devtools.orchestration.runner import run_langchain_workflow

                # Should not raise, should print pause/resume instructions
                run_langchain_workflow("TEST-789", resume=True)

        captured = capsys.readouterr()
        assert "paused" in captured.err
        assert "--resume" in captured.err


class TestRunLangchainWorkflowCheckpointerCleanup:
    """Tests for checkpointer connection cleanup."""

    def test_checkpointer_connection_closed_on_success(self, capsys):
        """Checkpointer connection is closed after successful invocation."""
        mock_conn = MagicMock()
        mock_checkpointer = MagicMock()
        mock_checkpointer.conn = mock_conn

        mock_compiled = MagicMock()
        mock_compiled.invoke.return_value = {
            "step": "completion",
            "status": "completed",
            "events": [],
        }

        with patch("agentic_devtools.orchestration.checkpointing.get_checkpointer") as mock_get_cp:
            mock_get_cp.return_value = mock_checkpointer
            with patch("agentic_devtools.orchestration.graph_builder.build_work_on_issue_graph") as mock_build:
                mock_build.return_value = mock_compiled
                from agentic_devtools.orchestration.runner import run_langchain_workflow

                run_langchain_workflow("TEST-123")

        mock_conn.close.assert_called_once()

    def test_checkpointer_connection_closed_on_error(self, capsys):
        """Checkpointer connection is closed even when invocation fails."""
        mock_conn = MagicMock()
        mock_checkpointer = MagicMock()
        mock_checkpointer.conn = mock_conn

        mock_compiled = MagicMock()
        mock_compiled.invoke.side_effect = RuntimeError("fail")

        with patch("agentic_devtools.orchestration.checkpointing.get_checkpointer") as mock_get_cp:
            mock_get_cp.return_value = mock_checkpointer
            with patch("agentic_devtools.orchestration.graph_builder.build_work_on_issue_graph") as mock_build:
                mock_build.return_value = mock_compiled
                from agentic_devtools.orchestration.runner import run_langchain_workflow

                with pytest.raises(SystemExit):
                    run_langchain_workflow("TEST-123")

        mock_conn.close.assert_called_once()

    def test_checkpointer_without_conn_attribute_does_not_crash(self, capsys):
        """Checkpointer without a conn attribute does not crash on cleanup."""
        mock_checkpointer = MagicMock(spec=[])  # no attributes

        mock_compiled = MagicMock()
        mock_compiled.invoke.return_value = {
            "step": "completion",
            "status": "completed",
            "events": [],
        }

        with patch("agentic_devtools.orchestration.checkpointing.get_checkpointer") as mock_get_cp:
            mock_get_cp.return_value = mock_checkpointer
            with patch("agentic_devtools.orchestration.graph_builder.build_work_on_issue_graph") as mock_build:
                mock_build.return_value = mock_compiled
                from agentic_devtools.orchestration.runner import run_langchain_workflow

                # Should not raise
                run_langchain_workflow("TEST-123")
