"""
Tests for review_prompts module.
"""


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

    def test_prints_all_reviewed_message(self, tmp_path, capsys):
        """Test that message is printed when all files already reviewed."""
        from agentic_devtools.cli.azure_devops.review_prompts import (
            print_review_instructions,
        )

        pr_details = {"pullRequest": {"pullRequestId": 123, "title": "Test PR"}}

        results = [{"file_path": "/src/app.ts", "skipped": True, "reason": "already_reviewed"}]

        print_review_instructions(pr_details, tmp_path, results)

        captured = capsys.readouterr()
        assert "already" in captured.out.lower() or "reviewed" in captured.out.lower()
