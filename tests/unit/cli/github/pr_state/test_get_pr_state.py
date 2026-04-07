"""Tests for get_pr_state in pr_state module."""

from unittest.mock import call, patch

from agentic_devtools.cli.github import pr_state as pr_state_module


class TestGetPrState:
    """Tests for get_pr_state."""

    def _mock_api_response(self, **overrides):
        """Build a mock API response dict."""
        data = {
            "state": "OPEN",
            "headRefOid": "9123c3c53d7d4a5b6c7d8e9f0a1b2c3d4e5f6a7b",
            "mergeable": "MERGEABLE",
            "mergeStateStatus": "CLEAN",
            "mergedAt": None,
            "isDraft": False,
            "locked": False,
        }
        data.update(overrides)
        return data

    def test_returns_structured_dict(self):
        """Returns a dict with all expected output fields."""
        api_data = self._mock_api_response()

        with patch.object(pr_state_module, "_fetch_pr_with_retry", return_value=api_data):
            with patch.object(pr_state_module, "set_value"):
                result = pr_state_module.get_pr_state(1115, "ayaiayorg/agentic-devtools")

        assert result["prNumber"] == 1115
        assert result["repo"] == "ayaiayorg/agentic-devtools"
        assert result["state"] == "OPEN"
        assert result["headRefOid"] == "9123c3c53d7d4a5b6c7d8e9f0a1b2c3d4e5f6a7b"
        assert result["headRefOidShort"] == "9123c3c"
        assert result["mergeable"] == "MERGEABLE"
        assert result["mergeStateStatus"] == "CLEAN"
        assert result["mergedAt"] is None
        assert result["isDraft"] is False
        assert result["locked"] is False
        assert result["isTerminal"] is False
        assert result["terminalReason"] is None

    def test_head_ref_oid_short_is_7_chars(self):
        """headRefOidShort is the first 7 characters of headRefOid."""
        api_data = self._mock_api_response(headRefOid="abcdef1234567890")

        with patch.object(pr_state_module, "_fetch_pr_with_retry", return_value=api_data):
            with patch.object(pr_state_module, "set_value"):
                result = pr_state_module.get_pr_state(1, "o/r")

        assert result["headRefOidShort"] == "abcdef1"

    def test_empty_head_ref_oid(self):
        """Empty headRefOid produces empty headRefOidShort."""
        api_data = self._mock_api_response(headRefOid="")

        with patch.object(pr_state_module, "_fetch_pr_with_retry", return_value=api_data):
            with patch.object(pr_state_module, "set_value"):
                result = pr_state_module.get_pr_state(1, "o/r")

        assert result["headRefOidShort"] == ""

    def test_null_head_ref_oid(self):
        """None headRefOid produces empty headRefOidShort."""
        api_data = self._mock_api_response(headRefOid=None)

        with patch.object(pr_state_module, "_fetch_pr_with_retry", return_value=api_data):
            with patch.object(pr_state_module, "set_value"):
                result = pr_state_module.get_pr_state(1, "o/r")

        assert result["headRefOid"] == ""
        assert result["headRefOidShort"] == ""

    def test_writes_state_keys(self):
        """All 9 github.* state keys are written."""
        api_data = self._mock_api_response()

        with patch.object(pr_state_module, "_fetch_pr_with_retry", return_value=api_data):
            with patch.object(pr_state_module, "set_value") as mock_set:
                pr_state_module.get_pr_state(1115, "ayaiayorg/agentic-devtools")

        expected_calls = [
            call("github.pull_request_number", 1115),
            call("github.repo", "ayaiayorg/agentic-devtools"),
            call("github.pr_state", "OPEN"),
            call("github.head_ref_oid", "9123c3c53d7d4a5b6c7d8e9f0a1b2c3d4e5f6a7b"),
            call("github.head_ref_oid_short", "9123c3c"),
            call("github.mergeable", "MERGEABLE"),
            call("github.merge_state_status", "CLEAN"),
            call("github.is_draft", False),
            call("github.is_terminal", False),
        ]
        mock_set.assert_has_calls(expected_calls, any_order=False)

    def test_terminal_merged_state(self):
        """MERGED state sets isTerminal and terminalReason."""
        api_data = self._mock_api_response(state="MERGED", mergedAt="2024-01-01T00:00:00Z")

        with patch.object(pr_state_module, "_fetch_pr_with_retry", return_value=api_data):
            with patch.object(pr_state_module, "set_value"):
                result = pr_state_module.get_pr_state(1, "o/r")

        assert result["isTerminal"] is True
        assert result["terminalReason"] == "PR is merged"

    def test_locked_none_in_response(self):
        """locked=None in API response propagates to output."""
        api_data = self._mock_api_response(locked=None)

        with patch.object(pr_state_module, "_fetch_pr_with_retry", return_value=api_data):
            with patch.object(pr_state_module, "set_value"):
                result = pr_state_module.get_pr_state(1, "o/r")

        assert result["locked"] is None
        assert result["isTerminal"] is False
