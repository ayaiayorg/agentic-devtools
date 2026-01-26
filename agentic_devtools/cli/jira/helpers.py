"""
Jira utility helpers: request handling, SSL, parsing.
"""

import os
import re
import socket
import ssl
import subprocess
import warnings
from pathlib import Path
from typing import Any, List, Optional, Union

from agentic_devtools.cli.subprocess_utils import run_safe
from agentic_devtools.state import get_state_dir


def _get_requests():
    """
    Get requests module with lazy import.

    Returns:
        requests module

    Raises:
        ImportError: If requests is not installed
    """
    try:
        import requests

        # Suppress InsecureRequestWarning when SSL verification is disabled
        # (common for internal corporate networks with custom CAs)
        from urllib3.exceptions import InsecureRequestWarning

        warnings.filterwarnings("ignore", category=InsecureRequestWarning)

        return requests
    except ImportError:  # pragma: no cover
        raise ImportError("requests library required. Install with: pip install requests")


def _get_repo_jira_pem_path() -> Path:
    """
    Get the path to the repo-committed Jira CA bundle PEM file.

    This file is version-controlled at scripts/jira_ca_bundle.pem and contains
    the SSL certificate chain for jira.swica.ch. It's the same for all users.
    """
    # Walk up from state dir to find scripts/ folder
    state_dir = get_state_dir()
    # state_dir is typically scripts/temp, so parent is scripts/
    scripts_dir = state_dir.parent
    if scripts_dir.name == "scripts":
        return scripts_dir / "jira_ca_bundle.pem"
    # Fallback: search upward for scripts directory
    for parent in state_dir.parents:
        if parent.name == "scripts":
            return parent / "jira_ca_bundle.pem"
        candidate = parent / "scripts" / "jira_ca_bundle.pem"
        if candidate.exists():
            return candidate
    # Last resort: same directory as state
    return state_dir / "jira_ca_bundle.pem"


def _get_temp_jira_pem_path() -> Path:
    """Get the fallback path for auto-fetched Jira CA bundle (in temp dir)."""
    state_dir = get_state_dir()
    return state_dir / "jira_ca_bundle.pem"


def _fetch_certificate_chain_openssl(hostname: str, port: int = 443) -> Optional[str]:
    """
    Fetch the SSL certificate chain from a server using openssl command.

    Args:
        hostname: The server hostname
        port: The server port (default 443)

    Returns:
        PEM-encoded certificate chain string, or None if failed
    """
    try:
        # Use openssl s_client to get the full certificate chain
        result = run_safe(
            [
                "openssl",
                "s_client",
                "-showcerts",
                "-servername",
                hostname,
                "-connect",
                f"{hostname}:{port}",
            ],
            input=b"",
            capture_output=True,
            timeout=10,
        )

        output = result.stdout.decode("utf-8", errors="ignore")

        # Extract all certificates from the output
        cert_pattern = r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----"
        certs = re.findall(cert_pattern, output, re.DOTALL)

        if certs:
            return "\n".join(certs)

    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass

    return None


def _fetch_certificate_chain_ssl(hostname: str, port: int = 443) -> Optional[str]:
    """
    Fetch SSL certificate using Python's ssl module (fallback if openssl not available).

    Note: This only gets the server certificate, not the full chain.

    Args:
        hostname: The server hostname
        port: The server port (default 443)

    Returns:
        PEM-encoded certificate string, or None if failed
    """
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        with socket.create_connection((hostname, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert_der = ssock.getpeercert(binary_form=True)
                if cert_der:
                    cert_pem = ssl.DER_cert_to_PEM_cert(cert_der)
                    return cert_pem
    except Exception:
        pass

    return None


def _count_certificates_in_pem(pem_content: str) -> int:
    """Count the number of certificates in a PEM file content."""
    return pem_content.count("-----BEGIN CERTIFICATE-----")


def _ensure_jira_pem(hostname: str = "jira.swica.ch") -> Optional[str]:
    """
    Ensure the Jira CA bundle PEM file exists with a complete certificate chain.

    This is a fallback for when the repo-committed PEM doesn't exist.
    It auto-fetches the certificate chain and stores it in the temp folder.

    Args:
        hostname: Jira server hostname

    Returns:
        Path to the PEM file if successful, None otherwise
    """
    pem_path = _get_temp_jira_pem_path()

    # Check if PEM file exists and has a complete chain (at least 2 certs)
    if pem_path.exists():
        existing_content = pem_path.read_text(encoding="utf-8")
        if _count_certificates_in_pem(existing_content) >= 2:
            return str(pem_path)
        # Existing file only has server cert, need to re-fetch full chain

    # Try to fetch certificate chain using openssl (gets full chain)
    cert_chain = _fetch_certificate_chain_openssl(hostname)

    if cert_chain and _count_certificates_in_pem(cert_chain) >= 2:
        pem_path.parent.mkdir(parents=True, exist_ok=True)
        pem_path.write_text(cert_chain, encoding="utf-8")
        return str(pem_path)

    # Fallback to ssl module - only gets server cert, won't work for verification
    # but we still save it and return the path (caller will handle verification failure)
    if not cert_chain:
        cert_chain = _fetch_certificate_chain_ssl(hostname)

    if cert_chain:
        pem_path.parent.mkdir(parents=True, exist_ok=True)
        pem_path.write_text(cert_chain, encoding="utf-8")
        return str(pem_path)

    return None


def _get_ssl_verify() -> Union[bool, str]:
    """
    Get SSL verification setting from environment or state.

    Priority:
    1. If JIRA_SSL_VERIFY=0, disable SSL verification
    2. State value 'jira.ca_bundle_path' (set via dfly-set)
    3. Environment variable JIRA_CA_BUNDLE or REQUESTS_CA_BUNDLE
    4. Try to auto-generate/use cached Jira CA bundle PEM with full chain
    5. Fall back to disabled verification for corporate internal CAs

    Returns:
        False to skip verification, path to CA bundle, or True for strict verification
    """
    # Explicit opt-out of SSL verification
    if os.environ.get("JIRA_SSL_VERIFY") == "0":
        return False

    # Check state for CA bundle path (allows dfly-set jira.ca_bundle_path)
    from agentic_devtools.state import get_value

    state_ca_bundle = get_value("jira.ca_bundle_path")
    if state_ca_bundle and os.path.exists(state_ca_bundle):
        return state_ca_bundle

    # Check for custom CA bundle path from environment
    ca_bundle = os.environ.get("JIRA_CA_BUNDLE") or os.environ.get("REQUESTS_CA_BUNDLE")
    if ca_bundle and os.path.exists(ca_bundle):
        return ca_bundle

    # Check for repo-committed CA bundle first (preferred)
    repo_pem = _get_repo_jira_pem_path()
    if repo_pem.exists():
        return str(repo_pem)

    # Try to use auto-generated Jira PEM file as fallback
    from .config import get_jira_base_url

    base_url = get_jira_base_url()
    # Extract hostname from URL
    hostname = base_url.replace("https://", "").replace("http://", "").split("/")[0]

    pem_path = _ensure_jira_pem(hostname)
    if pem_path:
        return pem_path

    # Default: disable SSL verification for corporate internal CAs
    return False


def _parse_multiline_string(value: Any) -> Optional[List[str]]:
    """
    Parse a value that could be a list or newline-separated string.

    Args:
        value: List of strings, newline-separated string, or None

    Returns:
        List of non-empty stripped strings, or None if input was None
    """
    if value is None:
        return None
    if isinstance(value, list):
        return [item.strip() for item in value if item and item.strip()]
    if isinstance(value, str):
        return [line.strip() for line in value.split("\n") if line.strip()]
    return None


def _parse_comma_separated(value: Any) -> Optional[List[str]]:
    """
    Parse a value that could be a list or comma-separated string.

    Args:
        value: List of strings, comma-separated string, or None

    Returns:
        List of non-empty stripped strings, or None if input was None
    """
    if value is None:
        return None
    if isinstance(value, list):
        return [item.strip() for item in value if item and item.strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return None
