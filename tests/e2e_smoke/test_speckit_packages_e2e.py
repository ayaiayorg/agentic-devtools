"""
E2E smoke tests for spec-kit local extension and preset package resolution.

These tests validate that the monorepo-based spec-kit extension and preset
packages are correctly structured and can be resolved from `.specify/config.yml`
relative paths, simulating a fresh-clone scenario.
"""

from pathlib import Path
from typing import Any

import pytest

# Repository root (tests run from the repo root)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
EXTENSION_DIR = REPO_ROOT / ".specify" / "extensions" / "agdt-workflows"
PRESET_DIR = REPO_ROOT / ".specify" / "presets" / "agdt-templates"


def _safe_parse_manifest_lists(path: Path) -> dict[str, Any]:
    """Parse a manifest file when present; return empty data otherwise."""
    if not path.is_file():
        return {}
    return _parse_manifest_lists(path)


def _parse_manifest_lists(path: Path) -> dict[str, Any]:
    """Parse the simple YAML list structures used by spec-kit manifests."""
    result: dict[str, Any] = {}
    current_section: str | None = None
    current_nested: str | None = None

    for raw_line in path.read_text().splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent == 0 and stripped.endswith(":"):
            current_section = stripped[:-1]
            current_nested = None
            if current_section == "scripts":
                result[current_section] = {}
            else:
                result.setdefault(current_section, [])
        elif indent == 2 and stripped.endswith(":") and current_section == "scripts":
            current_nested = stripped[:-1]
            result.setdefault(current_section, {})
            result[current_section].setdefault(current_nested, [])
        elif stripped.startswith("- ") and current_section:
            value = stripped[2:].strip().strip("'\"")
            if current_section == "scripts" and current_nested:
                result[current_section][current_nested].append(value)
            elif isinstance(result.get(current_section), list):
                result[current_section].append(value)

    return result


EXTENSION_MANIFEST_DATA = _safe_parse_manifest_lists(EXTENSION_DIR / "extension.yml")
PRESET_MANIFEST_DATA = _safe_parse_manifest_lists(PRESET_DIR / "preset.yml")
LEGACY_SPECIFY_PATH_TOKENS = (".specify/templates/", ".specify/scripts/")


class TestSpecKitExtensionPackage:
    """Validate the local extension package structure and integrity."""

    extension_dir = EXTENSION_DIR

    def test_extension_directory_exists(self) -> None:
        """Extension package directory must exist."""
        assert self.extension_dir.is_dir(), f"Extension directory not found: {self.extension_dir}"

    def test_extension_manifest_exists(self) -> None:
        """extension.yml manifest must be present."""
        manifest = self.extension_dir / "extension.yml"
        assert manifest.is_file(), f"extension.yml not found at {manifest}"

    def test_extension_manifest_has_required_fields(self) -> None:
        """extension.yml must contain name, version, description, commands, scripts."""
        manifest = self.extension_dir / "extension.yml"
        content = manifest.read_text()
        required_fields = ["name:", "version:", "description:", "commands:", "scripts:"]
        for field in required_fields:
            assert field in content, f"Required field '{field}' missing from extension.yml"

    def test_extension_commands_directory_exists(self) -> None:
        """Commands directory must exist within the extension."""
        commands_dir = self.extension_dir / "commands"
        assert commands_dir.is_dir(), f"Commands directory not found: {commands_dir}"

    @pytest.mark.parametrize(
        "command_file",
        EXTENSION_MANIFEST_DATA.get("commands", []),
    )
    def test_extension_command_file_exists(self, command_file: str) -> None:
        """Each declared command file must exist."""
        cmd_path = self.extension_dir / "commands" / command_file
        assert cmd_path.is_file(), f"Command file not found: {cmd_path}"

    @pytest.mark.parametrize(
        "command_file",
        EXTENSION_MANIFEST_DATA.get("commands", []),
    )
    def test_extension_command_files_are_non_empty(self, command_file: str) -> None:
        """Each command file must have content."""
        cmd_path = self.extension_dir / "commands" / command_file
        content = cmd_path.read_text()
        assert len(content.strip()) > 0, f"Command file is empty: {cmd_path}"

    def test_extension_scripts_bash_directory_exists(self) -> None:
        """Bash scripts directory must exist."""
        bash_dir = self.extension_dir / "scripts" / "bash"
        assert bash_dir.is_dir(), f"Bash scripts directory not found: {bash_dir}"

    def test_extension_scripts_powershell_directory_exists(self) -> None:
        """PowerShell scripts directory must exist."""
        ps_dir = self.extension_dir / "scripts" / "powershell"
        assert ps_dir.is_dir(), f"PowerShell scripts directory not found: {ps_dir}"

    @pytest.mark.parametrize(
        "script_file",
        EXTENSION_MANIFEST_DATA.get("scripts", {}).get("bash", []),
    )
    def test_extension_bash_script_exists(self, script_file: str) -> None:
        """Each declared bash script must exist."""
        script_path = self.extension_dir / "scripts" / "bash" / script_file
        assert script_path.is_file(), f"Bash script not found: {script_path}"

    @pytest.mark.parametrize(
        "script_file",
        EXTENSION_MANIFEST_DATA.get("scripts", {}).get("bash", []),
    )
    def test_extension_bash_scripts_are_non_empty(self, script_file: str) -> None:
        """Each declared bash script must have content."""
        script_path = self.extension_dir / "scripts" / "bash" / script_file
        content = script_path.read_text()
        assert len(content.strip()) > 0, f"Bash script is empty: {script_path}"

    @pytest.mark.parametrize(
        "script_file",
        EXTENSION_MANIFEST_DATA.get("scripts", {}).get("powershell", []),
    )
    def test_extension_powershell_script_exists(self, script_file: str) -> None:
        """Each declared PowerShell script must exist."""
        script_path = self.extension_dir / "scripts" / "powershell" / script_file
        assert script_path.is_file(), f"PowerShell script not found: {script_path}"

    @pytest.mark.parametrize(
        "script_file",
        EXTENSION_MANIFEST_DATA.get("scripts", {}).get("powershell", []),
    )
    def test_extension_powershell_scripts_are_non_empty(self, script_file: str) -> None:
        """Each declared PowerShell script must have content."""
        script_path = self.extension_dir / "scripts" / "powershell" / script_file
        content = script_path.read_text()
        assert len(content.strip()) > 0, f"PowerShell script is empty: {script_path}"


class TestSpecKitPresetPackage:
    """Validate the local preset package structure and integrity."""

    preset_dir = PRESET_DIR

    def test_preset_directory_exists(self) -> None:
        """Preset package directory must exist."""
        assert self.preset_dir.is_dir(), f"Preset directory not found: {self.preset_dir}"

    def test_preset_manifest_exists(self) -> None:
        """preset.yml manifest must be present."""
        manifest = self.preset_dir / "preset.yml"
        assert manifest.is_file(), f"preset.yml not found at {manifest}"

    def test_preset_manifest_has_required_fields(self) -> None:
        """preset.yml must contain name, version, description, templates."""
        manifest = self.preset_dir / "preset.yml"
        content = manifest.read_text()
        required_fields = ["name:", "version:", "description:", "templates:"]
        for field in required_fields:
            assert field in content, f"Required field '{field}' missing from preset.yml"

    def test_preset_templates_directory_exists(self) -> None:
        """Templates directory must exist within the preset."""
        templates_dir = self.preset_dir / "templates"
        assert templates_dir.is_dir(), f"Templates directory not found: {templates_dir}"

    @pytest.mark.parametrize(
        "template_file",
        PRESET_MANIFEST_DATA.get("templates", []),
    )
    def test_preset_template_file_exists(self, template_file: str) -> None:
        """Each declared template file must exist."""
        tmpl_path = self.preset_dir / "templates" / template_file
        assert tmpl_path.is_file(), f"Template file not found: {tmpl_path}"

    @pytest.mark.parametrize(
        "template_file",
        PRESET_MANIFEST_DATA.get("templates", []),
    )
    def test_preset_template_files_are_non_empty(self, template_file: str) -> None:
        """Each template file must have content."""
        tmpl_path = self.preset_dir / "templates" / template_file
        content = tmpl_path.read_text()
        assert len(content.strip()) > 0, f"Template file is empty: {tmpl_path}"

    def test_preset_vscode_settings_exists(self) -> None:
        """vscode-settings.json asset must exist."""
        settings = self.preset_dir / "templates" / "vscode-settings.json"
        assert settings.is_file(), f"vscode-settings.json not found at {settings}"


class TestSpecKitConfigResolution:
    """Validate that config.yml correctly references local packages."""

    config_path = REPO_ROOT / ".specify" / "config.yml"

    def test_config_yml_exists(self) -> None:
        """config.yml must exist."""
        assert self.config_path.is_file(), f"config.yml not found at {self.config_path}"

    def test_config_references_local_extension(self) -> None:
        """config.yml must reference the local extension package."""
        content = self.config_path.read_text()
        assert "./.specify/extensions/agdt-workflows" in content, (
            "config.yml does not reference the local extension package"
        )

    def test_config_references_local_preset(self) -> None:
        """config.yml must reference the local preset package."""
        content = self.config_path.read_text()
        assert "./.specify/presets/agdt-templates" in content, "config.yml does not reference the local preset package"

    def test_config_extension_path_resolves(self) -> None:
        """The extension path referenced in config.yml must resolve to an existing directory."""
        ext_dir = REPO_ROOT / ".specify" / "extensions" / "agdt-workflows"
        assert ext_dir.is_dir(), f"Extension path from config.yml does not resolve: {ext_dir}"

    def test_config_preset_path_resolves(self) -> None:
        """The preset path referenced in config.yml must resolve to an existing directory."""
        preset_dir = REPO_ROOT / ".specify" / "presets" / "agdt-templates"
        assert preset_dir.is_dir(), f"Preset path from config.yml does not resolve: {preset_dir}"

    def test_no_remote_version_pins_in_config(self) -> None:
        """config.yml should not contain remote version pins (semver patterns)."""
        import re

        content = self.config_path.read_text()
        # Remote version pins look like: speckit-ext-agdt: "1.0.0" or speckit-ext-agdt@1.0.0
        remote_pin_pattern = re.compile(
            r'speckit-(?:ext|preset)-agdt(?:\s*:\s*["\']?|\s*@)\d+\.\d+\.\d+\b'
        )
        assert not remote_pin_pattern.search(content), (
            "config.yml still contains remote version pins; should use local paths"
        )

    def test_no_legacy_directories_exist(self) -> None:
        """Legacy .specify/scripts/ and .specify/templates/ directories should not exist."""
        legacy_scripts = REPO_ROOT / ".specify" / "scripts"
        legacy_templates = REPO_ROOT / ".specify" / "templates"
        assert not legacy_scripts.is_dir(), "Legacy .specify/scripts/ directory still exists — should be removed"
        assert not legacy_templates.is_dir(), "Legacy .specify/templates/ directory still exists — should be removed"

    def test_extension_scripts_and_commands_have_no_legacy_path_references(self) -> None:
        """Extension scripts/commands must not reference legacy .specify/scripts|templates paths."""
        search_roots = [EXTENSION_DIR / "scripts", EXTENSION_DIR / "commands"]
        stale_references: list[str] = []
        for search_root in search_roots:
            for path in search_root.rglob("*"):
                if not path.is_file():
                    continue
                content = path.read_text()
                if any(token in content for token in LEGACY_SPECIFY_PATH_TOKENS):
                    stale_references.append(str(path.relative_to(REPO_ROOT)))

        assert not stale_references, (
            "Found stale legacy .specify path references in extension assets: "
            + ", ".join(sorted(stale_references))
        )


class TestExtensionManifestConsistency:
    """Cross-validate manifest declarations against actual files on disk."""

    extension_dir = EXTENSION_DIR

    def test_all_declared_commands_exist_on_disk(self) -> None:
        """Every command listed in extension.yml must have a corresponding file."""
        manifest = self.extension_dir / "extension.yml"
        commands = _parse_manifest_lists(manifest).get("commands", [])

        assert len(commands) > 0, "No commands found in extension.yml"
        for cmd in commands:
            cmd_path = self.extension_dir / "commands" / cmd
            assert cmd_path.is_file(), f"Command '{cmd}' declared in extension.yml but file not found: {cmd_path}"

    def test_all_declared_bash_scripts_exist_on_disk(self) -> None:
        """Every bash script listed in extension.yml must have a corresponding file."""
        manifest = self.extension_dir / "extension.yml"
        scripts = _parse_manifest_lists(manifest).get("scripts", {}).get("bash", [])

        assert len(scripts) > 0, "No bash scripts found in extension.yml"
        for script in scripts:
            script_path = self.extension_dir / "scripts" / "bash" / script
            assert script_path.is_file(), (
                f"Bash script '{script}' declared in extension.yml but not found: {script_path}"
            )

    def test_all_declared_powershell_scripts_exist_on_disk(self) -> None:
        """Every PowerShell script listed in extension.yml must have a corresponding file."""
        manifest = self.extension_dir / "extension.yml"
        scripts = _parse_manifest_lists(manifest).get("scripts", {}).get("powershell", [])

        assert len(scripts) > 0, "No PowerShell scripts found in extension.yml"
        for script in scripts:
            script_path = self.extension_dir / "scripts" / "powershell" / script
            assert script_path.is_file(), (
                f"PowerShell script '{script}' declared in extension.yml but not found: {script_path}"
            )


class TestPresetManifestConsistency:
    """Cross-validate preset manifest declarations against actual files on disk."""

    preset_dir = PRESET_DIR

    def test_all_declared_templates_and_assets_exist_on_disk(self) -> None:
        """Every template and asset listed in preset.yml must have a corresponding file."""
        manifest = self.preset_dir / "preset.yml"
        manifest_data = _parse_manifest_lists(manifest)
        templates = manifest_data.get("templates", [])
        assets = manifest_data.get("assets", [])
        declared_entries = templates + assets

        assert len(declared_entries) > 0, "No templates or assets found in preset.yml"
        for tmpl in declared_entries:
            tmpl_path = self.preset_dir / "templates" / tmpl
            assert tmpl_path.is_file(), f"Entry '{tmpl}' declared in preset.yml but file not found: {tmpl_path}"
