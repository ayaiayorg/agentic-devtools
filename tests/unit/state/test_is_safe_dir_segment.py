"""Tests for agentic_devtools.state.is_safe_dir_segment."""

from agentic_devtools.state import is_safe_dir_segment


class TestIsSafeDirSegment:
    """Tests for the centralized path-safety helper."""

    def test_valid_simple_name(self):
        assert is_safe_dir_segment("ama") is True

    def test_valid_worktree_key(self):
        assert is_safe_dir_segment("PR123") is True

    def test_valid_name_with_hyphen(self):
        assert is_safe_dir_segment("PROJECT-1234") is True

    def test_rejects_empty_string(self):
        assert is_safe_dir_segment("") is False

    def test_rejects_forward_slash(self):
        assert is_safe_dir_segment("foo/bar") is False

    def test_rejects_backslash(self):
        assert is_safe_dir_segment("foo\\bar") is False

    def test_rejects_dot_dot(self):
        assert is_safe_dir_segment("..") is False

    def test_rejects_dot_dot_in_path(self):
        assert is_safe_dir_segment("a..b") is False

    def test_rejects_colon_windows_drive(self):
        """Colons reset the drive on Windows (e.g., Path(base) / 'D:')."""
        assert is_safe_dir_segment("D:") is False

    def test_rejects_colon_in_name(self):
        assert is_safe_dir_segment("foo:bar") is False

    def test_rejects_embedded_nul(self):
        """NUL bytes cause pathlib.Path to raise ValueError."""
        assert is_safe_dir_segment("a\x00b") is False

    def test_rejects_nul_only(self):
        assert is_safe_dir_segment("\x00") is False

    def test_rejects_control_char(self):
        """Non-printable control characters must be rejected."""
        assert is_safe_dir_segment("foo\x01bar") is False
