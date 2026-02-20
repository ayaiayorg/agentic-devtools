"""Tests for the review_commands module and helper functions."""





class TestCheckoutAndSyncBranch:
    """Tests for checkout_and_sync_branch function."""

    def test_success_returns_files_on_branch(self):
        """Test successful checkout and sync returns files."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.azure_devops.review_commands import checkout_and_sync_branch
        from agdt_ai_helpers.cli.git.operations import CheckoutResult, RebaseResult

        with patch("agdt_ai_helpers.cli.git.operations.checkout_branch") as mock_checkout:
            with patch("agdt_ai_helpers.cli.git.operations.fetch_main") as mock_fetch:
                with patch("agdt_ai_helpers.cli.git.operations.rebase_onto_main") as mock_rebase:
                    with patch("agdt_ai_helpers.cli.git.operations.get_files_changed_on_branch") as mock_get_files:
                        mock_checkout.return_value = CheckoutResult(CheckoutResult.SUCCESS)
                        mock_fetch.return_value = True
                        mock_rebase.return_value = RebaseResult(RebaseResult.SUCCESS)
                        mock_get_files.return_value = ["file1.ts", "file2.ts"]

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
            with patch("agdt_ai_helpers.cli.git.operations.fetch_main") as mock_fetch:
                with patch("agdt_ai_helpers.cli.git.operations.rebase_onto_main") as mock_rebase:
                    with patch("agdt_ai_helpers.cli.git.operations.get_files_changed_on_branch") as mock_get_files:
                        mock_checkout.return_value = CheckoutResult(CheckoutResult.SUCCESS)
                        mock_fetch.return_value = True
                        mock_rebase.return_value = RebaseResult(
                            RebaseResult.CONFLICT,
                            "Rebase had conflicts",
                        )
                        mock_get_files.return_value = ["file1.ts"]

                        success, error, files = checkout_and_sync_branch("feature/test")

                        # Success because we can still continue with review
                        assert success is True
                        assert error is None
                        assert files == {"file1.ts"}

    def test_fetch_failure_still_continues(self):
        """Test fetch failure doesn't block the workflow."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.azure_devops.review_commands import checkout_and_sync_branch
        from agdt_ai_helpers.cli.git.operations import CheckoutResult

        with patch("agdt_ai_helpers.cli.git.operations.checkout_branch") as mock_checkout:
            with patch("agdt_ai_helpers.cli.git.operations.fetch_main") as mock_fetch:
                with patch("agdt_ai_helpers.cli.git.operations.get_files_changed_on_branch") as mock_get_files:
                    mock_checkout.return_value = CheckoutResult(CheckoutResult.SUCCESS)
                    # fetch_main returns False on failure
                    mock_fetch.return_value = False
                    mock_get_files.return_value = ["file.ts"]

                    success, error, files = checkout_and_sync_branch("feature/test")

                    # Should still succeed
                    assert success is True
                    assert files == {"file.ts"}
