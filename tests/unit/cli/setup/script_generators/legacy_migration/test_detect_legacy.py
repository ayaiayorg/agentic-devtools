"""Tests for detect_legacy_script."""

from agentic_devtools.cli.setup.script_generators.constants import ORCHESTRATOR_MARKER
from agentic_devtools.cli.setup.script_generators.legacy_migration import detect_legacy_script


class TestDetectLegacy:
    """Tests for detect_legacy_script."""

    def test_no_file(self, tmp_path):
        """Returns False when file does not exist."""
        assert detect_legacy_script(tmp_path / "setup-dev-tools.py") is False

    def test_file_with_marker(self, tmp_path):
        """Returns False when file contains the marker."""
        f = tmp_path / "setup-dev-tools.py"
        f.write_text(f"#!/usr/bin/env python3\n{ORCHESTRATOR_MARKER}\n", encoding="utf-8")
        assert detect_legacy_script(f) is False

    def test_file_without_marker(self, tmp_path):
        """Returns True when file exists but lacks the marker."""
        f = tmp_path / "setup-dev-tools.py"
        f.write_text("#!/usr/bin/env python3\nprint('legacy')\n", encoding="utf-8")
        assert detect_legacy_script(f) is True

    def test_empty_file(self, tmp_path):
        """Returns True for empty file (no marker)."""
        f = tmp_path / "setup-dev-tools.py"
        f.write_text("", encoding="utf-8")
        assert detect_legacy_script(f) is True
