"""Tests for _propagate_agdt_cache() in worktree_setup.py."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from agentic_devtools.cli.workflows.worktree_setup import _propagate_agdt_cache
from agentic_devtools.state import BOOTSTRAP_FILENAME, IDENTITY_CACHE_FILENAME

_MODULE = "agentic_devtools.cli.workflows.worktree_setup"


class TestPropagateAgdtCache:
    """Tests for _propagate_agdt_cache()."""

    def test_copies_identity_file_when_exists(self, tmp_path: Path) -> None:
        """Happy path: copies identity.json from main repo to worktree."""
        main_repo = tmp_path / "main"
        main_repo.mkdir()
        src_agdt = main_repo / ".agdt"
        src_agdt.mkdir()
        identity_content = '{"user": "test"}'
        (src_agdt / IDENTITY_CACHE_FILENAME).write_text(identity_content)

        worktree = tmp_path / "worktree"
        worktree.mkdir()

        with patch(f"{_MODULE}.get_main_repo_root", return_value=str(main_repo)):
            _propagate_agdt_cache(str(worktree))

        dst = worktree / ".agdt" / IDENTITY_CACHE_FILENAME
        assert dst.is_file()
        assert dst.read_text() == identity_content

    def test_no_op_when_main_repo_root_is_none(self, tmp_path: Path) -> None:
        """No-op when get_main_repo_root returns None."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()

        with patch(f"{_MODULE}.get_main_repo_root", return_value=None):
            _propagate_agdt_cache(str(worktree))

        assert not (worktree / ".agdt").exists()

    def test_no_op_when_identity_file_missing(self, tmp_path: Path) -> None:
        """No-op when identity.json does not exist in main repo."""
        main_repo = tmp_path / "main"
        main_repo.mkdir()
        (main_repo / ".agdt").mkdir()

        worktree = tmp_path / "worktree"
        worktree.mkdir()

        with patch(f"{_MODULE}.get_main_repo_root", return_value=str(main_repo)):
            _propagate_agdt_cache(str(worktree))

        assert not (worktree / ".agdt").exists()

    def test_oserror_is_non_fatal(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """OSError during copy is caught and logged to stderr."""
        with patch(f"{_MODULE}.get_main_repo_root", side_effect=OSError("disk full")):
            _propagate_agdt_cache(str(tmp_path))

        captured = capsys.readouterr()
        assert "Warning: failed to propagate AGDT cache" in captured.err
        assert "disk full" in captured.err

    def test_valueerror_is_non_fatal(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """ValueError during processing is caught and logged to stderr."""
        with patch(f"{_MODULE}.get_main_repo_root", side_effect=ValueError("bad value")):
            _propagate_agdt_cache(str(tmp_path))

        captured = capsys.readouterr()
        assert "Warning: failed to propagate AGDT cache" in captured.err
        assert "bad value" in captured.err

    def test_creates_agdt_directory_in_worktree(self, tmp_path: Path) -> None:
        """Ensures .agdt directory is created in worktree when it doesn't exist."""
        main_repo = tmp_path / "main"
        main_repo.mkdir()
        src_agdt = main_repo / ".agdt"
        src_agdt.mkdir()
        (src_agdt / IDENTITY_CACHE_FILENAME).write_text("{}")

        worktree = tmp_path / "worktree"
        worktree.mkdir()
        # .agdt does not exist yet in worktree

        with patch(f"{_MODULE}.get_main_repo_root", return_value=str(main_repo)):
            _propagate_agdt_cache(str(worktree))

        assert (worktree / ".agdt").is_dir()
        assert (worktree / ".agdt" / IDENTITY_CACHE_FILENAME).is_file()

    def test_no_agdt_dir_in_main_repo(self, tmp_path: Path) -> None:
        """No-op when .agdt directory doesn't exist in main repo."""
        main_repo = tmp_path / "main"
        main_repo.mkdir()
        # No .agdt dir

        worktree = tmp_path / "worktree"
        worktree.mkdir()

        with patch(f"{_MODULE}.get_main_repo_root", return_value=str(main_repo)):
            _propagate_agdt_cache(str(worktree))

        assert not (worktree / ".agdt").exists()

    def test_copies_bootstrap_file_when_exists(self, tmp_path: Path) -> None:
        """Happy path: copies both identity.json and runtime-bootstrap.json when both exist."""
        main_repo = tmp_path / "main"
        main_repo.mkdir()
        src_agdt = main_repo / ".agdt"
        src_agdt.mkdir()
        (src_agdt / IDENTITY_CACHE_FILENAME).write_text('{"user": "test"}')
        bootstrap_content = '{"worktree_key": "PROJECT-9999"}'
        (src_agdt / BOOTSTRAP_FILENAME).write_text(bootstrap_content)

        worktree = tmp_path / "worktree"
        worktree.mkdir()

        with patch(f"{_MODULE}.get_main_repo_root", return_value=str(main_repo)):
            _propagate_agdt_cache(str(worktree))

        dst_identity = worktree / ".agdt" / IDENTITY_CACHE_FILENAME
        dst_bootstrap = worktree / ".agdt" / BOOTSTRAP_FILENAME
        assert dst_identity.is_file()
        assert dst_bootstrap.is_file()
        assert dst_bootstrap.read_text() == bootstrap_content

    def test_writes_bootstrap_with_worktree_key_override(self, tmp_path: Path) -> None:
        """When worktree_key is provided, writes fresh bootstrap instead of copying."""
        main_repo = tmp_path / "main"
        main_repo.mkdir()
        src_agdt = main_repo / ".agdt"
        src_agdt.mkdir()
        (src_agdt / IDENTITY_CACHE_FILENAME).write_text('{"user": "test"}')
        # Stale bootstrap in main repo
        (src_agdt / BOOTSTRAP_FILENAME).write_text('{"worktree_key": "STALE-KEY"}')

        worktree = tmp_path / "worktree"
        worktree.mkdir()

        with patch(f"{_MODULE}.get_main_repo_root", return_value=str(main_repo)):
            _propagate_agdt_cache(str(worktree), worktree_key="PROJECT-1234")

        dst_bootstrap = worktree / ".agdt" / BOOTSTRAP_FILENAME
        assert dst_bootstrap.is_file()
        data = json.loads(dst_bootstrap.read_text())
        assert data == {"worktree_key": "PROJECT-1234"}

    def test_creates_bootstrap_when_source_missing_but_worktree_key_provided(self, tmp_path: Path) -> None:
        """Creates runtime-bootstrap.json with worktree_key even when source has no bootstrap."""
        main_repo = tmp_path / "main"
        main_repo.mkdir()
        src_agdt = main_repo / ".agdt"
        src_agdt.mkdir()
        (src_agdt / IDENTITY_CACHE_FILENAME).write_text('{"user": "test"}')
        # No bootstrap file in source

        worktree = tmp_path / "worktree"
        worktree.mkdir()

        with patch(f"{_MODULE}.get_main_repo_root", return_value=str(main_repo)):
            _propagate_agdt_cache(str(worktree), worktree_key="PROJECT-5678")

        dst_bootstrap = worktree / ".agdt" / BOOTSTRAP_FILENAME
        assert dst_bootstrap.is_file()
        data = json.loads(dst_bootstrap.read_text())
        assert data == {"worktree_key": "PROJECT-5678"}

    def test_no_bootstrap_when_source_missing_and_no_worktree_key(self, tmp_path: Path) -> None:
        """No runtime-bootstrap.json propagated when source has none and no key provided."""
        main_repo = tmp_path / "main"
        main_repo.mkdir()
        src_agdt = main_repo / ".agdt"
        src_agdt.mkdir()
        (src_agdt / IDENTITY_CACHE_FILENAME).write_text('{"user": "test"}')
        # No bootstrap file in source

        worktree = tmp_path / "worktree"
        worktree.mkdir()

        with patch(f"{_MODULE}.get_main_repo_root", return_value=str(main_repo)):
            _propagate_agdt_cache(str(worktree))

        dst_bootstrap = worktree / ".agdt" / BOOTSTRAP_FILENAME
        assert not dst_bootstrap.exists()

    def test_propagates_bootstrap_only_without_identity(self, tmp_path: Path) -> None:
        """Propagates bootstrap when identity.json is absent but bootstrap exists (worktree_key=None)."""
        main_repo = tmp_path / "main"
        main_repo.mkdir()
        src_agdt = main_repo / ".agdt"
        src_agdt.mkdir()
        # No identity.json, but bootstrap exists
        bootstrap_content = '{"worktree_key": "PR-100"}'
        (src_agdt / BOOTSTRAP_FILENAME).write_text(bootstrap_content)

        worktree = tmp_path / "worktree"
        worktree.mkdir()

        with patch(f"{_MODULE}.get_main_repo_root", return_value=str(main_repo)):
            _propagate_agdt_cache(str(worktree))

        # Should NOT return early — should propagate bootstrap
        dst_agdt = worktree / ".agdt"
        assert dst_agdt.is_dir()
        dst_bootstrap = dst_agdt / BOOTSTRAP_FILENAME
        assert dst_bootstrap.is_file()
        assert dst_bootstrap.read_text() == bootstrap_content
        # Identity should not be propagated
        assert not (dst_agdt / IDENTITY_CACHE_FILENAME).exists()
