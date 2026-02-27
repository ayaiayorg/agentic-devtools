"""
Shared SSL certificate utilities for agentic-devtools.

Fetches and caches corporate CA certificate chains so that ``requests``
calls succeed on corporate networks where a proxy re-signs TLS connections
with a custom CA certificate.

Certificates are cached in ``~/.agdt/certs/<hostname>.pem`` and only
re-fetched when the cached file is missing or empty.
"""

import os
import re
import socket
import ssl
import subprocess
from pathlib import Path
from typing import Optional, Union

from agentic_devtools.cli.subprocess_utils import run_safe

# Default directory for cached CA bundles
_CERTS_DIR = Path.home() / ".agdt" / "certs"


def fetch_certificate_chain_openssl(hostname: str, port: int = 443) -> Optional[str]:
    """Fetch the SSL certificate chain from *hostname* using ``openssl s_client``.

    Returns the full chain (all certificates) as a PEM string, or ``None``
    if ``openssl`` is unavailable or the connection fails.

    Args:
        hostname: The server hostname.
        port: The server port (default 443).

    Returns:
        PEM-encoded certificate chain string, or ``None`` on failure.
    """
    try:
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
            shell=False,
        )
        output = result.stdout.decode("utf-8", errors="ignore")
        cert_pattern = r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----"
        certs = re.findall(cert_pattern, output, re.DOTALL)
        if certs:
            return "\n".join(certs)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError, subprocess.SubprocessError):
        pass
    except Exception:  # noqa: BLE001 — cert fetch must not crash setup
        pass
    return None


def fetch_certificate_chain_ssl(hostname: str, port: int = 443) -> Optional[str]:
    """Fetch the SSL certificate from *hostname* using Python's :mod:`ssl` module.

    This is a fallback for when ``openssl`` is not available.  Note that the
    :mod:`ssl` module can only retrieve the server certificate, **not** the
    full chain.

    Args:
        hostname: The server hostname.
        port: The server port (default 443).

    Returns:
        PEM-encoded certificate string, or ``None`` on failure.
    """
    try:
        # Intentionally disable SSL verification here: we must fetch the certificate
        # chain *before* we can trust it.  The chain is only used as a CA bundle for
        # subsequent requests — never to authenticate the connection where it was fetched.
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE  # noqa: S501

        with socket.create_connection((hostname, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert_der = ssock.getpeercert(binary_form=True)
                if cert_der:
                    return ssl.DER_cert_to_PEM_cert(cert_der)
    except Exception:  # pragma: no cover
        pass

    return None  # pragma: no cover


def count_certificates_in_pem(pem_content: str) -> int:
    """Return the number of ``BEGIN CERTIFICATE`` blocks in *pem_content*."""
    return pem_content.count("-----BEGIN CERTIFICATE-----")


def ensure_ca_bundle(
    hostname: str,
    cache_file: Optional[Path] = None,
) -> Optional[str]:
    """Ensure a CA bundle PEM file exists for *hostname* and return its path.

    The certificate chain is fetched exactly once and cached.  Subsequent
    calls return the cached path immediately when the cache contains at
    least one certificate — even if only the server cert was available.

    On the *first* fetch the function prefers ``openssl`` (which usually
    retrieves the full chain including the root CA).  If ``openssl``
    fails to return any certificates, the :mod:`ssl` module is used as a
    fallback to obtain at least the server certificate.

    All certificate fetching targets port 443 (standard HTTPS).  For
    non-standard ports, use :func:`fetch_certificate_chain_openssl` or
    :func:`fetch_certificate_chain_ssl` directly.

    Args:
        hostname: Server hostname to fetch certificates from.
        cache_file: Explicit path to store the PEM file.  Defaults to
            ``~/.agdt/certs/<hostname>.pem``.

    Returns:
        Absolute path to the cached PEM file, or ``None`` if fetching failed.
    """
    if cache_file is None:
        # Sanitize hostname to prevent path traversal (e.g. "../" in hostname).
        safe_name = re.sub(r"[^\w.\-]", "_", hostname)
        cache_file = _CERTS_DIR / f"{safe_name}.pem"
    cache_file = cache_file.expanduser().resolve()

    # Return cached file when it already contains at least one certificate.
    # We accept single-cert caches to avoid re-fetching on every call for
    # hosts that only ever yield one cert (e.g. ssl-module fallback).
    if cache_file.exists():
        try:
            existing = cache_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            # Treat unreadable or undecodable cache as missing and refetch.
            existing = ""
        if count_certificates_in_pem(existing) >= 1:
            return str(cache_file)

    # Prefer openssl — it retrieves the full chain including the root CA
    cert_chain = fetch_certificate_chain_openssl(hostname)
    if cert_chain and count_certificates_in_pem(cert_chain) >= 2:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(cert_chain, encoding="utf-8")
        return str(cache_file)

    # Fallback: ssl module (server cert only — may not work as a CA bundle)
    if not cert_chain:
        cert_chain = fetch_certificate_chain_ssl(hostname)

    if cert_chain:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(cert_chain, encoding="utf-8")
        return str(cache_file)

    return None


def get_ssl_verify(hostname: str) -> Union[bool, str]:
    """Return the ``verify`` argument for :func:`requests.get` when connecting to *hostname*.

    Priority:
    1. ``REQUESTS_CA_BUNDLE`` environment variable (if set and file exists).
    2. Cached CA bundle at ``~/.agdt/certs/<hostname>.pem``, fetched on
       demand if not present.
    3. ``True`` — fall back to the system default CA bundle.

    Args:
        hostname: The target server hostname.

    Returns:
        Path to a CA bundle file, or ``True`` to use the system CA bundle.
    """
    ca_bundle = os.environ.get("REQUESTS_CA_BUNDLE")
    if ca_bundle:
        normalized = os.path.abspath(os.path.expanduser(os.path.expandvars(ca_bundle)))
        if os.path.exists(normalized):
            return normalized

    pem_path = ensure_ca_bundle(hostname)
    if pem_path:
        return pem_path

    return True
