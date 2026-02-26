"""Tests for _run."""

from agentic_devtools.cli.speckit.commands import _run


def test_run_with_repo_root(tmp_path, monkeypatch, capsys):
    """_run prints the prompt and saves to scripts/temp/."""
    monkeypatch.setattr(
        "agentic_devtools.cli.speckit.commands._get_git_repo_root",
        lambda: tmp_path,
    )
    agents_dir = tmp_path / ".github" / "agents"
    agents_dir.mkdir(parents=True)
    agent_file = agents_dir / "speckit.analyze.agent.md"
    agent_file.write_text("Analyze $ARGUMENTS", encoding="utf-8")

    _run("analyze", "my project")

    captured = capsys.readouterr()
    assert "SPECKIT: ANALYZE" in captured.out
    assert "Analyze my project" in captured.out
    assert "[Prompt saved to:" in captured.out

    saved = tmp_path / "scripts" / "temp" / "temp-speckit-analyze-prompt.md"
    assert saved.exists()
    assert saved.read_text(encoding="utf-8") == "Analyze my project"


def test_run_without_repo_root_for_save(tmp_path, monkeypatch, capsys):
    """_run still prints prompt when repo root is None on second call."""
    call_count = {"n": 0}

    def mock_root():
        call_count["n"] += 1
        if call_count["n"] == 1:
            return tmp_path
        return None

    monkeypatch.setattr(
        "agentic_devtools.cli.speckit.commands._get_git_repo_root",
        mock_root,
    )
    agents_dir = tmp_path / ".github" / "agents"
    agents_dir.mkdir(parents=True)
    agent_file = agents_dir / "speckit.plan.agent.md"
    agent_file.write_text("Plan content", encoding="utf-8")

    _run("plan", "")

    captured = capsys.readouterr()
    assert "SPECKIT: PLAN" in captured.out
    assert "Plan content" in captured.out
    assert "[Prompt saved to:" not in captured.out
