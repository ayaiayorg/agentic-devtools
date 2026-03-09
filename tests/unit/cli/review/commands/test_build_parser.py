"""Tests for build_parser."""

from agentic_devtools.cli.review.commands import build_parser


class TestBuildParser:
    """Tests for build_parser."""

    def test_creates_parser(self):
        """Parser is created with correct program name."""
        parser = build_parser()
        assert parser.prog == "agdt-review"

    def test_subcommands_registered(self):
        """All subcommands are registered."""
        parser = build_parser()
        # Parse help to verify subcommands exist
        args = parser.parse_args(["dispatch", "--pr-id", "1", "--label", "x"])
        assert args.subcommand == "dispatch"
        assert args.pr_id == 1

    def test_config_get_subcommand(self):
        """config-get subcommand is available."""
        parser = build_parser()
        args = parser.parse_args(["config-get"])
        assert args.subcommand == "config-get"

    def test_config_validate_subcommand(self):
        """config-validate subcommand is available."""
        parser = build_parser()
        args = parser.parse_args(["config-validate"])
        assert args.subcommand == "config-validate"

    def test_status_subcommand(self):
        """status subcommand is available."""
        parser = build_parser()
        args = parser.parse_args(["status", "--pr-id", "42"])
        assert args.subcommand == "status"
        assert args.pr_id == 42

    def test_consolidate_subcommand(self):
        """consolidate subcommand is available."""
        parser = build_parser()
        args = parser.parse_args(["consolidate", "--pr-id", "99"])
        assert args.subcommand == "consolidate"
        assert args.pr_id == 99

    def test_dispatch_dry_run(self):
        """dispatch --dry-run flag is parsed."""
        parser = build_parser()
        args = parser.parse_args(["dispatch", "--pr-id", "1", "--label", "x", "--dry-run"])
        assert args.dry_run is True
