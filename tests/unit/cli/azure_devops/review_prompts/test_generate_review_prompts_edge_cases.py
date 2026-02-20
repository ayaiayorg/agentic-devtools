"""
Tests for review_prompts module.
"""


class TestGenerateReviewPromptsEdgeCases:
    """Tests for edge cases in generate_review_prompts."""

    def test_cleans_existing_prompt_files(self, tmp_path):
        """Test that existing prompt files are cleaned before generating new ones."""
        from agentic_devtools.cli.azure_devops.review_prompts import (
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
        from agentic_devtools.cli.azure_devops.review_prompts import (
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
