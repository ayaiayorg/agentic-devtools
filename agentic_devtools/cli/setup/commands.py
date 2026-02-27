"""
CLI commands for the agdt-setup family of commands.

Entry points:
- ``agdt-setup``            — full setup (install copilot CLI + gh CLI, check all deps)
- ``agdt-setup-copilot-cli`` — install only the Copilot CLI standalone binary
- ``agdt-setup-gh-cli``     — install only the GitHub CLI
- ``agdt-setup-check``      — verify all dependencies without installing anything

All install commands accept ``--system-only`` to skip managed installs and rely
on whatever is available on the system ``PATH``.
"""

import argparse
import sys
from pathlib import Path

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


def _prefetch_certs() -> None:
    """Pre-fetch and cache corporate CA certificates for common setup hosts.

    Fetches the certificate chain for external hosts used during setup and
    stores the PEM bundles in ``~/.agdt/certs/``.  Also writes an
    ``~/.agdt/npmrc`` file that configures npm to use the cached CA bundle
    for ``registry.npmjs.org``, enabling npm installs on corporate networks.

    The cert cache only needs to be refreshed infrequently (e.g. yearly).
    To force a refresh, delete ``~/.agdt/certs/``.
    """
    print("Fetching CA certificates for external hosts...")

    # Hosts used by the CLI installers — store api.github.com result for pip hint below
    gh_pem = None
    for hostname in ("api.github.com", "github.com"):
        pem = _ensure_ca_bundle(hostname)
        if hostname == "api.github.com":
            gh_pem = pem
        if pem:
            print(f"  ✓ CA bundle cached for {hostname}")
        else:
            print(f"  ⚠ Could not cache CA bundle for {hostname}; will try system CA")

    # npm registry — write cafile to ~/.agdt/npmrc so npm works on corporate networks
    npm_pem = _ensure_ca_bundle("registry.npmjs.org")
    if npm_pem:
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

    # Print pip CA instructions (pip respects REQUESTS_CA_BUNDLE or PIP_CERT)
    if gh_pem:
        print("  ℹ For pip/requests:")
        print("    # bash/zsh:")
        print(f'    export REQUESTS_CA_BUNDLE="{gh_pem}"')
        print("    # PowerShell:")
        print(f'    $env:REQUESTS_CA_BUNDLE = "{gh_pem}"')


def _print_path_instructions_if_needed() -> None:
    """Print PATH setup instructions when ``~/.agdt/bin`` is not on the PATH."""
    import os

    managed_bin = str(_MANAGED_BIN_DIR)
    path_entries = os.environ.get("PATH", "").split(os.pathsep)
    home = str(Path.home())
    normalised_path_entries = [p.replace("~", home).rstrip("/").rstrip("\\") for p in path_entries]
    if managed_bin.rstrip("/").rstrip("\\") not in normalised_path_entries:
        print(_PATH_INSTRUCTIONS)


def setup_cmd() -> None:
    """Full setup: install Copilot CLI + GitHub CLI, then verify all dependencies.

    Usage:
        agdt-setup [--system-only]

    Options:
        --system-only   Skip managed installs into ~/.agdt/bin/; only verify
                        already-installed dependencies.
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
    args = parser.parse_args()

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
        agdt-setup-copilot-cli [--system-only]

    Options:
        --system-only   Skip the managed install.
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
    args = parser.parse_args()

    if args.system_only:
        print("Skipping managed install of Copilot CLI (--system-only).")
        return

    ok = install_copilot_cli()
    if not ok:
        sys.exit(1)
    _print_path_instructions_if_needed()


def setup_gh_cli_cmd() -> None:
    """Install the GitHub CLI (``gh``) into ``~/.agdt/bin/``.

    Usage:
        agdt-setup-gh-cli [--system-only]

    Options:
        --system-only   Skip the managed install.
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
    args = parser.parse_args()

    if args.system_only:
        print("Skipping managed install of GitHub CLI (--system-only).")
        return

    ok = install_gh_cli()
    if not ok:
        sys.exit(1)
    _print_path_instructions_if_needed()


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
