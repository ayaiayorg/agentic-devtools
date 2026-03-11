"""Tests for agentic_devtools.state._resolve_identity."""

from unittest.mock import MagicMock, patch

from agentic_devtools import state


def _mock_git_email(email: str):
    """Return a mock subprocess result simulating git config user.email."""
    mock = MagicMock()
    mock.returncode = 0
    mock.stdout = f"{email}\n"
    return mock


def _mock_git_email_fail():
    """Return a mock subprocess result simulating git config failure."""
    mock = MagicMock()
    mock.returncode = 1
    mock.stdout = ""
    return mock


def _setup_identity_owner(git_root, identity, email):
    """Create a .identity-owner file for the given identity."""
    identity_dir = git_root / ".agdt" / "workflows" / identity
    identity_dir.mkdir(parents=True, exist_ok=True)
    (identity_dir / ".identity-owner").write_text(email, encoding="utf-8")


class TestResolveIdentityBasic:
    """Tests for basic identity derivation from email."""

    def test_normal_two_part_name(self, tmp_path):
        """albert.marsnik@example.com → ama."""
        with patch("agentic_devtools.state.subprocess.run", return_value=_mock_git_email("albert.marsnik@example.com")):
            result = state._resolve_identity(tmp_path)

        assert result == "ama"

    def test_single_part_name(self, tmp_path):
        """admin@example.com → adm."""
        with patch("agentic_devtools.state.subprocess.run", return_value=_mock_git_email("admin@example.com")):
            result = state._resolve_identity(tmp_path)

        assert result == "adm"

    def test_short_name_parts(self, tmp_path):
        """a.b@example.com → ab."""
        with patch("agentic_devtools.state.subprocess.run", return_value=_mock_git_email("a.b@example.com")):
            result = state._resolve_identity(tmp_path)

        assert result == "ab"

    def test_hyphenated_email(self, tmp_path):
        """john-doe@example.com → jdo."""
        with patch("agentic_devtools.state.subprocess.run", return_value=_mock_git_email("john-doe@example.com")):
            result = state._resolve_identity(tmp_path)

        assert result == "jdo"

    def test_underscore_email(self, tmp_path):
        """john_doe@example.com → jdo."""
        with patch("agentic_devtools.state.subprocess.run", return_value=_mock_git_email("john_doe@example.com")):
            result = state._resolve_identity(tmp_path)

        assert result == "jdo"

    def test_mixed_delimiters(self, tmp_path):
        """john-paul.doe_smith → 4 parts; first='john', last='smith' → jsm."""
        email = "john-paul.doe_smith@example.com"
        with patch(
            "agentic_devtools.state.subprocess.run",
            return_value=_mock_git_email(email),
        ):
            result = state._resolve_identity(tmp_path)

        # Split produces ["john", "paul", "doe", "smith"]
        # first="john"[0] + last="smith"[:2] → "jsm"
        assert result == "jsm"

    def test_no_git_email_returns_default(self, tmp_path):
        """Returns 'default' when git config user.email fails."""
        with patch("agentic_devtools.state.subprocess.run", return_value=_mock_git_email_fail()):
            result = state._resolve_identity(tmp_path)

        assert result == "default"

    def test_no_git_root_returns_default(self):
        """Returns 'default' when git_root is None."""
        with patch.object(state, "_get_git_repo_root", return_value=None):
            result = state._resolve_identity(None)
        assert result == "default"


class TestResolveIdentityCollision:
    """Tests for collision resolution in identity derivation."""

    def test_collision_prefers_shorter_extension(self, tmp_path):
        """When extending, pick the shorter unique result."""
        # Set up existing identity "ama" owned by a different email
        _setup_identity_owner(tmp_path, "ama", "other.user@example.com")

        with patch("agentic_devtools.state.subprocess.run", return_value=_mock_git_email("albert.marsnik@example.com")):
            result = state._resolve_identity(tmp_path)

        # ama collides → try amar (extend last, 4 chars) vs alma (extend first, 4 chars)
        # Both 4 chars → prefer last name (amar)
        assert result == "amar"

    def test_collision_prefers_last_name_on_tie(self, tmp_path):
        """When both extensions yield same length, prefer last name."""
        _setup_identity_owner(tmp_path, "ama", "other@example.com")

        with patch("agentic_devtools.state.subprocess.run", return_value=_mock_git_email("albert.marsnik@example.com")):
            result = state._resolve_identity(tmp_path)

        # amar and alma both 4 chars → prefer amar (last name extension)
        assert result == "amar"

    def test_collision_chain(self, tmp_path):
        """Multiple collisions resolved correctly."""
        # Set up: ama taken by different user, amar taken by different user
        _setup_identity_owner(tmp_path, "ama", "user1@example.com")
        _setup_identity_owner(tmp_path, "amar", "user2@example.com")

        email = "andreas.martino@example.com"
        with patch("agentic_devtools.state.subprocess.run", return_value=_mock_git_email(email)):
            result = state._resolve_identity(tmp_path)

        # ama collides → amar collides, anma unique → anma
        assert result == "anma"

    def test_collision_numeric_fallback(self, tmp_path):
        """All chars exhausted → appends 1, 2, etc."""
        # Use a very short email: a.b@example.com → initial "ab"
        # Set up collisions for all possible char extensions
        _setup_identity_owner(tmp_path, "ab", "other1@example.com")
        # With only 1 char in first ("a") and 1 char in last ("b"),
        # there are no chars left to extend. Numeric fallback kicks in.

        with patch("agentic_devtools.state.subprocess.run", return_value=_mock_git_email("a.b@example.com")):
            result = state._resolve_identity(tmp_path)

        assert result == "ab1"

    def test_no_collision_same_email(self, tmp_path):
        """Same email → same identity (no collision)."""
        _setup_identity_owner(tmp_path, "ama", "albert.marsnik@example.com")

        with patch("agentic_devtools.state.subprocess.run", return_value=_mock_git_email("albert.marsnik@example.com")):
            result = state._resolve_identity(tmp_path)

        assert result == "ama"

    def test_numeric_fallback_increments(self, tmp_path):
        """Numeric suffix increments until unique."""
        _setup_identity_owner(tmp_path, "ab", "user1@example.com")
        _setup_identity_owner(tmp_path, "ab1", "user2@example.com")

        with patch("agentic_devtools.state.subprocess.run", return_value=_mock_git_email("a.b@example.com")):
            result = state._resolve_identity(tmp_path)

        assert result == "ab2"
