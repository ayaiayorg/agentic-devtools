"""Tests for WorkflowDefinition.get_next_step()."""

from agentic_devtools.cli.workflows.manager import (
    WorkflowDefinition,
    WorkflowEvent,
    WorkflowTransition,
)


def test_get_next_step_returns_manual_advance_step():
    """get_next_step prefers a MANUAL_ADVANCE transition."""
    workflow = WorkflowDefinition(
        name="test-workflow",
        transitions=[
            WorkflowTransition(
                from_step="step-a",
                to_step="step-b",
                trigger_events={WorkflowEvent.MANUAL_ADVANCE},
            ),
        ],
    )
    assert workflow.get_next_step("step-a") == "step-b"


def test_get_next_step_falls_back_to_any_transition():
    """When no MANUAL_ADVANCE exists, get_next_step uses the first match."""
    workflow = WorkflowDefinition(
        name="test-workflow",
        transitions=[
            WorkflowTransition(
                from_step="step-a",
                to_step="step-c",
                trigger_events={WorkflowEvent.CHECKLIST_CREATED},
            ),
        ],
    )
    assert workflow.get_next_step("step-a") == "step-c"


def test_get_next_step_returns_none_for_unknown_step():
    """get_next_step returns None when no transitions match the step."""
    workflow = WorkflowDefinition(
        name="test-workflow",
        transitions=[
            WorkflowTransition(
                from_step="step-a",
                to_step="step-b",
                trigger_events={WorkflowEvent.MANUAL_ADVANCE},
            ),
        ],
    )
    assert workflow.get_next_step("unknown-step") is None
