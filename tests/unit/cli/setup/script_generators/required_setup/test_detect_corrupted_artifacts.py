"""Tests for detect_corrupted_artifacts."""

from agentic_devtools.cli.setup.script_generators.required_setup import detect_corrupted_artifacts


class TestDetectCorruptedArtifacts:
    """Tests for detect_corrupted_artifacts."""

    def test_detects_tilde_prefixed_directories(self, tmp_path, monkeypatch):
        """Tilde-prefixed directories are flagged as corrupted."""
        sp = tmp_path / "site-packages"
        sp.mkdir()
        (sp / "~gentic-devtools").mkdir()
        (sp / "~gentic_devtools").mkdir()
        monkeypatch.setattr(
            "agentic_devtools.cli.setup.script_generators.required_setup._site_packages_dirs",
            lambda: [str(sp)],
        )
        artifacts = detect_corrupted_artifacts()
        names = {a.name for a in artifacts}
        assert "~gentic-devtools" in names
        assert "~gentic_devtools" in names

    def test_detects_dist_info_without_record(self, tmp_path, monkeypatch):
        """dist-info directories without RECORD are flagged."""
        sp = tmp_path / "site-packages"
        sp.mkdir()
        dist = sp / "agentic_devtools-1.0.0.dist-info"
        dist.mkdir()
        # No RECORD file
        monkeypatch.setattr(
            "agentic_devtools.cli.setup.script_generators.required_setup._site_packages_dirs",
            lambda: [str(sp)],
        )
        artifacts = detect_corrupted_artifacts()
        assert len(artifacts) == 1
        assert artifacts[0].name == "agentic_devtools-1.0.0.dist-info"

    def test_skips_dist_info_with_record(self, tmp_path, monkeypatch):
        """dist-info directories WITH RECORD are not flagged."""
        sp = tmp_path / "site-packages"
        sp.mkdir()
        dist = sp / "agentic_devtools-1.0.0.dist-info"
        dist.mkdir()
        (dist / "RECORD").write_text("something", encoding="utf-8")
        monkeypatch.setattr(
            "agentic_devtools.cli.setup.script_generators.required_setup._site_packages_dirs",
            lambda: [str(sp)],
        )
        artifacts = detect_corrupted_artifacts()
        assert len(artifacts) == 0

    def test_detects_editable_pth(self, tmp_path, monkeypatch):
        """Editable .pth files are flagged."""
        sp = tmp_path / "site-packages"
        sp.mkdir()
        (sp / "_editable_impl_agentic_devtools.pth").write_text("x", encoding="utf-8")
        monkeypatch.setattr(
            "agentic_devtools.cli.setup.script_generators.required_setup._site_packages_dirs",
            lambda: [str(sp)],
        )
        artifacts = detect_corrupted_artifacts()
        assert len(artifacts) == 1
        assert artifacts[0].name == "_editable_impl_agentic_devtools.pth"

    def test_no_artifacts_in_clean_site_packages(self, tmp_path, monkeypatch):
        """Clean site-packages returns no artifacts."""
        sp = tmp_path / "site-packages"
        sp.mkdir()
        (sp / "some_package").mkdir()
        monkeypatch.setattr(
            "agentic_devtools.cli.setup.script_generators.required_setup._site_packages_dirs",
            lambda: [str(sp)],
        )
        assert detect_corrupted_artifacts() == []

    def test_handles_nonexistent_site_packages(self, monkeypatch):
        """Nonexistent site-packages dir is skipped."""
        monkeypatch.setattr(
            "agentic_devtools.cli.setup.script_generators.required_setup._site_packages_dirs",
            lambda: ["/nonexistent/dir/xyz"],
        )
        assert detect_corrupted_artifacts() == []
