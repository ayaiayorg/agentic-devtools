"""Tests for show_cmd function."""

from unittest.mock import patch

import pytest

from agentic_devtools.cli.git.commit_body import show_cmd


class TestShowCmd:
    """Tests for show_cmd."""

    def _setup_body_file(self, tmp_path, content=None, raw_bytes=None):
        """Helper to create a commit-body.md file."""
        files_dir = tmp_path / "files"
        files_dir.mkdir(parents=True, exist_ok=True)
        body_file = files_dir / "commit-body.md"
        if raw_bytes is not None:
            body_file.write_bytes(raw_bytes)
        elif content is not None:
            body_file.write_text(content, encoding="utf-8")
        return body_file

    def test_file_present_no_frontmatter(self, tmp_path, capsys):
        """Test show_cmd with body file present, no frontmatter."""
        self._setup_body_file(tmp_path, content="## Changes\n\n- item 1")
        with patch(
            "agentic_devtools.cli.git.commit_body.get_state_dir",
            return_value=tmp_path,
        ):
            show_cmd()
        captured = capsys.readouterr()
        assert "COMMIT BODY:" in captured.out
        assert "Frontmatter: no" in captured.out
        assert "--- Body ---" in captured.out
        assert "## Changes" in captured.out

    def test_file_present_with_frontmatter(self, tmp_path, capsys):
        """Test show_cmd with valid frontmatter."""
        content = "---\nstatus: approved\nitems: [1, 2]\n---\n## Body\nContent"
        self._setup_body_file(tmp_path, content=content)
        with patch(
            "agentic_devtools.cli.git.commit_body.get_state_dir",
            return_value=tmp_path,
        ):
            show_cmd()
        captured = capsys.readouterr()
        assert "Frontmatter: yes (2 keys)" in captured.out
        assert "--- Frontmatter ---" in captured.out
        assert "status:" in captured.out
        assert "items:" in captured.out
        assert "--- Body ---" in captured.out

    def test_file_missing_exits_with_error(self, tmp_path, capsys):
        """Test show_cmd exits 1 when file is missing."""
        with patch(
            "agentic_devtools.cli.git.commit_body.get_state_dir",
            return_value=tmp_path,
        ):
            with pytest.raises(SystemExit) as exc_info:
                show_cmd()
            assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_file_exceeds_max_size_exits_with_error(self, tmp_path, capsys):
        """Test show_cmd exits 1 when file >100KB."""
        large = "x" * 102_401
        self._setup_body_file(tmp_path, content=large)
        with patch(
            "agentic_devtools.cli.git.commit_body.get_state_dir",
            return_value=tmp_path,
        ):
            with pytest.raises(SystemExit) as exc_info:
                show_cmd()
            assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "exceeds maximum size" in captured.err

    def test_malformed_yaml_shows_warning_and_body(self, tmp_path, capsys):
        """Test malformed YAML prints warning, shows body only."""
        content = "---\n: bad: [yaml\n---\nActual body text"
        self._setup_body_file(tmp_path, content=content)
        with patch(
            "agentic_devtools.cli.git.commit_body.get_state_dir",
            return_value=tmp_path,
        ):
            show_cmd()
        captured = capsys.readouterr()
        # Warning about malformed YAML
        assert "Malformed YAML" in captured.err
        # Body shows the entire content (fallback behavior)
        assert "--- Body ---" in captured.out
        assert "Frontmatter: no" in captured.out

    def test_output_includes_length(self, tmp_path, capsys):
        """Test output includes character length."""
        self._setup_body_file(tmp_path, content="Hello world")
        with patch(
            "agentic_devtools.cli.git.commit_body.get_state_dir",
            return_value=tmp_path,
        ):
            show_cmd()
        captured = capsys.readouterr()
        assert "Length:" in captured.out
        assert "11 characters" in captured.out

    def test_no_reconfigure_on_stdout_or_stderr(self, tmp_path, capsys):
        """Test show_cmd succeeds when stdout/stderr lack reconfigure (Python <3.7 or bare streams)."""
        self._setup_body_file(tmp_path, content="body text")

        class _NoReconfigure:
            """Minimal stream without reconfigure."""

            def __init__(self):
                self._data = []

            def write(self, s):
                self._data.append(s)

            def flush(self):
                pass

            def getvalue(self):
                return "".join(self._data)

        fake_stdout = _NoReconfigure()
        fake_stderr = _NoReconfigure()
        assert not hasattr(fake_stdout, "reconfigure")
        assert not hasattr(fake_stderr, "reconfigure")

        with (
            patch(
                "agentic_devtools.cli.git.commit_body.get_state_dir",
                return_value=tmp_path,
            ),
            patch("agentic_devtools.cli.git.commit_body.sys.stdout", fake_stdout),
            patch("agentic_devtools.cli.git.commit_body.sys.stderr", fake_stderr),
        ):
            show_cmd()

        output = fake_stdout.getvalue()
        assert "COMMIT BODY:" in output
        assert "--- Body ---" in output
