"""Tests for the review_commands module and helper functions."""


class TestGenerateReviewPrompts:
    """Tests for generate_review_prompts function."""

    def test_generates_prompts_for_files(self, tmp_path):
        """Test generates prompt files for PR files."""
        from unittest.mock import patch

        from agentic_devtools.cli.azure_devops.review_commands import generate_review_prompts

        pr_details = {
            "files": [
                {"path": "/src/file1.ts", "changeType": "edit"},
                {"path": "/src/file2.ts", "changeType": "add"},
            ],
            "threads": [],
        }

        # Patch the scripts directory location
        with patch("agentic_devtools.cli.azure_devops.review_commands.Path") as mock_path:
            # Make the path operations work with tmp_path
            mock_path.return_value.parent.parent.parent.parent.parent = tmp_path
            mock_path.return_value.__truediv__ = lambda self, x: tmp_path / x

            # Actually call the function but with simplified setup
            from agentic_devtools.cli.azure_devops.review_commands import generate_review_prompts

            # Minimal patching to avoid complex path issues
            with patch.object(
                __import__("agentic_devtools.cli.azure_devops.review_commands", fromlist=["get_state_dir"]),
                "get_state_dir",
                return_value=tmp_path,
            ):
                prompts_count, skipped_reviewed, skipped_not_on_branch, prompts_dir, skipped_files = (
                    generate_review_prompts(
                        pull_request_id=123,
                        pr_details=pr_details,
                        files_on_branch=None,
                    )
                )

        assert prompts_count == 2
        assert skipped_reviewed == 0
        assert skipped_not_on_branch == 0
        assert skipped_files == []

    def test_no_longer_skips_reviewed_files(self, tmp_path):
        """Test that previously-reviewed files are no longer skipped.

        All in-scope files are now reviewed every run regardless of prior review status.
        """
        from unittest.mock import patch

        from agentic_devtools.cli.azure_devops.review_commands import generate_review_prompts

        pr_details = {
            "files": [
                {"path": "/src/file1.ts", "changeType": "edit"},
            ],
            "threads": [],
            "reviewer": {
                "reviewedFiles": ["/src/file1.ts"],
            },
        }

        with patch.object(
            __import__("agentic_devtools.cli.azure_devops.review_commands", fromlist=["get_state_dir"]),
            "get_state_dir",
            return_value=tmp_path,
        ):
            prompts_count, skipped_reviewed, skipped_not_on_branch, _, skipped_files = generate_review_prompts(
                pull_request_id=123,
                pr_details=pr_details,
                files_on_branch=None,
            )

        # File is NOT skipped — all files are reviewed every run
        assert prompts_count == 1
        assert skipped_reviewed == 0
        assert skipped_files == []

    def test_skips_files_not_on_branch(self, tmp_path):
        """Test skips files not in the branch changes."""
        from unittest.mock import patch

        from agentic_devtools.cli.azure_devops.review_commands import generate_review_prompts

        pr_details = {
            "files": [
                {"path": "/src/file1.ts", "changeType": "edit"},
                {"path": "/src/file2.ts", "changeType": "edit"},
            ],
            "threads": [],
        }

        # Only file1.ts is actually on the branch
        files_on_branch = {"/src/file1.ts"}

        with patch.object(
            __import__("agentic_devtools.cli.azure_devops.review_commands", fromlist=["get_state_dir"]),
            "get_state_dir",
            return_value=tmp_path,
        ):
            prompts_count, skipped_reviewed, skipped_not_on_branch, _, skipped_files = generate_review_prompts(
                pull_request_id=123,
                pr_details=pr_details,
                files_on_branch=files_on_branch,
            )

        assert prompts_count == 1
        assert skipped_not_on_branch == 1
        assert len(skipped_files) == 1
        assert skipped_files[0].path == "/src/file2.ts"
        assert skipped_files[0].reason == "not_on_branch"

    def test_loads_pr_details_from_temp_file_when_none(self, tmp_path):
        """Test loads pr_details from temp file when None is passed.

        Covers lines 419-423.
        """
        import json
        from unittest.mock import patch

        from agentic_devtools.cli.azure_devops.review_commands import generate_review_prompts

        pr_details = {
            "files": [
                {"path": "/src/file1.ts", "changeType": "edit"},
            ],
            "threads": [],
        }

        # Write the temp file
        details_path = tmp_path / "temp-get-pull-request-details-response.json"
        with open(details_path, "w", encoding="utf-8") as f:
            json.dump(pr_details, f)

        with patch.object(
            __import__("agentic_devtools.cli.azure_devops.review_commands", fromlist=["get_state_dir"]),
            "get_state_dir",
            return_value=tmp_path,
        ):
            prompts_count, _, _, _, _ = generate_review_prompts(
                pull_request_id=123,
                pr_details=None,  # Force loading from file
                files_on_branch=None,
            )

        assert prompts_count == 1

    def test_loads_files_on_branch_from_json_when_none(self, tmp_path):
        """Test loads files_on_branch from files-on-branch.json when None.

        Covers lines 429-432.
        """
        import json
        from unittest.mock import patch

        from agentic_devtools.cli.azure_devops.review_commands import generate_review_prompts

        pr_details = {
            "files": [
                {"path": "/src/file1.ts", "changeType": "edit"},
                {"path": "/src/file2.ts", "changeType": "edit"},
            ],
            "threads": [],
        }

        # The function uses resolve_review_artifact_dir_name which, with
        # commit_hash_short=None, falls back to "PR{id}" (e.g. "PR123").
        prompts_dir = tmp_path / "pull-request-review" / "PR123"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        files_json = prompts_dir / "files-on-branch.json"
        with open(files_json, "w", encoding="utf-8") as f:
            json.dump({"files": ["/src/file1.ts"]}, f)

        with patch.object(
            __import__("agentic_devtools.cli.azure_devops.review_commands", fromlist=["get_state_dir"]),
            "get_state_dir",
            return_value=tmp_path,
        ):
            with patch(
                "agentic_devtools.cli.azure_devops.review_commands.get_value",
                return_value=None,
            ):
                prompts_count, _, skipped_not_on_branch, _, _ = generate_review_prompts(
                    pull_request_id=123,
                    pr_details=pr_details,
                    files_on_branch=None,  # Force loading from file
                )

        assert prompts_count == 1
        assert skipped_not_on_branch == 1

    def test_raises_when_pr_details_none_and_temp_file_missing(self, tmp_path):
        """Test raises FileNotFoundError when pr_details is None and temp file doesn't exist.

        Covers line 421.
        """
        from unittest.mock import patch

        import pytest

        from agentic_devtools.cli.azure_devops.review_commands import generate_review_prompts

        with patch.object(
            __import__("agentic_devtools.cli.azure_devops.review_commands", fromlist=["get_state_dir"]),
            "get_state_dir",
            return_value=tmp_path,
        ):
            with pytest.raises(FileNotFoundError, match="PR details file not found"):
                generate_review_prompts(
                    pull_request_id=999,
                    pr_details=None,
                    files_on_branch=None,
                )

    def test_inherited_path_uses_unchanged_file_prompt(self, tmp_path):
        """Test that files with PROCESSING_PATH_INHERITED use the simplified prompt.

        Covers line 506 — the _write_unchanged_file_prompt branch.
        """
        from unittest.mock import MagicMock, patch

        from agentic_devtools.cli.azure_devops.review_commands import generate_review_prompts
        from agentic_devtools.cli.azure_devops.review_state import (
            FileEntry,
            ReviewStatus,
        )

        pr_details = {
            "files": [
                {"path": "/src/app.ts", "changeType": "edit"},
            ],
            "threads": [],
        }

        # Create a mock prior review state with a completed entry for the file
        prior_entry = FileEntry(
            threadId=100,
            commentId=200,
            folder="src",
            fileName="app.ts",
            status=ReviewStatus.APPROVED.value,
            summary="Looks good.",
        )
        prior_state = MagicMock()
        prior_state.commitHash = "abc1234def5678"
        prior_state.files = {"/src/app.ts": prior_entry}

        with (
            patch.object(
                __import__("agentic_devtools.cli.azure_devops.review_commands", fromlist=["get_state_dir"]),
                "get_state_dir",
                return_value=tmp_path,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.review_state.load_review_state",
                return_value=prior_state,
            ),
        ):
            prompts_count, _, _, prompts_dir, _ = generate_review_prompts(
                pull_request_id=123,
                pr_details=pr_details,
                files_on_branch=None,
                unchanged_files={"/src/app.ts"},
            )

        assert prompts_count == 1
        # Verify the prompt uses the simplified unchanged content
        prompt_files = list(prompts_dir.glob("*.md"))
        assert len(prompt_files) == 1
        content = prompt_files[0].read_text()
        assert "no changes since last review" in content
