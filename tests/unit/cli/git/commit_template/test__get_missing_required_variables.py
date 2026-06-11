"""Tests for _get_missing_required_variables."""

from agentic_devtools.cli.git.commit_template import (
    HARD_REQUIRED_VARIABLES,
    _get_missing_required_variables,
)


class TestGetMissingRequiredVariables:
    """Tests for _get_missing_required_variables."""

    def test_returns_empty_when_all_hard_required_resolved(self):
        """Returns empty frozenset when all hard-required vars are in context."""
        context = {
            "issueType": "feat",
            "issueKey": "42",
            "issueLink": "https://github.com/org/repo/issues/42",
            "commitMessageTitle": "add feature",
        }
        template = "{{ issueType }}([#{{ issueKey }}]({{ issueLink }})): {{ commitMessageTitle }}"
        result = _get_missing_required_variables(context, template)
        assert result == frozenset()

    def test_returns_missing_hard_required_vars(self):
        """Returns frozenset of hard-required vars referenced in template but absent from context."""
        context = {}
        template = "{{ issueType }}([#{{ issueKey }}]({{ issueLink }})): {{ commitMessageTitle }}"
        result = _get_missing_required_variables(context, template)
        assert result == frozenset({"issueType", "issueKey", "issueLink", "commitMessageTitle"})

    def test_commit_message_body_is_not_hard_required(self):
        """commitMessageBody absence does not appear in the missing set."""
        context = {}
        template = "feat: title\n\n{{ commitMessageBody }}"
        result = _get_missing_required_variables(context, template)
        assert "commitMessageBody" not in result
        assert result == frozenset()

    def test_only_referenced_vars_are_checked(self):
        """Only variables actually referenced in the template can appear in result."""
        context = {}
        # Template only uses issueKey; issueType/issueLink/commitMessageTitle are NOT referenced
        template = "fix({{ issueKey }}): some message"
        result = _get_missing_required_variables(context, template)
        assert result == frozenset({"issueKey"})

    def test_returns_empty_for_syntax_error(self):
        """Returns empty frozenset when template has a syntax error (not our concern here)."""
        context = {}
        template = "{% if x %}"  # unclosed block — syntax error
        result = _get_missing_required_variables(context, template)
        assert result == frozenset()

    def test_partial_context_reports_only_missing_vars(self):
        """Returns only the hard-required vars that are missing, not those already resolved."""
        context = {"issueKey": "42", "issueLink": "https://github.com/org/repo/issues/42"}
        template = "{{ issueType }}([#{{ issueKey }}]({{ issueLink }})): {{ commitMessageTitle }}"
        result = _get_missing_required_variables(context, template)
        assert result == frozenset({"issueType", "commitMessageTitle"})

    def test_returns_empty_when_template_has_no_hard_required_vars(self):
        """Returns empty frozenset for a template that references no hard-required vars."""
        context = {}
        template = "chore: housekeeping"
        result = _get_missing_required_variables(context, template)
        assert result == frozenset()

    def test_hard_required_variables_constant_excludes_commit_message_body(self):
        """HARD_REQUIRED_VARIABLES does not include commitMessageBody."""
        assert "commitMessageBody" not in HARD_REQUIRED_VARIABLES
        assert "issueType" in HARD_REQUIRED_VARIABLES
        assert "issueKey" in HARD_REQUIRED_VARIABLES
        assert "issueLink" in HARD_REQUIRED_VARIABLES
        assert "commitMessageTitle" in HARD_REQUIRED_VARIABLES
