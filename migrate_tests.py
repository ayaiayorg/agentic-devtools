#!/usr/bin/env python3
"""
Script to migrate Azure DevOps tests to 1:1:1 structure.
"""
import os
import re
from pathlib import Path

# Base paths
OLD_TEST_DIR = Path("tests/azure_devops")
NEW_TEST_DIR = Path("tests/unit/cli/azure_devops")

def read_file(filepath):
    """Read file content."""
    with open(filepath, 'r') as f:
        return f.read()

def write_file(filepath, content):
    """Write file content."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(content)

def extract_imports_and_fixtures(content):
    """Extract imports and module-level fixtures from content."""
    lines = content.split('\n')
    imports = []
    in_imports = True
    
    for line in lines:
        if line.startswith('import ') or line.startswith('from '):
            imports.append(line)
        elif line.strip() and not line.startswith('#') and not line.startswith('"""'):
            if not line.startswith('@') and not line.startswith('def '):
                in_imports = False
    
    return '\n'.join(imports)

def extract_test_class(content, class_name):
    """Extract a complete test class from content."""
    pattern = rf'^class {class_name}:.*?(?=^class |\Z)'
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    if match:
        return match.group(0)
    return None

def extract_imports_from_file(filepath):
    """Extract standard imports from a test file."""
    content = read_file(filepath)
    lines = content.split('\n')
    imports = []
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('import ') or stripped.startswith('from '):
            imports.append(line)
        elif stripped and not stripped.startswith('#') and not stripped.startswith('"""'):
            if not (stripped.startswith('@') or stripped.startswith('def ') or stripped.startswith('class ')):
                continue
            else:
                break
    
    return '\n'.join(imports)

# Test file mappings
test_mappings = {
    # auth.py functions
    ('auth', 'test_get_pat.py'): ('test_auth.py', 'TestAuthentication', [
        'test_get_pat_from_env',
        'test_get_pat_from_ext_env_fallback',
        'test_get_pat_prefers_copilot_pat',
        'test_get_pat_missing_raises'
    ]),
    ('auth', 'test_get_auth_headers.py'): ('test_auth.py', 'TestAuthentication', [
        'test_get_auth_headers',
        'test_get_auth_headers_base64_encoding'
    ]),
}

def create_auth_tests():
    """Create auth test files."""
    print("Creating auth tests...")
    
    # Read source file
    source = read_file(OLD_TEST_DIR / 'test_auth.py')
    imports = extract_imports_from_file(OLD_TEST_DIR / 'test_auth.py')
    
    # test_get_pat.py
    test_get_pat_content = f'''"""Tests for get_pat function."""
{imports}


class TestGetPat:
    """Tests for get_pat function."""

    def test_get_pat_from_env(self):
        """Test getting PAT from environment variable."""
        with patch.dict("os.environ", {{"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"}}):
            pat = azure_devops.get_pat()
            assert pat == "test-pat"

    def test_get_pat_from_ext_env_fallback(self):
        """Test getting PAT from AZURE_DEVOPS_EXT_PAT as fallback."""
        with patch.dict("os.environ", {{"AZURE_DEVOPS_EXT_PAT": "ext-test-pat"}}, clear=True):
            pat = azure_devops.get_pat()
            assert pat == "ext-test-pat"

    def test_get_pat_prefers_copilot_pat(self):
        """Test that AZURE_DEV_OPS_COPILOT_PAT takes precedence over AZURE_DEVOPS_EXT_PAT."""
        with patch.dict("os.environ", {{"AZURE_DEV_OPS_COPILOT_PAT": "copilot-pat", "AZURE_DEVOPS_EXT_PAT": "ext-pat"}}):
            pat = azure_devops.get_pat()
            assert pat == "copilot-pat"

    def test_get_pat_missing_raises(self):
        """Test that missing PAT raises EnvironmentError."""
        with patch.dict("os.environ", clear=True):
            with pytest.raises(EnvironmentError, match="AZURE_DEV_OPS_COPILOT_PAT"):
                azure_devops.get_pat()
'''
    
    write_file(NEW_TEST_DIR / 'auth' / 'test_get_pat.py', test_get_pat_content)
    
    # test_get_auth_headers.py
    test_get_auth_headers_content = f'''"""Tests for get_auth_headers function."""
{imports}


class TestGetAuthHeaders:
    """Tests for get_auth_headers function."""

    def test_get_auth_headers(self):
        """Test auth headers contain required fields."""
        headers = azure_devops.get_auth_headers("test-pat")
        assert "Authorization" in headers
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"

    def test_get_auth_headers_base64_encoding(self):
        """Test auth header uses base64 encoded PAT."""
        headers = azure_devops.get_auth_headers("test-pat")
        # Base64 of ":test-pat" is "OnRlc3QtcGF0"
        assert "OnRlc3QtcGF0" in headers["Authorization"]
        assert headers["Authorization"].startswith("Basic ")
'''
    
    write_file(NEW_TEST_DIR / 'auth' / 'test_get_auth_headers.py', test_get_auth_headers_content)
    print("✓ Created auth tests")

def main():
    """Main migration function."""
    print("Starting test migration...")
    create_auth_tests()
    print("\nMigration complete!")

if __name__ == '__main__':
    main()
