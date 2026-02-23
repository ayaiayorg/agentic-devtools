"""Tests for agentic_devtools.state.clear_temp_folder."""

from unittest.mock import patch

from agentic_devtools import state


class TestClearTempFolder:
    """Tests for clear_temp_folder function."""

    def test_clear_temp_folder_removes_state_file(self, temp_state_dir):
        """Test that clear_temp_folder removes the state file."""
        state.set_value("key1", "value1")
        state.set_value("key2", "value2")

        assert state.get_value("key1") == "value1"

        state.clear_temp_folder()

        assert state.get_value("key1") is None
        assert state.get_value("key2") is None

    def test_clear_temp_folder_removes_other_files(self, temp_state_dir):
        """Test that clear_temp_folder removes other files in temp directory."""
        (temp_state_dir / "temp-file.json").write_text("{}", encoding="utf-8")
        (temp_state_dir / "another-file.txt").write_text("content", encoding="utf-8")

        assert (temp_state_dir / "temp-file.json").exists()
        assert (temp_state_dir / "another-file.txt").exists()

        state.clear_temp_folder()

        remaining_files = list(temp_state_dir.iterdir())
        assert len(remaining_files) <= 1
        assert state.load_state() == {}

    def test_clear_temp_folder_removes_subdirectories(self, temp_state_dir):
        """Test that clear_temp_folder removes subdirectories."""
        subdir = temp_state_dir / "subdir"
        subdir.mkdir()
        (subdir / "nested-file.json").write_text("{}", encoding="utf-8")

        assert subdir.exists()

        state.clear_temp_folder()

        assert not subdir.exists()

    def test_clear_temp_folder_with_preserve_keys(self, temp_state_dir):
        """Test that clear_temp_folder preserves specified keys."""
        state.set_value("key1", "value1")
        state.set_value("key2", "value2")
        state.set_value("key3", "value3")

        state.clear_temp_folder(preserve_keys={"key1": "value1", "key3": "preserved"})

        assert state.get_value("key1") == "value1"
        assert state.get_value("key2") is None
        assert state.get_value("key3") == "preserved"

    def test_clear_temp_folder_preserves_nested_keys(self, temp_state_dir):
        """Test that clear_temp_folder preserves nested keys correctly."""
        state.set_value("jira.issue_key", "DFLY-1234")
        state.set_value("jira.summary", "Test summary")
        state.set_value("other", "value")

        state.clear_temp_folder(preserve_keys={"jira": {"issue_key": "DFLY-5678"}})

        assert state.get_value("jira.issue_key") == "DFLY-5678"
        assert state.get_value("jira.summary") is None
        assert state.get_value("other") is None

    def test_clear_temp_folder_recreates_directory(self, temp_state_dir):
        """Test that clear_temp_folder recreates the temp directory."""
        state.set_value("key", "value")

        state.clear_temp_folder()

        assert temp_state_dir.exists()

        state.set_value("new_key", "new_value")
        assert state.get_value("new_key") == "new_value"

    def test_clear_temp_folder_handles_missing_directory(self, tmp_path):
        """Test that clear_temp_folder handles missing directory gracefully."""
        missing_dir = tmp_path / "nonexistent"

        with patch.object(state, "get_state_dir", return_value=missing_dir):
            state.clear_temp_folder()

            assert missing_dir.exists()

    def test_clear_temp_folder_ignores_oserror_on_rmtree(self, temp_state_dir):
        """Test that clear_temp_folder ignores OSError when removing directories."""
        subdir = temp_state_dir / "subdir"
        subdir.mkdir()
        (subdir / "file.txt").write_text("content")

        def raise_oserror(path, **kwargs):
            raise OSError("Directory in use")

        with patch("shutil.rmtree", raise_oserror):
            state.clear_temp_folder()
