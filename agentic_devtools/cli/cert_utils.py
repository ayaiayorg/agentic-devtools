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
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
    import requests

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
    force: bool = False,
) -> Optional[str]:
    """Ensure a CA bundle PEM file exists for *hostname* and return its path.

    When a complete certificate chain is successfully fetched and written to
    the cache file, subsequent calls return the cached path immediately as
    long as the cache contains at least two certificates (leaf + at least
    one CA).  Single-cert (leaf-only) caches are treated as invalid and
    trigger a re-fetch, because a leaf certificate cannot validate itself
    and will always fail SSL verification.

    On the *first* fetch the function prefers ``openssl`` (which usually
    retrieves the full chain including the root CA).  If ``openssl``
    fails to return any certificates, the :mod:`ssl` module is used as a
    fallback — but since the :mod:`ssl` module can only retrieve the server
    certificate (not the chain), a leaf-only result is **not** cached and
    ``None`` is returned instead.  In any case where no complete chain can
    be cached (because only a leaf certificate is available or the cache
    file cannot be written), future calls may re-fetch the certificates.

    All certificate fetching targets port 443 (standard HTTPS).  For
    non-standard ports, use :func:`fetch_certificate_chain_openssl` or
    :func:`fetch_certificate_chain_ssl` directly.

    Args:
        hostname: Server hostname to fetch certificates from.
        cache_file: Explicit path to store the PEM file.  Defaults to
            ``~/.agdt/certs/<hostname>.pem``.
        force: When ``True``, delete any existing cached file and re-fetch.

    Returns:
        Absolute path to the cached PEM file, or ``None`` if a complete chain
        (leaf + at least one CA certificate) could not be obtained or the
        cache file could not be written.
    """
    if cache_file is None:
        # Sanitize hostname to prevent path traversal (e.g. "../" in hostname).
        safe_name = re.sub(r"[^\w.\-]", "_", hostname)
        cache_file = _CERTS_DIR / f"{safe_name}.pem"
    cache_file = cache_file.expanduser().resolve()

    # Remove stale cache when a forced re-fetch is requested.
    if force and cache_file.exists():
        try:
            cache_file.unlink()
        except OSError:
            # Even if deletion fails, skip using the existing cache when force=True.
            pass

    # Return cached file only when it contains a full chain (>= 2 certs).
    # A single-cert (leaf-only) cache cannot be used as a CA bundle and will
    # always fail SSL verification, so treat it as invalid and re-fetch.
    if cache_file.exists() and not force:
        try:
            existing = cache_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            # Treat unreadable or undecodable cache as missing and refetch.
            existing = ""
        if count_certificates_in_pem(existing) >= 2:
            return str(cache_file)
        # Stale/leaf-only cache — remove it before refetching so it doesn't
        # linger on disk and get picked up by external configs (e.g. npmrc cafile).
        try:
            cache_file.unlink()
        except OSError as exc:
            print(
                f"  ⚠ Could not delete stale CA bundle cache at {cache_file}: {exc}. "
                "The invalid file may still be referenced by external tools (for example, an npmrc cafile). "
                "Consider removing or replacing it manually.",
                file=sys.stderr,
            )

    # Prefer openssl — it retrieves the full chain including the root CA
    cert_chain = fetch_certificate_chain_openssl(hostname)
    if cert_chain and count_certificates_in_pem(cert_chain) >= 2:
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(cert_chain, encoding="utf-8")
            return str(cache_file)
        except OSError as exc:
            print(
                f"  ⚠ Could not cache CA bundle for {hostname}: {exc}. Will use requests' default CA bundle.",
                file=sys.stderr,
            )
            return None

    # Fallback: ssl module (only if openssl returned nothing at all).
    # The ssl module can only retrieve the server (leaf) certificate, not the
    # full chain, so we only try it when openssl gave us nothing at all.
    if not cert_chain:
        cert_chain = fetch_certificate_chain_ssl(hostname)

    # If we only have a leaf cert (from either method), do not cache it.
    # A leaf cert cannot validate itself, so it would always fail verification.
    if cert_chain and count_certificates_in_pem(cert_chain) < 2:
        print(
            f"  ⚠ Only leaf certificate retrieved for {hostname}; "
            "chain is incomplete. Will use requests' default CA bundle.",
            file=sys.stderr,
        )
        return None

    # cert_chain is None — both methods failed
    return None


def get_ssl_verify(hostname: str) -> Union[bool, str]:
    """Return the ``verify`` argument for :func:`requests.get` when connecting to *hostname*.

    Priority:
    1. ``REQUESTS_CA_BUNDLE`` environment variable (if set and file exists).
    2. Unified CA bundle at ``~/.agdt/certs/unified-ca-bundle.pem`` (if it
       exists and contains at least one certificate).
    3. Cached CA bundle at ``~/.agdt/certs/<hostname>.pem``, fetched on
       demand if not present.
    4. ``True`` — fall back to the system default CA bundle.

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

    # Check for the unified CA bundle (built by _prefetch_certs / agdt-setup-certs)
    unified_bundle = _CERTS_DIR / "unified-ca-bundle.pem"
    if unified_bundle.exists():
        try:
            content = unified_bundle.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            content = ""
        if count_certificates_in_pem(content) >= 1:
            return str(unified_bundle)

    pem_path = ensure_ca_bundle(hostname)
    if pem_path:
        return pem_path

    return True


def _print_ssl_error_help(hostname: str) -> None:
    """Print actionable SSL troubleshooting suggestions to stderr.

    Args:
        hostname: The hostname that failed SSL verification.
    """
    print(f"\n  ✗ SSL verification failed for {hostname}.", file=sys.stderr)
    print("  This is common on corporate networks with custom CA certificates.", file=sys.stderr)
    print("\n  Suggestions:", file=sys.stderr)
    print("    1. Run `agdt-setup-certs` to refresh the CA certificate cache.", file=sys.stderr)
    print("    2. Set REQUESTS_CA_BUNDLE=/path/to/corporate-ca.pem", file=sys.stderr)
    print("    3. Use `agdt-setup --no-verify-ssl` to skip SSL verification (insecure).", file=sys.stderr)


def ssl_request_with_retry(
    url: str,
    hostname: str,
    *,
    timeout: int = 30,
    stream: bool = False,
) -> "requests.Response":
    """Make a GET request with automatic SSL retry for corporate networks.

    Behaviour:
    1. If the ``AGDT_NO_VERIFY_SSL`` environment variable is set, the request
       is made with ``verify=False`` and a warning is printed.  No retry is
       attempted.
    2. Otherwise the first attempt uses :func:`get_ssl_verify` to pick the best
       available CA bundle.
    3. On :class:`requests.exceptions.SSLError` the cached CA bundle is
       invalidated, a fresh bundle is fetched, and the request is retried once.
    4. If the retry also fails, :func:`_print_ssl_error_help` prints actionable
       suggestions before re-raising the exception.

    Args:
        url: The URL to request.
        hostname: The target server hostname (used for CA bundle lookup).
        timeout: Request timeout in seconds.
        stream: Whether to stream the response.

    Returns:
        The :class:`requests.Response` object.

    Raises:
        requests.RequestException: On network errors after all retries.
    """
    import requests

    # --no-verify-ssl override via environment variable.
    # The user has explicitly opted in by setting AGDT_NO_VERIFY_SSL (via agdt-setup --no-verify-ssl)
    # and is aware of the security implications (printed warning during setup).
    if os.environ.get("AGDT_NO_VERIFY_SSL"):
        print(
            "  ⚠  SSL verification disabled (AGDT_NO_VERIFY_SSL). Use only on trusted networks.",
            file=sys.stderr,
        )
        print("  ℹ Using CA bundle: False (SSL verification disabled)", file=sys.stderr)
        return requests.get(url, timeout=timeout, stream=stream, verify=False)  # noqa: S501

    verify = get_ssl_verify(hostname)
    try:
        print(f"  ℹ Using CA bundle: {verify}", file=sys.stderr)
        return requests.get(url, timeout=timeout, stream=stream, verify=verify)
    except requests.exceptions.SSLError as ssl_error:
        # Force-refetch the CA bundle and retry once.
        # The refreshed bundle is typically written to the same cache path, so we
        # always retry when a bundle is available (the file contents may have changed).
        last_ssl_error = ssl_error
        verify_retry = ensure_ca_bundle(hostname, force=True)
        if verify_retry:
            try:
                print(f"  ℹ Using CA bundle: {verify_retry}", file=sys.stderr)
                return requests.get(url, timeout=timeout, stream=stream, verify=verify_retry)
            except requests.exceptions.SSLError as retry_error:
                last_ssl_error = retry_error
        _print_ssl_error_help(hostname)
        raise last_ssl_error
