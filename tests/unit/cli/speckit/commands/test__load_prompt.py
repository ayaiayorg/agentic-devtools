"""Tests for _load_prompt."""

import pytest

from agentic_devtools.cli.speckit.commands import _load_prompt


def test_load_prompt_no_repo_root(monkeypatch):
    """Exit with code 1 when not inside a git repository."""
    monkeypatch.setattr(
        "agentic_devtools.cli.speckit.commands._get_git_repo_root",
        lambda: None,
    )
    with pytest.raises(SystemExit) as exc_info:
        _load_prompt("specify", "some args")
    assert exc_info.value.code == 1


def test_load_prompt_agent_file_not_found(tmp_path, monkeypatch):
    """Exit with code 1 when the agent file does not exist."""
    monkeypatch.setattr(
        "agentic_devtools.cli.speckit.commands._get_git_repo_root",
        lambda: tmp_path,
    )
    (tmp_path / ".github" / "agents").mkdir(parents=True)
    with pytest.raises(SystemExit) as exc_info:
        _load_prompt("specify", "some args")
    assert exc_info.value.code == 1


def test_load_prompt_strips_frontmatter_and_substitutes(tmp_path, monkeypatch):
    """Happy path: strip YAML frontmatter and replace $ARGUMENTS."""
    monkeypatch.setattr(
        "agentic_devtools.cli.speckit.commands._get_git_repo_root",
        lambda: tmp_path,
    )
    agents_dir = tmp_path / ".github" / "agents"
    agents_dir.mkdir(parents=True)
    agent_file = agents_dir / "speckit.specify.agent.md"
    agent_file.write_text(
        "---\ndescription: test\n---\nHello $ARGUMENTS world",
        encoding="utf-8",
    )
    result = _load_prompt("specify", "my feature")
    assert result == "Hello my feature world"


def test_load_prompt_no_frontmatter(tmp_path, monkeypatch):
    """When no frontmatter present, content is returned with substitution."""
    monkeypatch.setattr(
        "agentic_devtools.cli.speckit.commands._get_git_repo_root",
        lambda: tmp_path,
    )
    agents_dir = tmp_path / ".github" / "agents"
    agents_dir.mkdir(parents=True)
    agent_file = agents_dir / "speckit.plan.agent.md"
    agent_file.write_text("Plan for $ARGUMENTS", encoding="utf-8")
    result = _load_prompt("plan", "dark mode")
    assert result == "Plan for dark mode"
