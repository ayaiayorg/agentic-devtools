"""Tests for .github/scripts/speckit-trigger/copilot_generate.py.

Validates that the Copilot SDK wrapper script uses the correct API
contract for ``CopilotClient.create_session()`` (keyword-only arguments,
no positional dict).
"""

import ast
import importlib.util
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

SCRIPT_PATH = Path(__file__).resolve().parent.parent / ".github" / "scripts" / "speckit-trigger" / "copilot_generate.py"


# ---------------------------------------------------------------------------
# AST-level: verify create_session is called with keyword args only
# ---------------------------------------------------------------------------


class TestCreateSessionCallSite:
    """Verify that create_session uses keyword arguments, not a positional dict."""

    def test_create_session_has_no_positional_args(self):
        source = SCRIPT_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(SCRIPT_PATH))

        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "create_session"
        ]
        assert calls, "Expected at least one create_session() call in the script"

        for call in calls:
            assert call.args == [], (
                f"create_session() at line {call.lineno} must not have positional "
                f"arguments (found {len(call.args)}); use keyword arguments instead."
            )

    def test_create_session_passes_required_keywords(self):
        source = SCRIPT_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(SCRIPT_PATH))

        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "create_session"
        ]
        assert calls

        kw_names = {kw.arg for kw in calls[0].keywords}
        assert "model" in kw_names, "create_session() must pass 'model' as a keyword arg"
        assert "on_permission_request" in kw_names, (
            "create_session() must pass 'on_permission_request' as a keyword arg"
        )


# ---------------------------------------------------------------------------
# Runtime-level: load the script module and exercise main() with mocks
# ---------------------------------------------------------------------------


def _load_module():
    """Dynamically import copilot_generate.py as a module."""
    spec = importlib.util.spec_from_file_location("copilot_generate", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {SCRIPT_PATH!s}")
    module = importlib.util.module_from_spec(spec)
    return module, spec


class TestMainFunction:
    """Exercise copilot_generate.main() with mocked Copilot SDK objects."""

    @pytest.fixture(autouse=True)
    def _mock_copilot_sdk(self):
        """Provide a fake ``copilot`` top-level package so the script can be imported."""
        fake_copilot = MagicMock()
        # PermissionHandler.approve_all needs to be a callable sentinel
        fake_copilot.PermissionHandler.approve_all = MagicMock(name="approve_all")
        with patch.dict(sys.modules, {"copilot": fake_copilot}):
            yield fake_copilot

    def test_empty_stdin_returns_1(self, _mock_copilot_sdk):
        module, spec = _load_module()
        spec.loader.exec_module(module)

        import asyncio

        with patch("sys.stdin", MagicMock(read=MagicMock(return_value=""))):
            result = asyncio.run(module.main())
        assert result == 1

    def test_missing_token_returns_1(self, _mock_copilot_sdk):
        module, spec = _load_module()
        spec.loader.exec_module(module)

        import asyncio

        with (
            patch("sys.stdin", MagicMock(read=MagicMock(return_value="some prompt"))),
            patch.dict("os.environ", {"COPILOT_GITHUB_TOKEN": ""}, clear=False),
        ):
            result = asyncio.run(module.main())
        assert result == 1

    def test_create_session_called_with_keyword_args(self, _mock_copilot_sdk):
        """Verify that the actual runtime call passes keyword args, not a dict."""
        module, spec = _load_module()
        spec.loader.exec_module(module)

        import asyncio

        mock_session = AsyncMock()
        mock_session.on = MagicMock()
        mock_session.disconnect = AsyncMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.start = AsyncMock()
        mock_client_instance.stop = AsyncMock()
        mock_client_instance.create_session = AsyncMock(return_value=mock_session)

        # Simulate session.idle event to unblock done.wait()
        def fake_on(callback):
            class FakeEvent:
                class event_type:
                    value = "session.idle"

                type = event_type
                data = None

            callback(FakeEvent())

        mock_session.on = fake_on
        mock_session.send = AsyncMock()

        _mock_copilot_sdk.CopilotClient.return_value = mock_client_instance

        with (
            patch("sys.stdin", MagicMock(read=MagicMock(return_value="test prompt"))),
            patch.dict(
                "os.environ",
                {"COPILOT_GITHUB_TOKEN": "fake-token", "COPILOT_MODEL": "test-model"},
                clear=False,
            ),
        ):
            asyncio.run(module.main())

        # Verify create_session was called with keyword arguments
        mock_client_instance.create_session.assert_called_once()
        call_kwargs = mock_client_instance.create_session.call_args
        # Should have no positional args (beyond self which is implicit)
        assert call_kwargs.args == (), "create_session should not receive positional arguments"
        # Should have keyword args
        assert "model" in call_kwargs.kwargs
        assert call_kwargs.kwargs["model"] == "test-model"
        assert "on_permission_request" in call_kwargs.kwargs
