"""Tests for _build_unified_ca_bundle."""

from pathlib import Path
from unittest.mock import patch

from agentic_devtools.cli.setup.commands import _build_unified_ca_bundle

_FAKE_CERT_A = (
    "-----BEGIN CERTIFICATE-----\n"
    "MIIDLEAFCERT0000000000000000000000000000000000000000000000000000\n"
    "-----END CERTIFICATE-----"
)
_FAKE_CERT_B = (
    "-----BEGIN CERTIFICATE-----\n"
    "MIIDLEAFCERT1111111111111111111111111111111111111111111111111111\n"
    "-----END CERTIFICATE-----"
)
_FAKE_CERT_INTERMEDIATE = (
    "-----BEGIN CERTIFICATE-----\n"
    "MIIDINTERMEDIATECERT22222222222222222222222222222222222222222222\n"
    "-----END CERTIFICATE-----"
)
_FAKE_CERT_ROOT = (
    "-----BEGIN CERTIFICATE-----\n"
    "MIIDROOTCERT333333333333333333333333333333333333333333333333333\n"
    "-----END CERTIFICATE-----"
)


class TestBuildUnifiedCaBundle:
    """Tests for _build_unified_ca_bundle."""

    def test_returns_none_when_certifi_unavailable(self, tmp_path):
        """Returns None when certifi cannot be imported."""
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "certifi":
                raise ImportError("certifi not available")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = _build_unified_ca_bundle([])

        assert result is None

    def test_creates_unified_bundle_at_expected_path(self, tmp_path):
        """Creates unified-ca-bundle.pem under ~/.agdt/certs/."""
        certifi_pem_path = tmp_path / "cacert.pem"
        certifi_pem_path.write_text(_FAKE_CERT_A + "\n", encoding="utf-8")

        with patch("certifi.where", return_value=str(certifi_pem_path)):
            with patch.object(Path, "home", return_value=tmp_path):
                result = _build_unified_ca_bundle([])

        assert result is not None
        # The unified bundle is written under ~/.agdt/certs/
        assert "unified-ca-bundle.pem" in str(result)
        assert result.exists()

    def test_appends_non_leaf_certs_from_per_host_pems(self, tmp_path):
        """Non-leaf certs (index > 0) from per-host PEMs are appended to the bundle."""
        # Write a fake certifi bundle with one cert
        certifi_pem_path = tmp_path / "cacert.pem"
        certifi_pem_path.write_text(_FAKE_CERT_A + "\n", encoding="utf-8")

        # Write a per-host PEM with leaf cert (index 0) + intermediate (index 1) + root (index 2)
        host_pem_path = tmp_path / "host.pem"
        host_pem_content = "\n".join([_FAKE_CERT_B, _FAKE_CERT_INTERMEDIATE, _FAKE_CERT_ROOT])
        host_pem_path.write_text(host_pem_content, encoding="utf-8")

        with patch("certifi.where", return_value=str(certifi_pem_path)):
            with patch.object(Path, "home", return_value=tmp_path):
                result = _build_unified_ca_bundle([str(host_pem_path)])

        assert result is not None
        content = result.read_text(encoding="utf-8")
        # Leaf cert (CERT_B) must NOT be in the unified bundle
        assert _FAKE_CERT_B not in content
        # Intermediate and root MUST be in the unified bundle
        assert _FAKE_CERT_INTERMEDIATE in content
        assert _FAKE_CERT_ROOT in content
        # Original certifi cert must still be present
        assert _FAKE_CERT_A in content

    def test_deduplicates_certs(self, tmp_path):
        """The same certificate is not added twice to the unified bundle."""
        certifi_pem_path = tmp_path / "cacert.pem"
        certifi_pem_path.write_text(_FAKE_CERT_A + "\n", encoding="utf-8")

        # Two host PEMs sharing the same intermediate cert
        host_pem_1 = tmp_path / "host1.pem"
        host_pem_1.write_text("\n".join([_FAKE_CERT_B, _FAKE_CERT_INTERMEDIATE]), encoding="utf-8")
        host_pem_2 = tmp_path / "host2.pem"
        host_pem_2.write_text("\n".join([_FAKE_CERT_ROOT, _FAKE_CERT_INTERMEDIATE]), encoding="utf-8")

        with patch("certifi.where", return_value=str(certifi_pem_path)):
            with patch.object(Path, "home", return_value=tmp_path):
                result = _build_unified_ca_bundle([str(host_pem_1), str(host_pem_2)])

        assert result is not None
        content = result.read_text(encoding="utf-8")
        assert content.count(_FAKE_CERT_INTERMEDIATE) == 1

    def test_no_extra_certs_writes_certifi_bundle(self, tmp_path):
        """When there are no new corporate certs, writes certifi bundle as-is."""
        certifi_pem_path = tmp_path / "cacert.pem"
        certifi_pem_path.write_text(_FAKE_CERT_A + "\n", encoding="utf-8")

        # Host PEM with only a leaf cert — nothing to add
        host_pem = tmp_path / "host.pem"
        host_pem.write_text(_FAKE_CERT_B, encoding="utf-8")

        with patch("certifi.where", return_value=str(certifi_pem_path)):
            with patch.object(Path, "home", return_value=tmp_path):
                result = _build_unified_ca_bundle([str(host_pem)])

        assert result is not None
        content = result.read_text(encoding="utf-8")
        assert _FAKE_CERT_A in content

    def test_skips_unreadable_pem_files(self, tmp_path, capsys):
        """OSError when reading a per-host PEM file is silently skipped with a warning."""
        certifi_pem_path = tmp_path / "cacert.pem"
        certifi_pem_path.write_text(_FAKE_CERT_A + "\n", encoding="utf-8")

        nonexistent_path = str(tmp_path / "does-not-exist.pem")

        with patch("certifi.where", return_value=str(certifi_pem_path)):
            with patch.object(Path, "home", return_value=tmp_path):
                # Should not raise even though the file doesn't exist
                result = _build_unified_ca_bundle([nonexistent_path])

        assert result is not None
        err = capsys.readouterr().err
        assert "Could not read CA bundle" in err
