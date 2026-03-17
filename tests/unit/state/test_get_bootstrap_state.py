"""Tests for agentic_devtools.state.get_bootstrap_state."""

import json
from unittest.mock import patch

from agentic_devtools import state


class TestGetBootstrapState:
    """Tests for reading the runtime bootstrap file."""

    def test_reads_valid_bootstrap_file(self, tmp_path):
        """Reads identity and worktree_key from a well-formed bootstrap file."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        bootstrap_data = {"identity": "ama", "worktree_key": "DFLY-1234"}
        (agdt_dir / "runtime-bootstrap.json").write_text(json.dumps(bootstrap_data), encoding="utf-8")

        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            result = state.get_bootstrap_state()

        assert result == {"identity": "ama", "worktree_key": "DFLY-1234"}

    def test_returns_empty_dict_when_file_missing(self, tmp_path):
        """Returns {} when the bootstrap file does not exist."""
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            result = state.get_bootstrap_state()

        assert result == {}

    def test_returns_empty_dict_when_malformed_json(self, tmp_path):
        """Returns {} when the bootstrap file contains malformed JSON."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        (agdt_dir / "runtime-bootstrap.json").write_text("not valid json {{{", encoding="utf-8")

        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            result = state.get_bootstrap_state()

        assert result == {}

    def test_returns_empty_dict_when_not_in_git_repo(self):
        """Returns {} when _get_git_repo_root returns None."""
        with patch.object(state, "_get_git_repo_root", return_value=None):
            result = state.get_bootstrap_state()

        assert result == {}

    def test_returns_partial_dict_when_keys_missing(self, tmp_path):
        """Returns only existing string keys from the bootstrap file."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        bootstrap_data = {"identity": "ama"}  # no worktree_key
        (agdt_dir / "runtime-bootstrap.json").write_text(json.dumps(bootstrap_data), encoding="utf-8")

        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            result = state.get_bootstrap_state()

        assert result == {"identity": "ama"}

    def test_filters_non_string_values(self, tmp_path):
        """Non-string values are filtered out."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        bootstrap_data = {"identity": "ama", "worktree_key": 123, "extra": True}
        (agdt_dir / "runtime-bootstrap.json").write_text(json.dumps(bootstrap_data), encoding="utf-8")

        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            result = state.get_bootstrap_state()

        assert result == {"identity": "ama"}

    def test_only_whitelisted_keys_returned(self, tmp_path):
        """Only 'identity' and 'worktree_key' keys are returned, even if file has more."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        bootstrap_data = {"identity": "ama", "worktree_key": "DFLY-1", "extra_key": "val", "debug": "true"}
        (agdt_dir / "runtime-bootstrap.json").write_text(json.dumps(bootstrap_data), encoding="utf-8")

        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            result = state.get_bootstrap_state()

        assert result == {"identity": "ama", "worktree_key": "DFLY-1"}
        assert "extra_key" not in result
        assert "debug" not in result

    def test_strips_whitespace_from_values(self, tmp_path):
        """Values are stripped of leading/trailing whitespace."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        bootstrap_data = {"identity": "  ama  ", "worktree_key": "  DFLY-1  "}
        (agdt_dir / "runtime-bootstrap.json").write_text(json.dumps(bootstrap_data), encoding="utf-8")

        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            result = state.get_bootstrap_state()

        assert result == {"identity": "ama", "worktree_key": "DFLY-1"}

    def test_omits_keys_with_whitespace_only_values(self, tmp_path):
        """Keys whose values become empty after stripping are omitted entirely."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        bootstrap_data = {"identity": "   ", "worktree_key": "DFLY-1"}
        (agdt_dir / "runtime-bootstrap.json").write_text(json.dumps(bootstrap_data), encoding="utf-8")

        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            result = state.get_bootstrap_state()

        assert result == {"worktree_key": "DFLY-1"}
        assert "identity" not in result

    def test_returns_empty_dict_when_bootstrap_is_array(self, tmp_path):
        """Returns {} when bootstrap file contains a JSON array instead of object."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        (agdt_dir / "runtime-bootstrap.json").write_text("[1, 2, 3]", encoding="utf-8")

        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            result = state.get_bootstrap_state()

        assert result == {}

    def test_returns_empty_dict_when_file_has_invalid_encoding(self, tmp_path):
        """Returns {} when the bootstrap file has invalid UTF-8 bytes."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        # Write raw bytes that are not valid UTF-8
        (agdt_dir / "runtime-bootstrap.json").write_bytes(b"\x80\x81\x82\x83")

        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            result = state.get_bootstrap_state()

        assert result == {}

    def test_reads_identity_from_identity_json(self, tmp_path):
        """Reads identity from identity.json (new cache) instead of bootstrap."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()

        (agdt_dir / "identity.json").write_text(json.dumps({"identity": "ama", "email": "a@b.com"}), encoding="utf-8")
        (agdt_dir / "runtime-bootstrap.json").write_text(json.dumps({"worktree_key": "DFLY-42"}), encoding="utf-8")

        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            result = state.get_bootstrap_state()

        assert result == {"identity": "ama", "worktree_key": "DFLY-42"}

    def test_identity_json_takes_precedence_over_bootstrap_identity(self, tmp_path):
        """identity.json identity overrides legacy identity in runtime-bootstrap.json."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()

        (agdt_dir / "identity.json").write_text(
            json.dumps({"identity": "new", "email": "new@example.com"}), encoding="utf-8"
        )
        # Legacy bootstrap still has old identity
        (agdt_dir / "runtime-bootstrap.json").write_text(
            json.dumps({"identity": "old", "worktree_key": "DFLY-1"}), encoding="utf-8"
        )

        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            result = state.get_bootstrap_state()

        assert result["identity"] == "new"  # identity.json wins
        assert result["worktree_key"] == "DFLY-1"
