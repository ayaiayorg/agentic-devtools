"""LangGraph workflow runner for the work-on-jira-issue workflow.

This module provides the entry point for running the LangGraph-based
work-on-jira-issue workflow when ``--engine langchain`` is selected.
"""

import sys
from typing import Any


def run_langchain_workflow(
    issue_key: str,
    *,
    interactive: bool = False,
    model: str | None = None,
    resume: bool = False,
    resume_data: dict | None = None,
) -> None:
    """Run the LangGraph-based work-on-jira-issue workflow.

    This is invoked when ``--engine langchain`` (or ``--use-langchain``) is
    provided on the CLI.  It builds and invokes the compiled StateGraph with
    real tool integrations.

    Args:
        issue_key: Jira issue key (e.g., PROJECT-1234).
        interactive: Whether to start the Copilot session interactively.
        model: Copilot model to use.
        resume: Whether to resume from an existing checkpoint.
        resume_data: Structured resume payload for gate nodes.
    """
    # FR-009: Dependency guard — surface actionable install message.
    try:
        from langgraph.graph.state import CompiledStateGraph  # noqa: F401
    except ImportError:  # pragma: no cover
        print(
            "ERROR: LangGraph dependencies are not available.\n\nInstall them with:\n  pip install agentic-devtools\n",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        from langgraph.checkpoint.sqlite import SqliteSaver  # noqa: F401
    except ImportError:  # pragma: no cover
        print(
            "ERROR: LangGraph checkpoint dependencies are not available.\n"
            "\n"
            "Install them with:\n"
            "  pip install agentic-devtools\n",
            file=sys.stderr,
        )
        sys.exit(1)

    from .checkpointing import get_checkpointer
    from .graph_builder import build_work_on_issue_graph

    # Build the thread ID for checkpoint scoping.
    thread_id = f"work-on-issue-{issue_key}"

    # Initialize checkpointer and build graph.
    checkpointer = get_checkpointer()
    try:
        compiled = build_work_on_issue_graph(checkpointer=checkpointer)

        config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}

        if resume:
            # Resume from existing checkpoint.
            from langgraph.types import Command

            # Check if there is an existing checkpoint to resume from.
            checkpoint = checkpointer.get(config)  # type: ignore[arg-type]
            if checkpoint is None:
                print(
                    f"ERROR: No existing checkpoint found for issue {issue_key}.\n"
                    "Cannot resume without a prior interrupted workflow run.\n"
                    "\n"
                    "Start a fresh run without --resume.",
                    file=sys.stderr,
                )
                sys.exit(1)

            # Determine resume payload based on gate type.
            resume_value: Any
            if resume_data is not None:
                resume_value = resume_data
            else:
                resume_value = True

            print(f"[langchain] Resuming workflow for {issue_key}...")
            try:
                result = compiled.invoke(Command(resume=resume_value), config=config)  # type: ignore[call-overload]
            except Exception as e:
                if type(e).__name__ == "GraphInterrupt":
                    _print_pause_message(issue_key)
                    return
                print(f"ERROR: Workflow resume failed: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            # Fresh invocation.
            initial_state: dict[str, Any] = {
                "issue_key": issue_key,
                "step": "",
                "status": "",
                "plan": "",
                "error": None,
                "retry_count": 0,
                "events": [],
                "human_approved": False,
                "agent_context": {
                    "interactive": interactive,
                    "model": model,
                },
                "affected_paths": [],
            }

            print(f"[langchain] Starting workflow for {issue_key}...")
            try:
                result = compiled.invoke(initial_state, config=config)  # type: ignore[call-overload]
            except Exception as e:
                if type(e).__name__ == "GraphInterrupt":
                    _print_pause_message(issue_key)
                    return
                print(f"ERROR: Workflow execution failed: {e}", file=sys.stderr)
                sys.exit(1)

        # Determine outcome: pause or completion.
        if _is_workflow_paused(result):
            _print_pause_message(issue_key)
            return

        # True completion.
        final_step = result.get("step", "unknown")
        final_status = result.get("status", "unknown")
        print(f"[langchain] Workflow completed: step={final_step}, status={final_status}")
    finally:
        # Close the checkpointer's underlying SQLite connection to avoid
        # leaking file descriptors / holding the DB file locked.
        if hasattr(checkpointer, "conn"):
            checkpointer.conn.close()


def _is_workflow_paused(result: object) -> bool:
    """Return True if the workflow is paused (not completed).

    When a LangGraph workflow with a checkpointer pauses at a human-in-the-loop
    gate node, ``invoke()`` returns the current state dict instead of raising
    ``GraphInterrupt``.  This helper detects that situation by checking whether
    the returned status is anything other than ``"completed"``.
    """
    if not isinstance(result, dict):
        return True
    return result.get("status") != "completed"


def _print_pause_message(issue_key: str) -> None:
    """Print human-in-the-loop pause instructions to stderr."""
    print(
        f"\n[langchain] Workflow paused — waiting for human input.\n"
        f"Resume with: agdt-initiate-work-on-jira-issue-workflow "
        f"--issue-key {issue_key} --engine langchain --resume",
        file=sys.stderr,
    )
