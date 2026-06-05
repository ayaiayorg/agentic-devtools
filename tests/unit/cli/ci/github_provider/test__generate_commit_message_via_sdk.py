"""Tests for GitHubActionsProvider._generate_commit_message_via_sdk."""

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
    create_session_side_effect: Exception | None = None,
    create_session_fallback: bool = False,
) -> tuple[MagicMock, MagicMock, MagicMock, MagicMock]:
    """Return (mock_copilot_module, mock_copilot_config, mock_session_module, mock_session).

    ``mock_session.send`` is left as a plain MagicMock so callers can replace it
    with an async function that fires events into the captured on_event callback.
    """
    mock_session = MagicMock()
    mock_session.disconnect = AsyncMock()
    mock_session.on = MagicMock()

    mock_client = MagicMock()
    mock_client.start = AsyncMock()
    mock_client.stop = AsyncMock()

    if create_session_side_effect is not None and not create_session_fallback:
        mock_client.create_session = AsyncMock(side_effect=create_session_side_effect)
    elif create_session_fallback:
        # First call raises the expected TypeError; second call succeeds.
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

    mock_copilot_config = MagicMock()
    mock_copilot_config.SubprocessConfig = MagicMock()

    mock_session_module = MagicMock()
    mock_session_module.PermissionHandler = MagicMock()

    return mock_copilot, mock_copilot_config, mock_session_module, mock_session


class TestGenerateCommitMessageViaSdk:
    """Tests for the Copilot-SDK-backed squash commit message generator."""

    # ── No token ─────────────────────────────────────────────────────────────

    def test_no_token_returns_none(self, monkeypatch: object) -> None:
        monkeypatch.delenv("COPILOT_GITHUB_TOKEN", raising=False)  # type: ignore[attr-defined]
        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider._generate_commit_message_via_sdk(
            head_sha="abc123",
            commit_subjects=["feat: test"],
        )
        assert result is None

    def test_empty_token_returns_none(self, monkeypatch: object) -> None:
        monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "")  # type: ignore[attr-defined]
        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider._generate_commit_message_via_sdk(
            head_sha="abc123",
            commit_subjects=["feat: test"],
        )
        assert result is None

    # ── Happy path ───────────────────────────────────────────────────────────

    def test_sdk_happy_path_returns_message(self, monkeypatch: object) -> None:
        """SDK session fires assistant.message then session.idle; clean message returned."""
        monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "test-token")  # type: ignore[attr-defined]
        mock_copilot, mock_copilot_config, mock_session_module, mock_session = _build_sdk_mocks()

        captured_callback: list = []

        def capture_on(cb: object) -> None:
            captured_callback.append(cb)

        mock_session.on = MagicMock(side_effect=capture_on)

        async def fire_events_and_return(prompt: str) -> None:  # noqa: ARG001
            cb = captured_callback[0]
            cb(_make_event("assistant.message", "feat: add squash feature"))
            cb(_make_event("session.idle"))

        mock_session.send = fire_events_and_return

        with patch.dict(
            sys.modules,
            {"copilot": mock_copilot, "copilot.config": mock_copilot_config, "copilot.session": mock_session_module},
        ):
            provider = GitHubActionsProvider(repo="owner/repo")
            result = provider._generate_commit_message_via_sdk(
                head_sha="abc123",
                commit_subjects=["feat: add squash feature"],
            )

        assert result == "feat: add squash feature"

    def test_sdk_empty_content_returns_none(self, monkeypatch: object) -> None:
        """SDK fires session.idle without any assistant.message; returns None."""
        monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "test-token")  # type: ignore[attr-defined]
        mock_copilot, mock_copilot_config, mock_session_module, mock_session = _build_sdk_mocks()

        captured_callback: list = []

        def capture_on(cb: object) -> None:
            captured_callback.append(cb)

        mock_session.on = MagicMock(side_effect=capture_on)

        async def fire_idle_only(prompt: str) -> None:  # noqa: ARG001
            cb = captured_callback[0]
            cb(_make_event("session.idle"))

        mock_session.send = fire_idle_only

        with patch.dict(
            sys.modules,
            {"copilot": mock_copilot, "copilot.config": mock_copilot_config, "copilot.session": mock_session_module},
        ):
            provider = GitHubActionsProvider(repo="owner/repo")
            result = provider._generate_commit_message_via_sdk(
                head_sha="abc123",
                commit_subjects=["feat: test"],
            )

        assert result is None

    # ── Error event ──────────────────────────────────────────────────────────

    def test_sdk_error_event_returns_none(self, monkeypatch: object) -> None:
        """SDK fires an error event; returns None and logs a warning."""
        monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "test-token")  # type: ignore[attr-defined]
        mock_copilot, mock_copilot_config, mock_session_module, mock_session = _build_sdk_mocks()

        captured_callback: list = []

        def capture_on(cb: object) -> None:
            captured_callback.append(cb)

        mock_session.on = MagicMock(side_effect=capture_on)

        async def fire_error_event(prompt: str) -> None:  # noqa: ARG001
            cb = captured_callback[0]
            cb(_make_event("session.error", "SDK internal error"))

        mock_session.send = fire_error_event

        with patch.dict(
            sys.modules,
            {"copilot": mock_copilot, "copilot.config": mock_copilot_config, "copilot.session": mock_session_module},
        ):
            provider = GitHubActionsProvider(repo="owner/repo")
            result = provider._generate_commit_message_via_sdk(
                head_sha="abc123",
                commit_subjects=["feat: test"],
            )

        assert result is None

    # ── Timeout ──────────────────────────────────────────────────────────────

    def test_sdk_timeout_returns_none(self, monkeypatch: object) -> None:
        """asyncio.wait_for times out inside _run(); returns None and logs a warning."""
        monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "test-token")  # type: ignore[attr-defined]
        mock_copilot, mock_copilot_config, mock_session_module, mock_session = _build_sdk_mocks()

        captured_callback: list = []

        def capture_on(cb: object) -> None:
            captured_callback.append(cb)

        mock_session.on = MagicMock(side_effect=capture_on)

        async def send_without_events(prompt: str) -> None:  # noqa: ARG001
            pass  # never fires events; wait_for will be patched to time out

        mock_session.send = send_without_events

        with patch.dict(
            sys.modules,
            {"copilot": mock_copilot, "copilot.config": mock_copilot_config, "copilot.session": mock_session_module},
        ):
            with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()):
                provider = GitHubActionsProvider(repo="owner/repo")
                result = provider._generate_commit_message_via_sdk(
                    head_sha="abc123",
                    commit_subjects=["feat: test"],
                    timeout_seconds=1,
                )

        assert result is None

    def test_sdk_timeout_covers_client_start(self, monkeypatch: object) -> None:
        """Timeout also covers SDK startup before a session is created."""
        monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "test-token")  # type: ignore[attr-defined]
        mock_copilot, mock_copilot_config, mock_session_module, _ = _build_sdk_mocks()

        async def hang_on_start() -> None:
            await asyncio.Future()

        mock_copilot.CopilotClient.return_value.start = hang_on_start

        with patch.dict(
            sys.modules,
            {"copilot": mock_copilot, "copilot.config": mock_copilot_config, "copilot.session": mock_session_module},
        ):
            provider = GitHubActionsProvider(repo="owner/repo")
            result = provider._generate_commit_message_via_sdk(
                head_sha="abc123",
                commit_subjects=["feat: test"],
                timeout_seconds=0,
            )

        assert result is None

    # ── create_session github_token TypeError fallback ───────────────────────

    def test_sdk_github_token_type_error_falls_back(self, monkeypatch: object) -> None:
        """Older SDK that doesn't accept github_token kwarg; fallback create_session used."""
        monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "test-token")  # type: ignore[attr-defined]
        mock_copilot, mock_copilot_config, mock_session_module, mock_session = _build_sdk_mocks(
            create_session_fallback=True,
        )

        captured_callback: list = []

        def capture_on(cb: object) -> None:
            captured_callback.append(cb)

        mock_session.on = MagicMock(side_effect=capture_on)

        async def fire_events_and_return(prompt: str) -> None:  # noqa: ARG001
            cb = captured_callback[0]
            cb(_make_event("assistant.message", "chore: squash post-repair updates"))
            cb(_make_event("session.idle"))

        mock_session.send = fire_events_and_return

        with patch.dict(
            sys.modules,
            {"copilot": mock_copilot, "copilot.config": mock_copilot_config, "copilot.session": mock_session_module},
        ):
            provider = GitHubActionsProvider(repo="owner/repo")
            result = provider._generate_commit_message_via_sdk(
                head_sha="abc123",
                commit_subjects=["chore: squash post-repair updates"],
            )

        assert result == "chore: squash post-repair updates"
        # Ensure create_session was called twice (with then without github_token).
        assert mock_copilot.CopilotClient.return_value.create_session.call_count == 2

    # ── Validation / cleaning integration ────────────────────────────────────

    def test_sdk_fenced_message_cleaned_before_return(self, monkeypatch: object) -> None:
        """Fence markers in SDK output are stripped before the message is returned."""
        monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "test-token")  # type: ignore[attr-defined]
        mock_copilot, mock_copilot_config, mock_session_module, mock_session = _build_sdk_mocks()

        captured_callback: list = []

        def capture_on(cb: object) -> None:
            captured_callback.append(cb)

        mock_session.on = MagicMock(side_effect=capture_on)

        async def fire_fenced_message(prompt: str) -> None:  # noqa: ARG001
            cb = captured_callback[0]
            cb(_make_event("assistant.message", "```\nfeat: add feature\n```"))
            cb(_make_event("session.idle"))

        mock_session.send = fire_fenced_message

        with patch.dict(
            sys.modules,
            {"copilot": mock_copilot, "copilot.config": mock_copilot_config, "copilot.session": mock_session_module},
        ):
            provider = GitHubActionsProvider(repo="owner/repo")
            result = provider._generate_commit_message_via_sdk(
                head_sha="abc123",
                commit_subjects=["feat: add feature"],
            )

        assert result == "feat: add feature"

    def test_sdk_conversational_message_returns_none(self, monkeypatch: object) -> None:
        """Conversational SDK output is rejected; returns None for deterministic fallback."""
        monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "test-token")  # type: ignore[attr-defined]
        mock_copilot, mock_copilot_config, mock_session_module, mock_session = _build_sdk_mocks()

        captured_callback: list = []

        def capture_on(cb: object) -> None:
            captured_callback.append(cb)

        mock_session.on = MagicMock(side_effect=capture_on)

        async def fire_conversational_message(prompt: str) -> None:  # noqa: ARG001
            cb = captured_callback[0]
            cb(_make_event("assistant.message", "Here is the commit message: feat: add feature"))
            cb(_make_event("session.idle"))

        mock_session.send = fire_conversational_message

        with patch.dict(
            sys.modules,
            {"copilot": mock_copilot, "copilot.config": mock_copilot_config, "copilot.session": mock_session_module},
        ):
            provider = GitHubActionsProvider(repo="owner/repo")
            result = provider._generate_commit_message_via_sdk(
                head_sha="abc123",
                commit_subjects=["feat: add feature"],
            )

        assert result is None
