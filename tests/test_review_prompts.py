"""
Tests for review_prompts module.
"""


class TestGetPromptsOutputDir:
    """Tests for get_prompts_output_dir function."""

    def test_returns_path_to_temp_pr_review_prompts(self):
        """Test that the function returns the correct path."""
        from dfly_ai_helpers.cli.azure_devops.review_prompts import (
            get_prompts_output_dir,
        )

        result = get_prompts_output_dir()
        assert result.name == "pr-review-prompts"
        assert result.parent.name == "temp"


class TestBuildFilePromptContent:
    """Tests for build_file_prompt_content function."""

    def test_builds_basic_prompt(self):
        """Test building a basic prompt without threads."""
        from dfly_ai_helpers.cli.azure_devops.review_prompts import (
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
        from dfly_ai_helpers.cli.azure_devops.review_prompts import (
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
        from dfly_ai_helpers.cli.azure_devops.review_prompts import (
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
        from dfly_ai_helpers.cli.azure_devops.review_prompts import (
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
        from dfly_ai_helpers.cli.azure_devops.review_prompts import (
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


class TestWriteFilePrompt:
    """Tests for write_file_prompt function."""

    def test_writes_prompt_file(self, tmp_path):
        """Test that prompt file is written correctly."""
        from dfly_ai_helpers.cli.azure_devops.review_prompts import write_file_prompt

        result = write_file_prompt(
            file_path="/src/components/Button.tsx",
            change_type="edit",
            pr_id=123,
            file_content="code changes",
            threads=[],
            output_dir=tmp_path,
        )

        assert result.exists()
        assert result.suffix == ".md"
        content = result.read_text(encoding="utf-8")
        assert "# PR Review: /src/components/Button.tsx" in content


class TestGenerateReviewPrompts:
    """Tests for generate_review_prompts function."""

    def test_generates_prompts_for_all_changes(self, tmp_path):
        """Test generating prompts for all changes."""
        from dfly_ai_helpers.cli.azure_devops.review_prompts import (
            generate_review_prompts,
        )

        pr_details = {
            "pullRequest": {"pullRequestId": 123},
            "changes": [
                {
                    "item": {"path": "/src/app.ts"},
                    "changeType": "edit",
                    "content": "code",
                },
                {
                    "item": {"path": "/src/util.ts"},
                    "changeType": "add",
                    "content": "new",
                },
            ],
            "threads": [],
        }

        results = generate_review_prompts(pr_details, tmp_path)

        assert len(results) == 2
        assert all(not r["skipped"] for r in results)
        # Filenames use SHA256 hash, so check that prompt files were created
        assert all(r.get("prompt_path") is not None for r in results)
        prompt_files = list(tmp_path.glob("file-*.md"))
        assert len(prompt_files) == 2

    def test_skips_already_reviewed_files(self, tmp_path):
        """Test that already reviewed files are skipped."""
        from dfly_ai_helpers.cli.azure_devops.review_prompts import (
            generate_review_prompts,
        )

        # The function uses reviewer.reviewedFiles to determine what's already reviewed
        pr_details = {
            "pullRequest": {"pullRequestId": 123},
            "changes": [
                {
                    "item": {"path": "/src/app.ts"},
                    "changeType": "edit",
                    "content": "code",
                }
            ],
            "threads": [],
            "reviewer": {"reviewedFiles": ["/src/app.ts"]},
        }

        results = generate_review_prompts(pr_details, tmp_path)

        assert len(results) == 1
        assert results[0]["skipped"] is True

    def test_skips_files_without_path(self, tmp_path):
        """Test that files without path are skipped."""
        from dfly_ai_helpers.cli.azure_devops.review_prompts import (
            generate_review_prompts,
        )

        pr_details = {
            "pullRequest": {"pullRequestId": 123},
            "changes": [{"item": {}, "changeType": "edit", "content": "code"}],
            "threads": [],
        }

        results = generate_review_prompts(pr_details, tmp_path)

        assert len(results) == 0

    def test_handles_empty_changes(self, tmp_path):
        """Test handling empty changes list."""
        from dfly_ai_helpers.cli.azure_devops.review_prompts import (
            generate_review_prompts,
        )

        pr_details = {
            "pullRequest": {"pullRequestId": 123},
            "changes": None,
            "threads": [],
        }

        results = generate_review_prompts(pr_details, tmp_path)

        assert len(results) == 0

    def test_verbose_mode_prints_progress(self, tmp_path, capsys):
        """Test that verbose mode prints progress."""
        from dfly_ai_helpers.cli.azure_devops.review_prompts import (
            generate_review_prompts,
        )

        pr_details = {
            "pullRequest": {"pullRequestId": 123},
            "changes": [
                {
                    "item": {"path": "/src/app.ts"},
                    "changeType": "edit",
                    "content": "code",
                }
            ],
            "threads": [],
        }

        generate_review_prompts(pr_details, tmp_path, verbose=True)

        captured = capsys.readouterr()
        assert "Generated" in captured.out or "✅" in captured.out


class TestPrintReviewInstructions:
    """Tests for print_review_instructions function."""

    def test_prints_summary(self, tmp_path, capsys):
        """Test that summary is printed."""
        from dfly_ai_helpers.cli.azure_devops.review_prompts import (
            print_review_instructions,
        )

        pr_details = {"pullRequest": {"pullRequestId": 123, "title": "Test PR"}}

        results = [
            {
                "file_path": "/src/app.ts",
                "prompt_path": str(tmp_path / "file.md"),
                "skipped": False,
            }
        ]

        print_review_instructions(pr_details, tmp_path, results)

        captured = capsys.readouterr()
        assert "123" in captured.out
        assert "Test PR" in captured.out

    def test_prints_all_reviewed_message(self, tmp_path, capsys):
        """Test that message is printed when all files already reviewed."""
        from dfly_ai_helpers.cli.azure_devops.review_prompts import (
            print_review_instructions,
        )

        pr_details = {"pullRequest": {"pullRequestId": 123, "title": "Test PR"}}

        results = [{"file_path": "/src/app.ts", "skipped": True, "reason": "already_reviewed"}]

        print_review_instructions(pr_details, tmp_path, results)

        captured = capsys.readouterr()
        assert "already" in captured.out.lower() or "reviewed" in captured.out.lower()


class TestNormalizeRepoPath:
    """Tests for normalize_repo_path function."""

    def test_returns_none_for_empty_path(self):
        """Test that empty paths return None."""
        from dfly_ai_helpers.cli.azure_devops.review_helpers import normalize_repo_path

        assert normalize_repo_path("") is None
        assert normalize_repo_path("   ") is None
        assert normalize_repo_path("/") is None
        assert normalize_repo_path("  /  ") is None


class TestGenerateReviewPromptsEdgeCases:
    """Tests for edge cases in generate_review_prompts."""

    def test_cleans_existing_prompt_files(self, tmp_path):
        """Test that existing prompt files are cleaned before generating new ones."""
        from dfly_ai_helpers.cli.azure_devops.review_prompts import (
            generate_review_prompts,
        )

        # Create pre-existing prompt files
        old_file = tmp_path / "file-oldprompt12345.md"
        old_file.write_text("old content")
        another_old = tmp_path / "file-another67890.md"
        another_old.write_text("another old")

        # Non-matching file should be preserved
        keep_file = tmp_path / "other-file.md"
        keep_file.write_text("keep this")

        pr_details = {
            "pullRequest": {"pullRequestId": 123},
            "changes": [
                {
                    "item": {"path": "/src/new.ts"},
                    "changeType": "add",
                    "content": "new code",
                }
            ],
            "threads": [],
        }

        generate_review_prompts(pr_details, tmp_path)

        # Old file-*.md files should be deleted
        assert not old_file.exists()
        assert not another_old.exists()
        # Non-matching file should be preserved
        assert keep_file.exists()
        # New prompt file should exist
        assert len(list(tmp_path.glob("file-*.md"))) == 1

    def test_verbose_mode_prints_skip_message(self, tmp_path, capsys):
        """Test that verbose mode prints skip message for reviewed files."""
        from dfly_ai_helpers.cli.azure_devops.review_prompts import (
            generate_review_prompts,
        )

        pr_details = {
            "pullRequest": {"pullRequestId": 123},
            "changes": [
                {
                    "item": {"path": "/src/app.ts"},
                    "changeType": "edit",
                    "content": "code",
                }
            ],
            "threads": [],
            "reviewer": {"reviewedFiles": ["/src/app.ts"]},
        }

        generate_review_prompts(pr_details, tmp_path, verbose=True)

        captured = capsys.readouterr()
        assert "Skipping" in captured.out
        assert "already reviewed" in captured.out
