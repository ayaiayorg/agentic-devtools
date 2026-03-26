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

SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent.parent / ".github" / "scripts" / "speckit-trigger" / "copilot_generate.py"
)


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
        assert calls, "Expected at least one create_session() call in the script"

        for call in calls:
            kw_names = {kw.arg for kw in call.keywords}
            assert "model" in kw_names, f"create_session() at line {call.lineno} must pass 'model' as a keyword arg"
            assert "on_permission_request" in kw_names, (
                f"create_session() at line {call.lineno} must pass 'on_permission_request' as a keyword arg"
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

    def _make_mock_session_and_client(self, _mock_copilot_sdk, events):
        """Create a mock session/client pair that fires the given events in order.

        Each entry in *events* is a ``(event_type_str, data)`` tuple.
        Events are delivered from the ``send()`` side-effect (not during
        ``on()`` registration) to mirror the real Copilot SDK ordering.
        """
        mock_session = AsyncMock()
        mock_session.disconnect = AsyncMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.start = AsyncMock()
        mock_client_instance.stop = AsyncMock()
        mock_client_instance.create_session = AsyncMock(return_value=mock_session)

        # Store the callback registered via on(); fire events from send().
        _callback = None

        def fake_on(callback):
            nonlocal _callback
            _callback = callback

        async def fake_send(_prompt):
            assert _callback is not None, "on() must be called before send()"
            for event_type_str, data in events:

                class _Type:
                    value = event_type_str

                class _Event:
                    type = _Type

                _Event.data = data
                _callback(_Event())

        mock_session.on = fake_on
        mock_session.send = fake_send

        _mock_copilot_sdk.CopilotClient.return_value = mock_client_instance
        return mock_session, mock_client_instance

    def test_create_session_called_with_keyword_args(self, _mock_copilot_sdk):
        """Verify that the actual runtime call passes keyword args, not a dict."""
        module, spec = _load_module()
        spec.loader.exec_module(module)

        import asyncio

        # Simulate assistant.message + session.idle so main() returns 0
        msg_data = MagicMock()
        msg_data.content = "generated spec"
        events = [("assistant.message", msg_data), ("session.idle", None)]
        _mock_session, mock_client_instance = self._make_mock_session_and_client(_mock_copilot_sdk, events)

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
        assert call_kwargs.kwargs["on_permission_request"] is _mock_copilot_sdk.PermissionHandler.approve_all
        assert call_kwargs.kwargs["infinite_sessions"] == {"enabled": False}

    def test_successful_response_returns_0(self, _mock_copilot_sdk):
        """A valid assistant.message followed by session.idle returns 0."""
        module, spec = _load_module()
        spec.loader.exec_module(module)

        import asyncio

        msg_data = MagicMock()
        msg_data.content = "spec content"
        events = [("assistant.message", msg_data), ("session.idle", None)]
        self._make_mock_session_and_client(_mock_copilot_sdk, events)

        with (
            patch("sys.stdin", MagicMock(read=MagicMock(return_value="prompt"))),
            patch.dict(
                "os.environ",
                {"COPILOT_GITHUB_TOKEN": "fake-token"},
                clear=False,
            ),
        ):
            result = asyncio.run(module.main())
        assert result == 0

    def test_empty_response_returns_1(self, _mock_copilot_sdk):
        """session.idle without assistant.message returns 1 (empty response)."""
        module, spec = _load_module()
        spec.loader.exec_module(module)

        import asyncio

        events = [("session.idle", None)]
        self._make_mock_session_and_client(_mock_copilot_sdk, events)

        with (
            patch("sys.stdin", MagicMock(read=MagicMock(return_value="prompt"))),
            patch.dict(
                "os.environ",
                {"COPILOT_GITHUB_TOKEN": "fake-token"},
                clear=False,
            ),
        ):
            result = asyncio.run(module.main())
        assert result == 1

    def test_error_event_returns_1(self, _mock_copilot_sdk):
        """An error event causes main() to return 1."""
        module, spec = _load_module()
        spec.loader.exec_module(module)

        import asyncio

        err_data = MagicMock()
        err_data.message = "authentication failed"
        events = [("error", err_data)]
        self._make_mock_session_and_client(_mock_copilot_sdk, events)

        with (
            patch("sys.stdin", MagicMock(read=MagicMock(return_value="prompt"))),
            patch.dict(
                "os.environ",
                {"COPILOT_GITHUB_TOKEN": "fake-token"},
                clear=False,
            ),
        ):
            result = asyncio.run(module.main())
        assert result == 1

    def test_uses_last_assistant_message(self, _mock_copilot_sdk):
        """When multiple assistant.message events arrive, the last one is used."""
        module, spec = _load_module()
        spec.loader.exec_module(module)

        import asyncio
        import io

        msg1 = MagicMock()
        msg1.content = "first draft"
        msg2 = MagicMock()
        msg2.content = "final version"
        events = [
            ("assistant.message", msg1),
            ("assistant.message", msg2),
            ("session.idle", None),
        ]
        self._make_mock_session_and_client(_mock_copilot_sdk, events)

        stdout_buf = io.StringIO()
        with (
            patch("sys.stdin", MagicMock(read=MagicMock(return_value="prompt"))),
            patch("sys.stdout", stdout_buf),
            patch.dict(
                "os.environ",
                {"COPILOT_GITHUB_TOKEN": "fake-token"},
                clear=False,
            ),
        ):
            result = asyncio.run(module.main())
        assert result == 0
        assert stdout_buf.getvalue() == "final version"

    def test_custom_timeout_is_applied(self, _mock_copilot_sdk):
        """A valid COPILOT_TIMEOUT value is passed to asyncio.wait_for and shown in timeout errors."""
        module, spec = _load_module()
        spec.loader.exec_module(module)

        import asyncio
        import io

        # Use events that never set done, so we hit the timeout path
        events = []
        self._make_mock_session_and_client(_mock_copilot_sdk, events)

        stderr_buf = io.StringIO()
        with (
            patch("sys.stdin", MagicMock(read=MagicMock(return_value="prompt"))),
            patch("sys.stderr", stderr_buf),
            patch.dict(
                "os.environ",
                {"COPILOT_GITHUB_TOKEN": "fake-token", "COPILOT_TIMEOUT": "42"},
                clear=False,
            ),
            # Patch wait_for to immediately raise TimeoutError and capture the timeout arg
            patch("asyncio.wait_for", side_effect=asyncio.TimeoutError) as mock_wait_for,
        ):
            result = asyncio.run(module.main())

        assert result == 1
        # Verify the custom timeout value was passed to asyncio.wait_for
        mock_wait_for.assert_called_once()
        _args, kwargs = mock_wait_for.call_args
        assert kwargs.get("timeout") == 42 or (len(_args) >= 2 and _args[1] == 42), (
            f"Expected timeout=42 in asyncio.wait_for call, got args={_args}, kwargs={kwargs}"
        )
        # Verify the error message reflects the custom value
        assert "42s" in stderr_buf.getvalue()

    def test_invalid_timeout_returns_1(self, _mock_copilot_sdk):
        """A non-integer COPILOT_TIMEOUT returns 1 with an error message."""
        module, spec = _load_module()
        spec.loader.exec_module(module)

        import asyncio
        import io

        stderr_buf = io.StringIO()
        with (
            patch("sys.stdin", MagicMock(read=MagicMock(return_value="prompt"))),
            patch("sys.stderr", stderr_buf),
            patch.dict(
                "os.environ",
                {"COPILOT_GITHUB_TOKEN": "fake-token", "COPILOT_TIMEOUT": "not-a-number"},
                clear=False,
            ),
        ):
            result = asyncio.run(module.main())
        assert result == 1
        assert "COPILOT_TIMEOUT must be a positive integer" in stderr_buf.getvalue()
        assert "not-a-number" in stderr_buf.getvalue()

    def test_zero_timeout_returns_1(self, _mock_copilot_sdk):
        """A zero COPILOT_TIMEOUT returns 1 with an error message."""
        module, spec = _load_module()
        spec.loader.exec_module(module)

        import asyncio
        import io

        stderr_buf = io.StringIO()
        with (
            patch("sys.stdin", MagicMock(read=MagicMock(return_value="prompt"))),
            patch("sys.stderr", stderr_buf),
            patch.dict(
                "os.environ",
                {"COPILOT_GITHUB_TOKEN": "fake-token", "COPILOT_TIMEOUT": "0"},
                clear=False,
            ),
        ):
            result = asyncio.run(module.main())
        assert result == 1
        assert "COPILOT_TIMEOUT must be a positive integer" in stderr_buf.getvalue()

    def test_negative_timeout_returns_1(self, _mock_copilot_sdk):
        """A negative COPILOT_TIMEOUT returns 1 with an error message."""
        module, spec = _load_module()
        spec.loader.exec_module(module)

        import asyncio
        import io

        stderr_buf = io.StringIO()
        with (
            patch("sys.stdin", MagicMock(read=MagicMock(return_value="prompt"))),
            patch("sys.stderr", stderr_buf),
            patch.dict(
                "os.environ",
                {"COPILOT_GITHUB_TOKEN": "fake-token", "COPILOT_TIMEOUT": "-5"},
                clear=False,
            ),
        ):
            result = asyncio.run(module.main())
        assert result == 1
        assert "COPILOT_TIMEOUT must be a positive integer" in stderr_buf.getvalue()
