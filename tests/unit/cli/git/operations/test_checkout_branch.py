"""Tests for agentic_devtools.cli.git.operations.checkout_branch."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.git import core, operations


class TestCheckoutResult:
    """Tests for CheckoutResult class."""

    def test_success_result(self):
        """Test SUCCESS result properties."""
        result = operations.CheckoutResult(operations.CheckoutResult.SUCCESS)
        assert result.status == operations.CheckoutResult.SUCCESS
        assert result.is_success
        assert not result.needs_user_action
        assert result.message == ""

    def test_uncommitted_changes_result(self):
        """Test UNCOMMITTED_CHANGES result properties."""
        result = operations.CheckoutResult(operations.CheckoutResult.UNCOMMITTED_CHANGES, "uncommitted changes message")
        assert result.status == operations.CheckoutResult.UNCOMMITTED_CHANGES
        assert not result.is_success
        assert result.needs_user_action
        assert "uncommitted" in result.message.lower()

    def test_branch_not_found_result(self):
        """Test BRANCH_NOT_FOUND result properties."""
        result = operations.CheckoutResult(operations.CheckoutResult.BRANCH_NOT_FOUND, "Branch feature/test not found")
        assert result.status == operations.CheckoutResult.BRANCH_NOT_FOUND
        assert not result.is_success
        assert result.needs_user_action
        assert "feature/test" in result.message

    def test_error_result(self):
        """Test ERROR result properties."""
        result = operations.CheckoutResult(operations.CheckoutResult.ERROR, "Something went wrong")
        assert result.status == operations.CheckoutResult.ERROR
        assert not result.is_success
        assert not result.needs_user_action
        assert "Something went wrong" in result.message


class TestCheckoutBranch:
    """Tests for checkout_branch function."""

    def test_checkout_success(self, mock_run_safe):
        """Test successful checkout."""
        with patch.object(core, "get_current_branch", return_value="other-branch"):
            with patch.object(operations, "has_local_changes", return_value=False):
                with patch.object(operations, "run_git") as mock_run_git:
                    mock_run_git.return_value = MagicMock(returncode=0, stdout="", stderr="")

                    result = operations.checkout_branch("feature/test", dry_run=False)

                    assert result.is_success
                    mock_run_git.assert_called()

    def test_checkout_already_on_branch(self, mock_run_safe):
        """Test checkout when already on the branch."""
        with patch.object(core, "get_current_branch", return_value="feature/test"):
            result = operations.checkout_branch("feature/test", dry_run=False)

            assert result.is_success

    def test_checkout_dry_run(self, mock_run_safe, capsys):
        """Test dry run doesn't execute checkout."""
        with patch.object(core, "get_current_branch", return_value="other-branch"):
            result = operations.checkout_branch("feature/test", dry_run=True)

            assert result.is_success
            captured = capsys.readouterr()
            assert "[DRY RUN]" in captured.out
            assert "feature/test" in captured.out

    def test_checkout_uncommitted_changes(self, mock_run_safe):
        """Test checkout fails with uncommitted changes."""
        with patch.object(core, "get_current_branch", return_value="other-branch"):
            with patch.object(operations, "has_local_changes", return_value=True):
                result = operations.checkout_branch("feature/test", dry_run=False)

                assert not result.is_success
                assert result.status == operations.CheckoutResult.UNCOMMITTED_CHANGES

    def test_checkout_branch_not_found(self, mock_run_safe):
        """Test checkout fails when branch doesn't exist."""
        with patch.object(core, "get_current_branch", return_value="other-branch"):
            with patch.object(operations, "has_local_changes", return_value=False):
                with patch.object(operations, "run_git") as mock_run_git:
                    mock_run_git.return_value = MagicMock(
                        returncode=1,
                        stdout="",
                        stderr="error: pathspec 'feature/nonexistent' did not match any file(s) known to git",
                    )

                    result = operations.checkout_branch("feature/nonexistent", dry_run=False)

                    assert not result.is_success
                    assert result.status == operations.CheckoutResult.BRANCH_NOT_FOUND

    def test_checkout_generic_error(self, mock_run_safe):
        """Test checkout handles generic errors."""
        with patch.object(core, "get_current_branch", return_value="other-branch"):
            with patch.object(operations, "has_local_changes", return_value=False):
                with patch.object(operations, "run_git") as mock_run_git:
                    mock_run_git.return_value = MagicMock(
                        returncode=1,
                        stdout="",
                        stderr="fatal: some unexpected error",
                    )

                    result = operations.checkout_branch("feature/test", dry_run=False)

                    assert not result.is_success
                    assert result.status == operations.CheckoutResult.ERROR

    def test_checkout_from_detached_head(self, mock_run_safe):
        """Test checkout when starting from detached HEAD (get_current_branch raises SystemExit)."""
        with patch.object(core, "get_current_branch", side_effect=SystemExit(1)):
            with patch.object(operations, "has_local_changes", return_value=False):
                with patch.object(operations, "run_git") as mock_run_git:
                    mock_run_git.return_value = MagicMock(returncode=0, stdout="", stderr="")

                    result = operations.checkout_branch("feature/test", dry_run=False)

                    assert result.is_success
                    mock_run_git.assert_called()

    def test_checkout_from_origin_when_local_does_not_exist(self, mock_run_safe):
        """Test checkout creates local branch from origin when local doesn't exist."""
        with patch.object(core, "get_current_branch", return_value="main"):
            with patch.object(operations, "has_local_changes", return_value=False):
                with patch.object(operations, "run_git") as mock_run_git:
                    mock_run_git.side_effect = [
                        MagicMock(returncode=1, stdout="", stderr="did not match"),
                        MagicMock(returncode=0, stdout="", stderr=""),
                    ]

                    result = operations.checkout_branch("feature/new-branch", dry_run=False)

                    assert result.is_success
                    assert mock_run_git.call_count == 2
