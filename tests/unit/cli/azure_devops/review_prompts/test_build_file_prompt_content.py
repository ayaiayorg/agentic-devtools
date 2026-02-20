"""
Tests for review_prompts module.
"""


class TestBuildFilePromptContent:
    """Tests for build_file_prompt_content function."""

    def test_builds_basic_prompt(self):
        """Test building a basic prompt without threads."""
        from agentic_devtools.cli.azure_devops.review_prompts import (
            build_file_prompt_content,
        )

        result = build_file_prompt_content(
            file_path="/src/app.ts",
            change_type="edit",
            pr_id=123,
            file_content="+ added line",
            threads=[],
            timestamp="2025-01-01T00:00:00Z",
        )

        assert "# PR Review: /src/app.ts" in result
        assert "**PR ID**: 123" in result
        assert "**Change Type**: edit" in result
        assert "+ added line" in result

    def test_includes_jira_issue_key_when_provided(self):
        """Test that Jira issue key is included when provided."""
        from agentic_devtools.cli.azure_devops.review_prompts import (
            build_file_prompt_content,
        )

        result = build_file_prompt_content(
            file_path="/src/app.ts",
            change_type="add",
            pr_id=123,
            file_content="new code",
            threads=[],
            jira_issue_key="DFLY-1234",
            timestamp="2025-01-01T00:00:00Z",
        )

        assert "DFLY-1234" in result
        assert "jira.swica.ch/browse/DFLY-1234" in result

    def test_includes_existing_threads(self):
        """Test that existing threads are included."""
        from agentic_devtools.cli.azure_devops.review_prompts import (
            build_file_prompt_content,
        )

        threads = [
            {
                "status": "active",
                "comments": [
                    {
                        "author": {"displayName": "Reviewer"},
                        "content": "Please fix this.",
                    }
                ],
            }
        ]

        result = build_file_prompt_content(
            file_path="/src/app.ts",
            change_type="edit",
            pr_id=123,
            file_content="code",
            threads=threads,
            timestamp="2025-01-01T00:00:00Z",
        )

        assert "## Existing Review Comments" in result
        assert "Thread (active)" in result
        assert "Reviewer" in result
        assert "Please fix this." in result

    def test_handles_empty_file_content(self):
        """Test that empty file content is handled."""
        from agentic_devtools.cli.azure_devops.review_prompts import (
            build_file_prompt_content,
        )

        result = build_file_prompt_content(
            file_path="/src/app.ts",
            change_type="delete",
            pr_id=123,
            file_content="",
            threads=[],
            timestamp="2025-01-01T00:00:00Z",
        )

        assert "(no content available)" in result

    def test_uses_current_timestamp_when_not_provided(self):
        """Test that a timestamp is generated when not provided."""
        from agentic_devtools.cli.azure_devops.review_prompts import (
            build_file_prompt_content,
        )

        result = build_file_prompt_content(
            file_path="/src/app.ts",
            change_type="edit",
            pr_id=123,
            file_content="code",
            threads=[],
        )

        assert "**Generated**:" in result
