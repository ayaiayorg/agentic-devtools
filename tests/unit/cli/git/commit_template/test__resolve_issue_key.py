"""Tests for _resolve_issue_key."""

from unittest.mock import patch

from agentic_devtools.cli.git.commit_template import _resolve_issue_key

_MOD = "agentic_devtools.cli.git.commit_template"


class TestResolveIssueKey:
    """Tests for _resolve_issue_key."""

    @patch(f"{_MOD}.get_value", return_value=None)
    def test_returns_none_when_no_state(self, mock_get):
        """Returns (None, None) when neither issue_key nor jira.issue_key is set."""
        result = _resolve_issue_key()
        assert result == (None, None)

    @patch(f"{_MOD}.get_value", side_effect=lambda k: 42 if k == "issue_key" else None)
    def test_integer_issue_key(self, mock_get):
        """Integer value is normalized to string."""
        normalized, raw = _resolve_issue_key()
        assert normalized == "42"
        assert raw == 42

    @patch(f"{_MOD}.get_value", side_effect=lambda k: "123" if k == "issue_key" else None)
    def test_digits_only_string(self, mock_get):
        """Digits-only string is kept as-is."""
        normalized, raw = _resolve_issue_key()
        assert normalized == "123"
        assert raw == "123"

    @patch(f"{_MOD}.get_value", side_effect=lambda k: "#99" if k == "issue_key" else None)
    def test_hash_prefix_stripped(self, mock_get):
        """Leading # is stripped for GitHub-style #N."""
        normalized, raw = _resolve_issue_key()
        assert normalized == "99"
        assert raw == "#99"

    @patch(f"{_MOD}.get_value", side_effect=lambda k: "#abc" if k == "issue_key" else None)
    def test_hash_prefix_non_numeric_kept(self, mock_get):
        """Leading # with non-numeric remainder is kept as-is."""
        normalized, raw = _resolve_issue_key()
        assert normalized == "#abc"
        assert raw == "#abc"

    @patch(f"{_MOD}.get_value", side_effect=lambda k: "PROJECT-1234" if k == "issue_key" else None)
    def test_jira_style_key(self, mock_get):
        """Jira-style keys are preserved as-is."""
        normalized, raw = _resolve_issue_key()
        assert normalized == "PROJECT-1234"
        assert raw == "PROJECT-1234"

    @patch(f"{_MOD}.get_value", side_effect=lambda k: "PROJ-99" if k == "jira.issue_key" else None)
    def test_fallback_to_jira_issue_key(self, mock_get):
        """Falls back to jira.issue_key when issue_key is None."""
        normalized, raw = _resolve_issue_key()
        assert normalized == "PROJ-99"
        assert raw == "PROJ-99"

    @patch(f"{_MOD}.get_value", side_effect=lambda k: "007" if k == "issue_key" else None)
    def test_leading_zeros_digits_only(self, mock_get):
        """Leading zeros in digits-only string are preserved."""
        normalized, raw = _resolve_issue_key()
        assert normalized == "007"
        assert raw == "007"

    @patch(
        f"{_MOD}.get_value",
        side_effect=lambda k: "PROJ-99" if k == "jira.issue_key" else "   " if k == "issue_key" else None,
    )
    def test_whitespace_only_issue_key_falls_back_to_jira_issue_key(self, mock_get):
        """Whitespace-only issue_key is treated as unset."""
        normalized, raw = _resolve_issue_key()
        assert normalized == "PROJ-99"
        assert raw == "PROJ-99"

    @patch(f"{_MOD}.get_value", side_effect=lambda k: "   " if k == "issue_key" else None)
    def test_whitespace_only_issue_key_returns_none_when_no_jira_fallback(self, mock_get):
        """Whitespace-only issue_key returns no value when fallback is absent."""
        normalized, raw = _resolve_issue_key()
        assert normalized is None
        assert raw is None

    @patch(
        f"{_MOD}.get_value",
        side_effect=lambda k: 7 if k == "jira.issue_key" else "   " if k == "issue_key" else None,
    )
    def test_whitespace_only_issue_key_uses_integer_jira_fallback(self, mock_get):
        """Whitespace-only issue_key still accepts integer jira.issue_key fallback."""
        normalized, raw = _resolve_issue_key()
        assert normalized == "7"
        assert raw == 7

    @patch(
        f"{_MOD}.get_value",
        side_effect=lambda k: "   " if k in {"issue_key", "jira.issue_key"} else None,
    )
    def test_whitespace_only_issue_key_and_jira_fallback_return_none(self, mock_get):
        """Whitespace-only values are ignored for both issue_key sources."""
        assert _resolve_issue_key() == (None, None)

    @patch(f"{_MOD}.get_value")
    def test_ignores_non_scalar_values_and_uses_workflow_context(self, mock_get):
        """Ignores non-str/int keys and falls back to workflow context key."""
        values = {
            "issue_key": {"bad": "value"},
            "jira.issue_key": [],
            "workflow": {"context": {"jira_issue_key": "PROJ-42"}},
        }
        mock_get.side_effect = lambda key: values.get(key)
        normalized, raw = _resolve_issue_key()
        assert normalized == "PROJ-42"
        assert raw == "PROJ-42"

    @patch(f"{_MOD}.get_value")
    def test_excludes_bool_and_accepts_int_from_workflow_context(self, mock_get):
        """Excludes bool values and accepts int issue key from workflow context."""
        values = {
            "issue_key": True,
            "jira.issue_key": False,
            "workflow": {"context": {"jira_issue_key": 77}},
        }
        mock_get.side_effect = lambda key: values.get(key)
        normalized, raw = _resolve_issue_key()
        assert normalized == "77"
        assert raw == 77

    @patch(f"{_MOD}.get_value")
    def test_ignores_non_dict_workflow_context(self, mock_get):
        """Ignores workflow context when it is not a dictionary."""
        values = {
            "issue_key": None,
            "jira.issue_key": None,
            "workflow": {"context": "not-a-dict"},
        }
        mock_get.side_effect = lambda key: values.get(key)
        normalized, raw = _resolve_issue_key()
        assert normalized is None
        assert raw is None
