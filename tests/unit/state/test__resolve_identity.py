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
        """john-paul.doe_smith → 4 parts; first='john', second='paul' → jpa."""
        email = "john-paul.doe_smith@example.com"
        with patch(
            "agentic_devtools.state.subprocess.run",
            return_value=_mock_git_email(email),
        ):
            result = state._resolve_identity(tmp_path)

        # Split produces ["john", "paul", "doe", "smith"]
        # first="john"[0] + second="paul"[:2] → "jpa"
        assert result == "jpa"

    def test_three_part_email_uses_second_segment(self, tmp_path):
        """Albert.Marsnik.ext@swica.ch → ama (uses 2nd segment 'marsnik', not 3rd 'ext')."""
        with patch(
            "agentic_devtools.state.subprocess.run", return_value=_mock_git_email("Albert.Marsnik.ext@swica.ch")
        ):
            result = state._resolve_identity(tmp_path)

        # Split produces ["albert", "marsnik", "ext"]
        # first="albert"[0] + second="marsnik"[:2] → "ama"
        assert result == "ama"

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

        # ama collides → try amar (extend second, 4 chars) vs alma (extend first, 4 chars)
        # Both 4 chars → prefer second name (amar)
        assert result == "amar"

    def test_collision_prefers_second_name_on_tie(self, tmp_path):
        """When both extensions yield same length, prefer second name."""
        _setup_identity_owner(tmp_path, "ama", "other@example.com")

        with patch("agentic_devtools.state.subprocess.run", return_value=_mock_git_email("albert.marsnik@example.com")):
            result = state._resolve_identity(tmp_path)

        # amar and alma both 4 chars → prefer amar (second name extension)
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
        # With only 1 char in first ("a") and 1 char in second ("b"),
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


class TestResolveIdentityEdgeCases:
    """Tests for edge cases in identity derivation."""

    def test_empty_local_part(self, tmp_path):
        """Email with empty local part → default."""
        with patch("agentic_devtools.state.subprocess.run", return_value=_mock_git_email("@example.com")):
            result = state._resolve_identity(tmp_path)

        assert result == "default"

    def test_all_delimiter_local_part(self, tmp_path):
        """Email local part is all delimiters → default."""
        with patch("agentic_devtools.state.subprocess.run", return_value=_mock_git_email(".-._@example.com")):
            result = state._resolve_identity(tmp_path)

        assert result == "default"

    def test_dir_without_identity_owner_is_collision(self, tmp_path):
        """Existing directory without .identity-owner treated as collision."""
        # Create directory without .identity-owner file
        (tmp_path / ".agdt" / "workflows" / "ama").mkdir(parents=True)

        with patch("agentic_devtools.state.subprocess.run", return_value=_mock_git_email("albert.marsnik@example.com")):
            result = state._resolve_identity(tmp_path)

        # "ama" is treated as claimed → must resolve to something else
        assert result != "ama"
        assert result == "amar"  # extends second name

    def test_unreadable_owner_file_is_collision(self, tmp_path):
        """Owner file that raises OSError is treated as collision."""
        identity_dir = tmp_path / ".agdt" / "workflows" / "ama"
        identity_dir.mkdir(parents=True)
        owner_file = identity_dir / ".identity-owner"
        owner_file.write_text("other@example.com", encoding="utf-8")
        # Make unreadable
        owner_file.chmod(0o000)

        try:
            email = "albert.marsnik@example.com"
            with patch(
                "agentic_devtools.state.subprocess.run",
                return_value=_mock_git_email(email),
            ):
                result = state._resolve_identity(tmp_path)

            # Unreadable → treated as collision (empty sentinel)
            assert result != "ama"
        finally:
            # Restore permissions for cleanup
            owner_file.chmod(0o644)

    def test_collision_both_unique_prefers_shorter(self, tmp_path):
        """When both extensions are unique but different length, pick shorter."""
        # Set up collision for "ama" with a long first name and short second name
        # john.ma → initial "jma"
        _setup_identity_owner(tmp_path, "jma", "other@example.com")

        # Extensions: jma (3) → jmac (extend second, 4) vs joma (extend first, 4)
        # Both 4 chars → tie → prefer second name (jmac)
        with patch(
            "agentic_devtools.state.subprocess.run",
            return_value=_mock_git_email("john.mack@example.com"),
        ):
            result = state._resolve_identity(tmp_path)

        assert result == "jmac"

    def test_collision_neither_unique_advances(self, tmp_path):
        """When neither single extension is unique, keep trying."""
        # Set up so both amar and alma collide too
        _setup_identity_owner(tmp_path, "ama", "user1@example.com")
        _setup_identity_owner(tmp_path, "amar", "user2@example.com")
        _setup_identity_owner(tmp_path, "alma", "user3@example.com")

        with patch(
            "agentic_devtools.state.subprocess.run",
            return_value=_mock_git_email("albert.marsnik@example.com"),
        ):
            result = state._resolve_identity(tmp_path)

        # Both first extensions collide → advance both → try amars/albma etc
        assert result not in ("ama", "amar", "alma")

    def test_collision_only_a_unique(self, tmp_path):
        """When only second-name extension is unique, use it."""
        # Set up collision for initial candidate
        _setup_identity_owner(tmp_path, "jdo", "user1@example.com")
        # Also make first-name extension collide: jodo
        _setup_identity_owner(tmp_path, "jodo", "user2@example.com")

        with patch(
            "agentic_devtools.state.subprocess.run",
            return_value=_mock_git_email("john.doe@example.com"),
        ):
            result = state._resolve_identity(tmp_path)

        # jdo collides → opt_a=jdoe (unique), opt_b=jodo (collides) → jdoe
        assert result == "jdoe"

    def test_collision_only_b_unique(self, tmp_path):
        """When only first-name extension is unique, use it."""
        # ama collides, extend-second (amar) also collides, but extend-first (alma) is unique
        _setup_identity_owner(tmp_path, "ama", "user1@example.com")
        _setup_identity_owner(tmp_path, "amar", "user2@example.com")

        with patch(
            "agentic_devtools.state.subprocess.run",
            return_value=_mock_git_email("albert.marsnik@example.com"),
        ):
            result = state._resolve_identity(tmp_path)

        # Only option B (alma) is unique at first iteration
        assert result == "alma"

    def test_email_with_plus_tag_produces_safe_identity(self, tmp_path):
        """Email local part with '+' tag (e.g. doe+work) is sanitized to alphanumeric only."""
        with patch("agentic_devtools.state.subprocess.run", return_value=_mock_git_email("doe+work@example.com")):
            result = state._resolve_identity(tmp_path)

        # "doe+work" → split on [.-_] → ["doe+work"] → sanitize → ["doework"]
        # first="doework", candidate = first[:3] = "doe"
        assert result == "doe"
        assert state.is_safe_dir_segment(result)

    def test_email_with_equals_char_produces_safe_identity(self, tmp_path):
        """Email local part with '=' char is sanitized to alphanumeric only."""
        with patch("agentic_devtools.state.subprocess.run", return_value=_mock_git_email("user=tag@example.com")):
            result = state._resolve_identity(tmp_path)

        # "user=tag" → split on [.-_] → ["user=tag"] → sanitize → ["usertag"]
        # first="usertag", candidate = first[:3] = "use"
        assert result == "use"
        assert state.is_safe_dir_segment(result)

    def test_email_with_only_special_chars_after_sanitize_returns_default(self, tmp_path):
        """Email local part that reduces to empty after sanitization returns 'default'."""
        with patch("agentic_devtools.state.subprocess.run", return_value=_mock_git_email("+=!@example.com")):
            result = state._resolve_identity(tmp_path)

        assert result == "default"

    def test_ignores_non_directory_entries_under_workflows(self, tmp_path):
        """Non-directory workflow entries are ignored safely."""
        workflows_dir = tmp_path / ".agdt" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)
        (workflows_dir / "README.txt").write_text("not a directory", encoding="utf-8")

        with patch("agentic_devtools.state.subprocess.run", return_value=_mock_git_email("albert.marsnik@example.com")):
            result = state._resolve_identity(tmp_path)

        assert result == "ama"
