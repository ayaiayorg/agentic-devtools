"""Tests for route_after_initiate conditional edge function."""

from agentic_devtools.orchestration.pilot_workflow import route_after_initiate


class TestRouteAfterInitiate:
    def test_routes_to_planning_when_no_error(self):
        assert route_after_initiate({"error": None}) == "planning"

    def test_routes_to_planning_when_error_missing(self):
        assert route_after_initiate({}) == "planning"

    def test_routes_to_setup_when_error_present(self):
        assert route_after_initiate({"error": "pre-flight failed"}) == "setup"

    def test_routes_to_planning_when_error_empty_string(self):
        assert route_after_initiate({"error": ""}) == "planning"
