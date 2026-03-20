"""Tests for agentic_devtools.state._update_bootstrap_worktree_key."""

import json

from agentic_devtools import state


class TestUpdateBootstrapWorktreeKey:
    """Tests for the subprocess-free bootstrap updater."""

    def test_updates_existing_bootstrap_via_cwd(self, tmp_path, monkeypatch):
        """Walks up from CWD to find .agdt/runtime-bootstrap.json."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        bootstrap_path = agdt_dir / "runtime-bootstrap.json"
        bootstrap_path.write_text(json.dumps({"identity": "ama", "worktree_key": "OLD"}), encoding="utf-8")

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("AGENTIC_DEVTOOLS_STATE_DIR", raising=False)
        state._update_bootstrap_worktree_key("NEW-1234")

        data = json.loads(bootstrap_path.read_text(encoding="utf-8"))
        assert data["worktree_key"] == "NEW-1234"
        assert data["identity"] == "ama"

    def test_updates_existing_bootstrap_via_env_var(self, tmp_path, monkeypatch):
        """Uses AGENTIC_DEVTOOLS_STATE_DIR as starting point when set."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        bootstrap_path = agdt_dir / "runtime-bootstrap.json"
        bootstrap_path.write_text(json.dumps({"identity": "xyz"}), encoding="utf-8")

        state_dir = tmp_path / ".agdt" / "workflows" / "_unscoped"
        state_dir.mkdir(parents=True)

        monkeypatch.setenv("AGENTIC_DEVTOOLS_STATE_DIR", str(state_dir))
        state._update_bootstrap_worktree_key("PR42")

        data = json.loads(bootstrap_path.read_text(encoding="utf-8"))
        assert data["worktree_key"] == "PR42"

    def test_creates_bootstrap_when_agdt_dir_exists_but_no_file(self, tmp_path, monkeypatch):
        """Creates bootstrap file when .agdt/ exists but bootstrap file does not."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("AGENTIC_DEVTOOLS_STATE_DIR", raising=False)
        state._update_bootstrap_worktree_key("DFLY-42")

        bootstrap_path = agdt_dir / "runtime-bootstrap.json"
        assert bootstrap_path.exists()
        data = json.loads(bootstrap_path.read_text(encoding="utf-8"))
        assert data == {"worktree_key": "DFLY-42"}

    def test_noop_when_no_agdt_dir(self, tmp_path, monkeypatch):
        """Does nothing when no .agdt/ directory exists anywhere."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("AGENTIC_DEVTOOLS_STATE_DIR", raising=False)
        # Should not raise
        state._update_bootstrap_worktree_key("IGNORED")
        # No files created
        assert not (tmp_path / ".agdt").exists()

    def test_noop_on_malformed_json(self, tmp_path, monkeypatch):
        """Does nothing when bootstrap file contains invalid JSON."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        bootstrap_path = agdt_dir / "runtime-bootstrap.json"
        bootstrap_path.write_text("not json!", encoding="utf-8")

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("AGENTIC_DEVTOOLS_STATE_DIR", raising=False)
        # Should not raise
        state._update_bootstrap_worktree_key("IGNORED")

    def test_noop_on_non_dict_json(self, tmp_path, monkeypatch):
        """Does nothing when bootstrap file contains non-dict JSON."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        bootstrap_path = agdt_dir / "runtime-bootstrap.json"
        bootstrap_path.write_text(json.dumps(["a", "b"]), encoding="utf-8")

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("AGENTIC_DEVTOOLS_STATE_DIR", raising=False)
        state._update_bootstrap_worktree_key("IGNORED")

        # File unchanged — still a list
        data = json.loads(bootstrap_path.read_text(encoding="utf-8"))
        assert isinstance(data, list)

    def test_walks_up_from_nested_dir(self, tmp_path, monkeypatch):
        """Walks up multiple levels from CWD to find .agdt/."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        bootstrap_path = agdt_dir / "runtime-bootstrap.json"
        bootstrap_path.write_text(json.dumps({"identity": "ama"}), encoding="utf-8")

        nested = tmp_path / "a" / "b" / "c"
        nested.mkdir(parents=True)
        monkeypatch.chdir(nested)
        monkeypatch.delenv("AGENTIC_DEVTOOLS_STATE_DIR", raising=False)
        state._update_bootstrap_worktree_key("DEEP")

        data = json.loads(bootstrap_path.read_text(encoding="utf-8"))
        assert data["worktree_key"] == "DEEP"

    def test_noop_on_invalid_encoding(self, tmp_path, monkeypatch):
        """Does nothing when bootstrap file has invalid UTF-8 bytes."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        bootstrap_path = agdt_dir / "runtime-bootstrap.json"
        original_bytes = b"\x80\x81\x82\x83"
        bootstrap_path.write_bytes(original_bytes)

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("AGENTIC_DEVTOOLS_STATE_DIR", raising=False)
        # Should not raise
        state._update_bootstrap_worktree_key("IGNORED")

        # File unchanged — still has the same invalid bytes
        assert bootstrap_path.read_bytes() == original_bytes
