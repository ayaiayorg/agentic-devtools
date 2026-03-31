"""
CLI commands for the agdt-setup family of commands.

Entry points:
- ``agdt-setup``            — full setup (install copilot CLI + gh CLI, check all deps)
- ``agdt-setup-copilot-cli`` — install only the Copilot CLI standalone binary
- ``agdt-setup-gh-cli``     — install only the GitHub CLI
- ``agdt-setup-check``      — verify all dependencies without installing anything
- ``agdt-setup-certs``      — prefetch/refresh CA certificate bundles

All install commands accept ``--system-only`` to skip managed installs and rely
on whatever is available on the system ``PATH``.
"""

import argparse
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from agentic_devtools.cli.cert_utils import ensure_ca_bundle as _ensure_ca_bundle

from .copilot_cli_installer import install_copilot_cli
from .dependency_checker import check_all_dependencies, print_dependency_report
from .gh_cli_installer import install_gh_cli
from .shell_profile import detect_shell_profile, detect_shell_type, persist_env_var, persist_path_entry

try:
    from agentic_devtools.config import VALID_ISSUE_ADAPTERS as _VALID_ISSUE_ADAPTERS
except ImportError:
    _VALID_ISSUE_ADAPTERS = frozenset({"jira", "github", "markdown"})

_MANAGED_BIN_DIR = Path.home() / ".agdt" / "bin"

_BANNER = """\
╔══════════════════════════════════════════════════════════════╗
║                    agentic-devtools Setup                    ║
╚══════════════════════════════════════════════════════════════╝"""

_PATH_INSTRUCTIONS = (
    "\n"
    "PATH Setup:\n"
    "  Add ~/.agdt/bin to your PATH:\n"
    "    # bash/zsh:\n"
    '    export PATH="$HOME/.agdt/bin:$PATH"\n'
    "    # PowerShell:\n"
    '    $env:PATH = "$env:USERPROFILE\\.agdt\\bin;$env:PATH"'
)


_SETUP_HOSTS = (
    "api.github.com",
    "github.com",
    "dev.azure.com",
    "release-assets.githubusercontent.com",
)


def _build_unified_ca_bundle(per_host_pem_paths: list[str]) -> Path | None:
    """Build a unified CA bundle combining certifi's system CAs and fetched corporate CAs.

    Reads the system certifi CA bundle, appends all non-leaf certificates
    (index > 0 in each chain, i.e. intermediates and roots) from the
    per-host PEM files, de-duplicates, and writes the result to
    ``~/.agdt/certs/unified-ca-bundle.pem``.

    The bundle is always written even when no extra corporate CA certificates
    are found — in that case the result is a copy of the certifi bundle.
    This ensures ``REQUESTS_CA_BUNDLE`` can always be pointed at the unified
    bundle, giving subsequent requests a known-good CA store to fall back to.

    Args:
        per_host_pem_paths: List of paths to per-host PEM files.

    Returns:
        Path to the unified bundle file, or ``None`` if certifi is unavailable
        or if the certifi bundle cannot be read / the unified file cannot be
        written.
    """
    try:
        import certifi
    except ImportError:
        return None

    cert_pattern = r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----"

    # Start with certifi system CAs
    certifi_path = Path(certifi.where())
    try:
        system_pem = certifi_path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        print(f"  ⚠ Could not read certifi CA bundle {certifi_path}: {exc}", file=sys.stderr)
        return None
    system_certs = set(re.findall(cert_pattern, system_pem, re.DOTALL))

    extra_certs: list[str] = []
    for pem_path in per_host_pem_paths:
        try:
            content = Path(pem_path).read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            print(f"  ⚠ Could not read CA bundle {pem_path}: {exc}", file=sys.stderr)
            continue
        chain = re.findall(cert_pattern, content, re.DOTALL)
        # Skip index 0 (leaf/server cert); only add intermediates and roots
        for cert in chain[1:]:
            if cert not in system_certs:
                system_certs.add(cert)
                extra_certs.append(cert)

    # Always write a unified bundle: if no additional corporate CAs are found
    # this is effectively a certifi-only bundle, ensuring REQUESTS_CA_BUNDLE
    # always points at a known-good CA store instead of per-host leaf-only PEMs.
    unified_content = system_pem.rstrip("\n") + "\n" + "\n".join(extra_certs) + "\n"
    unified_path = Path.home() / ".agdt" / "certs" / "unified-ca-bundle.pem"
    try:
        unified_path.parent.mkdir(parents=True, exist_ok=True)
        unified_path.write_text(unified_content, encoding="utf-8")
    except OSError as exc:
        print(f"  ⚠ Could not write unified CA bundle {unified_path}: {exc}", file=sys.stderr)
        return None
    return unified_path


def _prefetch_certs() -> Path | None:
    """Pre-fetch and cache corporate CA certificates for common setup hosts.

    Fetches the certificate chain for external hosts used during setup and
    stores the PEM bundles in ``~/.agdt/certs/``.  Also writes an
    ``~/.agdt/npmrc`` file that configures npm to use the cached CA bundle
    for ``registry.npmjs.org``, enabling npm installs on corporate networks.

    After fetching all per-host bundles a unified CA bundle is built at
    ``~/.agdt/certs/unified-ca-bundle.pem`` by combining the system certifi
    CA store with any extra intermediate/root CAs found in the per-host chains.
    When the unified bundle is built and ``REQUESTS_CA_BUNDLE`` is not already
    set by the user, it is set in ``os.environ`` so that all subsequent HTTPS
    calls within the same process use it automatically.

    The cert cache only needs to be refreshed infrequently (e.g. yearly).
    To force a refresh, delete ``~/.agdt/certs/``.

    Returns:
        Path to the unified CA bundle file (certifi-only when no extra
        corporate CAs are found), or ``None`` only if certifi is unavailable
        or if a read/write failure prevents the bundle from being written.
    """
    print("Fetching CA certificates for external hosts...")

    # Determine Jira hostname dynamically
    extra_hosts: list[str] = []
    try:
        from ..jira.config import get_jira_base_url

        jira_url = get_jira_base_url()
        # Use urlparse to correctly strip port numbers (e.g. jira.example.com:8443).
        # Scheme-less URLs like "jira.example.com" need a "//" prefix so urlparse
        # treats the first component as a network location rather than a path.
        parsed = urlparse(jira_url)
        jira_hostname = parsed.hostname
        if not jira_hostname:
            jira_hostname = urlparse("//" + jira_url).hostname
        if jira_hostname:
            extra_hosts.append(jira_hostname)
    except Exception as exc:  # noqa: BLE001
        print(f"  ⚠ Could not determine Jira hostname (skipping Jira cert): {exc}", file=sys.stderr)

    all_pem_paths: list[str] = []

    # Fetch certs for fixed setup hosts
    for hostname in _SETUP_HOSTS:
        pem = _ensure_ca_bundle(hostname)
        if pem:
            all_pem_paths.append(pem)
            print(f"  ✓ CA bundle cached for {hostname}")
        else:
            print(f"  ⚠ Could not cache CA bundle for {hostname}; will try system CA")

    # Fetch certs for dynamically determined hosts (e.g. Jira)
    for hostname in extra_hosts:
        pem = _ensure_ca_bundle(hostname)
        if pem:
            all_pem_paths.append(pem)
            print(f"  ✓ CA bundle cached for {hostname}")
        else:
            print(f"  ⚠ Could not cache CA bundle for {hostname}; will try system CA")

    # npm registry — write cafile to ~/.agdt/npmrc so npm works on corporate networks
    npm_pem = _ensure_ca_bundle("registry.npmjs.org")
    if npm_pem:
        all_pem_paths.append(npm_pem)
        npmrc_path = Path.home() / ".agdt" / "npmrc"
        npmrc_path.parent.mkdir(parents=True, exist_ok=True)
        npmrc_path.write_text(f"cafile={npm_pem}\n", encoding="utf-8")
        print("  ✓ CA bundle cached for registry.npmjs.org")
        print("  ✓ npm CA config written to ~/.agdt/npmrc")
        # Set NPM_CONFIG_USERCONFIG for the current process
        npmrc_str = str(npmrc_path)
        if not os.environ.get("NPM_CONFIG_USERCONFIG"):
            os.environ["NPM_CONFIG_USERCONFIG"] = npmrc_str
            print(f"  ✓ NPM_CONFIG_USERCONFIG set for this session: {npmrc_str}")
    else:
        print("  ⚠ Could not cache CA bundle for registry.npmjs.org; will try system CA")

    # Build unified CA bundle combining certifi + fetched corporate CAs
    unified_path = _build_unified_ca_bundle(all_pem_paths)

    # Wire the unified bundle into the running process so that all
    # subsequent HTTPS calls (e.g. install_copilot_cli, install_gh_cli)
    # use corporate CAs automatically.
    if unified_path:
        if not os.environ.get("REQUESTS_CA_BUNDLE"):
            os.environ["REQUESTS_CA_BUNDLE"] = str(unified_path)
            print(f"  ✓ REQUESTS_CA_BUNDLE set for this session: {unified_path}")
        if not os.environ.get("NODE_EXTRA_CA_CERTS"):
            os.environ["NODE_EXTRA_CA_CERTS"] = str(unified_path)
            print(f"  ✓ NODE_EXTRA_CA_CERTS set for this session: {unified_path}")
        print("  ✓ Unified CA bundle written to ~/.agdt/certs/unified-ca-bundle.pem")

    return unified_path


def _is_managed_bin_on_path() -> bool:
    """Check if ``~/.agdt/bin`` is already on the ``PATH``."""
    managed_bin = str(_MANAGED_BIN_DIR).rstrip(os.sep)
    path_entries = [entry.rstrip(os.sep) for entry in os.environ.get("PATH", "").split(os.pathsep) if entry]
    home = str(Path.home())
    normalised = [p.replace("~", home) for p in path_entries]
    return managed_bin in normalised


def _print_path_instructions_if_needed(*, persist_env: bool = False, overwrite_env: bool = False) -> None:
    """Print PATH setup instructions when ``~/.agdt/bin`` is not on the PATH.

    When *persist_env* is ``True``, attempts to persist the PATH entry to the
    shell profile instead of just printing instructions.
    """
    if not _is_managed_bin_on_path():
        if persist_env:
            _persist_env_vars_to_profile(
                npmrc_path=None,
                unified_path=None,
                persist_env=True,
                overwrite_env=overwrite_env,
                path_only=True,
            )
        else:
            print(_PATH_INSTRUCTIONS)


def _persist_env_vars_to_profile(
    *,
    npmrc_path: Path | None,
    unified_path: Path | None,
    persist_env: bool,
    overwrite_env: bool,
    path_only: bool = False,
) -> None:
    """Orchestrate persisting env vars to the user's shell profile.

    When *persist_env* is ``False``, prints manual instructions instead.
    When *path_only* is ``True``, only handles the ``PATH`` entry.

    Args:
        npmrc_path: Path to the ``~/.agdt/npmrc`` file (or ``None``).
        unified_path: Path to the unified CA bundle (or ``None``).
        persist_env: Whether to persist to the shell profile.
        overwrite_env: Whether to replace existing lines.
        path_only: Only persist/print ``PATH`` instructions.
    """
    managed_bin_str = str(_MANAGED_BIN_DIR)

    # Check if PATH already contains the managed bin dir
    managed_on_path = _is_managed_bin_on_path()

    # Best-effort shell detection for manual instructions; ignore failures.
    try:
        shell_type_hint = detect_shell_type()
    except Exception:  # noqa: BLE001
        shell_type_hint = None

    if not persist_env:
        if path_only:
            if not managed_on_path:
                print(_PATH_INSTRUCTIONS)
        else:
            _print_manual_instructions(npmrc_path, unified_path, managed_on_path, shell_type_hint)
        return

    try:
        profile_path = detect_shell_profile()
        shell_type = detect_shell_type()
    except Exception as exc:  # noqa: BLE001
        print(f"  ⚠ Could not detect shell profile: {exc}", file=sys.stderr)
        # Fall back to manual instructions
        _persist_env_vars_to_profile(
            npmrc_path=npmrc_path,
            unified_path=unified_path,
            persist_env=False,
            overwrite_env=overwrite_env,
            path_only=path_only,
        )
        return

    if profile_path is None:
        # Unknown shell — print manual instructions
        if path_only:
            if not managed_on_path:
                print(_PATH_INSTRUCTIONS)
        else:
            _print_manual_instructions(npmrc_path, unified_path, managed_on_path, shell_type_hint)
        return

    if not path_only:
        if npmrc_path:
            _persist_single_var(profile_path, "NPM_CONFIG_USERCONFIG", str(npmrc_path), shell_type, overwrite_env)
        if unified_path:
            _persist_single_var(profile_path, "REQUESTS_CA_BUNDLE", str(unified_path), shell_type, overwrite_env)
            _persist_single_var(profile_path, "NODE_EXTRA_CA_CERTS", str(unified_path), shell_type, overwrite_env)

    # PATH entry
    if not managed_on_path:
        result = persist_path_entry(profile_path, managed_bin_str, shell_type, overwrite=overwrite_env)
        if result:
            print(f"  ✓ PATH entry persisted to {profile_path}")
        else:
            # Check if it was skipped (already exists) vs. failed
            try:
                if profile_path.exists() and managed_bin_str in profile_path.read_text(
                    encoding="utf-8", errors="replace"
                ):
                    print(f"  ℹ PATH entry already set in {profile_path} (use --overwrite-env to replace)")
            except OSError:
                pass  # persist_path_entry already printed a warning


def _print_manual_instructions(
    npmrc_path: Path | None,
    unified_path: Path | None,
    managed_on_path: bool,
    shell_type: str | None,
) -> None:
    """Print shell-specific manual instructions for env var persistence."""
    has_vars = bool(npmrc_path or unified_path or not managed_on_path)
    if not has_vars:
        return

    if shell_type in ("bash", "zsh"):
        instructions = ["\n  ℹ Add the following to your ~/.bashrc or ~/.zshrc:"]
        if npmrc_path:
            instructions.append(f'    export NPM_CONFIG_USERCONFIG="{npmrc_path}"')
        if unified_path:
            instructions.append(f'    export REQUESTS_CA_BUNDLE="{unified_path}"')
            instructions.append(f'    export NODE_EXTRA_CA_CERTS="{unified_path}"')
        if not managed_on_path:
            instructions.append('    export PATH="$HOME/.agdt/bin:$PATH"')
        print("\n".join(instructions))
    elif shell_type == "powershell":
        instructions = ["\n  ℹ Add the following to your PowerShell $PROFILE:"]
        if npmrc_path:
            instructions.append(f'    $env:NPM_CONFIG_USERCONFIG = "{npmrc_path}"')
        if unified_path:
            instructions.append(f'    $env:REQUESTS_CA_BUNDLE = "{unified_path}"')
            instructions.append(f'    $env:NODE_EXTRA_CA_CERTS = "{unified_path}"')
        if not managed_on_path:
            instructions.append('    $env:PATH = "$env:USERPROFILE\\.agdt\\bin;$env:PATH"')
        print("\n".join(instructions))
    else:
        # Unknown shell: show both bash/zsh and PowerShell examples
        instructions = [
            "\n  ℹ Add the following to your shell profile.",
            "  Examples for bash/zsh and PowerShell:",
        ]
        if npmrc_path or unified_path or not managed_on_path:
            instructions.append("    # bash / zsh:")
        if npmrc_path:
            instructions.append(f'    export NPM_CONFIG_USERCONFIG="{npmrc_path}"')
        if unified_path:
            instructions.append(f'    export REQUESTS_CA_BUNDLE="{unified_path}"')
            instructions.append(f'    export NODE_EXTRA_CA_CERTS="{unified_path}"')
        if not managed_on_path:
            instructions.append('    export PATH="$HOME/.agdt/bin:$PATH"')
        if npmrc_path or unified_path or not managed_on_path:
            instructions.append("    # PowerShell:")
        if npmrc_path:
            instructions.append(f'    $env:NPM_CONFIG_USERCONFIG = "{npmrc_path}"')
        if unified_path:
            instructions.append(f'    $env:REQUESTS_CA_BUNDLE = "{unified_path}"')
            instructions.append(f'    $env:NODE_EXTRA_CA_CERTS = "{unified_path}"')
        if not managed_on_path:
            instructions.append('    $env:PATH = "$env:USERPROFILE\\.agdt\\bin;$env:PATH"')
        print("\n".join(instructions))


def _persist_single_var(profile_path: Path, var_name: str, var_value: str, shell_type: str, overwrite: bool) -> None:
    """Persist a single env var and print the appropriate message."""
    result = persist_env_var(profile_path, var_name, var_value, shell_type, overwrite=overwrite)
    if result:
        print(f"  ✓ {var_name} persisted to {profile_path}")
    else:
        # Check if it was skipped (already exists) vs. failed
        try:
            if profile_path.exists() and var_name in profile_path.read_text(encoding="utf-8", errors="replace"):
                print(f"  ℹ {var_name} already set in {profile_path} (use --overwrite-env to replace)")
        except OSError:
            pass  # persist_env_var already printed a warning


def _prompt_project_config(*, force_prompt: bool = False) -> None:
    """Prompt the user for project-specific configuration values.

    Reads existing values from ``.agdt/config/project.json`` as defaults.
    Saves responses back to the same file.

    When *force_prompt* is ``False`` (the default), prompts are **skipped**
    for any key that is already present in the config (even if the value is
    ``""``).  Pass ``force_prompt=True`` (via ``--reconfigure``) to
    re-prompt for every field.
    """
    from agentic_devtools.cli.config.project_config import (
        load_project_config,
        save_project_config,
    )

    existing = load_project_config()

    print()
    print("─── Project Configuration ───────────────────────────────────")
    print("  Configure project-specific settings.")
    print("  Press Enter to keep current value; for optional fields, type '-' to clear.")
    print()

    def _ask(prompt: str, key: str, allow_clear: bool = False) -> str:
        if not force_prompt and key in existing:
            return existing[key]
        current = existing.get(key, "")
        suffix = f" [{current}]" if current else ""
        answer = input(f"  {prompt}{suffix}: ").strip()
        if allow_clear and answer.lower() in {"-", "clear"}:
            return ""
        # Reject clear sentinels for required fields — treat as "keep current"
        if not allow_clear and answer.lower() in {"-", "clear"}:
            return current
        if answer:
            return answer
        return current

    jira_keys = _ask("Jira project key(s), comma-separated (e.g. ACME,PROJ)", "jira_project_keys")
    jira_base_url = _ask("Jira base URL (e.g. https://jira.example.com)", "jira_base_url")
    corp_host = _ask("Corporate network test host (type '-' to clear)", "corporate_network_test_host", allow_clear=True)
    vpn_url = _ask("VPN portal URL (type '-' to clear)", "vpn_url", allow_clear=True)
    vpn_hostnames = _ask(
        "VPN hostnames for smart detection, comma-separated (type '-' to clear)",
        "vpn_hostnames",
        allow_clear=True,
    )

    config = dict(existing)  # preserve any extra keys
    for key, value in [
        ("jira_project_keys", jira_keys),
        ("jira_base_url", jira_base_url),
        ("corporate_network_test_host", corp_host),
        ("vpn_url", vpn_url),
        ("vpn_hostnames", vpn_hostnames),
    ]:
        config[key] = value

    path = save_project_config(config)
    print(f"\n  ✓ Project configuration saved to {path}")


# Curated list of known-good Copilot models used when the binary cannot be
# queried for the live list.
_KNOWN_COPILOT_MODELS = [
    "gpt-5.3-codex",
    "claude-opus-4.6",
    "claude-sonnet-4.5",
    "gpt-4o",
    "gemini-3.1-pro-preview",
    "gemini-2.5-pro",
    "o4-mini",
]


def _query_copilot_models() -> list[str]:
    """Try to retrieve available models from the installed Copilot binary.

    Runs ``copilot --list-models`` and parses each non-empty line as a model
    name.  Falls back to :data:`_KNOWN_COPILOT_MODELS` on any error.
    """
    import subprocess

    from agentic_devtools.cli.copilot.session import _get_copilot_binary

    binary = _get_copilot_binary()
    if binary is None:
        return list(_KNOWN_COPILOT_MODELS)
    try:
        result = subprocess.run(
            [binary, "--list-models"],
            capture_output=True,
            text=True,
            timeout=10,
            shell=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            models = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            if models:
                return models
    except (OSError, subprocess.TimeoutExpired, ValueError):
        pass
    return list(_KNOWN_COPILOT_MODELS)


def _prompt_copilot_model(*, force_prompt: bool = False) -> None:
    """Prompt the user to select the default Copilot model for workflow sessions.

    Queries available models from the installed Copilot binary; falls back to a
    curated list when querying fails.  Persists the selection to
    ``.agdt/config/project.json`` under ``"default_copilot_model"``.

    When *force_prompt* is ``False`` (the default), the prompt is **skipped**
    if ``"default_copilot_model"`` already exists in the config (even if
    ``""``).  Pass ``force_prompt=True`` (via ``--reconfigure``) to force
    re-selection.
    """
    from agentic_devtools.cli.config.project_config import (
        load_project_config,
        save_project_config,
    )

    existing = load_project_config()
    current_model = existing.get("default_copilot_model", "").strip()

    if not force_prompt and "default_copilot_model" in existing:
        print()
        print("─── Copilot Model Configuration ─────────────────────────────")
        print(f"  ℹ Default Copilot model already set: {existing['default_copilot_model']}")
        return

    print()
    print("─── Copilot Model Configuration ─────────────────────────────")
    print("  Select the default Copilot model for workflow sessions.")
    print()

    models = _query_copilot_models()

    print("  Available models:")
    for i, m in enumerate(models, start=1):
        print(f"    {i}. {m}")
    print()

    # Default selection: already-configured model if still in the list, else first
    default_selection = current_model if current_model in models else models[0]

    try:
        answer = input(f"  Default Copilot model [{default_selection}]: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    if not answer:
        chosen = default_selection
    elif answer.isdigit():
        idx = int(answer) - 1
        if 0 <= idx < len(models):
            chosen = models[idx]
        else:
            print(f"  ⚠ Invalid selection — keeping current default ({default_selection})")
            chosen = default_selection
    else:
        # Accept a free-form model name typed directly
        chosen = answer

    config = dict(existing)
    config["default_copilot_model"] = chosen
    save_project_config(config)
    print(f"  ✓ Default Copilot model set to: {chosen}")


def setup_cmd() -> None:
    """Full setup: install Copilot CLI + GitHub CLI, then verify all dependencies.

    Usage:
        agdt-setup [--system-only] [--no-verify-ssl] [--no-persist-env] [--overwrite-env]
                   [--reconfigure]

    Options:
        --system-only   Skip managed installs into ~/.agdt/bin/; only verify
                        already-installed dependencies.
        --no-verify-ssl Disable SSL certificate verification (insecure; use
                        only on trusted networks).
        --no-persist-env  Do not persist env vars to shell profile.
        --overwrite-env   Overwrite existing env var lines in shell profile.
        --reconfigure     Re-prompt for all project configuration values,
                          even if already set.
    """
    parser = argparse.ArgumentParser(
        prog="agdt-setup",
        description="Full setup: install managed CLIs and verify all dependencies.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--system-only",
        action="store_true",
        default=False,
        help="Skip managed installs; only verify already-installed dependencies.",
    )
    parser.add_argument(
        "--no-verify-ssl",
        action="store_true",
        default=False,
        help="Disable SSL certificate verification (insecure; use only on trusted networks).",
    )
    parser.add_argument(
        "--no-persist-env",
        action="store_true",
        default=False,
        help="Do not persist environment variables to shell profile.",
    )
    parser.add_argument(
        "--overwrite-env",
        action="store_true",
        default=False,
        help="Overwrite existing environment variable lines in shell profile.",
    )
    parser.add_argument(
        "--skip-platform-detection",
        action="store_true",
        default=False,
        help="Skip automatic platform detection step.",
    )
    parser.add_argument(
        "--issue-adapter",
        choices=sorted(_VALID_ISSUE_ADAPTERS),
        default=None,
        help="Override detected issue adapter (skips platform detection).",
    )
    parser.add_argument(
        "--skip-templates",
        action="store_true",
        default=False,
        help="Skip workflow template generation step.",
    )
    parser.add_argument(
        "--reconfigure",
        action="store_true",
        default=False,
        help="Re-prompt for all project configuration values, even if already set.",
    )
    args = parser.parse_args()

    original_no_verify = os.environ.get("AGDT_NO_VERIFY_SSL")
    try:
        if args.no_verify_ssl:
            os.environ["AGDT_NO_VERIFY_SSL"] = "1"
            print("  ⚠  SSL verification disabled. Use only on trusted networks.")
            print()

        print(_BANNER)
        print()

        unified_path = None
        npmrc_written = False
        if args.system_only:
            print("Skipping managed installs (--system-only).")
            print()
            copilot_ok = True
            gh_ok = True
        else:
            unified_path = _prefetch_certs()
            # Check if npmrc was written
            npmrc_path = Path.home() / ".agdt" / "npmrc"
            npmrc_written = npmrc_path.exists()
            print()

            copilot_ok = install_copilot_cli()
            print()
            gh_ok = install_gh_cli()

        statuses = check_all_dependencies()
        print_dependency_report(statuses)

        persist_env = not args.no_persist_env and not args.system_only
        _persist_env_vars_to_profile(
            npmrc_path=Path.home() / ".agdt" / "npmrc" if npmrc_written else None,
            unified_path=unified_path,
            persist_env=persist_env,
            overwrite_env=args.overwrite_env,
        )

        any_required_missing = any(s.required and not s.found for s in statuses)

        # Ensure .agdt/.gitignore exists in the current repo (if any)
        from agentic_devtools.agdt_gitignore import ensure_agdt_gitignore
        from agentic_devtools.state import _get_git_repo_root

        git_root = _get_git_repo_root()
        if ensure_agdt_gitignore(git_root):
            print(
                "  ✓ Ensured .agdt/.gitignore — commit this file to propagate to all worktrees"
                "\n    (if your root .gitignore ignores .agdt/, add '!.agdt/.gitignore' so git tracks it)"
            )
        elif git_root is not None:
            print("  ⚠ Failed to create/update .agdt/.gitignore — check directory permissions", file=sys.stderr)

        # ── Project configuration prompts ───────────────────────────────
        if not args.system_only and git_root is not None:
            _prompt_project_config(force_prompt=args.reconfigure)
            _prompt_copilot_model(force_prompt=args.reconfigure)
        # ────────────────────────────────────────────────────────────────

        # Inject bundled agent/prompt skills where supported. Skill injection is a
        # best-effort optional feature: guard the import so that agdt-setup still
        # works even if the module is missing or uses syntax/features not supported
        # by the current interpreter.
        inject_skills = None  # type: ignore[assignment]
        try:
            from agentic_devtools.skill_injector import inject_skills as _inject_skills

            inject_skills = _inject_skills
        except (SyntaxError, ImportError) as exc:
            if git_root is not None:
                print(
                    f"  ⚠ Failed to import skill injector ({exc!r}) — skipping agent/prompt skill injection",
                    file=sys.stderr,
                )

        if inject_skills is not None and inject_skills(git_root):
            print("  ✓ Injected agent/prompt skills into .github/agents/ and .github/prompts/")
        elif git_root is not None and inject_skills is not None:
            print(
                "  ⚠ Failed to inject agent/prompt skills — this may be due to directory permissions or missing/corrupted bundled skills",
                file=sys.stderr,
            )

        # ── Platform & Workflow Setup ──────────────────────────────
        if not args.system_only and git_root is not None:
            print()
            print("─── Platform & Workflow Setup ────────────────────────────────")

            # Step 1: Platform detection + adapter configuration
            try:
                if args.issue_adapter is not None:
                    from agentic_devtools.config import (  # noqa: PLC0415
                        load_platform_config,
                        save_platform_config,
                    )

                    # Load existing config to preserve fields like github.repo
                    # or azure_devops.project; only override issue_adapter.
                    platform_config = load_platform_config(str(git_root))
                    platform_config["issue_adapter"] = args.issue_adapter
                    if save_platform_config(str(git_root), platform_config):
                        print(f"  ✓ Issue adapter configured: {args.issue_adapter}")
                    else:
                        print(
                            "  ⚠ Failed to save platform configuration — check directory permissions",
                            file=sys.stderr,
                        )
                elif not args.skip_platform_detection:
                    from agentic_devtools.cli.setup.platform_detection import (  # noqa: PLC0415
                        confirm_and_override,
                        detect_platforms,
                    )
                    from agentic_devtools.config import save_platform_config  # noqa: PLC0415

                    result = detect_platforms(str(git_root))
                    platform_config = confirm_and_override(result)
                    if save_platform_config(str(git_root), platform_config):
                        print("  ✓ Platform configuration saved")
                    else:
                        print(
                            "  ⚠ Failed to save platform configuration — check directory permissions",
                            file=sys.stderr,
                        )
            except Exception as exc:  # noqa: BLE001
                print(f"  ⚠ Platform setup failed ({exc}) — skipping", file=sys.stderr)

            # Step 2: Template generation
            try:
                if not args.skip_templates:
                    from agentic_devtools.cli.setup.workflow_templates import (  # noqa: PLC0415
                        generate_default_templates,
                    )

                    generated = generate_default_templates(git_root / ".agdt" / "workflow-definitions")
                    if generated:
                        for path in generated:
                            print(f"  ✓ Generated template: {path}")
                    else:
                        print("  ℹ Workflow templates already exist (use --skip-templates to suppress this message)")
            except Exception as exc:  # noqa: BLE001
                print(f"  ⚠ Template generation failed ({exc}) — skipping", file=sys.stderr)

        print()
        if not copilot_ok or not gh_ok or any_required_missing:
            print("Setup complete with warnings. See above for details.")
            sys.exit(1)
        else:
            print("Setup complete! ✅")
    finally:
        # Restore the original AGDT_NO_VERIFY_SSL state so that the env var does
        # not leak into the calling process when agdt-setup is invoked from within
        # a larger script or automation pipeline.
        if original_no_verify is None:
            os.environ.pop("AGDT_NO_VERIFY_SSL", None)
        else:
            os.environ["AGDT_NO_VERIFY_SSL"] = original_no_verify


def setup_copilot_cli_cmd() -> None:
    """Install the GitHub Copilot CLI standalone binary into ``~/.agdt/bin/``.

    Usage:
        agdt-setup-copilot-cli [--system-only] [--no-verify-ssl] [--no-persist-env] [--overwrite-env]

    Options:
        --system-only   Skip the managed install.
        --no-verify-ssl Disable SSL certificate verification.
        --no-persist-env  Do not persist env vars to shell profile.
        --overwrite-env   Overwrite existing env var lines in shell profile.
    """
    parser = argparse.ArgumentParser(
        prog="agdt-setup-copilot-cli",
        description="Install the GitHub Copilot CLI standalone binary into ~/.agdt/bin/.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--system-only",
        action="store_true",
        default=False,
        help="Skip managed install.",
    )
    parser.add_argument(
        "--no-verify-ssl",
        action="store_true",
        default=False,
        help="Disable SSL certificate verification (insecure; use only on trusted networks).",
    )
    parser.add_argument(
        "--no-persist-env",
        action="store_true",
        default=False,
        help="Do not persist environment variables to shell profile.",
    )
    parser.add_argument(
        "--overwrite-env",
        action="store_true",
        default=False,
        help="Overwrite existing environment variable lines in shell profile.",
    )
    args = parser.parse_args()

    original_no_verify = os.environ.get("AGDT_NO_VERIFY_SSL")
    try:
        if args.no_verify_ssl:
            os.environ["AGDT_NO_VERIFY_SSL"] = "1"
            print("  ⚠  SSL verification disabled. Use only on trusted networks.")

        if args.system_only:
            print("Skipping managed install of Copilot CLI (--system-only).")
            return

        unified_path = _prefetch_certs()
        print()

        ok = install_copilot_cli()
        if not ok:
            sys.exit(1)

        npmrc_path = Path.home() / ".agdt" / "npmrc"
        _persist_env_vars_to_profile(
            npmrc_path=npmrc_path if npmrc_path.exists() else None,
            unified_path=unified_path,
            persist_env=not args.no_persist_env,
            overwrite_env=args.overwrite_env,
        )
    finally:
        # Restore the original AGDT_NO_VERIFY_SSL state.
        if original_no_verify is None:
            os.environ.pop("AGDT_NO_VERIFY_SSL", None)
        else:
            os.environ["AGDT_NO_VERIFY_SSL"] = original_no_verify


def setup_gh_cli_cmd() -> None:
    """Install the GitHub CLI (``gh``) into ``~/.agdt/bin/``.

    Usage:
        agdt-setup-gh-cli [--system-only] [--no-verify-ssl] [--no-persist-env] [--overwrite-env]

    Options:
        --system-only   Skip the managed install.
        --no-verify-ssl Disable SSL certificate verification.
        --no-persist-env  Do not persist env vars to shell profile.
        --overwrite-env   Overwrite existing env var lines in shell profile.
    """
    parser = argparse.ArgumentParser(
        prog="agdt-setup-gh-cli",
        description="Install the GitHub CLI (gh) into ~/.agdt/bin/.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--system-only",
        action="store_true",
        default=False,
        help="Skip managed install.",
    )
    parser.add_argument(
        "--no-verify-ssl",
        action="store_true",
        default=False,
        help="Disable SSL certificate verification (insecure; use only on trusted networks).",
    )
    parser.add_argument(
        "--no-persist-env",
        action="store_true",
        default=False,
        help="Do not persist environment variables to shell profile.",
    )
    parser.add_argument(
        "--overwrite-env",
        action="store_true",
        default=False,
        help="Overwrite existing environment variable lines in shell profile.",
    )
    args = parser.parse_args()

    original_no_verify = os.environ.get("AGDT_NO_VERIFY_SSL")
    try:
        if args.no_verify_ssl:
            os.environ["AGDT_NO_VERIFY_SSL"] = "1"
            print("  ⚠  SSL verification disabled. Use only on trusted networks.")

        if args.system_only:
            print("Skipping managed install of GitHub CLI (--system-only).")
            return

        unified_path = _prefetch_certs()
        print()

        ok = install_gh_cli()
        if not ok:
            sys.exit(1)

        npmrc_path = Path.home() / ".agdt" / "npmrc"
        _persist_env_vars_to_profile(
            npmrc_path=npmrc_path if npmrc_path.exists() else None,
            unified_path=unified_path,
            persist_env=not args.no_persist_env,
            overwrite_env=args.overwrite_env,
        )
    finally:
        # Restore the original AGDT_NO_VERIFY_SSL state.
        if original_no_verify is None:
            os.environ.pop("AGDT_NO_VERIFY_SSL", None)
        else:
            os.environ["AGDT_NO_VERIFY_SSL"] = original_no_verify


def setup_certs_cmd() -> None:
    """Prefetch and refresh CA certificate bundles for all setup hosts.

    Fetches the certificate chain for external hosts used during setup and
    stores the PEM bundles in ``~/.agdt/certs/``.  Also writes an
    ``~/.agdt/npmrc`` file that configures npm to use the cached CA bundle
    for ``registry.npmjs.org``.

    Run this command when you encounter SSL errors during setup on a
    corporate network with a custom CA certificate.

    Usage:
        agdt-setup-certs [--no-verify-ssl] [--no-persist-env] [--overwrite-env]
    """
    parser = argparse.ArgumentParser(
        prog="agdt-setup-certs",
        description="Prefetch and refresh CA certificate bundles for all setup hosts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--no-verify-ssl",
        action="store_true",
        default=False,
        help="Disable SSL certificate verification (insecure; use only on trusted networks).",
    )
    parser.add_argument(
        "--no-persist-env",
        action="store_true",
        default=False,
        help="Do not persist environment variables to shell profile.",
    )
    parser.add_argument(
        "--overwrite-env",
        action="store_true",
        default=False,
        help="Overwrite existing environment variable lines in shell profile.",
    )
    args = parser.parse_args()

    original_no_verify = os.environ.get("AGDT_NO_VERIFY_SSL")
    try:
        if args.no_verify_ssl:
            os.environ["AGDT_NO_VERIFY_SSL"] = "1"
            print("  ⚠  SSL verification disabled. Use only on trusted networks.")

        print("Refreshing CA certificate bundles...")
        print()
        unified_path = _prefetch_certs()

        npmrc_path = Path.home() / ".agdt" / "npmrc"
        npmrc_written = npmrc_path.exists()
        _persist_env_vars_to_profile(
            npmrc_path=npmrc_path if npmrc_written else None,
            unified_path=unified_path,
            persist_env=not args.no_persist_env,
            overwrite_env=args.overwrite_env,
        )
    finally:
        # Restore the original AGDT_NO_VERIFY_SSL state.
        if original_no_verify is None:
            os.environ.pop("AGDT_NO_VERIFY_SSL", None)
        else:
            os.environ["AGDT_NO_VERIFY_SSL"] = original_no_verify


def setup_check_cmd() -> None:
    """Verify all external CLI dependencies and print their status.

    Does not install anything.

    Usage:
        agdt-setup-check
    """
    statuses = check_all_dependencies()
    print_dependency_report(statuses)

    any_required_missing = any(s.required and not s.found for s in statuses)
    if any_required_missing:
        sys.exit(1)
