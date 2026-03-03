"""Tests for PR review initiate prompt rendering with repo_review_focus_areas."""

from agdt_ai_helpers.prompts import loader


class TestPrReviewInitiatePromptRendering:
    """Tests for the default-initiate-prompt.md template in pull-request-review workflow."""

    def _render(self, **kwargs):
        """Render the actual PR review initiate template with the given variables."""
        template = loader.load_prompt_template("pull-request-review", "initiate")
        return loader.substitute_variables(template, kwargs)

    def _base_variables(self):
        return {
            "pull_request_id": "42",
            "pr_title": "feat: add feature",
            "pr_author": "Alice",
            "source_branch": "feature/test",
            "target_branch": "main",
            "jira_issue_key": "",
            "file_count": "3",
            "repo_review_focus_areas": "",
            "pr_url": "https://dev.azure.com/swica/DragonflyMgmt/_git/dfly-platform-management/pullrequest/42",
            "source_code_platform": "AzureDevOps",
        }

    def test_renders_without_focus_areas(self):
        """Focus areas section is absent when repo_review_focus_areas is empty."""
        variables = self._base_variables()
        result = self._render(**variables)

        assert "Repo-Specific Review Focus Areas" not in result

    def test_renders_with_focus_areas(self):
        """Focus areas section appears when repo_review_focus_areas has content."""
        variables = self._base_variables()
        variables["repo_review_focus_areas"] = "## .NET DI\n- Use constructor injection"
        result = self._render(**variables)

        assert "Repo-Specific Review Focus Areas" in result
        assert ".NET DI" in result
        assert "constructor injection" in result

    def test_focus_areas_section_omitted_when_none(self):
        """Focus areas section is omitted when variable is not provided (treated as falsy)."""
        variables = self._base_variables()
        del variables["repo_review_focus_areas"]
        result = self._render(**variables)

        assert "Repo-Specific Review Focus Areas" not in result

    def test_important_note_section_present(self):
        """Important Note About Existing Comments section is always present."""
        result = self._render(**self._base_variables())

        assert "Important Note About Existing Comments" in result
        assert "independent review" in result

    def test_review_outcomes_section_present(self):
        """Review Outcomes section is always present."""
        result = self._render(**self._base_variables())

        assert "Review Outcomes" in result
        assert "Approve" in result
        assert "Request Changes" in result
        assert "Security vulnerabilities" in result

    def test_pr_details_rendered(self):
        """Core PR details are rendered in the output."""
        result = self._render(**self._base_variables())

        assert "42" in result
        assert "feat: add feature" in result
        assert "Alice" in result

    def test_jira_link_absent_when_no_issue_key(self):
        """Jira link is absent when jira_issue_key is empty."""
        result = self._render(**self._base_variables())

        assert "Jira Issue" not in result

    def test_jira_link_present_when_issue_key_provided(self):
        """Jira link appears when jira_issue_key is provided."""
        variables = self._base_variables()
        variables["jira_issue_key"] = "DFLY-1234"
        result = self._render(**variables)

        assert "DFLY-1234" in result

    def test_next_action_appears_before_pr_details(self):
        """Next Action section appears before PR Details in the rendered output."""
        result = self._render(**self._base_variables())

        next_action_pos = result.find("## Next Action")
        pr_details_pos = result.find("## PR Details")
        assert next_action_pos != -1
        assert pr_details_pos != -1
        assert next_action_pos < pr_details_pos

    def test_pr_url_rendered(self):
        """PR URL value appears in the rendered output."""
        result = self._render(**self._base_variables())

        assert "https://dev.azure.com/swica/DragonflyMgmt/_git/dfly-platform-management/pullrequest/42" in result

    def test_source_code_platform_rendered(self):
        """Source Code Hosting Platform field and value appear in the rendered output."""
        result = self._render(**self._base_variables())

        assert "Source Code Hosting Platform" in result
        assert "AzureDevOps" in result

    def test_instructions_file_reference_present(self):
        """Instructions file reference appears at the end of the rendered output."""
        result = self._render(**self._base_variables())

        assert "scripts/temp/temp-pull-request-review-initiate-prompt.md" in result
