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
        print("  ℹ To apply:")
        print("    # bash/zsh:")
        print('    export NPM_CONFIG_USERCONFIG="$HOME/.agdt/npmrc"')
        print("    # PowerShell:")
        print('    $env:NPM_CONFIG_USERCONFIG = "$env:USERPROFILE\\.agdt\\npmrc"')
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
        unified_str = str(unified_path)
        print("  ✓ Unified CA bundle written to ~/.agdt/certs/unified-ca-bundle.pem")
        print("  ℹ For pip/requests/az CLI (covers GitHub, Azure DevOps, Jira, etc.):")
        print("    # bash/zsh:")
        print(f'    export REQUESTS_CA_BUNDLE="{unified_str}"')
        print("    # PowerShell:")
        print(f'    $env:REQUESTS_CA_BUNDLE = "{unified_str}"')

    return unified_path


def _print_path_instructions_if_needed() -> None:
    """Print PATH setup instructions when ``~/.agdt/bin`` is not on the PATH."""
    managed_bin = str(_MANAGED_BIN_DIR)
    path_entries = os.environ.get("PATH", "").split(os.pathsep)
    home = str(Path.home())
    normalised_path_entries = [p.replace("~", home).rstrip("/").rstrip("\\") for p in path_entries]
    if managed_bin.rstrip("/").rstrip("\\") not in normalised_path_entries:
        print(_PATH_INSTRUCTIONS)


def setup_cmd() -> None:
    """Full setup: install Copilot CLI + GitHub CLI, then verify all dependencies.

    Usage:
        agdt-setup [--system-only] [--no-verify-ssl]

    Options:
        --system-only   Skip managed installs into ~/.agdt/bin/; only verify
                        already-installed dependencies.
        --no-verify-ssl Disable SSL certificate verification (insecure; use
                        only on trusted networks).
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
    args = parser.parse_args()
    if args.no_verify_ssl:
        os.environ["AGDT_NO_VERIFY_SSL"] = "1"
        print("  ⚠  SSL verification disabled. Use only on trusted networks.")
        print()

    print(_BANNER)
    print()

    if args.system_only:
        print("Skipping managed installs (--system-only).")
        print()
        copilot_ok = True
        gh_ok = True
    else:
        _prefetch_certs()
        print()

        copilot_ok = install_copilot_cli()
        print()
        gh_ok = install_gh_cli()

    statuses = check_all_dependencies()
    print_dependency_report(statuses)

    _print_path_instructions_if_needed()

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
        agdt-setup-copilot-cli [--system-only] [--no-verify-ssl]

    Options:
        --system-only   Skip the managed install.
        --no-verify-ssl Disable SSL certificate verification.
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
    _print_path_instructions_if_needed()


def setup_gh_cli_cmd() -> None:
    """Install the GitHub CLI (``gh``) into ``~/.agdt/bin/``.

    Usage:
        agdt-setup-gh-cli [--system-only] [--no-verify-ssl]

    Options:
        --system-only   Skip the managed install.
        --no-verify-ssl Disable SSL certificate verification.
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
    _print_path_instructions_if_needed()


def setup_certs_cmd() -> None:
    """Prefetch and refresh CA certificate bundles for all setup hosts.

    Fetches the certificate chain for external hosts used during setup and
    stores the PEM bundles in ``~/.agdt/certs/``.  Also writes an
    ``~/.agdt/npmrc`` file that configures npm to use the cached CA bundle
    for ``registry.npmjs.org``.

    Run this command when you encounter SSL errors during setup on a
    corporate network with a custom CA certificate.

    Usage:
        agdt-setup-certs
    """
    print("Refreshing CA certificate bundles...")
    print()
    _prefetch_certs()


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
