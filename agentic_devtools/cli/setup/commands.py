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
from typing import List, Optional
from urllib.parse import urlparse

from agentic_devtools.cli.cert_utils import ensure_ca_bundle as _ensure_ca_bundle

from .copilot_cli_installer import install_copilot_cli
from .dependency_checker import check_all_dependencies, print_dependency_report
from .gh_cli_installer import install_gh_cli
from .shell_profile import detect_shell_profile, detect_shell_type, persist_env_var, persist_path_entry

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


def _build_unified_ca_bundle(per_host_pem_paths: List[str]) -> Optional[Path]:
    """Build a unified CA bundle combining certifi's system CAs and fetched corporate CAs.

    Reads the system certifi CA bundle, appends all non-leaf certificates
    (index > 0 in each chain, i.e. intermediates and roots) from the
    per-host PEM files, de-duplicates, and writes the result to
    ``~/.agdt/certs/unified-ca-bundle.pem``.

    Args:
        per_host_pem_paths: List of paths to per-host PEM files.

    Returns:
        Path to the unified bundle file, or ``None`` if certifi is unavailable,
        if no additional corporate CA certificates are found in the provided
        PEM files, or if the certifi bundle cannot be read / the unified file
        cannot be written.
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

    extra_certs: List[str] = []
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

    if not extra_certs:
        # No additional corporate CAs found — no point writing a copy of the
        # system bundle.  Return None so the caller can skip the REQUESTS_CA_BUNDLE
        # hint (pointing users at a file identical to certifi is misleading).
        return None

    unified_content = system_pem.rstrip("\n") + "\n" + "\n".join(extra_certs) + "\n"
    unified_path = Path.home() / ".agdt" / "certs" / "unified-ca-bundle.pem"
    try:
        unified_path.parent.mkdir(parents=True, exist_ok=True)
        unified_path.write_text(unified_content, encoding="utf-8")
    except OSError as exc:
        print(f"  ⚠ Could not write unified CA bundle {unified_path}: {exc}", file=sys.stderr)
        return None
    return unified_path


def _prefetch_certs() -> Optional[Path]:
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
        Path to the unified CA bundle file, or ``None`` if no unified bundle
        was built (e.g. no corporate CAs found or certifi unavailable).
    """
    print("Fetching CA certificates for external hosts...")

    # Determine Jira hostname dynamically
    extra_hosts: List[str] = []
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

    all_pem_paths: List[str] = []

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


def _print_path_instructions_if_needed(*, persist_env: bool = False, overwrite_env: bool = False) -> None:
    """Print PATH setup instructions when ``~/.agdt/bin`` is not on the PATH.

    When *persist_env* is ``True``, attempts to persist the PATH entry to the
    shell profile instead of just printing instructions.
    """
    managed_bin = str(_MANAGED_BIN_DIR)
    path_entries = os.environ.get("PATH", "").split(os.pathsep)
    home = str(Path.home())
    normalised_path_entries = [p.replace("~", home).rstrip("/").rstrip("\\") for p in path_entries]
    if managed_bin.rstrip("/").rstrip("\\") not in normalised_path_entries:
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


_MANUAL_INSTRUCTIONS = (
    "\n"
    "  ℹ Add the following to your ~/.bashrc, ~/.zshrc, or PowerShell $PROFILE:\n"
    '    export NPM_CONFIG_USERCONFIG="$HOME/.agdt/npmrc"\n'
    '    export REQUESTS_CA_BUNDLE="<unified-ca-bundle-path>"\n'
    '    export NODE_EXTRA_CA_CERTS="<unified-ca-bundle-path>"\n'
    '    export PATH="$HOME/.agdt/bin:$PATH"'
)


def _persist_env_vars_to_profile(
    *,
    npmrc_path: Optional[Path],
    unified_path: Optional[Path],
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

    if not persist_env:
        # Print improved manual instructions with specific profile file names
        if path_only:
            print(_PATH_INSTRUCTIONS)
        else:
            instructions = ["\n  ℹ Add the following to your ~/.bashrc, ~/.zshrc, or PowerShell $PROFILE:"]
            if npmrc_path:
                instructions.append(f'    export NPM_CONFIG_USERCONFIG="{npmrc_path}"')
            if unified_path:
                instructions.append(f'    export REQUESTS_CA_BUNDLE="{unified_path}"')
                instructions.append(f'    export NODE_EXTRA_CA_CERTS="{unified_path}"')
            instructions.append('    export PATH="$HOME/.agdt/bin:$PATH"')
            print("\n".join(instructions))
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
            print(_PATH_INSTRUCTIONS)
        else:
            instructions = ["\n  ℹ Add the following to your ~/.bashrc, ~/.zshrc, or PowerShell $PROFILE:"]
            if npmrc_path:
                instructions.append(f'    export NPM_CONFIG_USERCONFIG="{npmrc_path}"')
            if unified_path:
                instructions.append(f'    export REQUESTS_CA_BUNDLE="{unified_path}"')
                instructions.append(f'    export NODE_EXTRA_CA_CERTS="{unified_path}"')
            instructions.append('    export PATH="$HOME/.agdt/bin:$PATH"')
            print("\n".join(instructions))
        return

    if not path_only:
        if npmrc_path:
            _persist_single_var(profile_path, "NPM_CONFIG_USERCONFIG", str(npmrc_path), shell_type, overwrite_env)
        if unified_path:
            _persist_single_var(profile_path, "REQUESTS_CA_BUNDLE", str(unified_path), shell_type, overwrite_env)
            _persist_single_var(profile_path, "NODE_EXTRA_CA_CERTS", str(unified_path), shell_type, overwrite_env)

    # PATH entry
    managed_bin = str(_MANAGED_BIN_DIR)
    path_entries = os.environ.get("PATH", "").split(os.pathsep)
    home = str(Path.home())
    normalised = [p.replace("~", home).rstrip("/").rstrip("\\") for p in path_entries]
    if managed_bin.rstrip("/").rstrip("\\") not in normalised:
        result = persist_path_entry(profile_path, managed_bin_str, shell_type, overwrite=overwrite_env)
        if result:
            print(f"  ✓ PATH entry persisted to {profile_path}")
        else:
            # Check if it was skipped (already exists) vs. failed
            if profile_path.exists() and managed_bin_str in profile_path.read_text(encoding="utf-8", errors="replace"):
                print(f"  ℹ PATH entry already set in {profile_path} (use --overwrite-env to replace)")
            # else: persist_path_entry already printed a warning


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


def setup_cmd() -> None:
    """Full setup: install Copilot CLI + GitHub CLI, then verify all dependencies.

    Usage:
        agdt-setup [--system-only] [--no-verify-ssl] [--no-persist-env] [--overwrite-env]

    Options:
        --system-only   Skip managed installs into ~/.agdt/bin/; only verify
                        already-installed dependencies.
        --no-verify-ssl Disable SSL certificate verification (insecure; use
                        only on trusted networks).
        --no-persist-env  Do not persist env vars to shell profile.
        --overwrite-env   Overwrite existing env var lines in shell profile.
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
    args = parser.parse_args()
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

    print()
    if not copilot_ok or not gh_ok or any_required_missing:
        print("Setup complete with warnings. See above for details.")
        sys.exit(1)
    else:
        print("Setup complete! ✅")


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
    if args.no_verify_ssl:
        os.environ["AGDT_NO_VERIFY_SSL"] = "1"
        print("  ⚠  SSL verification disabled. Use only on trusted networks.")

    if args.system_only:
        print("Skipping managed install of Copilot CLI (--system-only).")
        return

    _prefetch_certs()
    print()

    ok = install_copilot_cli()
    if not ok:
        sys.exit(1)
    _print_path_instructions_if_needed(persist_env=not args.no_persist_env, overwrite_env=args.overwrite_env)


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
    if args.no_verify_ssl:
        os.environ["AGDT_NO_VERIFY_SSL"] = "1"
        print("  ⚠  SSL verification disabled. Use only on trusted networks.")

    if args.system_only:
        print("Skipping managed install of GitHub CLI (--system-only).")
        return

    _prefetch_certs()
    print()

    ok = install_gh_cli()
    if not ok:
        sys.exit(1)
    _print_path_instructions_if_needed(persist_env=not args.no_persist_env, overwrite_env=args.overwrite_env)


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
