"""Tests for agentic_devtools.skill_injector._ensure_github_gitignore_unignores_agdt."""

from pathlib import Path
from unittest.mock import patch

from agentic_devtools.skill_injector import _ensure_github_gitignore_unignores_agdt


class TestEnsureGithubGitignoreUnignoresAgdt:
    """Tests for the helper that manages .github/.gitignore un-ignore rules."""

    def test_returns_without_raising_when_existing_gitignore_read_fails(self, tmp_path: Path):
        """Read errors should be ignored to keep injection best-effort."""
        github_dir = tmp_path / ".github"
        github_dir.mkdir(parents=True)
        github_gitignore = github_dir / ".gitignore"
        original = "existing content\n"
        github_gitignore.write_text(original, encoding="utf-8")

        with patch("pathlib.Path.read_text", side_effect=OSError("cannot read")):
            _ensure_github_gitignore_unignores_agdt(tmp_path)

        assert github_gitignore.read_text(encoding="utf-8") == original

    def test_returns_without_raising_when_gitignore_write_fails(self, tmp_path: Path):
        """Write errors should be ignored to keep injection best-effort."""
        github_dir = tmp_path / ".github"
        github_dir.mkdir(parents=True)
        github_gitignore = github_dir / ".gitignore"

        with patch("pathlib.Path.write_text", side_effect=OSError("cannot write")):
            _ensure_github_gitignore_unignores_agdt(tmp_path)

        assert not github_gitignore.exists()
