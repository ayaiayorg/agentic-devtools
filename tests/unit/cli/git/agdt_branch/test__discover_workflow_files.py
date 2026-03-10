"""Tests for agentic_devtools.cli.git.agdt_branch._discover_workflow_files."""

from unittest.mock import patch

from agentic_devtools.cli.git.agdt_branch import _discover_workflow_files

_MOD = "agentic_devtools.cli.git.agdt_branch"


class TestDiscoverWorkflowFiles:
    """Tests for _discover_workflow_files()."""

    def test_returns_empty_when_dir_missing(self, tmp_path):
        result = _discover_workflow_files(tmp_path, "default", "KEY")
        assert result == {}

    @patch(f"{_MOD}.hash_object", return_value="blob_sha")
    def test_discovers_files(self, _hash, tmp_path):
        wf = tmp_path / ".agdt" / "workflows" / "default" / "K"
        wf.mkdir(parents=True)
        (wf / "state.json").write_text("{}")
        result = _discover_workflow_files(tmp_path, "default", "K")
        assert ".agdt/workflows/default/K/state.json" in result
        assert result[".agdt/workflows/default/K/state.json"] == "blob_sha"

    @patch(f"{_MOD}.hash_object", return_value="blob_sha")
    def test_skips_directories(self, _hash, tmp_path):
        wf = tmp_path / ".agdt" / "workflows" / "default" / "K"
        wf.mkdir(parents=True)
        (wf / "subdir").mkdir()
        (wf / "file.txt").write_text("x")
        result = _discover_workflow_files(tmp_path, "default", "K")
        # Only the file, not the subdir
        assert len(result) == 1
        assert ".agdt/workflows/default/K/file.txt" in result
