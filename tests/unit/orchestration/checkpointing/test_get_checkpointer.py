"""Tests for get_checkpointer factory function."""

from unittest.mock import patch

from langgraph.checkpoint.sqlite import SqliteSaver

from agentic_devtools.orchestration.checkpointing import get_checkpointer


class TestGetCheckpointer:
    """Tests for get_checkpointer()."""

    def test_returns_sqlite_saver_instance(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        saver = get_checkpointer(db_path)
        try:
            assert isinstance(saver, SqliteSaver)
        finally:
            saver.conn.close()

    def test_creates_sqlite_file(self, tmp_path):
        db_path = tmp_path / "test.db"
        saver = get_checkpointer(str(db_path))
        try:
            assert db_path.exists()
        finally:
            saver.conn.close()

    def test_creates_parent_directories(self, tmp_path):
        db_path = tmp_path / "nested" / "dir" / "test.db"
        saver = get_checkpointer(str(db_path))
        try:
            assert db_path.parent.exists()
            assert db_path.exists()
        finally:
            saver.conn.close()

    def test_default_path_uses_git_repo_root(self, tmp_path):
        fake_root = tmp_path / "repo"
        fake_root.mkdir()
        with patch(
            "agentic_devtools.orchestration.checkpointing._get_git_repo_root",
            return_value=fake_root,
        ):
            saver = get_checkpointer()
        try:
            expected = fake_root / ".agdt" / "orchestration.db"
            assert expected.exists()
        finally:
            saver.conn.close()

    def test_default_path_falls_back_to_cwd_when_no_git_root(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with patch(
            "agentic_devtools.orchestration.checkpointing._get_git_repo_root",
            return_value=None,
        ):
            saver = get_checkpointer()
        try:
            expected = tmp_path / ".agdt" / "orchestration.db"
            assert expected.exists()
        finally:
            saver.conn.close()

    def test_custom_path_overrides_default(self, tmp_path):
        custom = tmp_path / "custom" / "my.db"
        saver = get_checkpointer(str(custom))
        try:
            assert custom.exists()
            default = tmp_path / ".agdt" / "orchestration.db"
            assert not default.exists()
        finally:
            saver.conn.close()

    def test_schema_is_initialized(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        saver = get_checkpointer(db_path)
        try:
            cursor = saver.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}
            assert "checkpoints" in tables
        finally:
            saver.conn.close()

    def test_existing_directory_no_error(self, tmp_path):
        db_dir = tmp_path / "existing"
        db_dir.mkdir()
        db_path = str(db_dir / "test.db")
        saver = get_checkpointer(db_path)
        try:
            assert isinstance(saver, SqliteSaver)
        finally:
            saver.conn.close()
