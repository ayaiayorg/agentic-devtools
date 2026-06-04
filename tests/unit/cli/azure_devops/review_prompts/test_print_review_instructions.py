"""Tests for print_review_instructions function."""


class TestPrintReviewInstructions:
    """Tests for print_review_instructions function."""

    def test_prints_summary(self, tmp_path, capsys):
        """Test that summary is printed."""
        from agentic_devtools.cli.azure_devops.review_prompts import (
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

    def test_prints_no_special_message_for_previously_reviewed(self, tmp_path, capsys):
        """Test that no special message is printed for reviewed files.

        All files are now reviewed every run — there is no 'already reviewed' state.
        """
        from agentic_devtools.cli.azure_devops.review_prompts import (
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
        assert "skipped (already reviewed)" not in captured.out.lower()

    def test_no_review_hint_when_all_skipped(self, tmp_path, capsys):
        """Test that review hint is omitted when no prompts are generated."""
        from agentic_devtools.cli.azure_devops.review_prompts import (
            print_review_instructions,
        )

        pr_details = {"pullRequest": {"pullRequestId": 456, "title": "Empty PR"}}

        results = [
            {
                "file_path": "/src/app.ts",
                "prompt_path": str(tmp_path / "file.md"),
                "skipped": True,
            }
        ]

        print_review_instructions(pr_details, tmp_path, results)

        captured = capsys.readouterr()
        assert "456" in captured.out
        assert "To review, open each .md file" not in captured.out
