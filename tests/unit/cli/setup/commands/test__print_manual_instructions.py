"""Tests for _print_manual_instructions."""

from pathlib import Path

from agentic_devtools.cli.setup.commands import _print_manual_instructions


class TestPrintManualInstructions:
    """Tests for _print_manual_instructions."""

    def test_nothing_to_print_when_no_vars_and_on_path(self, capsys):
        """Prints nothing when no env vars needed and managed bin is on PATH."""
        _print_manual_instructions(
            npmrc_path=None,
            unified_path=None,
            managed_on_path=True,
            shell_type=None,
        )
        out = capsys.readouterr().out
        assert out == ""

    def test_bash_instructions_with_all_vars(self, capsys):
        """Prints bash/zsh instructions with all env vars and PATH."""
        _print_manual_instructions(
            npmrc_path=Path("/home/user/.agdt/npmrc"),
            unified_path=Path("/home/user/.agdt/certs/bundle.pem"),
            managed_on_path=False,
            shell_type="bash",
        )
        out = capsys.readouterr().out
        assert "~/.bashrc or ~/.zshrc" in out
        assert "NPM_CONFIG_USERCONFIG" in out
        assert "REQUESTS_CA_BUNDLE" in out
        assert "NODE_EXTRA_CA_CERTS" in out
        assert "$HOME/.agdt/bin" in out

    def test_zsh_instructions_with_all_vars(self, capsys):
        """Prints zsh instructions (same as bash) with all env vars."""
        _print_manual_instructions(
            npmrc_path=Path("/home/user/.agdt/npmrc"),
            unified_path=Path("/home/user/.agdt/certs/bundle.pem"),
            managed_on_path=True,
            shell_type="zsh",
        )
        out = capsys.readouterr().out
        assert "NPM_CONFIG_USERCONFIG" in out
        assert "REQUESTS_CA_BUNDLE" in out
        assert "NODE_EXTRA_CA_CERTS" in out

    def test_bash_instructions_path_only(self, capsys):
        """Prints bash PATH instructions when only PATH is needed."""
        _print_manual_instructions(
            npmrc_path=None,
            unified_path=None,
            managed_on_path=False,
            shell_type="bash",
        )
        out = capsys.readouterr().out
        assert "$HOME/.agdt/bin" in out
        assert "NPM_CONFIG_USERCONFIG" not in out

    def test_powershell_instructions_with_all_vars(self, capsys):
        """Prints PowerShell instructions with all env vars and PATH."""
        _print_manual_instructions(
            npmrc_path=Path("/home/user/.agdt/npmrc"),
            unified_path=Path("/home/user/.agdt/certs/bundle.pem"),
            managed_on_path=False,
            shell_type="powershell",
        )
        out = capsys.readouterr().out
        assert "$PROFILE" in out
        assert "$env:NPM_CONFIG_USERCONFIG" in out
        assert "$env:REQUESTS_CA_BUNDLE" in out
        assert "$env:NODE_EXTRA_CA_CERTS" in out
        assert "$env:PATH" in out

    def test_powershell_instructions_path_only(self, capsys):
        """Prints PowerShell PATH instructions when only PATH is needed."""
        _print_manual_instructions(
            npmrc_path=None,
            unified_path=None,
            managed_on_path=False,
            shell_type="powershell",
        )
        out = capsys.readouterr().out
        assert "$env:PATH" in out
        assert "$env:NPM_CONFIG_USERCONFIG" not in out

    def test_unknown_shell_instructions_with_all_vars(self, capsys):
        """Prints both bash and PowerShell examples for unknown shell."""
        _print_manual_instructions(
            npmrc_path=Path("/home/user/.agdt/npmrc"),
            unified_path=Path("/home/user/.agdt/certs/bundle.pem"),
            managed_on_path=False,
            shell_type=None,
        )
        out = capsys.readouterr().out
        assert "bash / zsh" in out
        assert "PowerShell" in out
        assert "export NPM_CONFIG_USERCONFIG" in out
        assert "$env:NPM_CONFIG_USERCONFIG" in out
        assert "export REQUESTS_CA_BUNDLE" in out
        assert "$env:REQUESTS_CA_BUNDLE" in out
        assert "export NODE_EXTRA_CA_CERTS" in out
        assert "$env:NODE_EXTRA_CA_CERTS" in out
        assert "$HOME/.agdt/bin" in out
        assert "$env:PATH" in out

    def test_unknown_shell_instructions_path_only(self, capsys):
        """Prints both bash and PowerShell PATH examples for unknown shell."""
        _print_manual_instructions(
            npmrc_path=None,
            unified_path=None,
            managed_on_path=False,
            shell_type=None,
        )
        out = capsys.readouterr().out
        assert "bash / zsh" in out
        assert "PowerShell" in out
        assert "$HOME/.agdt/bin" in out
        assert "$env:PATH" in out

    def test_unknown_shell_npmrc_only(self, capsys):
        """Prints both bash and PowerShell examples with only npmrc."""
        _print_manual_instructions(
            npmrc_path=Path("/home/user/.agdt/npmrc"),
            unified_path=None,
            managed_on_path=True,
            shell_type=None,
        )
        out = capsys.readouterr().out
        assert "export NPM_CONFIG_USERCONFIG" in out
        assert "$env:NPM_CONFIG_USERCONFIG" in out
        assert "REQUESTS_CA_BUNDLE" not in out

    def test_unknown_shell_unified_only(self, capsys):
        """Prints both bash and PowerShell examples with only unified path."""
        _print_manual_instructions(
            npmrc_path=None,
            unified_path=Path("/home/user/.agdt/certs/bundle.pem"),
            managed_on_path=True,
            shell_type=None,
        )
        out = capsys.readouterr().out
        assert "export REQUESTS_CA_BUNDLE" in out
        assert "$env:REQUESTS_CA_BUNDLE" in out
        assert "export NODE_EXTRA_CA_CERTS" in out
        assert "$env:NODE_EXTRA_CA_CERTS" in out
        assert "NPM_CONFIG_USERCONFIG" not in out

    def test_powershell_on_path_with_unified(self, capsys):
        """Prints PowerShell instructions with unified path and managed bin on PATH."""
        _print_manual_instructions(
            npmrc_path=None,
            unified_path=Path("/some/bundle.pem"),
            managed_on_path=True,
            shell_type="powershell",
        )
        out = capsys.readouterr().out
        assert "$env:REQUESTS_CA_BUNDLE" in out
        assert "$env:NODE_EXTRA_CA_CERTS" in out
        assert "$env:PATH" not in out
