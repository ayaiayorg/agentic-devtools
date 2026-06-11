"""Tests for agentic_devtools.cli.git.commit_intent.resolve_commit_intent."""

import pytest

from agentic_devtools.cli.git.commit_intent import resolve_commit_intent


class TestResolveCommitIntent:
    """Tests for resolve_commit_intent function."""

    def test_create_path_cli_title_with_body(self):
        """Test create path with CLI title and commit_message body."""
        intent = resolve_commit_intent(
            cli_commit_message_title="feat: new feature",
            cli_overwrite_commit_message_title=None,
            cli_commit_message="- Added tests\n- Updated docs",
            state_commit_message_title=None,
            state_overwrite_commit_message_title=None,
            state_commit_message=None,
        )
        assert intent.mode == "create"
        assert intent.title == "feat: new feature"
        assert intent.body == "- Added tests\n- Updated docs"
        assert intent.full_message == "feat: new feature\n\n- Added tests\n- Updated docs"

    def test_create_path_cli_title_no_body(self):
        """Test create path with CLI title but no body source."""
        intent = resolve_commit_intent(
            cli_commit_message_title="feat: title only",
            cli_overwrite_commit_message_title=None,
            cli_commit_message=None,
            state_commit_message_title=None,
            state_overwrite_commit_message_title=None,
            state_commit_message=None,
        )
        assert intent.mode == "create"
        assert intent.title == "feat: title only"
        assert intent.body is None
        assert intent.full_message == "feat: title only"

    def test_create_path_state_title_with_state_body(self):
        """Test create path with state title and state commit_message body."""
        intent = resolve_commit_intent(
            cli_commit_message_title=None,
            cli_overwrite_commit_message_title=None,
            cli_commit_message=None,
            state_commit_message_title="feat: from state",
            state_overwrite_commit_message_title=None,
            state_commit_message="body from state",
        )
        assert intent.mode == "create"
        assert intent.title == "feat: from state"
        assert intent.body == "body from state"
        assert intent.full_message == "feat: from state\n\nbody from state"

    def test_create_path_cli_overrides_state(self):
        """Test that CLI title takes precedence over state title."""
        intent = resolve_commit_intent(
            cli_commit_message_title="cli title",
            cli_overwrite_commit_message_title=None,
            cli_commit_message=None,
            state_commit_message_title="state title",
            state_overwrite_commit_message_title=None,
            state_commit_message=None,
        )
        assert intent.title == "cli title"

    def test_create_path_strips_duplicate_title_from_body(self):
        """Test that body starting with title has title stripped."""
        intent = resolve_commit_intent(
            cli_commit_message_title="feat: feature",
            cli_overwrite_commit_message_title=None,
            cli_commit_message="feat: feature\n\nActual body",
            state_commit_message_title=None,
            state_overwrite_commit_message_title=None,
            state_commit_message=None,
        )
        assert intent.body == "Actual body"
        assert intent.full_message == "feat: feature\n\nActual body"

    def test_create_path_strips_duplicate_title_without_blank_separator(self):
        """Test duplicate first line is stripped even without blank separator."""
        intent = resolve_commit_intent(
            cli_commit_message_title="feat: feature",
            cli_overwrite_commit_message_title=None,
            cli_commit_message="feat: feature\nActual body",
            state_commit_message_title=None,
            state_overwrite_commit_message_title=None,
            state_commit_message=None,
        )
        assert intent.body == "Actual body"
        assert intent.full_message == "feat: feature\n\nActual body"

    def test_create_path_strips_different_leading_title_stanza(self):
        """Test that full-message body sources strip leading title stanza."""
        intent = resolve_commit_intent(
            cli_commit_message_title="feat: preferred title",
            cli_overwrite_commit_message_title=None,
            cli_commit_message="feat: stale title\n\nActual body",
            state_commit_message_title=None,
            state_overwrite_commit_message_title=None,
            state_commit_message=None,
        )
        assert intent.body == "Actual body"
        assert intent.full_message == "feat: preferred title\n\nActual body"

    def test_create_path_preserves_bullet_list_body_with_blank_second_line(self):
        """Test that a bullet-list body is never misidentified as a title stanza.

        A body like '- Added tests\\n\\n- Updated docs' must not lose its first
        line even though the second line is blank, because the first line starts
        with a list marker.
        """
        intent = resolve_commit_intent(
            cli_commit_message_title="feat: new feature",
            cli_overwrite_commit_message_title=None,
            cli_commit_message="- Added tests\n\n- Updated docs",
            state_commit_message_title=None,
            state_overwrite_commit_message_title=None,
            state_commit_message=None,
        )
        assert intent.body == "- Added tests\n\n- Updated docs"
        assert intent.full_message == "feat: new feature\n\n- Added tests\n\n- Updated docs"

    def test_create_path_preserves_asterisk_bullet_body(self):
        """Test that a body starting with '*' bullet is not stripped."""
        intent = resolve_commit_intent(
            cli_commit_message_title="feat: title",
            cli_overwrite_commit_message_title=None,
            cli_commit_message="* First point\n\n* Second point",
            state_commit_message_title=None,
            state_overwrite_commit_message_title=None,
            state_commit_message=None,
        )
        assert intent.body == "* First point\n\n* Second point"
        assert intent.full_message == "feat: title\n\n* First point\n\n* Second point"

    def test_overwrite_path_cli_flag(self):
        """Test overwrite path with CLI flag."""
        intent = resolve_commit_intent(
            cli_commit_message_title=None,
            cli_overwrite_commit_message_title="fix: new title",
            cli_commit_message=None,
            state_commit_message_title=None,
            state_overwrite_commit_message_title=None,
            state_commit_message=None,
        )
        assert intent.mode == "overwrite"
        assert intent.title == "fix: new title"
        assert intent.body is None

    def test_overwrite_path_state_key(self):
        """Test overwrite path with state key."""
        intent = resolve_commit_intent(
            cli_commit_message_title=None,
            cli_overwrite_commit_message_title=None,
            cli_commit_message=None,
            state_commit_message_title=None,
            state_overwrite_commit_message_title="fix: state overwrite",
            state_commit_message=None,
        )
        assert intent.mode == "overwrite"
        assert intent.title == "fix: state overwrite"

    def test_create_path_rejects_whitespace_only_title(self):
        """Test create path rejects whitespace-only title values."""
        with pytest.raises(SystemExit) as exc_info:
            resolve_commit_intent(
                cli_commit_message_title="   ",
                cli_overwrite_commit_message_title=None,
                cli_commit_message=None,
                state_commit_message_title=None,
                state_overwrite_commit_message_title=None,
                state_commit_message=None,
            )
        assert exc_info.value.code == 1

    def test_overwrite_path_rejects_whitespace_only_title(self):
        """Test overwrite path rejects whitespace-only title values."""
        with pytest.raises(SystemExit) as exc_info:
            resolve_commit_intent(
                cli_commit_message_title=None,
                cli_overwrite_commit_message_title="   ",
                cli_commit_message=None,
                state_commit_message_title=None,
                state_overwrite_commit_message_title=None,
                state_commit_message=None,
            )
        assert exc_info.value.code == 1

    def test_overwrite_path_rejects_legacy_commit_message_arg(self):
        """Test overwrite path rejects --commit-message input to avoid ambiguity."""
        with pytest.raises(SystemExit) as exc_info:
            resolve_commit_intent(
                cli_commit_message_title=None,
                cli_overwrite_commit_message_title="fix: new title",
                cli_commit_message="some body",
                state_commit_message_title=None,
                state_overwrite_commit_message_title=None,
                state_commit_message=None,
            )
        assert exc_info.value.code == 1

    def test_legacy_path_commit_message(self):
        """Test legacy path with commit_message only."""
        intent = resolve_commit_intent(
            cli_commit_message_title=None,
            cli_overwrite_commit_message_title=None,
            cli_commit_message="full message\n\nfull body",
            state_commit_message_title=None,
            state_overwrite_commit_message_title=None,
            state_commit_message=None,
        )
        assert intent.mode == "legacy"
        assert intent.title is None
        assert intent.full_message == "full message\n\nfull body"

    def test_legacy_path_state_commit_message(self):
        """Test legacy path with state commit_message only."""
        intent = resolve_commit_intent(
            cli_commit_message_title=None,
            cli_overwrite_commit_message_title=None,
            cli_commit_message=None,
            state_commit_message_title=None,
            state_overwrite_commit_message_title=None,
            state_commit_message="state message",
        )
        assert intent.mode == "legacy"
        assert intent.full_message == "state message"

    def test_legacy_path_empty_cli_commit_message_overrides_state_and_exits(self, capsys):
        """Test explicit empty CLI commit_message does not fall back to state."""
        with pytest.raises(SystemExit) as exc_info:
            resolve_commit_intent(
                cli_commit_message_title=None,
                cli_overwrite_commit_message_title=None,
                cli_commit_message="",
                state_commit_message_title=None,
                state_overwrite_commit_message_title=None,
                state_commit_message="state message",
            )
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "No commit message source available" in err

    def test_conflict_both_cli_flags_exits(self):
        """Test that both create and overwrite flags cause exit 1."""
        with pytest.raises(SystemExit) as exc_info:
            resolve_commit_intent(
                cli_commit_message_title="create title",
                cli_overwrite_commit_message_title="overwrite title",
                cli_commit_message=None,
                state_commit_message_title=None,
                state_overwrite_commit_message_title=None,
                state_commit_message=None,
            )
        assert exc_info.value.code == 1

    def test_conflict_both_cli_flags_error_message(self, capsys):
        """Test that the conflict message names both CLI flags."""
        with pytest.raises(SystemExit):
            resolve_commit_intent(
                cli_commit_message_title="create title",
                cli_overwrite_commit_message_title="overwrite title",
                cli_commit_message=None,
                state_commit_message_title=None,
                state_overwrite_commit_message_title=None,
                state_commit_message=None,
            )
        err = capsys.readouterr().err
        assert "--commit-message-title" in err
        assert "--overwrite-commit-message-title" in err
        assert "state key" not in err

    def test_conflict_both_state_keys_exits(self):
        """Test that both create and overwrite state keys cause exit 1."""
        with pytest.raises(SystemExit) as exc_info:
            resolve_commit_intent(
                cli_commit_message_title=None,
                cli_overwrite_commit_message_title=None,
                cli_commit_message=None,
                state_commit_message_title="state create",
                state_overwrite_commit_message_title="state overwrite",
                state_commit_message=None,
            )
        assert exc_info.value.code == 1

    def test_conflict_both_state_keys_error_message(self, capsys):
        """Test that conflict from state keys names the state keys, not CLI flags."""
        with pytest.raises(SystemExit):
            resolve_commit_intent(
                cli_commit_message_title=None,
                cli_overwrite_commit_message_title=None,
                cli_commit_message=None,
                state_commit_message_title="state create",
                state_overwrite_commit_message_title="state overwrite",
                state_commit_message=None,
            )
        err = capsys.readouterr().err
        assert "commit_message_title state key" in err
        assert "overwrite_commit_message_title state key" in err
        assert "--commit-message-title" not in err
        assert "--overwrite-commit-message-title" not in err

    def test_conflict_mixed_cli_and_state_exits(self):
        """Test that CLI create and state overwrite cause exit 1."""
        with pytest.raises(SystemExit) as exc_info:
            resolve_commit_intent(
                cli_commit_message_title="cli create",
                cli_overwrite_commit_message_title=None,
                cli_commit_message=None,
                state_commit_message_title=None,
                state_overwrite_commit_message_title="state overwrite",
                state_commit_message=None,
            )
        assert exc_info.value.code == 1

    def test_conflict_mixed_cli_and_state_error_message(self, capsys):
        """Test that mixed-source conflict message names CLI flag and state key."""
        with pytest.raises(SystemExit):
            resolve_commit_intent(
                cli_commit_message_title="cli create",
                cli_overwrite_commit_message_title=None,
                cli_commit_message=None,
                state_commit_message_title=None,
                state_overwrite_commit_message_title="state overwrite",
                state_commit_message=None,
            )
        err = capsys.readouterr().err
        assert "--commit-message-title" in err
        assert "overwrite_commit_message_title state key" in err

    def test_no_message_source_exits(self):
        """Test that having no message source causes exit 1."""
        with pytest.raises(SystemExit) as exc_info:
            resolve_commit_intent(
                cli_commit_message_title=None,
                cli_overwrite_commit_message_title=None,
                cli_commit_message=None,
                state_commit_message_title=None,
                state_overwrite_commit_message_title=None,
                state_commit_message=None,
            )
        assert exc_info.value.code == 1

    def test_create_path_preserves_plain_prose_paragraph(self):
        """Test that a plain-prose intro paragraph is never stripped.

        A body like "Intro paragraph\\n\\nMore details" must keep its first
        paragraph intact because it is not a conventional-commit title stanza.
        """
        intent = resolve_commit_intent(
            cli_commit_message_title="feat: new feature",
            cli_overwrite_commit_message_title=None,
            cli_commit_message="Intro paragraph\n\nMore details",
            state_commit_message_title=None,
            state_overwrite_commit_message_title=None,
            state_commit_message=None,
        )
        assert intent.body == "Intro paragraph\n\nMore details"
        assert intent.full_message == "feat: new feature\n\nIntro paragraph\n\nMore details"

    def test_create_path_preserves_prose_prefix_that_starts_with_commit_type(self):
        """Test prose like 'feature: ...' is not misidentified as a stale title."""
        intent = resolve_commit_intent(
            cli_commit_message_title="feat: new feature",
            cli_overwrite_commit_message_title=None,
            cli_commit_message="feature: release notes\n\nMore details",
            state_commit_message_title=None,
            state_overwrite_commit_message_title=None,
            state_commit_message=None,
        )
        assert intent.body == "feature: release notes\n\nMore details"
        assert intent.full_message == "feat: new feature\n\nfeature: release notes\n\nMore details"

    def test_create_path_preserves_body_whitespace_after_title_stanza_strip(self):
        """Test title-stanza stripping preserves indentation and trailing spaces."""
        intent = resolve_commit_intent(
            cli_commit_message_title="feat: preferred title",
            cli_overwrite_commit_message_title=None,
            cli_commit_message="feat: stale title\n\n  Indented body  \n\nTrailing spaces stay  \n",
            state_commit_message_title=None,
            state_overwrite_commit_message_title=None,
            state_commit_message=None,
        )
        assert intent.body == "  Indented body  \n\nTrailing spaces stay  "
        assert intent.full_message == "feat: preferred title\n\n  Indented body  \n\nTrailing spaces stay  "

    def test_create_path_preserves_leading_blank_line_after_duplicate_title(self):
        """Test duplicate-title stripping removes only one separator blank line."""
        intent = resolve_commit_intent(
            cli_commit_message_title="feat: feature",
            cli_overwrite_commit_message_title=None,
            cli_commit_message="feat: feature\n\n\nActual body",
            state_commit_message_title=None,
            state_overwrite_commit_message_title=None,
            state_commit_message=None,
        )
        assert intent.body == "\nActual body"
        assert intent.full_message == "feat: feature\n\n\nActual body"

    def test_create_path_strips_single_line_stale_conventional_title(self):
        """Test single-line stale conventional titles are removed entirely."""
        intent = resolve_commit_intent(
            cli_commit_message_title="feat: preferred title",
            cli_overwrite_commit_message_title=None,
            cli_commit_message="fix: stale title",
            state_commit_message_title=None,
            state_overwrite_commit_message_title=None,
            state_commit_message=None,
        )
        assert intent.body is None
        assert intent.full_message == "feat: preferred title"

    def test_create_path_strips_non_conventional_duplicate_title(self):
        """Test non-conventional duplicated title lines are stripped from body."""
        intent = resolve_commit_intent(
            cli_commit_message_title="Release notes update",
            cli_overwrite_commit_message_title=None,
            cli_commit_message="Release notes update\n\nActual body",
            state_commit_message_title=None,
            state_overwrite_commit_message_title=None,
            state_commit_message=None,
        )
        assert intent.body == "Actual body"
        assert intent.full_message == "Release notes update\n\nActual body"

    def test_legacy_path_conventional_commit_body_not_stripped(self):
        """Test that legacy mode never strips conventional-commit lines from the message.

        The strip heuristic only applies on the create-path.  A full commit
        message provided via the legacy path must be passed through verbatim.
        """
        full_message = "feat: old title\n\nBody text with details"
        intent = resolve_commit_intent(
            cli_commit_message_title=None,
            cli_overwrite_commit_message_title=None,
            cli_commit_message=full_message,
            state_commit_message_title=None,
            state_overwrite_commit_message_title=None,
            state_commit_message=None,
        )
        assert intent.mode == "legacy"
        assert intent.full_message == full_message
