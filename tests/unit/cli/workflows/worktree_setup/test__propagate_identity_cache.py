"""Tests for _propagate_identity_cache() in worktree_setup.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from agentic_devtools.cli.workflows.worktree_setup import _propagate_identity_cache
from agentic_devtools.state import IDENTITY_CACHE_FILENAME

_MODULE = "agentic_devtools.cli.workflows.worktree_setup"


class TestPropagateIdentityCache:
    """Tests for _propagate_identity_cache()."""

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
            _propagate_identity_cache(str(worktree))

        dst = worktree / ".agdt" / IDENTITY_CACHE_FILENAME
        assert dst.is_file()
        assert dst.read_text() == identity_content

    def test_no_op_when_main_repo_root_is_none(self, tmp_path: Path) -> None:
        """No-op when get_main_repo_root returns None."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()

        with patch(f"{_MODULE}.get_main_repo_root", return_value=None):
            _propagate_identity_cache(str(worktree))

        assert not (worktree / ".agdt").exists()

    def test_no_op_when_identity_file_missing(self, tmp_path: Path) -> None:
        """No-op when identity.json does not exist in main repo."""
        main_repo = tmp_path / "main"
        main_repo.mkdir()
        (main_repo / ".agdt").mkdir()

        worktree = tmp_path / "worktree"
        worktree.mkdir()

        with patch(f"{_MODULE}.get_main_repo_root", return_value=str(main_repo)):
            _propagate_identity_cache(str(worktree))

        assert not (worktree / ".agdt").exists()

    def test_oserror_is_non_fatal(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """OSError during copy is caught and logged to stderr."""
        with patch(f"{_MODULE}.get_main_repo_root", side_effect=OSError("disk full")):
            _propagate_identity_cache(str(tmp_path))

        captured = capsys.readouterr()
        assert "Warning: failed to propagate identity cache" in captured.err
        assert "disk full" in captured.err

    def test_valueerror_is_non_fatal(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """ValueError during processing is caught and logged to stderr."""
        with patch(f"{_MODULE}.get_main_repo_root", side_effect=ValueError("bad value")):
            _propagate_identity_cache(str(tmp_path))

        captured = capsys.readouterr()
        assert "Warning: failed to propagate identity cache" in captured.err
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
            _propagate_identity_cache(str(worktree))

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
            _propagate_identity_cache(str(worktree))

        assert not (worktree / ".agdt").exists()
