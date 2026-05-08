"""Tests for --foreground flag in root entry point."""

from agentic_devtools.cli.setup.script_generators.root_entry_point import generate_root_entry_point


class TestForegroundFlag:
    """Tests for --foreground flag propagation."""

    def test_foreground_flag_in_argparser(self):
        """Script includes --foreground in argument parser."""
        script = generate_root_entry_point()
        assert "--foreground" in script
        assert 'action="store_true"' in script

    def test_foreground_propagated_to_subprocess(self):
        """Script propagates --foreground to subprocess calls."""
        script = generate_root_entry_point()
        assert "foreground_args" in script
