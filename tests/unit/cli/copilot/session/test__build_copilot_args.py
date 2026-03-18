"""Tests for _build_copilot_args internal function."""

import warnings
from unittest.mock import patch

from agentic_devtools.cli.copilot import session as session_module
from agentic_devtools.cli.copilot.session import _build_copilot_args


class TestBuildCopilotArgsAutopilot:
    """Tests for the autopilot parameter in _build_copilot_args."""

    # ------------------------------------------------------------------
    # Standalone binary — interactive mode
    # ------------------------------------------------------------------

    def test_standalone_interactive_autopilot_true_includes_flag(self):
        """Standalone + interactive + autopilot=True → --autopilot before -i."""
        with patch.object(session_module, "_get_copilot_binary", return_value="/usr/bin/copilot"):
            result = _build_copilot_args("hello", interactive=True, autopilot=True)

        assert result is not None
        assert result[0] == "/usr/bin/copilot"
        assert "--autopilot" in result
        assert result.index("--autopilot") < result.index("-i")
        assert result[-1] == "hello"

    def test_standalone_interactive_autopilot_default_includes_flag(self):
        """Standalone + interactive + autopilot defaults to True → --autopilot included."""
        with patch.object(session_module, "_get_copilot_binary", return_value="/usr/bin/copilot"):
            result = _build_copilot_args("hello", interactive=True)

        assert result is not None
        assert "--autopilot" in result

    def test_standalone_interactive_autopilot_false_excludes_flag(self):
        """Standalone + interactive + autopilot=False → no --autopilot in args."""
        with patch.object(session_module, "_get_copilot_binary", return_value="/usr/bin/copilot"):
            result = _build_copilot_args("hello", interactive=True, autopilot=False)

        assert result is not None
        assert "--autopilot" not in result
        assert "-i" in result

    # ------------------------------------------------------------------
    # Standalone binary — non-interactive mode
    # ------------------------------------------------------------------

    def test_standalone_non_interactive_autopilot_true_excludes_flag(self):
        """Standalone + non-interactive + autopilot=True → no --autopilot (only --allow-all)."""
        with patch.object(session_module, "_get_copilot_binary", return_value="/usr/bin/copilot"):
            result = _build_copilot_args("hello", interactive=False, autopilot=True)

        assert result is not None
        assert "--autopilot" not in result
        assert "--allow-all" in result
        assert "-p" in result

    def test_standalone_non_interactive_autopilot_false_excludes_flag(self):
        """Standalone + non-interactive + autopilot=False → no --autopilot."""
        with patch.object(session_module, "_get_copilot_binary", return_value="/usr/bin/copilot"):
            result = _build_copilot_args("hello", interactive=False, autopilot=False)

        assert result is not None
        assert "--autopilot" not in result
        assert "--allow-all" in result

    # ------------------------------------------------------------------
    # Ordering: --autopilot before -i and before the prompt
    # ------------------------------------------------------------------

    def test_standalone_interactive_autopilot_ordering(self):
        """--autopilot appears immediately after binary, before -i and prompt."""
        with patch.object(session_module, "_get_copilot_binary", return_value="/usr/bin/copilot"):
            result = _build_copilot_args("my prompt", interactive=True, autopilot=True)

        assert result == ["/usr/bin/copilot", "--autopilot", "-i", "my prompt"]

    # ------------------------------------------------------------------
    # gh copilot fallback — interactive mode
    # ------------------------------------------------------------------

    def test_fallback_interactive_autopilot_true_emits_warning(self):
        """gh copilot fallback + interactive + autopilot=True → warning emitted."""
        with patch.object(session_module, "_get_copilot_binary", return_value=None):
            with patch.object(session_module.shutil, "which", return_value=None):
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")
                    result = _build_copilot_args("hello", interactive=True, autopilot=True)

        assert result == ["gh", "copilot", "suggest", "hello"]
        assert len(w) == 1
        assert "--autopilot" in str(w[0].message)
        assert "not supported" in str(w[0].message)

    def test_fallback_interactive_autopilot_false_no_warning(self):
        """gh copilot fallback + interactive + autopilot=False → no warning."""
        with patch.object(session_module, "_get_copilot_binary", return_value=None):
            with patch.object(session_module.shutil, "which", return_value=None):
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")
                    result = _build_copilot_args("hello", interactive=True, autopilot=False)

        assert result == ["gh", "copilot", "suggest", "hello"]
        assert len(w) == 0

    def test_fallback_non_interactive_autopilot_true_no_warning(self):
        """gh copilot fallback + non-interactive + autopilot=True → no warning."""
        with patch.object(session_module, "_get_copilot_binary", return_value=None):
            with patch.object(session_module.shutil, "which", return_value=None):
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")
                    result = _build_copilot_args("hello", interactive=False, autopilot=True)

        assert result == ["gh", "copilot", "suggest", "hello"]
        assert len(w) == 0
