#!/usr/bin/env python3
"""
Complete Azure DevOps test migration to 1:1:1 structure.

This script performs the full migration by:
1. Reading existing consolidated test files
2. Extracting test classes
3. Creating individual test files per function
4. Creating stub files for functions without tests
"""

import re
from pathlib import Path
from typing import List, Tuple

NEW_DIR = Path("tests/unit/cli/azure_devops")

def read_file(path):
    with open(path, 'r') as f:
        return f.read()

def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)

def extract_imports(content):
    """Extract all imports from file."""
    lines = content.split('\n')
    imports = []
    in_docstring = False
    docstring_char = None
    
    for line in lines:
        stripped = line.strip()
        
        # Handle docstrings
        if stripped.startswith('"""') or stripped.startswith("'''"):
            if not in_docstring:
                in_docstring = True
                docstring_char = stripped[:3]
                if stripped.endswith(docstring_char) and len(stripped) > 3:
                    in_docstring = False
            elif stripped.endswith(docstring_char):
                in_docstring = False
            continue
        
        if in_docstring:
            continue
            
        if stripped.startswith('import ') or stripped.startswith('from '):
            imports.append(line)
        elif stripped and not stripped.startswith('#'):
            break
    
    return '\n'.join(imports)

def extract_full_class(content, class_name):
    """Extract complete class definition."""
    pattern = rf'^class {re.escape(class_name)}[:\(]'
    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        return None
    
    start = match.start()
    lines = content[start:].split('\n')
    
    class_lines = [lines[0]]
    
    for i in range(1, len(lines)):
        line = lines[i]
        if line and not line[0].isspace() and not line.strip().startswith('#'):
            break
        class_lines.append(line)
    
    return '\n'.join(class_lines).rstrip() + '\n'

def create_stub_file(target_path, func_name):
    """Create a stub test file for functions without tests."""
    content = f'''"""Tests for {func_name} function."""
import pytest


def test_{func_name.replace(" ", "_")}_not_implemented():
    """Test for {func_name} not yet implemented."""
    raise NotImplementedError("Tests for {func_name} not yet implemented")
'''
    write_file(target_path, content)

def create_test_file(target_path, func_desc, imports, class_contents):
    """Create a test file with proper structure."""
    content = f'''"""Tests for {func_desc}."""
{imports}


{chr(10).join(class_contents)}'''
    write_file(target_path, content)

# Complete migration map
# Format: (source_dir, target_file, source_files_and_classes, func_description)
# source_files_and_classes is a list of (source_file, [class_names])

MIGRATIONS = [
    # COMMANDS - reply_to_pull_request_thread
    ('commands', 'test_reply_to_pull_request_thread', [
        ('test_commands_dry_run.py', ['TestReplyToPullRequestThread']),
        ('test_commands_api.py', ['TestReplyToPullRequestThreadActualCall']),
    ], 'reply_to_pull_request_thread function'),
    
    # COMMANDS - add_pull_request_comment
    ('commands', 'test_add_pull_request_comment', [
        ('test_commands_dry_run.py', ['TestAddPullRequestComment']),
        ('test_commands_api.py', ['TestAddPullRequestCommentActualCall']),
    ], 'add_pull_request_comment function'),
    
    # COMMANDS - create_pull_request
    ('commands', 'test_create_pull_request', [
        ('test_commands_dry_run.py', ['TestCreatePullRequest']),
        ('test_commands_api.py', ['TestCreatePullRequestActualCall']),
    ], 'create_pull_request function'),
    
    # COMMANDS - resolve_thread
    ('commands', 'test_resolve_thread', [
        ('test_commands_dry_run.py', ['TestResolveThread']),
        ('test_commands_api.py', ['TestResolveThreadActualCall']),
    ], 'resolve_thread function'),
    
    # COMMANDS - get_pull_request_threads
    ('commands', 'test_get_pull_request_threads', [
        ('test_commands_dry_run.py', ['TestGetPullRequestThreads']),
        ('test_commands_api.py', ['TestGetPullRequestThreadsActualCall']),
    ], 'get_pull_request_threads function'),
    
    # COMMANDS - approve_pull_request
    ('commands', 'test_approve_pull_request', [
        ('test_commands_dry_run.py', ['TestApprovePullRequest']),
        ('test_commands_api.py', ['TestApprovePullRequestActualCall']),
    ], 'approve_pull_request function'),
    
    # COMMANDS - mark_pull_request_draft
    ('commands', 'test_mark_pull_request_draft', [
        ('test_commands_dry_run.py', ['TestMarkPullRequestDraft']),
        ('test_commands_api.py', ['TestMarkPullRequestDraftActualCall']),
    ], 'mark_pull_request_draft function'),
    
    # COMMANDS - publish_pull_request
    ('commands', 'test_publish_pull_request', [
        ('test_commands_dry_run.py', ['TestPublishPullRequest']),
        ('test_commands_api.py', ['TestPublishPullRequestActualCall']),
    ], 'publish_pull_request function'),
    
    # HELPERS - All helper functions
    ('helpers', 'test_parse_bool_from_state_value', [
        ('test_helpers.py', ['TestParseBoolFromState']),
    ], 'parse_bool_from_state helper'),
    
    ('helpers', 'test_require_requests', [
        ('test_helpers.py', ['TestRequireRequests']),
    ], 'require_requests helper'),
    
    ('helpers', 'test_require_content', [
        ('test_helpers.py', ['TestRequireContent']),
    ], 'require_content helper'),
    
    ('helpers', 'test_build_thread_context', [
        ('test_helpers.py', ['TestBuildThreadContext']),
    ], 'build_thread_context helper'),
    
    ('helpers', 'test_convert_to_pull_request_title', [
        ('test_helpers.py', ['TestConvertToPullRequestTitle']),
    ], 'convert_to_pull_request_title helper'),
    
    ('helpers', 'test_format_approval_content', [
        ('test_helpers.py', ['TestFormatApprovalContent']),
    ], 'format_approval_content helper'),
    
    ('helpers', 'test_get_repository_id', [
        ('test_helpers.py', ['TestGetRepositoryId']),
    ], 'get_repository_id helper'),
    
    # MARK_REVIEWED
    ('mark_reviewed', 'test_normalize_repo_path', [
        ('test_mark_reviewed.py', ['TestNormalizeRepoPath', 'TestNormalizeRepoPathEdgeCases']),
    ], 'normalize_repo_path function'),
    
    ('mark_reviewed', 'test_mark_file_reviewed', [
        ('test_mark_reviewed.py', ['TestMarkFileReviewedDryRun', 'TestMarkFileReviewedMainPath', 'TestSyncViewedStatus']),
    ], 'mark_file_reviewed function'),
    
    ('mark_reviewed', 'test_mark_file_reviewed_cli', [
        ('test_mark_reviewed.py', ['TestMarkFileReviewedCli']),
    ], 'mark_file_reviewed_cli function'),
    
    # PIPELINE_COMMANDS
    ('pipeline_commands', 'test_run_e2e_tests_synapse', [
        ('test_commands_dry_run.py', ['TestRunE2eTestsSynapse']),
        ('test_commands_api.py', ['TestRunE2eTestsSynapseActualCall']),
        ('test_pipeline_commands.py', ['TestRunE2eTestsSynapseJsonParseError']),
    ], 'run_e2e_tests_synapse function'),
    
    ('pipeline_commands', 'test_run_e2e_tests_fabric', [
        ('test_commands_dry_run.py', ['TestRunE2eTestsFabric']),
        ('test_commands_api.py', ['TestRunE2eTestsFabricActualCall']),
        ('test_pipeline_commands.py', ['TestRunE2eTestsFabricJsonParseError']),
    ], 'run_e2e_tests_fabric function'),
    
    ('pipeline_commands', 'test_run_wb_patch', [
        ('test_commands_dry_run.py', ['TestRunWbPatch']),
        ('test_commands_api.py', ['TestRunWbPatchActualCall']),
        ('test_pipeline_commands.py', ['TestRunWbPatchJsonParseError']),
    ], 'run_wb_patch function'),
    
    ('pipeline_commands', 'test_list_pipelines', [
        ('test_pipeline_commands.py', ['TestListPipelinesDryRun', 'TestListPipelinesApiCall']),
    ], 'list_pipelines function'),
    
    ('pipeline_commands', 'test_get_pipeline_id', [
        ('test_pipeline_commands.py', ['TestGetPipelineIdDryRun', 'TestGetPipelineIdApiCall', 'TestGetPipelineIdJsonParseError']),
    ], 'get_pipeline_id function'),
    
    ('pipeline_commands', 'test_create_pipeline', [
        ('test_pipeline_commands.py', ['TestCreatePipelineDryRun', 'TestCreatePipelineApiCall', 'TestCreatePipelineJsonParseError']),
    ], 'create_pipeline function'),
    
    ('pipeline_commands', 'test_update_pipeline', [
        ('test_pipeline_commands.py', ['TestUpdatePipelineDryRun', 'TestUpdatePipelineApiCall', 'TestUpdatePipelineUrlOutput']),
    ], 'update_pipeline function'),
    
    # FILE_REVIEW_COMMANDS
    ('file_review_commands', 'test_approve_file', [
        ('test_file_review_commands.py', ['TestApproveFile']),
    ], 'approve_file function'),
    
    ('file_review_commands', 'test_submit_file_review', [
        ('test_file_review_commands.py', ['TestSubmitFileReview']),
    ], 'submit_file_review function'),
    
    ('file_review_commands', 'test_request_changes', [
        ('test_file_review_commands.py', ['TestRequestChanges']),
    ], 'request_changes function'),
    
    ('file_review_commands', 'test_request_changes_with_suggestion', [
        ('test_file_review_commands.py', ['TestRequestChangesWithSuggestion']),
    ], 'request_changes_with_suggestion function'),
    
    # PR_SUMMARY_COMMANDS
    ('pr_summary_commands', 'test_generate_overarching_pr_comments', [
        ('test_pr_summary_commands.py', ['TestGenerateOverarchingPrComments']),
    ], 'generate_overarching_pr_comments function'),
    
    ('pr_summary_commands', 'test_generate_overarching_pr_comments_cli', [
        ('test_pr_summary_commands.py', ['TestGenerateOverarchingPrCommentsCli']),
    ], 'generate_overarching_pr_comments_cli function'),
]

def run_migration():
    """Execute the full migration."""
    print("=" * 60)
    print("Azure DevOps Tests - Full 1:1:1 Migration")
    print("=" * 60)
    print()
    
    created = 0
    skipped = 0
    errors = 0
    
    for source_dir, target_file, sources, func_desc in MIGRATIONS:
        try:
            # Collect all class content and imports
            all_imports = set()
            all_classes = []
            
            for source_file, class_names in sources:
                source_path = NEW_DIR / source_dir / source_file
                if not source_path.exists():
                    print(f"⚠ Source file not found: {source_dir}/{source_file}")
                    skipped += 1
                    continue
                
                content = read_file(source_path)
                imports = extract_imports(content)
                if imports:
                    for line in imports.split('\n'):
                        if line.strip():
                            all_imports.add(line)
                
                for class_name in class_names:
                    class_content = extract_full_class(content, class_name)
                    if class_content:
                        all_classes.append(class_content)
                    else:
                        print(f"⚠ Class {class_name} not found in {source_file}")
            
            if all_classes:
                target_path = NEW_DIR / source_dir / f"{target_file}.py"
                sorted_imports = sorted(list(all_imports))
                create_test_file(target_path, func_desc, '\n'.join(sorted_imports), all_classes)
                created += 1
                print(f"✓ Created {source_dir}/{target_file}.py ({len(all_classes)} test classes)")
            else:
                print(f"⚠ No classes found for {target_file}")
                skipped += 1
                
        except Exception as e:
            print(f"✗ Error creating {target_file}: {e}")
            errors += 1
    
    print()
    print("=" * 60)
    print(f"Migration Summary:")
    print(f"  Created: {created}")
    print(f"  Skipped: {skipped}")
    print(f"  Errors: {errors}")
    print("=" * 60)

if __name__ == "__main__":
    run_migration()
