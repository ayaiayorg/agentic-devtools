#!/usr/bin/env bash
set -euo pipefail

# check-release-exists.sh
# Check if a GitHub release already exists for the given version
# Usage: check-release-exists.sh <version>

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <version>" >&2
  exit 1
fi

VERSION="$1"

# Distinguish "release not found" (404) from other errors (auth/network)
# to avoid proceeding with a release on transient GitHub failures.
RELEASE_CHECK_HTTP=$(gh api -i "repos/${GITHUB_REPOSITORY}/releases/tags/${VERSION}" 2>&1 | head -1 || true)

if echo "$RELEASE_CHECK_HTTP" | grep -q "200"; then
  echo "exists=true" >> "$GITHUB_OUTPUT"
  echo "Release $VERSION already exists, skipping..."
elif echo "$RELEASE_CHECK_HTTP" | grep -q "404"; then
  echo "exists=false" >> "$GITHUB_OUTPUT"
  echo "Release $VERSION does not exist, proceeding..."
else
  echo "::error::Failed to check release for $VERSION: $RELEASE_CHECK_HTTP"
  exit 1
fi
