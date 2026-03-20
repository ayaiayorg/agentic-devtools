"""Tests for route_after_verify conditional edge function."""

from agentic_devtools.orchestration.pilot_workflow import MAX_RETRIES, route_after_verify


class TestRouteAfterVerify:
    def test_routes_to_commit_when_no_error(self):
        assert route_after_verify({"error": None, "retry_count": 0}) == "commit"

    def test_routes_to_commit_when_error_missing(self):
        assert route_after_verify({}) == "commit"

    def test_routes_to_implementation_on_retryable_error(self):
        assert route_after_verify({"error": "test failed", "retry_count": 0}) == "implementation"

    def test_routes_to_implementation_below_max_retries(self):
        assert route_after_verify({"error": "test failed", "retry_count": MAX_RETRIES - 1}) == "implementation"

    def test_routes_to_commit_at_max_retries(self):
        assert route_after_verify({"error": "test failed", "retry_count": MAX_RETRIES}) == "commit"

    def test_routes_to_commit_above_max_retries(self):
        assert route_after_verify({"error": "test failed", "retry_count": MAX_RETRIES + 1}) == "commit"

    def test_max_retries_is_three(self):
        assert MAX_RETRIES == 3

    def test_routes_to_commit_when_no_error_despite_retries(self):
        assert route_after_verify({"error": None, "retry_count": 2}) == "commit"

    def test_routes_to_commit_when_error_is_empty_string(self):
        assert route_after_verify({"error": "", "retry_count": 1}) == "commit"
