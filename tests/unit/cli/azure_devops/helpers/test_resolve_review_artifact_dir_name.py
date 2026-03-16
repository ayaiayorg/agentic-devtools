"""Tests for resolve_review_artifact_dir_name helper."""

from agentic_devtools.cli.azure_devops.helpers import resolve_review_artifact_dir_name


class TestResolveReviewArtifactDirName:
    """Tests for resolve_review_artifact_dir_name."""

    def test_returns_commit_hash_when_valid(self):
        """Returns the commit hash unchanged when it is a valid dir segment."""
        result = resolve_review_artifact_dir_name(123, "abc12345")
        assert result == "abc12345"

    def test_returns_str_when_valid(self):
        """Return type is always str."""
        result = resolve_review_artifact_dir_name(123, "abc12345")
        assert isinstance(result, str)

    def test_coerces_non_str_int_to_str(self):
        """A valid integer value is coerced to str without TypeError."""
        result = resolve_review_artifact_dir_name(99, 12345678)
        assert result == "12345678"
        assert isinstance(result, str)

    def test_falls_back_to_pr_id_when_none(self, capsys):
        """Returns PR<id> fallback when commit_hash_short is None."""
        result = resolve_review_artifact_dir_name(99999, None)
        assert result == "PR99999"
        captured = capsys.readouterr()
        assert "PR99999" in captured.err
        assert "not set" in captured.err

    def test_falls_back_to_pr_id_when_empty_string(self, capsys):
        """Returns PR<id> fallback when commit_hash_short is empty string."""
        result = resolve_review_artifact_dir_name(42, "")
        assert result == "PR42"
        captured = capsys.readouterr()
        assert "PR42" in captured.err

    def test_falls_back_to_pr_id_when_unsafe_path_traversal(self, capsys):
        """Returns PR<id> fallback when commit_hash_short contains '..'."""
        result = resolve_review_artifact_dir_name(12345, "../evil")
        assert result == "PR12345"
        captured = capsys.readouterr()
        assert "PR12345" in captured.err
        assert "unsafe" in captured.err

    def test_uses_repr_formatting_for_unsafe_value(self, capsys):
        """Unsafe value is printed with repr() to prevent log injection."""
        result = resolve_review_artifact_dir_name(1, "line1\nline2")
        assert result == "PR1"
        captured = capsys.readouterr()
        # The repr of the unsafe value must appear (with quotes and escaped newline),
        # not the raw value — this ensures log injection is actually prevented.
        assert "'line1\\nline2'" in captured.err

    def test_falls_back_to_pr_id_when_unsafe_slash(self, capsys):
        """Returns PR<id> fallback when commit_hash_short contains '/'."""
        result = resolve_review_artifact_dir_name(7, "a/b")
        assert result == "PR7"
        captured = capsys.readouterr()
        assert "unsafe" in captured.err

    def test_falls_back_to_pr_id_when_unsafe_colon(self, capsys):
        """Returns PR<id> fallback when commit_hash_short contains ':'."""
        result = resolve_review_artifact_dir_name(7, "C:evil")
        assert result == "PR7"
        captured = capsys.readouterr()
        assert "unsafe" in captured.err

    def test_no_warning_when_valid(self, capsys):
        """No stderr warning is emitted when commit_hash_short is valid."""
        resolve_review_artifact_dir_name(5, "deadbeef")
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_no_warning_when_warn_false_and_absent(self, capsys):
        """No warning is emitted when warn=False, even when commit_hash_short is absent."""
        result = resolve_review_artifact_dir_name(42, None, warn=False)
        assert result == "PR42"
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_no_warning_when_warn_false_and_unsafe(self, capsys):
        """No warning is emitted when warn=False, even when commit_hash_short is unsafe."""
        result = resolve_review_artifact_dir_name(7, "../evil", warn=False)
        assert result == "PR7"
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_integer_zero_is_not_treated_as_absent(self, capsys):
        """Integer 0 is falsy but should be coerced to '0' (not treated as absent)."""
        # is_safe_dir_segment("0") → True, so the result should be "0", not "PR<id>"
        result = resolve_review_artifact_dir_name(99, 0)
        assert result == "0"
        # No "not set" warning should be emitted
        captured = capsys.readouterr()
        assert "not set" not in captured.err

    def test_falls_back_when_str_raises(self, capsys):
        """Falls back to PR<id> when str(commit_hash_short) raises, matching the docstring."""

        class BadStr:
            def __str__(self):
                raise RuntimeError("__str__ not allowed")

        result = resolve_review_artifact_dir_name(55, BadStr())
        assert result == "PR55"
        captured = capsys.readouterr()
        assert "PR55" in captured.err
        assert "could not be coerced" in captured.err

    def test_no_warning_when_str_raises_and_warn_false(self, capsys):
        """No warning when str() raises and warn=False."""

        class BadStr:
            def __str__(self):
                raise RuntimeError("__str__ not allowed")

        result = resolve_review_artifact_dir_name(55, BadStr(), warn=False)
        assert result == "PR55"
        captured = capsys.readouterr()
        assert captured.err == ""
