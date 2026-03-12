"""Tests for _run."""

from unittest.mock import patch

from agentic_devtools.cli.speckit.commands import _run


def test_run_with_repo_root(tmp_path, monkeypatch, capsys):
    """_run prints the prompt and saves to the state directory."""
    monkeypatch.setattr(
        "agentic_devtools.cli.speckit.commands._get_git_repo_root",
        lambda: tmp_path,
    )
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    with patch("agentic_devtools.cli.speckit.commands.get_state_dir", return_value=state_dir):
        agents_dir = tmp_path / ".github" / "agents"
        agents_dir.mkdir(parents=True)
        agent_file = agents_dir / "speckit.analyze.agent.md"
        agent_file.write_text("Analyze $ARGUMENTS", encoding="utf-8")

        _run("analyze", "my project")

    captured = capsys.readouterr()
    assert "SPECKIT: ANALYZE" in captured.out
    assert "Analyze my project" in captured.out
    assert "[Prompt saved to:" in captured.out

    saved = state_dir / "temp-speckit-analyze-prompt.md"
    assert saved.exists()
    assert saved.read_text(encoding="utf-8") == "Analyze my project"
