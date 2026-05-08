"""Tests for cross-platform path usage in generated scripts."""

from agentic_devtools.cli.setup.script_generators.complete_setup import generate_complete_setup_script
from agentic_devtools.cli.setup.script_generators.required_setup import generate_required_setup_script
from agentic_devtools.cli.setup.script_generators.root_entry_point import generate_root_entry_point


class TestCrossPlatform:
    """Generated scripts use pathlib.Path for cross-platform paths."""

    def test_required_setup_uses_pathlib(self):
        script = generate_required_setup_script()
        assert "from pathlib import Path" in script

    def test_complete_setup_uses_pathlib(self):
        script = generate_complete_setup_script()
        assert "from pathlib import Path" in script

    def test_root_entry_point_uses_pathlib(self):
        script = generate_root_entry_point()
        assert "from pathlib import Path" in script
