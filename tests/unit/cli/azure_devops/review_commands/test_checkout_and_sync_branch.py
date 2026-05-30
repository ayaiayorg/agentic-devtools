"""Tests for the review_commands module and helper functions."""


class TestCheckoutAndSyncBranch:
    """Tests for checkout_and_sync_branch function."""

    def test_success_returns_files_on_branch(self):
        """Test successful checkout and sync returns files."""
        from unittest.mock import patch

        from agentic_devtools.cli.azure_devops.review_commands import checkout_and_sync_branch
        from agentic_devtools.cli.git.operations import CheckoutResult, RebaseResult

        with patch("agentic_devtools.cli.git.operations.checkout_branch") as mock_checkout:
            with patch("agentic_devtools.cli.git.operations.fetch_branch") as mock_fetch_branch:
                with patch("agentic_devtools.cli.git.operations.reset_branch_to_origin") as mock_reset:
                    with patch("agentic_devtools.cli.git.operations.fetch_main") as mock_fetch:
                        with patch("agentic_devtools.cli.git.operations.rebase_onto_main") as mock_rebase:
                            with patch("agentic_devtools.cli.git.operations.get_files_changed_on_branch") as mock_files:
                                with patch("agentic_devtools.cli.git.operations.force_push"):
                                    mock_checkout.return_value = CheckoutResult(CheckoutResult.SUCCESS)
                                    mock_fetch_branch.return_value = True
                                    mock_reset.return_value = True
                                    mock_fetch.return_value = True
                                    mock_rebase.return_value = RebaseResult(RebaseResult.SUCCESS)
                                    mock_files.return_value = ["file1.ts", "file2.ts"]

                                    success, error, files, had_conflicts, push_succeeded = checkout_and_sync_branch(
                                        "feature/test"
                                    )

                                    assert success is True
                                    assert error is None
                                    assert files == {"file1.ts", "file2.ts"}
                                    assert had_conflicts is False
                                    assert push_succeeded is True

    def test_checkout_failure_returns_error(self):
        """Test checkout failure returns error message."""
        from unittest.mock import patch

        from agentic_devtools.cli.azure_devops.review_commands import checkout_and_sync_branch
        from agentic_devtools.cli.git.operations import CheckoutResult

        with patch("agentic_devtools.cli.git.operations.checkout_branch") as mock_checkout:
            mock_checkout.return_value = CheckoutResult(
                CheckoutResult.UNCOMMITTED_CHANGES,
                "You have uncommitted changes",
            )

            success, error, files, had_conflicts, _push = checkout_and_sync_branch("feature/test")

            assert success is False
            assert error is not None
            assert "uncommitted" in error.lower() or "cannot checkout" in error.lower()
            # Files is empty set on failure, not None
            assert files == set()
            assert had_conflicts is False

    def test_rebase_conflict_still_returns_files(self):
        """Test rebase conflict still returns files (review can continue)."""
        from unittest.mock import patch

        from agentic_devtools.cli.azure_devops.review_commands import checkout_and_sync_branch
        from agentic_devtools.cli.git.operations import CheckoutResult, RebaseResult

        with patch("agentic_devtools.cli.git.operations.checkout_branch") as mock_checkout:
            with patch("agentic_devtools.cli.git.operations.fetch_branch") as mock_fetch_branch:
                with patch("agentic_devtools.cli.git.operations.reset_branch_to_origin") as mock_reset:
                    with patch("agentic_devtools.cli.git.operations.fetch_main") as mock_fetch:
                        with patch("agentic_devtools.cli.git.operations.rebase_onto_main") as mock_rebase:
                            with patch("agentic_devtools.cli.git.operations.get_files_changed_on_branch") as mock_files:
                                mock_checkout.return_value = CheckoutResult(CheckoutResult.SUCCESS)
                                mock_fetch_branch.return_value = True
                                mock_reset.return_value = True
                                mock_fetch.return_value = True
                                mock_rebase.return_value = RebaseResult(
                                    RebaseResult.CONFLICT,
                                    "Rebase had conflicts",
                                )
                                mock_files.return_value = ["file1.ts"]

                                success, error, files, had_conflicts, _push = checkout_and_sync_branch("feature/test")

                                # Success because we can still continue with review
                                assert success is True
                                assert error is None
                                assert files == {"file1.ts"}
                                assert had_conflicts is True

    def test_fetch_failure_still_continues(self):
        """Test fetch_main failure doesn't block the workflow."""
        from unittest.mock import patch

        from agentic_devtools.cli.azure_devops.review_commands import checkout_and_sync_branch
        from agentic_devtools.cli.git.operations import CheckoutResult

        with patch("agentic_devtools.cli.git.operations.checkout_branch") as mock_checkout:
            with patch("agentic_devtools.cli.git.operations.fetch_branch") as mock_fetch_branch:
                with patch("agentic_devtools.cli.git.operations.reset_branch_to_origin") as mock_reset:
                    with patch("agentic_devtools.cli.git.operations.fetch_main") as mock_fetch:
                        with patch("agentic_devtools.cli.git.operations.get_files_changed_on_branch") as mock_files:
                            mock_checkout.return_value = CheckoutResult(CheckoutResult.SUCCESS)
                            mock_fetch_branch.return_value = True
                            mock_reset.return_value = True
                            # fetch_main returns False on failure
                            mock_fetch.return_value = False
                            mock_files.return_value = ["file.ts"]

                            success, error, files, had_conflicts, _push = checkout_and_sync_branch("feature/test")

                            # Should still succeed
                            assert success is True
                            assert files == {"file.ts"}
                            assert had_conflicts is False

    def test_fetch_source_branch_failure_returns_error(self):
        """Test fetch_branch failure for source branch returns error."""
        from unittest.mock import patch

        from agentic_devtools.cli.azure_devops.review_commands import checkout_and_sync_branch
        from agentic_devtools.cli.git.operations import CheckoutResult

        with patch("agentic_devtools.cli.git.operations.checkout_branch") as mock_checkout:
            with patch("agentic_devtools.cli.git.operations.fetch_branch") as mock_fetch_branch:
                mock_checkout.return_value = CheckoutResult(CheckoutResult.SUCCESS)
                mock_fetch_branch.return_value = False

                success, error, files, had_conflicts, _push = checkout_and_sync_branch("feature/test")

                assert success is False
                assert error is not None
                assert "fetch" in error.lower()
                assert "origin/feature/test" in error
                assert files == set()
                assert had_conflicts is False

    def test_reset_to_origin_failure_returns_error(self):
        """Test reset_branch_to_origin failure returns error."""
        from unittest.mock import patch

        from agentic_devtools.cli.azure_devops.review_commands import checkout_and_sync_branch
        from agentic_devtools.cli.git.operations import CheckoutResult

        with patch("agentic_devtools.cli.git.operations.checkout_branch") as mock_checkout:
            with patch("agentic_devtools.cli.git.operations.fetch_branch") as mock_fetch_branch:
                with patch("agentic_devtools.cli.git.operations.reset_branch_to_origin") as mock_reset:
                    mock_checkout.return_value = CheckoutResult(CheckoutResult.SUCCESS)
                    mock_fetch_branch.return_value = True
                    mock_reset.return_value = False

                    success, error, files, had_conflicts, _push = checkout_and_sync_branch("feature/test")

                    assert success is False
                    assert error is not None
                    assert "reset" in error.lower()
                    assert "origin/feature/test" in error
                    assert files == set()
                    assert had_conflicts is False

    def test_fetch_and_reset_called_before_fetch_main(self):
        """Test fetch_branch and reset_branch_to_origin are called before fetch_main."""
        from unittest.mock import patch

        from agentic_devtools.cli.azure_devops.review_commands import checkout_and_sync_branch
        from agentic_devtools.cli.git.operations import CheckoutResult, RebaseResult

        call_order = []

        def track_fetch_branch(*args, **kwargs):
            call_order.append("fetch_branch")
            return True

        def track_reset(*args, **kwargs):
            call_order.append("reset_branch_to_origin")
            return True

        def track_fetch_main(*args, **kwargs):
            call_order.append("fetch_main")
            return True

        with patch("agentic_devtools.cli.git.operations.checkout_branch") as mock_checkout:
            with patch("agentic_devtools.cli.git.operations.fetch_branch", side_effect=track_fetch_branch):
                with patch("agentic_devtools.cli.git.operations.reset_branch_to_origin", side_effect=track_reset):
                    with patch("agentic_devtools.cli.git.operations.fetch_main", side_effect=track_fetch_main):
                        with patch("agentic_devtools.cli.git.operations.rebase_onto_main") as mock_rebase:
                            with patch("agentic_devtools.cli.git.operations.get_files_changed_on_branch") as mock_files:
                                with patch("agentic_devtools.cli.git.operations.force_push"):
                                    mock_checkout.return_value = CheckoutResult(CheckoutResult.SUCCESS)
                                    mock_rebase.return_value = RebaseResult(RebaseResult.SUCCESS)
                                    mock_files.return_value = []

                                    checkout_and_sync_branch("feature/test")

                                    assert call_order == ["fetch_branch", "reset_branch_to_origin", "fetch_main"]

    def test_dry_run_passes_flag_to_all_operations(self):
        """Test dry_run flag is threaded through to all git operations."""
        from unittest.mock import patch

        from agentic_devtools.cli.azure_devops.review_commands import checkout_and_sync_branch
        from agentic_devtools.cli.git.operations import CheckoutResult, RebaseResult

        with patch("agentic_devtools.cli.git.operations.checkout_branch") as mock_checkout:
            with patch("agentic_devtools.cli.git.operations.fetch_branch") as mock_fetch_branch:
                with patch("agentic_devtools.cli.git.operations.reset_branch_to_origin") as mock_reset:
                    with patch("agentic_devtools.cli.git.operations.fetch_main") as mock_fetch_main:
                        with patch("agentic_devtools.cli.git.operations.rebase_onto_main") as mock_rebase:
                            with patch("agentic_devtools.cli.git.operations.get_files_changed_on_branch") as mock_files:
                                with patch("agentic_devtools.cli.git.operations.force_push") as mock_force_push:
                                    mock_checkout.return_value = CheckoutResult(CheckoutResult.SUCCESS)
                                    mock_fetch_branch.return_value = True
                                    mock_reset.return_value = True
                                    mock_fetch_main.return_value = True
                                    mock_rebase.return_value = RebaseResult(RebaseResult.SUCCESS)
                                    mock_files.return_value = ["file.ts"]

                                    success, error, files, had_conflicts, push_succeeded = checkout_and_sync_branch(
                                        "feature/test", dry_run=True
                                    )

                                    assert success is True
                                    assert push_succeeded is None  # dry-run returns None
                                    mock_checkout.assert_called_once_with("feature/test", dry_run=True)
                                    mock_fetch_branch.assert_called_once_with("feature/test", dry_run=True)
                                    mock_reset.assert_called_once_with("feature/test", dry_run=True)
                                    mock_fetch_main.assert_called_once_with(dry_run=True)
                                    mock_rebase.assert_called_once_with(dry_run=True)
                                    mock_force_push.assert_called_once_with(dry_run=True)

    def test_no_push_when_no_rebase_needed(self):
        """Test no push occurs when already up-to-date (was_rebased=False)."""
        from unittest.mock import patch

        from agentic_devtools.cli.azure_devops.review_commands import checkout_and_sync_branch
        from agentic_devtools.cli.git.operations import CheckoutResult, RebaseResult

        with patch("agentic_devtools.cli.git.operations.checkout_branch") as mock_checkout:
            with patch("agentic_devtools.cli.git.operations.fetch_branch") as mock_fetch_branch:
                with patch("agentic_devtools.cli.git.operations.reset_branch_to_origin") as mock_reset:
                    with patch("agentic_devtools.cli.git.operations.fetch_main") as mock_fetch:
                        with patch("agentic_devtools.cli.git.operations.rebase_onto_main") as mock_rebase:
                            with patch("agentic_devtools.cli.git.operations.get_files_changed_on_branch") as mock_files:
                                with patch("agentic_devtools.cli.git.operations.force_push") as mock_force_push:
                                    mock_checkout.return_value = CheckoutResult(CheckoutResult.SUCCESS)
                                    mock_fetch_branch.return_value = True
                                    mock_reset.return_value = True
                                    mock_fetch.return_value = True
                                    mock_rebase.return_value = RebaseResult(RebaseResult.NO_REBASE_NEEDED)
                                    mock_files.return_value = ["file.ts"]

                                    success, error, files, had_conflicts, push_succeeded = checkout_and_sync_branch(
                                        "feature/test"
                                    )

                                    assert success is True
                                    assert push_succeeded is None
                                    mock_force_push.assert_not_called()

    def test_push_failure_returns_false_and_continues(self, capsys):
        """Test force push failure is non-blocking and returns push_succeeded=False."""
        from unittest.mock import patch

        from agentic_devtools.cli.azure_devops.review_commands import checkout_and_sync_branch
        from agentic_devtools.cli.git.operations import CheckoutResult, RebaseResult

        with patch("agentic_devtools.cli.git.operations.checkout_branch") as mock_checkout:
            with patch("agentic_devtools.cli.git.operations.fetch_branch") as mock_fetch_branch:
                with patch("agentic_devtools.cli.git.operations.reset_branch_to_origin") as mock_reset:
                    with patch("agentic_devtools.cli.git.operations.fetch_main") as mock_fetch:
                        with patch("agentic_devtools.cli.git.operations.rebase_onto_main") as mock_rebase:
                            with patch("agentic_devtools.cli.git.operations.get_files_changed_on_branch") as mock_files:
                                with patch(
                                    "agentic_devtools.cli.git.operations.force_push",
                                    side_effect=SystemExit(1),
                                ):
                                    mock_checkout.return_value = CheckoutResult(CheckoutResult.SUCCESS)
                                    mock_fetch_branch.return_value = True
                                    mock_reset.return_value = True
                                    mock_fetch.return_value = True
                                    mock_rebase.return_value = RebaseResult(RebaseResult.SUCCESS)
                                    mock_files.return_value = ["file.ts"]

                                    success, error, files, had_conflicts, push_succeeded = checkout_and_sync_branch(
                                        "feature/test"
                                    )

                                    assert success is True
                                    assert push_succeeded is False
                                    captured = capsys.readouterr()
                                    assert "push failed" in captured.out.lower()
                                    assert "git push --force-with-lease" in captured.out

    def test_rebase_error_prints_warning_and_continues(self):
        """Test rebase with ERROR status prints warning and continues.

        Covers lines 253-254: the else branch (not success, not conflict).
        """
        from unittest.mock import patch

        from agentic_devtools.cli.azure_devops.review_commands import checkout_and_sync_branch
        from agentic_devtools.cli.git.operations import CheckoutResult, RebaseResult

        with patch("agentic_devtools.cli.git.operations.checkout_branch") as mock_checkout:
            with patch("agentic_devtools.cli.git.operations.fetch_branch") as mock_fetch_branch:
                with patch("agentic_devtools.cli.git.operations.reset_branch_to_origin") as mock_reset:
                    with patch("agentic_devtools.cli.git.operations.fetch_main") as mock_fetch:
                        with patch("agentic_devtools.cli.git.operations.rebase_onto_main") as mock_rebase:
                            with patch("agentic_devtools.cli.git.operations.get_files_changed_on_branch") as mock_files:
                                mock_checkout.return_value = CheckoutResult(CheckoutResult.SUCCESS)
                                mock_fetch_branch.return_value = True
                                mock_reset.return_value = True
                                mock_fetch.return_value = True
                                mock_rebase.return_value = RebaseResult(
                                    RebaseResult.ERROR,
                                    "Unexpected rebase error",
                                )
                                mock_files.return_value = ["file1.ts"]

                                success, error, files, had_conflicts, push_succeeded = checkout_and_sync_branch(
                                    "feature/test"
                                )

                                assert success is True
                                assert error is None
                                assert files == {"file1.ts"}
                                assert had_conflicts is False
                                assert push_succeeded is None

    def test_save_files_on_branch_writes_json(self, tmp_path):
        """Test save_files_on_branch=True writes files-on-branch.json.

        Covers lines 264-272.
        """
        import json
        from unittest.mock import patch

        from agentic_devtools.cli.azure_devops.review_commands import checkout_and_sync_branch
        from agentic_devtools.cli.git.operations import CheckoutResult, RebaseResult

        with patch("agentic_devtools.cli.git.operations.checkout_branch") as mock_checkout:
            with patch("agentic_devtools.cli.git.operations.fetch_branch") as mock_fetch_branch:
                with patch("agentic_devtools.cli.git.operations.reset_branch_to_origin") as mock_reset:
                    with patch("agentic_devtools.cli.git.operations.fetch_main") as mock_fetch:
                        with patch("agentic_devtools.cli.git.operations.rebase_onto_main") as mock_rebase:
                            with patch("agentic_devtools.cli.git.operations.get_files_changed_on_branch") as mock_files:
                                with patch(
                                    "agentic_devtools.cli.azure_devops.review_commands.get_value",
                                    return_value="abc123def456",
                                ):
                                    with patch(
                                        "agentic_devtools.cli.azure_devops.review_commands.get_state_dir",
                                        return_value=tmp_path,
                                    ):
                                        mock_checkout.return_value = CheckoutResult(CheckoutResult.SUCCESS)
                                        mock_fetch_branch.return_value = True
                                        mock_reset.return_value = True
                                        mock_fetch.return_value = True
                                        mock_rebase.return_value = RebaseResult(RebaseResult.NO_REBASE_NEEDED)
                                        mock_files.return_value = ["src/a.ts", "src/b.ts"]

                                        success, _error, files, _conflicts, _push = checkout_and_sync_branch(
                                            "feature/test",
                                            pull_request_id=123,
                                            save_files_on_branch=True,
                                        )

                                        assert success is True
                                        assert files == {"src/a.ts", "src/b.ts"}

                                        files_json = (
                                            tmp_path / "pull-request-review" / "abc123def456" / "files-on-branch.json"
                                        )
                                        assert files_json.exists()
                                        with open(files_json) as f:
                                            data = json.load(f)
                                        assert set(data["files"]) == {"src/a.ts", "src/b.ts"}
