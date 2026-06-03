"""Tests for GitHubActionsProvider._resolve_conflicted_file_content_via_sdk."""

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider


def _make_event(event_type: str, content: str | None = None) -> MagicMock:
    """Build a minimal mock SDK event object."""
    event = MagicMock()
    type_mock = MagicMock()
    type_mock.value = event_type
    event.type = type_mock
    if content is not None:
        data_mock = MagicMock()
        data_mock.content = content
        data_mock.message = content
        event.data = data_mock
    else:
        event.data = MagicMock(content="", message=None)
    return event


def _build_sdk_mocks(
    create_session_fallback: bool = False,
) -> tuple[MagicMock, MagicMock, MagicMock]:
    """Return (mock_copilot_module, mock_session_module, mock_session)."""
    mock_session = MagicMock()
    mock_session.disconnect = AsyncMock()
    mock_session.on = MagicMock()

    mock_client = MagicMock()
    mock_client.start = AsyncMock()
    mock_client.stop = AsyncMock()

    if create_session_fallback:
        mock_client.create_session = AsyncMock(
            side_effect=[
                TypeError("unexpected keyword argument 'github_token'"),
                mock_session,
            ]
        )
    else:
        mock_client.create_session = AsyncMock(return_value=mock_session)

    mock_copilot = MagicMock()
    mock_copilot.CopilotClient.return_value = mock_client
    mock_copilot.SubprocessConfig = MagicMock()

    mock_session_module = MagicMock()
    mock_session_module.PermissionHandler = MagicMock()

    return mock_copilot, mock_session_module, mock_session


def _build_sdk_mocks_no_subprocess_config() -> tuple[MagicMock, MagicMock, MagicMock, MagicMock]:
    """Return (mock_copilot, mock_copilot_config, mock_session_module, mock_session).

    ``mock_copilot`` has spec=['CopilotClient'] so that accessing SubprocessConfig raises
    AttributeError, which Python converts to ImportError during ``from copilot import SubprocessConfig``.
    SubprocessConfig is available on mock_copilot_config instead.
    """
    mock_session = MagicMock()
    mock_session.disconnect = AsyncMock()

    captured_callback: list = []

    def capture_on(cb: object) -> None:
        captured_callback.append(cb)

    mock_session.on = MagicMock(side_effect=capture_on)

    async def fire_events(prompt: str) -> None:  # noqa: ARG001
        cb = captured_callback[0]
        cb(_make_event("assistant.message", "resolved via fallback\n"))
        cb(_make_event("session.idle"))

    mock_session.send = fire_events

    mock_client = MagicMock()
    mock_client.start = AsyncMock()
    mock_client.stop = AsyncMock()
    mock_client.create_session = AsyncMock(return_value=mock_session)

    # copilot module WITHOUT SubprocessConfig
    mock_copilot = MagicMock(spec=["CopilotClient"])
    mock_copilot.CopilotClient.return_value = mock_client

    # copilot.config module WITH SubprocessConfig
    mock_copilot_config = MagicMock()
    mock_copilot_config.SubprocessConfig = MagicMock()

    mock_session_module = MagicMock()
    mock_session_module.PermissionHandler = MagicMock()

    return mock_copilot, mock_copilot_config, mock_session_module, mock_session


class TestResolveConflictedFileContentViaSdk:
    """Tests for SDK-driven single-file conflict resolution."""

    # ── No token ─────────────────────────────────────────────────────────────

    def test_no_token_returns_none(self, monkeypatch: object) -> None:
        monkeypatch.delenv("COPILOT_GITHUB_TOKEN", raising=False)  # type: ignore[attr-defined]
        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider._resolve_conflicted_file_content_via_sdk(
            file_path="src/main.py",
            conflict_content="<<<<<<< HEAD\nmine\n=======\ntheirs\n>>>>>>> branch\n",
            base_branch="main",
            head_branch="feature/test",
        )
        assert result is None

    def test_empty_token_returns_none(self, monkeypatch: object) -> None:
        monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "")  # type: ignore[attr-defined]
        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider._resolve_conflicted_file_content_via_sdk(
            file_path="src/main.py",
            conflict_content="<<<<<<< HEAD\nmine\n=======\ntheirs\n>>>>>>> branch\n",
            base_branch="main",
            head_branch="feature/test",
        )
        assert result is None

    # ── Happy path ───────────────────────────────────────────────────────────

    def test_sdk_happy_path_returns_resolved_content(self, monkeypatch: object) -> None:
        """SDK session fires assistant.message then session.idle; resolved content returned."""
        monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "test-token")  # type: ignore[attr-defined]
        mock_copilot, mock_session_module, mock_session = _build_sdk_mocks()

        captured_callback: list = []

        def capture_on(cb: object) -> None:
            captured_callback.append(cb)

        mock_session.on = MagicMock(side_effect=capture_on)

        async def fire_events(prompt: str) -> None:  # noqa: ARG001
            cb = captured_callback[0]
            cb(_make_event("assistant.message", "resolved_content = True\n"))
            cb(_make_event("session.idle"))

        mock_session.send = fire_events

        with patch.dict(sys.modules, {"copilot": mock_copilot, "copilot.session": mock_session_module}):
            provider = GitHubActionsProvider(repo="owner/repo")
            result = provider._resolve_conflicted_file_content_via_sdk(
                file_path="src/main.py",
                conflict_content="<<<<<<< HEAD\nmine\n=======\ntheirs\n>>>>>>> branch\n",
                base_branch="main",
                head_branch="feature/test",
            )

        assert result == "resolved_content = True\n"

    # ── Fence stripping ──────────────────────────────────────────────────────

    def test_sdk_fence_stripped(self, monkeypatch: object) -> None:
        """Markdown fences wrapping the SDK output are removed before returning."""
        monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "test-token")  # type: ignore[attr-defined]
        mock_copilot, mock_session_module, mock_session = _build_sdk_mocks()

        captured_callback: list = []

        def capture_on(cb: object) -> None:
            captured_callback.append(cb)

        mock_session.on = MagicMock(side_effect=capture_on)

        async def fire_fenced(prompt: str) -> None:  # noqa: ARG001
            cb = captured_callback[0]
            cb(_make_event("assistant.message", "```python\nresolved = True\n```"))
            cb(_make_event("session.idle"))

        mock_session.send = fire_fenced

        with patch.dict(sys.modules, {"copilot": mock_copilot, "copilot.session": mock_session_module}):
            provider = GitHubActionsProvider(repo="owner/repo")
            result = provider._resolve_conflicted_file_content_via_sdk(
                file_path="src/main.py",
                conflict_content="<<<<<<< HEAD\nmine\n=======\ntheirs\n>>>>>>> branch\n",
                base_branch="main",
                head_branch="feature/test",
            )

        assert result == "resolved = True"

    def test_sdk_incomplete_fence_not_stripped(self, monkeypatch: object) -> None:
        """If fence has fewer than 3 lines it is returned verbatim (no stripping)."""
        monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "test-token")  # type: ignore[attr-defined]
        mock_copilot, mock_session_module, mock_session = _build_sdk_mocks()

        captured_callback: list = []

        def capture_on(cb: object) -> None:
            captured_callback.append(cb)

        mock_session.on = MagicMock(side_effect=capture_on)
        raw = "```\n```"  # only 2 lines — incomplete fence pair

        async def fire_incomplete_fence(prompt: str) -> None:  # noqa: ARG001
            cb = captured_callback[0]
            cb(_make_event("assistant.message", raw))
            cb(_make_event("session.idle"))

        mock_session.send = fire_incomplete_fence

        with patch.dict(sys.modules, {"copilot": mock_copilot, "copilot.session": mock_session_module}):
            provider = GitHubActionsProvider(repo="owner/repo")
            result = provider._resolve_conflicted_file_content_via_sdk(
                file_path="src/main.py",
                conflict_content="<<<<<<< HEAD\nmine\n=======\ntheirs\n>>>>>>> branch\n",
                base_branch="main",
                head_branch="feature/test",
            )

        assert result == raw

    # ── Empty / no content ───────────────────────────────────────────────────

    def test_sdk_empty_content_returns_none(self, monkeypatch: object) -> None:
        """SDK fires session.idle without any assistant.message; returns None."""
        monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "test-token")  # type: ignore[attr-defined]
        mock_copilot, mock_session_module, mock_session = _build_sdk_mocks()

        captured_callback: list = []

        def capture_on(cb: object) -> None:
            captured_callback.append(cb)

        mock_session.on = MagicMock(side_effect=capture_on)

        async def fire_idle_only(prompt: str) -> None:  # noqa: ARG001
            cb = captured_callback[0]
            cb(_make_event("session.idle"))

        mock_session.send = fire_idle_only

        with patch.dict(sys.modules, {"copilot": mock_copilot, "copilot.session": mock_session_module}):
            provider = GitHubActionsProvider(repo="owner/repo")
            result = provider._resolve_conflicted_file_content_via_sdk(
                file_path="src/main.py",
                conflict_content="<<<<<<< HEAD\nmine\n=======\ntheirs\n>>>>>>> branch\n",
                base_branch="main",
                head_branch="feature/test",
            )

        assert result is None

    # ── Error event ──────────────────────────────────────────────────────────

    def test_sdk_error_event_returns_none(self, monkeypatch: object) -> None:
        """SDK fires an error event; returns None and logs a warning."""
        monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "test-token")  # type: ignore[attr-defined]
        mock_copilot, mock_session_module, mock_session = _build_sdk_mocks()

        captured_callback: list = []

        def capture_on(cb: object) -> None:
            captured_callback.append(cb)

        mock_session.on = MagicMock(side_effect=capture_on)

        async def fire_error(prompt: str) -> None:  # noqa: ARG001
            cb = captured_callback[0]
            cb(_make_event("session.error", "SDK internal error"))

        mock_session.send = fire_error

        with patch.dict(sys.modules, {"copilot": mock_copilot, "copilot.session": mock_session_module}):
            provider = GitHubActionsProvider(repo="owner/repo")
            result = provider._resolve_conflicted_file_content_via_sdk(
                file_path="src/main.py",
                conflict_content="<<<<<<< HEAD\nmine\n=======\ntheirs\n>>>>>>> branch\n",
                base_branch="main",
                head_branch="feature/test",
            )

        assert result is None

    # ── Timeout ──────────────────────────────────────────────────────────────

    def test_sdk_timeout_returns_none(self, monkeypatch: object) -> None:
        """asyncio.wait_for times out; returns None and logs a warning."""
        monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "test-token")  # type: ignore[attr-defined]
        mock_copilot, mock_session_module, mock_session = _build_sdk_mocks()

        captured_callback: list = []

        def capture_on(cb: object) -> None:
            captured_callback.append(cb)

        mock_session.on = MagicMock(side_effect=capture_on)

        async def never_completes(prompt: str) -> None:  # noqa: ARG001
            pass  # no events fired; wait_for will be patched to time out

        mock_session.send = never_completes

        with patch.dict(sys.modules, {"copilot": mock_copilot, "copilot.session": mock_session_module}):
            with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()):
                provider = GitHubActionsProvider(repo="owner/repo")
                result = provider._resolve_conflicted_file_content_via_sdk(
                    file_path="src/main.py",
                    conflict_content="<<<<<<< HEAD\nmine\n=======\ntheirs\n>>>>>>> branch\n",
                    base_branch="main",
                    head_branch="feature/test",
                    timeout_seconds=1,
                )

        assert result is None

    # ── create_session github_token TypeError fallback ───────────────────────

    def test_sdk_github_token_type_error_falls_back(self, monkeypatch: object) -> None:
        """Older SDK that rejects github_token kwarg falls back to call without it."""
        monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "test-token")  # type: ignore[attr-defined]
        mock_copilot, mock_session_module, mock_session = _build_sdk_mocks(create_session_fallback=True)

        captured_callback: list = []

        def capture_on(cb: object) -> None:
            captured_callback.append(cb)

        mock_session.on = MagicMock(side_effect=capture_on)

        async def fire_events(prompt: str) -> None:  # noqa: ARG001
            cb = captured_callback[0]
            cb(_make_event("assistant.message", "resolved content\n"))
            cb(_make_event("session.idle"))

        mock_session.send = fire_events

        with patch.dict(sys.modules, {"copilot": mock_copilot, "copilot.session": mock_session_module}):
            provider = GitHubActionsProvider(repo="owner/repo")
            result = provider._resolve_conflicted_file_content_via_sdk(
                file_path="src/main.py",
                conflict_content="<<<<<<< HEAD\nmine\n=======\ntheirs\n>>>>>>> branch\n",
                base_branch="main",
                head_branch="feature/test",
            )

        assert result == "resolved content\n"
        assert mock_copilot.CopilotClient.return_value.create_session.call_count == 2

    # ── Fallback import (copilot.config.SubprocessConfig) ────────────────────

    def test_sdk_fallback_import_path_succeeds(self, monkeypatch: object) -> None:
        """When SubprocessConfig is absent from copilot, falls back to copilot.config."""
        monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "test-token")  # type: ignore[attr-defined]
        mock_copilot, mock_copilot_config, mock_session_module, _ = _build_sdk_mocks_no_subprocess_config()

        with patch.dict(
            sys.modules,
            {
                "copilot": mock_copilot,
                "copilot.config": mock_copilot_config,
                "copilot.session": mock_session_module,
            },
        ):
            provider = GitHubActionsProvider(repo="owner/repo")
            result = provider._resolve_conflicted_file_content_via_sdk(
                file_path="src/main.py",
                conflict_content="<<<<<<< HEAD\nmine\n=======\ntheirs\n>>>>>>> branch\n",
                base_branch="main",
                head_branch="feature/test",
            )

        assert result == "resolved via fallback\n"
