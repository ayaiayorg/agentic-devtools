"""Tests for _resolve_repo_root."""

import pytest

from agentic_devtools.cli.azure_devops.review_config import ReviewConfigError
from agentic_devtools.cli.review.config_commands import _resolve_repo_root


class TestResolveRepoRoot:
    """Tests for _resolve_repo_root."""

    def test_cwd_when_no_config_path(self):
        """Returns CWD when no config_path given."""
        from pathlib import Path

        result = _resolve_repo_root(None)
        assert result == Path.cwd()

    def test_parent_parent_when_yaml_config_path(self, tmp_path):
        """Derives repo root from YAML config path."""
        config_file = tmp_path / ".agdt" / "review-config.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.touch()
        result = _resolve_repo_root(str(config_file))
        assert result == tmp_path

    def test_directory_path_returned_as_is(self, tmp_path):
        """Returns directory path directly when not a YAML file."""
        result = _resolve_repo_root(str(tmp_path))
        assert result == tmp_path.resolve()

    def test_yml_extension_treated_as_config_file(self, tmp_path):
        """Handles .yml extension the same as .yaml."""
        config_file = tmp_path / ".agdt" / "review-config.yml"
        config_file.parent.mkdir(parents=True)
        config_file.touch()
        result = _resolve_repo_root(str(config_file))
        assert result == tmp_path

    def test_rejects_non_canonical_yaml_path(self, tmp_path):
        """Raises ReviewConfigError for YAML file not at .agdt/review-config.*."""
        with pytest.raises(ReviewConfigError, match=r"review-config\.yaml.*review-config\.yml"):
            _resolve_repo_root("/repo/custom-config.yaml")

    def test_rejects_missing_yaml_config_file(self, tmp_path):
        """Raises ReviewConfigError when canonical YAML config file does not exist."""
        missing = tmp_path / ".agdt" / "review-config.yaml"
        with pytest.raises(ReviewConfigError, match="does not exist"):
            _resolve_repo_root(str(missing))

    def test_rejects_nonexistent_repo_root(self, tmp_path):
        """Raises ReviewConfigError when directory path does not exist."""
        missing = tmp_path / "no-such-dir"
        with pytest.raises(ReviewConfigError, match="does not exist"):
            _resolve_repo_root(str(missing))

    def test_rejects_file_as_repo_root(self, tmp_path):
        """Raises ReviewConfigError when path is a file, not a directory."""
        some_file = tmp_path / "not-a-dir.txt"
        some_file.touch()
        with pytest.raises(ReviewConfigError, match="is not a directory"):
            _resolve_repo_root(str(some_file))
