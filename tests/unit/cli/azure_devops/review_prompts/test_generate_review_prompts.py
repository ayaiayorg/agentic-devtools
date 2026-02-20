"""
Tests for review_prompts module.
"""


class TestGenerateReviewPrompts:
    """Tests for generate_review_prompts function."""

    def test_generates_prompts_for_all_changes(self, tmp_path):
        """Test generating prompts for all changes."""
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
        from agentic_devtools.cli.azure_devops.review_prompts import (
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
        from agentic_devtools.cli.azure_devops.review_prompts import (
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
        from agentic_devtools.cli.azure_devops.review_prompts import (
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
        }

        generate_review_prompts(pr_details, tmp_path, verbose=True)

        captured = capsys.readouterr()
        assert "Generated" in captured.out or "✅" in captured.out
