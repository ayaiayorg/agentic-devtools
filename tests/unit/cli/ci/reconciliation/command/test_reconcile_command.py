"""Tests for reconcile_command() CLI entry point."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.ci.reconciliation.command import _create_provider, reconcile_command
from agentic_devtools.cli.ci.reconciliation.models import (
    ReconciliationAction,
    ReconciliationResult,
)


class TestReconcileCommand:
    """Tests for reconcile_command() CLI entry point."""

    @patch("agentic_devtools.cli.ci.reconciliation.command.reconcile")
    @patch("agentic_devtools.cli.ci.reconciliation.command._create_provider")
    def test_successful_no_action(self, mock_create, mock_reconcile) -> None:
        """Returns 0 when reconcile reports no action."""
        mock_provider = MagicMock()
        mock_create.return_value = mock_provider
        mock_reconcile.return_value = ReconciliationResult(
            action=ReconciliationAction.NO_ACTION,
            message="No retriable runs found.",
        )

        exit_code = reconcile_command(["--workflow-id", "ci.yml"])

        assert exit_code == 0
        mock_create.assert_called_once_with("github", "")

    @patch("agentic_devtools.cli.ci.reconciliation.command.reconcile")
    @patch("agentic_devtools.cli.ci.reconciliation.command._create_provider")
    def test_escalation_returns_2(self, mock_create, mock_reconcile) -> None:
        """Returns 2 when reconcile escalates."""
        mock_create.return_value = MagicMock()
        mock_reconcile.return_value = ReconciliationResult(
            action=ReconciliationAction.ESCALATED,
            message="Escalated.",
        )

        exit_code = reconcile_command(["--workflow-id", "ci.yml"])

        assert exit_code == 2

    @patch("agentic_devtools.cli.ci.reconciliation.command.reconcile")
    @patch("agentic_devtools.cli.ci.reconciliation.command._create_provider")
    def test_not_implemented_returns_1(self, mock_create, mock_reconcile) -> None:
        """Returns 1 when provider raises NotImplementedError."""
        mock_create.return_value = MagicMock()
        mock_reconcile.side_effect = NotImplementedError("not supported")

        exit_code = reconcile_command(["--workflow-id", "ci.yml", "--provider", "ado"])

        assert exit_code == 1

    @patch("agentic_devtools.cli.ci.reconciliation.command.reconcile")
    @patch("agentic_devtools.cli.ci.reconciliation.command._create_provider")
    def test_json_output(self, mock_create, mock_reconcile, capsys) -> None:
        """--json-output flag produces JSON output."""
        import json

        mock_create.return_value = MagicMock()
        mock_reconcile.return_value = ReconciliationResult(
            action=ReconciliationAction.NO_ACTION,
            message="Nothing to do.",
        )

        reconcile_command(["--workflow-id", "ci.yml", "--json-output"])

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["action"] == "no_action"
        assert output["message"] == "Nothing to do."

    @patch("agentic_devtools.cli.ci.reconciliation.command.reconcile")
    @patch("agentic_devtools.cli.ci.reconciliation.command._create_provider")
    def test_custom_params_passed_to_reconcile(self, mock_create, mock_reconcile) -> None:
        """--max-attempts and --window-hours are passed to reconcile."""
        mock_create.return_value = MagicMock()
        mock_reconcile.return_value = ReconciliationResult(
            action=ReconciliationAction.NO_ACTION,
            message="Done.",
        )

        reconcile_command(
            [
                "--workflow-id",
                "speckit.yml",
                "--max-attempts",
                "5",
                "--window-hours",
                "48",
                "--repo",
                "org/repo",
            ]
        )

        mock_reconcile.assert_called_once()
        call_kwargs = mock_reconcile.call_args[1]
        assert call_kwargs["max_run_attempts"] == 5
        assert call_kwargs["window_hours"] == 48

    @patch("agentic_devtools.cli.ci.reconciliation.command.reconcile")
    @patch("agentic_devtools.cli.ci.reconciliation.command._create_provider")
    def test_verbose_flag_sets_debug_logging(self, mock_create, mock_reconcile) -> None:
        """--verbose flag sets logging to DEBUG level."""
        mock_create.return_value = MagicMock()
        mock_reconcile.return_value = ReconciliationResult(
            action=ReconciliationAction.NO_ACTION,
            message="Done.",
        )

        exit_code = reconcile_command(["--workflow-id", "ci.yml", "--verbose"])

        assert exit_code == 0

    @patch("agentic_devtools.cli.ci.reconciliation.command.reconcile")
    @patch("agentic_devtools.cli.ci.reconciliation.command._create_provider")
    def test_runtime_error_returns_1(self, mock_create, mock_reconcile) -> None:
        """Returns 1 when reconcile raises RuntimeError."""
        mock_create.return_value = MagicMock()
        mock_reconcile.side_effect = RuntimeError("API failure")

        exit_code = reconcile_command(["--workflow-id", "ci.yml"])

        assert exit_code == 1

    @patch("agentic_devtools.cli.ci.reconciliation.command.reconcile")
    @patch("agentic_devtools.cli.ci.reconciliation.command._create_provider")
    def test_unexpected_exception_returns_1(self, mock_create, mock_reconcile) -> None:
        """Returns 1 for unexpected exceptions not caught by RuntimeError/NotImplementedError."""
        mock_create.return_value = MagicMock()
        mock_reconcile.side_effect = ValueError("unexpected config error")

        exit_code = reconcile_command(["--workflow-id", "ci.yml"])

        assert exit_code == 1


class TestPositiveInt:
    """Tests for _positive_int argparse type helper."""

    def test_valid_positive_integer(self) -> None:
        """Positive integer string is parsed correctly."""
        from agentic_devtools.cli.ci.reconciliation.command import _positive_int

        assert _positive_int("5") == 5

    def test_zero_raises_argument_type_error(self) -> None:
        """Zero raises ArgumentTypeError."""
        import argparse

        from agentic_devtools.cli.ci.reconciliation.command import _positive_int

        with pytest.raises(argparse.ArgumentTypeError, match="must be >= 1"):
            _positive_int("0")

    def test_negative_raises_argument_type_error(self) -> None:
        """Negative integer raises ArgumentTypeError."""
        import argparse

        from agentic_devtools.cli.ci.reconciliation.command import _positive_int

        with pytest.raises(argparse.ArgumentTypeError, match="must be >= 1"):
            _positive_int("-3")

    def test_non_integer_string_raises(self) -> None:
        """Non-integer string raises ArgumentTypeError."""
        import argparse

        from agentic_devtools.cli.ci.reconciliation.command import _positive_int

        with pytest.raises(argparse.ArgumentTypeError, match="not a valid integer"):
            _positive_int("abc")


class TestCreateProvider:
    """Tests for _create_provider helper."""

    @patch("agentic_devtools.cli.ci.github_provider.GitHubActionsProvider.__init__", return_value=None)
    def test_github_provider(self, mock_init) -> None:
        """Creates a GitHubActionsProvider for 'github'."""
        from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider

        provider = _create_provider("github", "org/repo")
        assert isinstance(provider, GitHubActionsProvider)

    @patch("agentic_devtools.cli.ci.ado_provider.AzureDevOpsProvider.__init__", return_value=None)
    def test_ado_provider(self, mock_init) -> None:
        """Creates an AzureDevOpsProvider for 'ado'."""
        from agentic_devtools.cli.ci.ado_provider import AzureDevOpsProvider

        provider = _create_provider("ado", "")
        assert isinstance(provider, AzureDevOpsProvider)

    def test_unknown_provider_raises(self) -> None:
        """Raises ValueError for unknown provider name."""
        with pytest.raises(ValueError, match="Unknown provider"):
            _create_provider("unknown", "")
