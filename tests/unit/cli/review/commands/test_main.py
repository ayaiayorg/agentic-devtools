"""Tests for main entry point."""

from unittest.mock import patch

from agentic_devtools.cli.review.commands import main


class TestMain:
    """Tests for main entry point."""

    @patch("agentic_devtools.cli.review.commands.run_dispatch")
    def test_dispatch_subcommand(self, mock_dispatch):
        """main dispatches to run_dispatch."""
        with patch("sys.argv", ["agdt-review", "dispatch", "--pr-id", "1", "--label", "ai-review"]):
            main()
        mock_dispatch.assert_called_once_with(pr_id=1, label="ai-review", config_path=None, dry_run=False)

    @patch("agentic_devtools.cli.review.commands.run_consolidate")
    def test_consolidate_subcommand(self, mock_consolidate):
        """main dispatches to run_consolidate."""
        with patch("sys.argv", ["agdt-review", "consolidate", "--pr-id", "42"]):
            main()
        mock_consolidate.assert_called_once_with(pr_id=42, model_id=None)

    @patch("agentic_devtools.cli.review.commands.run_config_get")
    def test_config_get_subcommand(self, mock_config_get):
        """main dispatches to run_config_get."""
        with patch("sys.argv", ["agdt-review", "config-get"]):
            main()
        mock_config_get.assert_called_once_with(config_path=None)

    @patch("agentic_devtools.cli.review.commands.run_config_validate")
    def test_config_validate_subcommand(self, mock_validate):
        """main dispatches to run_config_validate."""
        with patch("sys.argv", ["agdt-review", "config-validate"]):
            main()
        mock_validate.assert_called_once_with(config_path=None)

    @patch("agentic_devtools.cli.review.commands.run_status")
    def test_status_subcommand(self, mock_status):
        """main dispatches to run_status."""
        with patch("sys.argv", ["agdt-review", "status", "--pr-id", "99"]):
            main()
        mock_status.assert_called_once_with(pr_id=99)

    def test_no_subcommand_prints_help(self, capsys):
        """No subcommand prints help and exits 0."""
        with patch("sys.argv", ["agdt-review"]):
            with patch("sys.exit") as mock_exit:
                main()
                mock_exit.assert_called_once_with(0)
