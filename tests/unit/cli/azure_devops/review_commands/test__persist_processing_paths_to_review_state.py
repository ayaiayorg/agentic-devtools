"""Tests for _persist_processing_paths_to_review_state()."""

import json
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.review_commands import _persist_processing_paths_to_review_state


class TestPersistProcessingPathsToReviewState:
    """Tests for _persist_processing_paths_to_review_state()."""

    def test_persists_processing_path_for_matching_files(self, tmp_path):
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        queue_path = prompts_dir / "queue.json"
        queue_path.write_text(
            json.dumps(
                {
                    "pending": [
                        {
                            "path": "/src/app.ts",
                            "normalizedPath": "/src/app.ts",
                            "processingPath": "inherited",
                        },
                        {
                            "path": "/src/other.ts",
                            "normalizedPath": "/src/other.ts",
                            "processingPath": "reviewed",
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )

        app_entry = MagicMock()
        other_entry = MagicMock()
        untouched_entry = MagicMock()
        state = MagicMock()
        state.files = {
            "/src/app.ts": app_entry,
            "/src/other.ts": other_entry,
            "/src/untouched.ts": untouched_entry,
        }

        with patch("agentic_devtools.cli.azure_devops.review_state.read_modify_write_review_state") as mock_rmw:
            mock_rmw.return_value.__enter__ = MagicMock(return_value=state)
            mock_rmw.return_value.__exit__ = MagicMock(return_value=False)

            _persist_processing_paths_to_review_state(123, prompts_dir)

        assert app_entry.processingPath == "inherited"
        assert other_entry.processingPath == "reviewed"
        assert untouched_entry.processingPath is None

    def test_skips_when_queue_file_missing(self, tmp_path):
        with patch("agentic_devtools.cli.azure_devops.review_state.read_modify_write_review_state") as mock_rmw:
            _persist_processing_paths_to_review_state(123, tmp_path)

        mock_rmw.assert_not_called()

    def test_skips_when_pending_is_not_list(self, tmp_path):
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "queue.json").write_text(json.dumps({"pending": {}}), encoding="utf-8")

        with patch("agentic_devtools.cli.azure_devops.review_state.read_modify_write_review_state") as mock_rmw:
            _persist_processing_paths_to_review_state(123, prompts_dir)

        mock_rmw.assert_not_called()

    def test_warns_on_persist_error(self, tmp_path, capsys):
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "queue.json").write_text(
            json.dumps({"pending": [{"normalizedPath": "/src/app.ts", "processingPath": "reviewed"}]}),
            encoding="utf-8",
        )

        with patch(
            "agentic_devtools.cli.azure_devops.review_state.read_modify_write_review_state",
            side_effect=OSError("boom"),
        ):
            _persist_processing_paths_to_review_state(123, prompts_dir)

        captured = capsys.readouterr()
        assert "Could not persist processing path metadata" in captured.err

    def test_skips_when_queue_json_invalid(self, tmp_path):
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "queue.json").write_text("{", encoding="utf-8")

        with patch("agentic_devtools.cli.azure_devops.review_state.read_modify_write_review_state") as mock_rmw:
            _persist_processing_paths_to_review_state(123, prompts_dir)

        mock_rmw.assert_not_called()

    def test_skips_when_no_valid_processing_entries(self, tmp_path):
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "queue.json").write_text(
            json.dumps(
                {
                    "pending": [
                        "not-a-dict",
                        {"normalizedPath": "/src/a.ts", "processingPath": ""},
                        {"path": 7, "processingPath": "reviewed"},
                    ]
                }
            ),
            encoding="utf-8",
        )

        with patch("agentic_devtools.cli.azure_devops.review_state.read_modify_write_review_state") as mock_rmw:
            _persist_processing_paths_to_review_state(123, prompts_dir)

        mock_rmw.assert_not_called()

    def test_normalizes_path_when_normalized_path_missing(self, tmp_path):
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "queue.json").write_text(
            json.dumps({"pending": [{"path": "src/app.ts", "processingPath": "reviewed"}]}),
            encoding="utf-8",
        )

        app_entry = MagicMock()
        state = MagicMock()
        state.files = {"/src/app.ts": app_entry}

        with patch("agentic_devtools.cli.azure_devops.review_state.read_modify_write_review_state") as mock_rmw:
            mock_rmw.return_value.__enter__ = MagicMock(return_value=state)
            mock_rmw.return_value.__exit__ = MagicMock(return_value=False)

            _persist_processing_paths_to_review_state(123, prompts_dir)

        assert app_entry.processingPath == "reviewed"
