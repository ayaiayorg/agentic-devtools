# Release Process for agentic-devtools

## Versioning Strategy

This package uses **automatic semantic versioning** based on Git tags via `hatch-vcs` and `setuptools-scm`.

### How It Works

- **Version source**: Git tags (e.g., `v0.0.10`, `v1.0.0`)
- **Automatic**: Version is automatically derived from the latest tag
- **No manual editing**: Version in `pyproject.toml` is dynamic, not hardcoded
- **Dev versions**: Commits after a tag get `.devN+g{hash}` suffix

### Version Examples

| Git State | Version Built |
|-----------|---------------|
| On tag `v0.0.10` | `0.0.10` |
| 3 commits after `v0.0.10` | `0.0.10.dev3+g{hash}` |
| Dirty working tree | `0.0.10.dev3+g{hash}.d{date}` |

## Release Workflow

### 1. Prepare Release

1. Ensure all changes are merged to `main`
2. Update CHANGELOG.md if needed
3. Ensure tests pass

### 2. Create Release Tag

```bash
# Semantic versioning: MAJOR.MINOR.PATCH
git tag -a v0.0.10 -m "Release v0.0.10"
git push origin v0.0.10
```

### 3. Publish Release on GitHub

1. Go to [Releases page](https://github.com/ayaiayorg/agentic-devtools/releases)
2. Click "Draft a new release"
3. Select the tag you just created (e.g., `v0.0.10`)
4. Add release title and description
5. Click "Publish release"

### 4. Automated Publishing

The GitHub Actions workflow (`.github/workflows/publish.yml`) will:

1. ✅ Build distributions with version from Git tag
2. ✅ List and validate distributions with `twine check --strict`
3. ✅ Check if version already exists on PyPI
4. ✅ Skip upload if version exists (avoids 400 errors)
5. ✅ Publish to PyPI with verbose logging if new version

## Troubleshooting

### Version Already Exists Error

**Symptom**: Workflow fails with "400 Bad Request" or "Version already exists" warning

**Cause**: Attempting to upload a version that already exists on PyPI (PyPI doesn't allow overwrites)

**Solution**:

1. Create a **new** Git tag with a different version: `git tag v0.0.11`
2. Push the tag: `git push origin v0.0.11`
3. Create a new GitHub release for the new tag

### Version Mismatch

**Symptom**: Built package version doesn't match expected tag

**Cause**: Working tree is dirty or not on a tagged commit

**Solution**:

1. Ensure working tree is clean: `git status`
2. Ensure you're on the tagged commit: `git describe --tags`
3. If building locally, commit or stash changes

### Manual Testing

To test versioning locally:

```bash
# Install build dependencies
pip install hatch-vcs build twine

# Build package (version will be derived from Git tags)
python -m build

# Check version in built wheel filename
ls dist/

# Validate package
twine check --strict dist/*
```

## Publishing to TestPyPI

For testing before production:

1. Go to [Actions > Publish to PyPI](https://github.com/ayaiayorg/agentic-devtools/actions/workflows/publish.yml)
2. Click "Run workflow"
3. Select "testpypi" as target
4. Run workflow

## Version Constraints

- PyPI requires **unique versions** - you cannot re-upload the same version
- Each Git tag should have a unique semantic version
- Don't delete and recreate tags with the same name
- Development versions (with `.devN`) are not typically published to PyPI

## RELEASE_PAT Requirement

The `release.yml` workflow must use a Personal Access Token (PAT) — not `GITHUB_TOKEN` — when
creating GitHub Releases. GitHub deliberately does **not** fire the `release: published` event to
other workflows when a release is created with `GITHUB_TOKEN` (to prevent cascading triggers).
Because `publish.yml` listens for `release: types: [published]`, it will **never run** unless the
release is created with a PAT.

### Creating the PAT

1. Go to **GitHub Settings → Developer settings → Personal access tokens → Fine-grained tokens**
2. Click **Generate new token**
3. Set the resource owner to `ayaiayorg`
4. Under **Repository access**, select **Only select repositories** → `ayaiayorg/agentic-devtools`
5. Under **Repository permissions**, grant **Contents: Read and write**
6. Generate the token and copy it

### Storing the PAT as a Repository Secret

1. Go to the repository **Settings → Secrets and variables → Actions**
2. Click **New repository secret**
3. Name: `RELEASE_PAT`
4. Value: the fine-grained PAT you just created
5. Click **Add secret**

### Fallback Behavior

If `RELEASE_PAT` is not configured, the workflow falls back to `GITHUB_TOKEN`. The release will
still be created, but `publish.yml` will **not** be triggered automatically. In that case, you can
trigger it manually via **Actions → Publish to PyPI → Run workflow → pypi**.

## References

- [hatch-vcs documentation](https://github.com/ofek/hatch-vcs)
- [setuptools-scm documentation](https://setuptools-scm.readthedocs.io/)
- [PyPI versioning guide](https://packaging.python.org/guides/distributing-packages-using-setuptools/#choosing-a-versioning-scheme)
