"""Tests for the module-level ``_VALID_ISSUE_ADAPTERS`` ImportError fallback."""

import builtins
import importlib
import sys
from unittest.mock import patch


class TestValidIssueAdaptersFallback:
    """Cover the ``except ImportError`` branch at module scope (lines 31-32)."""

    def test_fallback_when_config_import_fails(self):
        """``_VALID_ISSUE_ADAPTERS`` falls back to the hardcoded frozenset
        when ``agentic_devtools.config`` cannot be imported."""
        # Remove the cached module so re-import triggers the try/except
        saved = {}
        for key in list(sys.modules):
            if key == "agentic_devtools.cli.setup.commands" or key.startswith("agentic_devtools.cli.setup.commands."):
                saved[key] = sys.modules.pop(key)

        original_import = builtins.__import__

        def _blocking_import(name, *args, **kwargs):
            if name == "agentic_devtools.config":
                raise ImportError("simulated: config not available")
            return original_import(name, *args, **kwargs)

        try:
            with patch("builtins.__import__", side_effect=_blocking_import):
                mod = importlib.import_module("agentic_devtools.cli.setup.commands")

            assert mod._VALID_ISSUE_ADAPTERS == frozenset({"jira", "github", "markdown"})
        finally:
            # Restore the original module to avoid polluting other tests
            sys.modules.pop("agentic_devtools.cli.setup.commands", None)
            sys.modules.update(saved)
            # Force a clean re-import so subsequent tests get the real module
            importlib.import_module("agentic_devtools.cli.setup.commands")
