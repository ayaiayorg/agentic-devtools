"""Tests for route_after_plan conditional edge function."""

from agentic_devtools.orchestration.pilot_workflow import route_after_plan


class TestRouteAfterPlan:
    def test_routes_to_checklist_creation_when_approved(self):
        assert route_after_plan({"human_approved": True}) == "checklist_creation"

    def test_routes_to_planning_gate_when_not_approved(self):
        assert route_after_plan({"human_approved": False}) == "planning_gate"

    def test_routes_to_planning_gate_when_key_missing(self):
        assert route_after_plan({}) == "planning_gate"
