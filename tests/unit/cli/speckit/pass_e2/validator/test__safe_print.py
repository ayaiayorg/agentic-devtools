"""Tests for pass_e2.validator — _safe_print."""

import sys
from unittest.mock import patch

from agentic_devtools.cli.speckit.pass_e2.validator import _safe_print


class TestSafePrint:
    """Verify _safe_print handles UnicodeEncodeError gracefully."""

    def test_normal_text_prints_directly(self, capsys) -> None:
        """Regular ASCII text passes through print() normally."""
        _safe_print("Hello, world!")
        assert capsys.readouterr().out == "Hello, world!\n"

    def test_unicode_encode_error_falls_back(self, capsys) -> None:
        """When print() raises UnicodeEncodeError, the fallback path
        replaces known emoji characters and encodes with errors='replace'.
        """
        call_count = {"n": 0}
        original_print = print

        def mock_print(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise UnicodeEncodeError("cp1252", "text", 0, 1, "character maps to <undefined>")
            original_print(*args, **kwargs)

        with patch("builtins.print", side_effect=mock_print):
            _safe_print("\u26a0 Warning: check \u2705 passed \u2192 done")

        # The fallback handler was triggered (first call raised, second succeeded)
        assert call_count["n"] == 2

    def test_unicode_replacements_applied(self) -> None:
        """Known Unicode chars are replaced with ASCII equivalents."""
        call_count = {"n": 0}
        captured_output = {}

        def mock_print(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise UnicodeEncodeError("cp1252", "text", 0, 1, "character maps to <undefined>")
            # Capture the fallback output
            captured_output["text"] = args[0] if args else ""

        with patch("builtins.print", side_effect=mock_print):
            with patch.object(sys, "stdout") as mock_stdout:
                mock_stdout.encoding = "utf-8"
                _safe_print("\u26a0 Warning \u2705 OK \u2192 next")

        text = captured_output["text"]
        assert "[!]" in text
        assert "[OK]" in text
        assert "->" in text
