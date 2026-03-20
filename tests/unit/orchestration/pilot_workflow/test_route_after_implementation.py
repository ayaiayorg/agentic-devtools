"""Tests for route_after_implementation conditional edge function."""

from agentic_devtools.orchestration.pilot_workflow import route_after_implementation


class TestRouteAfterImplementation:
    def test_routes_to_implementation_review(self):
        assert route_after_implementation({}) == "implementation_review"

    def test_routes_to_implementation_review_regardless_of_state(self):
        assert route_after_implementation({"error": "something", "retry_count": 5}) == "implementation_review"
