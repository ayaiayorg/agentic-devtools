"""Tests for GitHubActionsProvider._clean_sdk_commit_message static method."""

import pytest

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider

_clean = GitHubActionsProvider._clean_sdk_commit_message


class TestCleanSdkCommitMessage:
    """Tests for the static message cleaning and validation helper."""

    def test_empty_string_returns_none(self) -> None:
        assert _clean("") is None

    def test_whitespace_only_returns_none(self) -> None:
        assert _clean("   \n  ") is None

    def test_valid_conventional_commit_returned_unchanged(self) -> None:
        msg = "feat: add new squash feature"
        assert _clean(msg) == msg

    def test_valid_commit_with_scope(self) -> None:
        msg = "fix(api): repair null check"
        assert _clean(msg) == msg

    def test_valid_commit_with_breaking_change(self) -> None:
        msg = "feat!: drop Python 3.9 support"
        assert _clean(msg) == msg

    def test_valid_commit_with_scope_and_breaking(self) -> None:
        msg = "refactor(core)!: rename provider interface"
        assert _clean(msg) == msg

    def test_valid_multiline_commit_returned(self) -> None:
        msg = "chore: squash post-repair updates\n\n- first fix\n- second fix"
        assert _clean(msg) == msg

    # ── Markdown fence stripping ─────────────────────────────────────────────

    def test_fenced_message_strips_fences(self) -> None:
        raw = "```\nfeat: add feature\n```"
        assert _clean(raw) == "feat: add feature"

    def test_fenced_message_with_language_strips_fences(self) -> None:
        raw = "```text\nfix: repair bug\n```"
        assert _clean(raw) == "fix: repair bug"

    def test_fenced_multiline_message_strips_fences(self) -> None:
        raw = "```\nchore: squash\n\n- first\n- second\n```"
        assert _clean(raw) == "chore: squash\n\n- first\n- second"

    def test_incomplete_fence_not_stripped(self) -> None:
        # Only one ``` — not a complete fence block; does not pass Conventional Commit check.
        raw = "```feat: add feature"
        assert _clean(raw) is None

    # ── "commit message:" prefix stripping ──────────────────────────────────

    def test_commit_message_prefix_stripped(self) -> None:
        raw = "commit message: feat: add feature"
        assert _clean(raw) == "feat: add feature"

    def test_commit_message_prefix_case_insensitive(self) -> None:
        raw = "Commit Message: fix: patch null dereference"
        assert _clean(raw) == "fix: patch null dereference"

    def test_commit_message_prefix_leaves_only_whitespace_returns_none(self) -> None:
        raw = "commit message:   "
        assert _clean(raw) is None

    # ── Conversational opener rejection ─────────────────────────────────────

    @pytest.mark.parametrize(
        "opener",
        [
            "Here is your commit message: feat: add",
            "Here's the message: fix: patch",
            "I'll generate that: chore: squash",
            "I've created: docs: update",
            "I would suggest: perf: improve",
            "Sure, here it is: feat: done",
            "Below is the message: chore: update",
            "Certainly, feat: add",
            "The following commit message covers: feat: add",
            "This commit adds: feat: new",
        ],
    )
    def test_conversational_opener_returns_none(self, opener: str) -> None:
        assert _clean(opener) is None

    # ── Subject line length cap ──────────────────────────────────────────────

    def test_subject_exactly_100_chars_accepted(self) -> None:
        # "feat: " is 6 chars; pad to exactly 100 chars total.
        subject = "feat: " + "x" * 94
        assert len(subject) == 100
        assert _clean(subject) == subject

    def test_subject_101_chars_rejected(self) -> None:
        subject = "feat: " + "x" * 95
        assert len(subject) == 101
        assert _clean(subject) is None

    # ── Conventional Commit format enforcement ───────────────────────────────

    def test_plain_sentence_without_type_rejected(self) -> None:
        assert _clean("Improve error handling in the service layer") is None

    def test_uppercase_type_rejected(self) -> None:
        assert _clean("Feat: add new thing") is None

    def test_missing_colon_rejected(self) -> None:
        assert _clean("feat add new thing") is None

    def test_missing_space_after_colon_rejected(self) -> None:
        assert _clean("feat:add new thing") is None

    def test_type_with_no_description_rejected(self) -> None:
        assert _clean("feat: ") is None

    def test_numeric_type_rejected(self) -> None:
        assert _clean("1fix: patch") is None
