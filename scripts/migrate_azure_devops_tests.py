#!/usr/bin/env python3
"""
Comprehensive migration script for Azure DevOps tests to 1:1:1 structure.

This script reads existing test files and reorganizes them into the 1:1:1 testing structure where:
- One folder per source file: tests/unit/cli/azure_devops/{source_file}/
- One test file per function: test_{function_name}.py
- Each directory has __init__.py
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

# Define paths
BASE_DIR = Path(__file__).parent.parent
OLD_TEST_DIR = BASE_DIR / "tests" / "azure_devops"
NEW_TEST_DIR = BASE_DIR / "tests" / "unit" / "cli" / "azure_devops"


def read_file(filepath: Path) -> str:
    """Read and return file content."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def write_file(filepath: Path, content: str):
    """Write content to file, creating directories as needed."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)


def extract_class_with_methods(content: str, class_name: str, method_names: List[str] = None) -> str:
    """
    Extract a test class and optionally filter to specific methods.
    
    Args:
        content: Full file content
        class_name: Name of the class to extract
        method_names: If provided, only include these methods
    
    Returns:
        The class definition with selected methods
    """
    # Find the class definition
    class_pattern = rf'^class {re.escape(class_name)}[:\(].*?(?=^class |\Z)'
    class_match = re.search(class_pattern, content, re.MULTILINE | re.DOTALL)
    
    if not class_match:
        return None
    
    class_content = class_match.group(0)
    
    # If specific methods requested, filter to those
    if method_names:
        lines = class_content.split('\n')
        filtered_lines = []
        current_method = None
        include_current = False
        indent_level = None
        
        for line in lines:
            # Class definition or docstring
            if line.startswith('class ') or (not line.strip() and not filtered_lines):
                filtered_lines.append(line)
                continue
            
            # Check if this is a method definition
            method_match = re.match(r'^    def (test_\w+)', line)
            if method_match:
                current_method = method_match.group(1)
                include_current = current_method in method_names
                if include_current:
                    filtered_lines.append(line)
                    indent_level = len(line) - len(line.lstrip())
            elif include_current:
                # Include lines that are part of the current method
                if line.strip() or filtered_lines[-1].strip():  # Preserve formatting
                    filtered_lines.append(line)
        
        class_content = '\n'.join(filtered_lines)
    
    return class_content


def get_standard_imports(old_file: Path) -> str:
    """Extract imports from the old test file."""
    content = read_file(old_file)
    lines = content.split('\n')
    import_lines = []
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('import ') or stripped.startswith('from '):
            import_lines.append(line)
        elif stripped and not stripped.startswith('#') and not stripped.startswith('"""') and not stripped.startswith("'''"):
            # Stop at first non-import, non-comment, non-docstring line
            if not (stripped.startswith('import ') or stripped.startswith('from ')):
                break
    
    return '\n'.join(import_lines)


def create_test_file(target_path: Path, docstring: str, imports: str, test_class_content: str):
    """Create a single test file with proper formatting."""
    content = f'''"""Tests for {docstring}."""
{imports}

{test_class_content}
'''
    write_file(target_path, content)


def migrate_auth_tests():
    """Migrate auth.py tests."""
    print("Migrating auth tests...")
    source_file = OLD_TEST_DIR / "test_auth.py"
    imports = get_standard_imports(source_file)
    content = read_file(source_file)
    
    # test_get_pat.py
    pat_methods = [
        'test_get_pat_from_env',
        'test_get_pat_from_ext_env_fallback',
        'test_get_pat_prefers_copilot_pat',
        'test_get_pat_missing_raises'
    ]
    pat_class = extract_class_with_methods(content, 'TestAuthentication', pat_methods)
    if pat_class:
        # Rename class
        pat_class = pat_class.replace('class TestAuthentication:', 'class TestGetPat:')
        create_test_file(
            NEW_TEST_DIR / 'auth' / 'test_get_pat.py',
            'get_pat function',
            imports,
            pat_class
        )
    
    # test_get_auth_headers.py
    headers_methods = [
        'test_get_auth_headers',
        'test_get_auth_headers_base64_encoding'
    ]
    headers_class = extract_class_with_methods(content, 'TestAuthentication', headers_methods)
    if headers_class:
        headers_class = headers_class.replace('class TestAuthentication:', 'class TestGetAuthHeaders:')
        create_test_file(
            NEW_TEST_DIR / 'auth' / 'test_get_auth_headers.py',
            'get_auth_headers function',
            imports,
            headers_class
        )


def migrate_config_tests():
    """Migrate config.py tests."""
    print("Migrating config tests...")
    source_file = OLD_TEST_DIR / "test_config.py"
    imports = get_standard_imports(source_file)
    content = read_file(source_file)
    
    # Copy entire classes for config tests since they test dataclass and main function
    test_constants = extract_class_with_methods(content, 'TestConstants')
    test_config = extract_class_with_methods(content, 'TestAzureDevOpsConfig')
    test_overrides = extract_class_with_methods(content, 'TestConfigurationOverrides')
    test_repo_detection = extract_class_with_methods(content, 'TestRepositoryDetection')
    
    # Create test_get_repository_name_from_git_remote.py with all repo detection tests
    if test_repo_detection:
        create_test_file(
            NEW_TEST_DIR / 'config' / 'test_get_repository_name_from_git_remote.py',
            'get_repository_name_from_git_remote function',
            imports,
            test_repo_detection
        )
    
    # Create test_constants.py
    if test_constants:
        create_test_file(
            NEW_TEST_DIR / 'config' / 'test_constants.py',
            'module constants',
            imports,
            test_constants
        )
    
    # Create test_azure_devops_config.py with config dataclass tests
    combined_config = f"{test_config}\n\n\n{test_overrides}" if test_config and test_overrides else (test_config or test_overrides or "")
    if combined_config:
        create_test_file(
            NEW_TEST_DIR / 'config' / 'test_azure_devops_config.py',
            'AzureDevOpsConfig dataclass',
            imports,
            combined_config
        )


def main():
    """Run the migration."""
    print("=" * 60)
    print("Migrating Azure DevOps Tests to 1:1:1 Structure")
    print("=" * 60)
    print()
    
    # Ensure base directories exist
    NEW_TEST_DIR.mkdir(parents=True, exist_ok=True)
    
    # Run migrations
    migrate_auth_tests()
    migrate_config_tests()
    
    print()
    print("=" * 60)
    print("Migration started. Additional manual work needed for remaining files.")
    print("=" * 60)


if __name__ == "__main__":
    main()
