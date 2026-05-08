"""Tests for edge cases in required_setup."""

from unittest.mock import patch

from agentic_devtools.cli.setup.script_generators.required_setup import (
    cleanup_artifacts,
    detect_corrupted_artifacts,
    setup_git_hooks,
)

_MOD = "agentic_devtools.cli.setup.script_generators.required_setup"


class TestEdgeCases:
    """Edge-case tests for required_setup."""

    def test_read_only_site_packages(self, tmp_path, monkeypatch):
        """Permission errors during cleanup are handled gracefully."""
        sp = tmp_path / "site-packages"
        sp.mkdir()
        d = sp / "~gentic-devtools"
        d.mkdir()
        (d / "file.py").write_text("x", encoding="utf-8")

        def failing_rmtree(path, **kw):
            raise PermissionError("read-only")

        with patch("shutil.rmtree", side_effect=failing_rmtree):
            msgs = cleanup_artifacts([d])
        assert any("Permission denied" in m for m in msgs)

    def test_non_git_context(self):
        """setup_git_hooks returns None when git is not available."""
        with patch(
            f"{_MOD}.subprocess.run",
            side_effect=FileNotFoundError("git not found"),
        ):
            result = setup_git_hooks()
            assert result is None

    def test_multiple_orphaned_artifacts(self, tmp_path, monkeypatch):
        """Multiple corrupted artifacts are all detected."""
        sp = tmp_path / "site-packages"
        sp.mkdir()
        (sp / "~gentic-devtools").mkdir()
        (sp / "~gentic_devtools").mkdir()
        dist = sp / "agentic-devtools-0.1.0.dist-info"
        dist.mkdir()
        (sp / "_editable_impl_agentic_devtools.pth").write_text("x", encoding="utf-8")

        monkeypatch.setattr(
            f"{_MOD}._site_packages_dirs",
            lambda: [str(sp)],
        )
        artifacts = detect_corrupted_artifacts()
        assert len(artifacts) == 4
