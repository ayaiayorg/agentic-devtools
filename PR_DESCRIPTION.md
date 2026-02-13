# Fix PyPI Publishing 400 Error

## Problem

The PyPI publishing workflow was failing with a **400 Bad Request** error when attempting to upload packages. Investigation revealed that:

1. **Version 0.2.0 already exists on PyPI** - PyPI doesn't allow re-uploading the same version
2. **Hardcoded version in pyproject.toml** - Version was static and not synchronized with Git release tags
3. **No duplicate detection** - Workflow didn't check if version existed before attempting upload
4. **Limited diagnostics** - Errors provided minimal information for troubleshooting

## Solution

This PR implements a comprehensive fix with multiple improvements:

### 1. Dynamic Versioning with hatch-vcs ✨

- Removed hardcoded version = "0.2.0" from pyproject.toml
- Added dynamic = ["version"] to derive version from Git tags
- Integrated hatch-vcs and setuptools-scm for automatic versioning
- Git tag v0.0.10 → Package version 0.0.10

**Benefits:**

- No manual version updates needed
- Perfect sync between Git tags and package versions
- Supports dev versions for non-tagged commits

### 2. Enhanced Workflow Diagnostics 🔍

Added to .github/workflows/publish.yml:

- ✅ fetch-depth: 0 to access full Git history (required by hatch-vcs)
- ✅ Distribution file listing for visibility
- ✅ Version extraction and display
- ✅ twine check --strict validation before upload
- ✅ Pre-upload PyPI duplicate version check
- ✅ Verbose logging (verbose: true, print-hash: true)

### 3. Duplicate Version Prevention 🛡️

- Queries PyPI before upload to check if version exists
- Skips upload with clear warning message if duplicate detected
- Provides actionable guidance (create new tag with unique version)

### 4. Comprehensive Documentation 📚

- **RELEASING.md**: Complete release process guide
- **SOLUTION_SUMMARY.md**: Technical details and benefits
- Versioning strategy explanation
- Troubleshooting guide
- TestPyPI testing instructions

## Changes

### Modified Files

- pyproject.toml - Dynamic versioning configuration
- .github/workflows/publish.yml - Enhanced validation and diagnostics

### New Files

- RELEASING.md - Release process documentation
- SOLUTION_SUMMARY.md - Technical solution summary
- agentic_devtools/_version.py - Auto-generated version file

## Testing

✅ Local build tested successfully:

```bash
$ python -m build
Successfully built agentic_devtools-0.0.9.dev1+gf5d261924.d20260213-py3-none-any.whl

$ twine check --strict dist/*
Checking dist/*.whl: PASSED
Checking dist/*.tar.gz: PASSED
```

✅ YAML workflow syntax validated
✅ Version detection logic tested

## How to Use

For the next release:

1. Create a git tag: git tag v0.0.10
2. Push the tag: git push origin v0.0.10
3. Create a GitHub release from the tag
4. Workflow automatically builds and publishes version 0.0.10

## Acceptance Criteria

- ✅ Prevents 400 Bad Request errors from duplicate uploads
- ✅ Improved logging and diagnostics
- ✅ Robust against attempting to upload existing versions
- ✅ Workflow continues to publish successfully under correct conditions
- ✅ Documentation provided for release process

## Related

Fixes the workflow failure in run [#21980681578](https://github.com/ayaiayorg/agentic-devtools/actions/runs/21980681578)

---

**Note**: This PR includes best practices for Python packaging:

- Semantic versioning from Git tags
- Automated version management
- Pre-upload validation
- Clear error messages and guidance
