"""
Tests for run_details_commands module.
"""

import json
from unittest.mock import patch

from agentic_devtools.cli.azure_devops.run_details_commands import (
    _save_json,
)


class TestSaveJson:
    """Tests for _save_json helper."""

    def test_saves_file_with_correct_name(self, tmp_path):
        """Should save JSON to correctly named file."""
        with patch(
            "agentic_devtools.cli.azure_devops.run_details_commands._get_temp_folder",
            return_value=tmp_path,
        ):
            data = {"test": "data"}
            filepath = _save_json(data, 12345, "pipeline")

            assert filepath.name == "temp-wb-patch-run-12345-pipeline.json"
            assert filepath.exists()

            with open(filepath) as f:
                saved_data = json.load(f)
            assert saved_data == {"test": "data"}

    def test_saves_error_file(self, tmp_path):
        """Should save error files with correct suffix."""
        with patch(
            "agentic_devtools.cli.azure_devops.run_details_commands._get_temp_folder",
            return_value=tmp_path,
        ):
            data = {"error": "Something went wrong"}
            filepath = _save_json(data, 99, "build-error")

            assert filepath.name == "temp-wb-patch-run-99-build-error.json"
            assert filepath.exists()
