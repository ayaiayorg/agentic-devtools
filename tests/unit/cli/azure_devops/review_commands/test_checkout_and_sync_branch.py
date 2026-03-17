"""Tests for the review_commands module and helper functions."""


class TestCheckoutAndSyncBranch:
    """Tests for checkout_and_sync_branch function."""

    def test_success_returns_files_on_branch(self):
        """Test successful checkout and sync returns files."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.azure_devops.review_commands import checkout_and_sync_branch
        from agdt_ai_helpers.cli.git.operations import CheckoutResult, RebaseResult

        with patch("agdt_ai_helpers.cli.git.operations.checkout_branch") as mock_checkout:
            with patch("agdt_ai_helpers.cli.git.operations.fetch_branch") as mock_fetch_branch:
                with patch("agdt_ai_helpers.cli.git.operations.reset_branch_to_origin") as mock_reset:
                    with patch("agdt_ai_helpers.cli.git.operations.fetch_main") as mock_fetch:
                        with patch("agdt_ai_helpers.cli.git.operations.rebase_onto_main") as mock_rebase:
                            with patch("agdt_ai_helpers.cli.git.operations.get_files_changed_on_branch") as mock_files:
                                mock_checkout.return_value = CheckoutResult(CheckoutResult.SUCCESS)
                                mock_fetch_branch.return_value = True
                                mock_reset.return_value = True
                                mock_fetch.return_value = True
                                mock_rebase.return_value = RebaseResult(RebaseResult.SUCCESS)
                                mock_files.return_value = ["file1.ts", "file2.ts"]

                                success, error, files = checkout_and_sync_branch("feature/test")

                                assert success is True
                                assert error is None
                                assert files == {"file1.ts", "file2.ts"}

    def test_checkout_failure_returns_error(self):
        """Test checkout failure returns error message."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.azure_devops.review_commands import checkout_and_sync_branch
        from agdt_ai_helpers.cli.git.operations import CheckoutResult

        with patch("agdt_ai_helpers.cli.git.operations.checkout_branch") as mock_checkout:
            mock_checkout.return_value = CheckoutResult(
                CheckoutResult.UNCOMMITTED_CHANGES,
                "You have uncommitted changes",
            )

            success, error, files = checkout_and_sync_branch("feature/test")

            assert success is False
            assert error is not None
            assert "uncommitted" in error.lower() or "cannot checkout" in error.lower()
            # Files is empty set on failure, not None
            assert files == set()

    def test_rebase_conflict_still_returns_files(self):
        """Test rebase conflict still returns files (review can continue)."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.azure_devops.review_commands import checkout_and_sync_branch
        from agdt_ai_helpers.cli.git.operations import CheckoutResult, RebaseResult

        with patch("agdt_ai_helpers.cli.git.operations.checkout_branch") as mock_checkout:
            with patch("agdt_ai_helpers.cli.git.operations.fetch_branch") as mock_fetch_branch:
                with patch("agdt_ai_helpers.cli.git.operations.reset_branch_to_origin") as mock_reset:
                    with patch("agdt_ai_helpers.cli.git.operations.fetch_main") as mock_fetch:
                        with patch("agdt_ai_helpers.cli.git.operations.rebase_onto_main") as mock_rebase:
                            with patch("agdt_ai_helpers.cli.git.operations.get_files_changed_on_branch") as mock_files:
                                mock_checkout.return_value = CheckoutResult(CheckoutResult.SUCCESS)
                                mock_fetch_branch.return_value = True
                                mock_reset.return_value = True
                                mock_fetch.return_value = True
                                mock_rebase.return_value = RebaseResult(
                                    RebaseResult.CONFLICT,
                                    "Rebase had conflicts",
                                )
                                mock_files.return_value = ["file1.ts"]

                                success, error, files = checkout_and_sync_branch("feature/test")

                                # Success because we can still continue with review
                                assert success is True
                                assert error is None
                                assert files == {"file1.ts"}

    def test_fetch_failure_still_continues(self):
        """Test fetch_main failure doesn't block the workflow."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.azure_devops.review_commands import checkout_and_sync_branch
        from agdt_ai_helpers.cli.git.operations import CheckoutResult

        with patch("agdt_ai_helpers.cli.git.operations.checkout_branch") as mock_checkout:
            with patch("agdt_ai_helpers.cli.git.operations.fetch_branch") as mock_fetch_branch:
                with patch("agdt_ai_helpers.cli.git.operations.reset_branch_to_origin") as mock_reset:
                    with patch("agdt_ai_helpers.cli.git.operations.fetch_main") as mock_fetch:
                        with patch("agdt_ai_helpers.cli.git.operations.get_files_changed_on_branch") as mock_files:
                            mock_checkout.return_value = CheckoutResult(CheckoutResult.SUCCESS)
                            mock_fetch_branch.return_value = True
                            mock_reset.return_value = True
                            # fetch_main returns False on failure
                            mock_fetch.return_value = False
                            mock_files.return_value = ["file.ts"]

                            success, error, files = checkout_and_sync_branch("feature/test")

                            # Should still succeed
                            assert success is True
                            assert files == {"file.ts"}

    def test_fetch_source_branch_failure_returns_error(self):
        """Test fetch_branch failure for source branch returns error."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.azure_devops.review_commands import checkout_and_sync_branch
        from agdt_ai_helpers.cli.git.operations import CheckoutResult

        with patch("agdt_ai_helpers.cli.git.operations.checkout_branch") as mock_checkout:
            with patch("agdt_ai_helpers.cli.git.operations.fetch_branch") as mock_fetch_branch:
                mock_checkout.return_value = CheckoutResult(CheckoutResult.SUCCESS)
                mock_fetch_branch.return_value = False

                success, error, files = checkout_and_sync_branch("feature/test")

                assert success is False
                assert error is not None
                assert "fetch" in error.lower()
                assert "origin/feature/test" in error
                assert files == set()

    def test_reset_to_origin_failure_returns_error(self):
        """Test reset_branch_to_origin failure returns error."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.azure_devops.review_commands import checkout_and_sync_branch
        from agdt_ai_helpers.cli.git.operations import CheckoutResult

        with patch("agdt_ai_helpers.cli.git.operations.checkout_branch") as mock_checkout:
            with patch("agdt_ai_helpers.cli.git.operations.fetch_branch") as mock_fetch_branch:
                with patch("agdt_ai_helpers.cli.git.operations.reset_branch_to_origin") as mock_reset:
                    mock_checkout.return_value = CheckoutResult(CheckoutResult.SUCCESS)
                    mock_fetch_branch.return_value = True
                    mock_reset.return_value = False

                    success, error, files = checkout_and_sync_branch("feature/test")

                    assert success is False
                    assert error is not None
                    assert "reset" in error.lower()
                    assert "origin/feature/test" in error
                    assert files == set()

    def test_fetch_and_reset_called_before_fetch_main(self):
        """Test fetch_branch and reset_branch_to_origin are called before fetch_main."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.azure_devops.review_commands import checkout_and_sync_branch
        from agdt_ai_helpers.cli.git.operations import CheckoutResult, RebaseResult

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

        with patch("agdt_ai_helpers.cli.git.operations.checkout_branch") as mock_checkout:
            with patch("agdt_ai_helpers.cli.git.operations.fetch_branch", side_effect=track_fetch_branch):
                with patch("agdt_ai_helpers.cli.git.operations.reset_branch_to_origin", side_effect=track_reset):
                    with patch("agdt_ai_helpers.cli.git.operations.fetch_main", side_effect=track_fetch_main):
                        with patch("agdt_ai_helpers.cli.git.operations.rebase_onto_main") as mock_rebase:
                            with patch("agdt_ai_helpers.cli.git.operations.get_files_changed_on_branch") as mock_files:
                                mock_checkout.return_value = CheckoutResult(CheckoutResult.SUCCESS)
                                mock_rebase.return_value = RebaseResult(RebaseResult.SUCCESS)
                                mock_files.return_value = []

                                checkout_and_sync_branch("feature/test")

                                assert call_order == ["fetch_branch", "reset_branch_to_origin", "fetch_main"]

    def test_dry_run_passes_flag_to_all_operations(self):
        """Test dry_run flag is threaded through to all git operations."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.azure_devops.review_commands import checkout_and_sync_branch
        from agdt_ai_helpers.cli.git.operations import CheckoutResult, RebaseResult

        with patch("agdt_ai_helpers.cli.git.operations.checkout_branch") as mock_checkout:
            with patch("agdt_ai_helpers.cli.git.operations.fetch_branch") as mock_fetch_branch:
                with patch("agdt_ai_helpers.cli.git.operations.reset_branch_to_origin") as mock_reset:
                    with patch("agdt_ai_helpers.cli.git.operations.fetch_main") as mock_fetch_main:
                        with patch("agdt_ai_helpers.cli.git.operations.rebase_onto_main") as mock_rebase:
                            with patch("agdt_ai_helpers.cli.git.operations.get_files_changed_on_branch") as mock_files:
                                mock_checkout.return_value = CheckoutResult(CheckoutResult.SUCCESS)
                                mock_fetch_branch.return_value = True
                                mock_reset.return_value = True
                                mock_fetch_main.return_value = True
                                mock_rebase.return_value = RebaseResult(RebaseResult.SUCCESS)
                                mock_files.return_value = ["file.ts"]

                                success, error, files = checkout_and_sync_branch("feature/test", dry_run=True)

                                assert success is True
                                mock_checkout.assert_called_once_with("feature/test", dry_run=True)
                                mock_fetch_branch.assert_called_once_with("feature/test", dry_run=True)
                                mock_reset.assert_called_once_with("feature/test", dry_run=True)
                                mock_fetch_main.assert_called_once_with(dry_run=True)
                                mock_rebase.assert_called_once_with(dry_run=True)
