"""
Tests for Jira formatting utilities.
"""

from unittest.mock import patch

from agdt_ai_helpers.cli import jira


class TestBuildUserStoryDescription:
    """Tests for build_user_story_description function."""

    def test_basic_user_story(self):
        """Test basic user story format."""
        with patch.dict("os.environ", {}, clear=True):
            result = jira.build_user_story_description(
                role="developer", desired_outcome="a feature", benefit="better UX"
            )

        assert "*As a* developer" in result
        assert "*I would like* a feature" in result
        assert "*so that* better UX" in result
        assert "Acceptance Criteria" in result

    def test_user_story_with_acceptance_criteria(self):
        """Test user story with acceptance criteria."""
        with patch.dict("os.environ", {}, clear=True):
            result = jira.build_user_story_description(
                role="user",
                desired_outcome="login",
                benefit="access",
                acceptance_criteria=["AC1", "AC2"],
            )

        assert "* AC1" in result
        assert "* AC2" in result

    def test_user_story_with_additional_info(self):
        """Test user story with additional information."""
        with patch.dict("os.environ", {}, clear=True):
            result = jira.build_user_story_description(
                role="user",
                desired_outcome="feature",
                benefit="value",
                additional_information=["Info1", "Info2"],
            )

        assert "Additional Information" in result
        assert "* Info1" in result
        assert "* Info2" in result

    def test_user_story_with_reviewer(self):
        """Test user story includes reviewer when email available."""
        with patch.dict("os.environ", {"JIRA_EMAIL": "reviewer@test.com"}):
            result = jira.build_user_story_description(role="user", desired_outcome="feature", benefit="value")

        assert "Reviewer" in result
        assert "reviewer@test.com" in result

    def test_user_story_with_username_reviewer(self):
        """Test user story includes reviewer from username."""
        with patch.dict("os.environ", {"JIRA_USERNAME": "testuser"}, clear=True):
            result = jira.build_user_story_description(role="user", desired_outcome="feature", benefit="value")

        assert "Reviewer" in result
        assert "testuser" in result

    def test_user_story_strips_role(self):
        """Test role whitespace is stripped."""
        with patch.dict("os.environ", {}, clear=True):
            result = jira.build_user_story_description(role="  developer  ", desired_outcome="feature", benefit="value")
        assert "*As a* developer," in result

    def test_user_story_no_additional_info_section_when_empty(self):
        """Test no Additional Information section when list is empty."""
        with patch.dict("os.environ", {}, clear=True):
            result = jira.build_user_story_description(
                role="user",
                desired_outcome="feature",
                benefit="value",
                additional_information=[],
            )
        assert "Additional Information" not in result

