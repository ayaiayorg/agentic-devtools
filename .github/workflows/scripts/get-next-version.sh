#!/usr/bin/env bash
set -euo pipefail

# get-next-version.sh
# Calculate the next version based on the latest git tag and output GitHub Actions variables
# Usage: get-next-version.sh

# Get the latest tag, or use v0.0.0 if no tags exist
LATEST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
echo "latest_tag=$LATEST_TAG" >> "$GITHUB_OUTPUT"

# If the latest tag has no corresponding release, reuse it instead of bumping.
# This handles the case where a previous run pushed the tag but failed during
# release creation — reruns will create the release for the existing tag.
# We distinguish "release not found" from other errors (auth/network) to avoid
# silently skipping a version bump on transient GitHub failures.
if [[ "$LATEST_TAG" != "v0.0.0" ]]; then
  RELEASE_CHECK_HTTP=$(gh api -i "repos/${GITHUB_REPOSITORY}/releases/tags/${LATEST_TAG}" 2>&1 | head -1 || true)
  if echo "$RELEASE_CHECK_HTTP" | grep -q "404"; then
    echo "new_version=$LATEST_TAG" >> "$GITHUB_OUTPUT"
    echo "Latest tag $LATEST_TAG has no release — reusing it instead of bumping"
    exit 0
  elif ! echo "$RELEASE_CHECK_HTTP" | grep -q "200"; then
    echo "::error::Failed to check release for $LATEST_TAG: $RELEASE_CHECK_HTTP"
    exit 1
  fi
fi

# Extract version number and increment
VERSION=$(echo "$LATEST_TAG" | sed 's/v//')
IFS='.' read -ra VERSION_PARTS <<< "$VERSION"
MAJOR=${VERSION_PARTS[0]:-0}
MINOR=${VERSION_PARTS[1]:-0}
PATCH=${VERSION_PARTS[2]:-0}

# Increment patch version
PATCH=$((PATCH + 1))
NEW_VERSION="v$MAJOR.$MINOR.$PATCH"

echo "new_version=$NEW_VERSION" >> "$GITHUB_OUTPUT"
echo "New version will be: $NEW_VERSION"
