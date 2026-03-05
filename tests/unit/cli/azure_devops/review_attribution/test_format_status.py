"""Tests for format_status function."""

from agentic_devtools.cli.azure_devops.review_attribution import format_status


class TestFormatStatus:
    """Tests for format_status."""

    # --- emoji mode (use_emoji=True, the default) ---

    def test_unreviewed_emoji(self):
        """Test 'unreviewed' with emoji returns the emoji-prefixed string."""
        assert format_status("unreviewed") == "⏳ Unreviewed"

    def test_in_progress_emoji(self):
        """Test 'in-progress' with emoji returns the emoji-prefixed string."""
        assert format_status("in-progress") == "🔃 In Progress"

    def test_approved_emoji(self):
        """Test 'approved' with emoji returns the emoji-prefixed string."""
        assert format_status("approved") == "✅ Approved"

    def test_needs_work_emoji(self):
        """Test 'needs-work' with emoji returns the emoji-prefixed string."""
        assert format_status("needs-work") == "📝 Needs Work"

    def test_unknown_status_emoji_returns_as_is(self):
        """Test unknown status with emoji mode returns the value unchanged."""
        assert format_status("some-unknown-status") == "some-unknown-status"

    # --- plain-text mode (use_emoji=False) ---

    def test_unreviewed_plain(self):
        """Test 'unreviewed' plain-text mode returns bracketed label."""
        assert format_status("unreviewed", use_emoji=False) == "[UNREVIEWED]"

    def test_in_progress_plain(self):
        """Test 'in-progress' plain-text mode returns bracketed label."""
        assert format_status("in-progress", use_emoji=False) == "[IN PROGRESS]"

    def test_approved_plain(self):
        """Test 'approved' plain-text mode returns bracketed label."""
        assert format_status("approved", use_emoji=False) == "[APPROVED]"

    def test_needs_work_plain(self):
        """Test 'needs-work' plain-text mode returns bracketed label."""
        assert format_status("needs-work", use_emoji=False) == "[NEEDS WORK]"

    def test_unknown_status_plain_returns_as_is(self):
        """Test unknown status with plain-text mode returns the value unchanged."""
        assert format_status("custom-status", use_emoji=False) == "custom-status"

    def test_empty_string_returns_as_is(self):
        """Test empty string is returned unchanged."""
        assert format_status("") == ""

    def test_use_emoji_default_is_true(self):
        """Test that the default use_emoji value is True (emoji mode)."""
        assert format_status("approved") == format_status("approved", use_emoji=True)
