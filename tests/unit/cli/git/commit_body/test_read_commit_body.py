"""Tests for read_commit_body function."""

from unittest.mock import patch

from agentic_devtools.cli.git.commit_body import (
    MAX_BODY_FILE_SIZE,
    read_commit_body,
)


class TestReadCommitBody:
    """Tests for read_commit_body."""

    def _setup_body_file(self, tmp_path, content=None, raw_bytes=None):
        """Helper to create a commit-body.md file in the expected location."""
        files_dir = tmp_path / "files"
        files_dir.mkdir(parents=True, exist_ok=True)
        body_file = files_dir / "commit-body.md"
        if raw_bytes is not None:
            body_file.write_bytes(raw_bytes)
        elif content is not None:
            body_file.write_text(content, encoding="utf-8")
        return body_file

    def test_file_missing(self, tmp_path):
        """Test missing file returns absent body without error."""
        with patch(
            "agentic_devtools.cli.git.commit_body.get_state_dir",
            return_value=tmp_path,
        ):
            result = read_commit_body()
            assert result.body == ""
            assert result.frontmatter == {}
            assert not result.file_exists
            assert result.error == ""

    def test_files_directory_missing(self, tmp_path):
        """Test missing files/ directory treated as absent body."""
        # Don't create files/ subdir at all
        with patch(
            "agentic_devtools.cli.git.commit_body.get_state_dir",
            return_value=tmp_path,
        ):
            result = read_commit_body()
            assert result.body == ""
            assert not result.file_exists
            assert result.error == ""

    def test_empty_file(self, tmp_path):
        """Test empty file returns empty body, file_exists=True."""
        self._setup_body_file(tmp_path, content="")
        with patch(
            "agentic_devtools.cli.git.commit_body.get_state_dir",
            return_value=tmp_path,
        ):
            result = read_commit_body()
            assert result.body == ""
            assert result.file_exists
            assert result.error == ""

    def test_whitespace_only_file(self, tmp_path):
        """Test whitespace-only file returns whitespace body, file_exists=True."""
        self._setup_body_file(tmp_path, content="   \n\n  \n")
        with patch(
            "agentic_devtools.cli.git.commit_body.get_state_dir",
            return_value=tmp_path,
        ):
            result = read_commit_body()
            assert result.body == "   \n\n  \n"
            assert result.file_exists
            assert result.error == ""

    def test_valid_content_happy_path(self, tmp_path):
        """Test valid content is returned correctly."""
        content = "## Changes\n\n- Added webhook\n- Fixed tests"
        self._setup_body_file(tmp_path, content=content)
        with patch(
            "agentic_devtools.cli.git.commit_body.get_state_dir",
            return_value=tmp_path,
        ):
            result = read_commit_body()
            assert result.body == content
            assert result.frontmatter == {}
            assert result.file_exists
            assert result.error == ""

    def test_exceeds_max_size(self, tmp_path):
        """Test file >100KB returns error."""
        large_content = "x" * (MAX_BODY_FILE_SIZE + 1)
        self._setup_body_file(tmp_path, content=large_content)
        with patch(
            "agentic_devtools.cli.git.commit_body.get_state_dir",
            return_value=tmp_path,
        ):
            result = read_commit_body()
            assert result.error != ""
            assert "exceeds maximum size" in result.error
            assert result.body == ""

    def test_non_utf8_encoding(self, tmp_path):
        """Test non-UTF-8 file returns error."""
        # Write raw bytes that aren't valid UTF-8
        self._setup_body_file(tmp_path, raw_bytes=b"\xff\xfe invalid utf8")
        with patch(
            "agentic_devtools.cli.git.commit_body.get_state_dir",
            return_value=tmp_path,
        ):
            result = read_commit_body()
            assert result.error != ""
            assert "not valid UTF-8" in result.error

    def test_bom_stripping(self, tmp_path):
        """Test UTF-8 BOM is stripped before parsing."""
        bom = b"\xef\xbb\xbf"
        content = "## Body\n\nContent here"
        self._setup_body_file(tmp_path, raw_bytes=bom + content.encode("utf-8"))
        with patch(
            "agentic_devtools.cli.git.commit_body.get_state_dir",
            return_value=tmp_path,
        ):
            result = read_commit_body()
            assert result.body == content
            assert result.error == ""

    def test_content_with_frontmatter(self, tmp_path):
        """Test content with valid frontmatter is parsed."""
        content = "---\nstatus: done\n---\n## Body\n\nContent"
        self._setup_body_file(tmp_path, content=content)
        with patch(
            "agentic_devtools.cli.git.commit_body.get_state_dir",
            return_value=tmp_path,
        ):
            result = read_commit_body()
            assert result.frontmatter == {"status": "done"}
            assert result.body == "## Body\n\nContent"
            assert result.error == ""
            assert result.warning == ""

    def test_worktree_isolation(self, tmp_path):
        """Test different worktree dirs read different files."""
        dir_a = tmp_path / "wt_a"
        dir_b = tmp_path / "wt_b"

        # Write different content to each
        files_a = dir_a / "files"
        files_a.mkdir(parents=True)
        (files_a / "commit-body.md").write_text("Body A", encoding="utf-8")

        files_b = dir_b / "files"
        files_b.mkdir(parents=True)
        (files_b / "commit-body.md").write_text("Body B", encoding="utf-8")

        with patch(
            "agentic_devtools.cli.git.commit_body.get_state_dir",
            return_value=dir_a,
        ):
            result_a = read_commit_body()

        with patch(
            "agentic_devtools.cli.git.commit_body.get_state_dir",
            return_value=dir_b,
        ):
            result_b = read_commit_body()

        assert result_a.body == "Body A"
        assert result_b.body == "Body B"

    def test_stat_os_error(self, tmp_path):
        """Test OS error during stat returns error."""
        self._setup_body_file(tmp_path, content="content")
        with patch(
            "agentic_devtools.cli.git.commit_body.get_state_dir",
            return_value=tmp_path,
        ):
            # Mock exists() to return True, but stat() to raise
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.stat", side_effect=OSError("permission denied")):
                    result = read_commit_body()
                    assert "Cannot stat" in result.error

    def test_read_bytes_os_error(self, tmp_path):
        """Test OS error during read returns error."""
        self._setup_body_file(tmp_path, content="content")
        with patch(
            "agentic_devtools.cli.git.commit_body.get_state_dir",
            return_value=tmp_path,
        ):
            with patch("pathlib.Path.read_bytes", side_effect=OSError("read failed")):
                result = read_commit_body()
                assert "Cannot read" in result.error
