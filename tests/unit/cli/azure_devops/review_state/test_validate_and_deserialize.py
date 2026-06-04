"""Tests for _validate_and_deserialize helper function."""

import pytest

from agentic_devtools.cli.azure_devops.review_state import ReviewState, _validate_and_deserialize


def _valid_data(pr_id: int = 25365) -> dict:
    return {
        "prId": pr_id,
        "repoId": "repo-guid",
        "repoName": "example-repo-name",
        "project": "ExampleProject",
        "organization": "https://dev.azure.com/example-org",
        "latestIterationId": 5,
        "scaffoldedUtc": "2026-02-25T10:00:00Z",
        "overallSummary": {"threadId": 161000, "commentId": 1771800000, "status": "unreviewed"},
        "folders": {},
        "files": {},
        "commitHash": "abc1234def567890",
    }


class TestValidateAndDeserialize:
    """Tests for _validate_and_deserialize function."""

    def test_returns_review_state_for_valid_data(self, tmp_path):
        """Returns a ReviewState for valid data with commitHash."""
        data = _valid_data()
        file_path = tmp_path / "review-state.json"
        result = _validate_and_deserialize(data, 25365, file_path, delete_on_migration=True)
        assert isinstance(result, ReviewState)
        assert result.prId == 25365

    def test_raises_for_missing_commit_hash(self, tmp_path):
        """Raises FileNotFoundError when commitHash is missing."""
        data = _valid_data()
        del data["commitHash"]
        file_path = tmp_path / "review-state.json"
        with pytest.raises(FileNotFoundError, match="25365"):
            _validate_and_deserialize(data, 25365, file_path, delete_on_migration=False)

    def test_deletes_file_on_migration_when_enabled(self, tmp_path):
        """Deletes local file when delete_on_migration=True and format is old."""
        data = _valid_data()
        del data["commitHash"]
        file_path = tmp_path / "review-state.json"
        file_path.write_text("{}", encoding="utf-8")

        with pytest.raises(FileNotFoundError):
            _validate_and_deserialize(data, 25365, file_path, delete_on_migration=True)
        assert not file_path.exists()

    def test_does_not_delete_file_when_disabled(self, tmp_path):
        """Does not delete file when delete_on_migration=False."""
        data = _valid_data()
        del data["commitHash"]
        file_path = tmp_path / "review-state.json"
        file_path.write_text("{}", encoding="utf-8")

        with pytest.raises(FileNotFoundError):
            _validate_and_deserialize(data, 25365, file_path, delete_on_migration=False)
        assert file_path.exists()

    def test_raises_for_folder_with_nonzero_thread_id(self, tmp_path):
        """Raises when folder has threadId != 0 (old format)."""
        data = _valid_data()
        data["folders"] = {"src": {"threadId": 100, "commentId": 200, "status": "unreviewed", "files": []}}
        file_path = tmp_path / "review-state.json"

        with pytest.raises(FileNotFoundError):
            _validate_and_deserialize(data, 25365, file_path, delete_on_migration=False)

    def test_allows_folder_with_zero_thread_id(self, tmp_path):
        """Passes validation when folder has threadId=0."""
        data = _valid_data()
        data["folders"] = {"src": {"threadId": 0, "commentId": 0, "files": ["/src/a.py"]}}
        file_path = tmp_path / "review-state.json"

        result = _validate_and_deserialize(data, 25365, file_path, delete_on_migration=False)
        assert isinstance(result, ReviewState)

    def test_raises_for_pr_id_mismatch(self, tmp_path):
        """Raises FileNotFoundError when prId in data does not match requested pr_id."""
        data = _valid_data(pr_id=999)
        file_path = tmp_path / "review-state.json"

        with pytest.raises(FileNotFoundError, match="25365"):
            _validate_and_deserialize(data, 25365, file_path, delete_on_migration=False)

    def test_deletes_file_on_pr_id_mismatch_when_enabled(self, tmp_path):
        """Deletes local file when delete_on_migration=True and prId mismatches."""
        data = _valid_data(pr_id=999)
        file_path = tmp_path / "review-state.json"
        file_path.write_text("{}", encoding="utf-8")

        with pytest.raises(FileNotFoundError):
            _validate_and_deserialize(data, 25365, file_path, delete_on_migration=True)
        assert not file_path.exists()

    def test_does_not_delete_on_pr_id_mismatch_when_disabled(self, tmp_path):
        """Does not delete file when delete_on_migration=False and prId mismatches."""
        data = _valid_data(pr_id=999)
        file_path = tmp_path / "review-state.json"
        file_path.write_text("{}", encoding="utf-8")

        with pytest.raises(FileNotFoundError):
            _validate_and_deserialize(data, 25365, file_path, delete_on_migration=False)
        assert file_path.exists()

    def test_raises_when_folders_is_not_dict(self, tmp_path):
        """Treats non-dict folders as needing migration (corrupted state)."""
        data = _valid_data()
        data["folders"] = ["corrupted", "list"]
        file_path = tmp_path / "review-state.json"

        with pytest.raises(FileNotFoundError, match="25365"):
            _validate_and_deserialize(data, 25365, file_path, delete_on_migration=False)

    def test_raises_when_folders_is_string(self, tmp_path):
        """Treats string folders as needing migration (corrupted state)."""
        data = _valid_data()
        data["folders"] = "corrupted"
        file_path = tmp_path / "review-state.json"

        with pytest.raises(FileNotFoundError, match="25365"):
            _validate_and_deserialize(data, 25365, file_path, delete_on_migration=False)

    def test_pr_id_mismatch_delete_when_file_missing(self, tmp_path):
        """Raises FileNotFoundError even when file doesn't exist on disk (PR mismatch)."""
        data = _valid_data(pr_id=999)
        file_path = tmp_path / "review-state.json"
        # File does not exist on disk

        with pytest.raises(FileNotFoundError):
            _validate_and_deserialize(data, 25365, file_path, delete_on_migration=True)

    def test_migration_delete_when_file_missing(self, tmp_path):
        """Raises FileNotFoundError even when file doesn't exist on disk (migration)."""
        data = _valid_data()
        del data["commitHash"]
        file_path = tmp_path / "review-state.json"
        # File does not exist on disk

        with pytest.raises(FileNotFoundError):
            _validate_and_deserialize(data, 25365, file_path, delete_on_migration=True)
