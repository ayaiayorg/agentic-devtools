# Feature Specification: Upgrade to github-copilot-sdk v1

**Feature Branch**: `speckit/1755/phase-1-specify`
**Created**: 2026-06-03
**Status**: Draft
**Input**: GitHub Issue #1755 — Upgrade to github-copilot-sdk v1
**Source Issue**: #1755 (<https://github.com/ayaiayorg/agentic-devtools/issues/1755>)

## Problem Statement

`agentic-devtools` currently pins `github-copilot-sdk` to `<1.0.0` and includes compatibility fallback logic
introduced in PR #1753 to support changed import paths. This leaves the codebase carrying temporary shim behavior
and blocks adoption of stable v1 SDK APIs.

## Summary

Upgrade the `github-copilot-sdk` dependency from `<1.0.0` to `>=1.0.0` and update all import paths and API usage to match the v1 API.

## Context

PR #1753 introduced a fallback for `SubprocessConfig` because its import path changed in v1. Rather than maintaining compatibility shims, we should fully upgrade to v1.

## Research

- [Deep research session: SDK v1 upgrade](https://github.com/ayaiayorg/agentic-devtools/tasks/bc797954-fac6-41ec-a129-4ed8ff51fb29)

## SDK Usage Inventory (all locations that need updating)

### Production Code

**File:** `agentic_devtools/cli/ci/github_provider.py`

- **Line 1459-1460:** `from copilot import CopilotClient, SubprocessConfig` / `from copilot.session import PermissionHandler`
- **Line 1483:** `client = CopilotClient(SubprocessConfig(github_token=token))`
- **Lines 1488, 1497:** `on_permission_request=PermissionHandler.approve_all`
- **Line 1567-1568:** Same import pattern (second call site)
- **Line 1593:** Same `CopilotClient(SubprocessConfig(...))` pattern
- **Lines 1598, 1607:** Same `PermissionHandler.approve_all` usage
- **Line 2497-2498:** Same import pattern (third call site)
- **Line 2509:** Same client instantiation
- **Lines 2514, 2523:** Same permission handler usage
- **Line 2614-2615:** Same import pattern (fourth call site)
- **Line 2629:** Same client instantiation
- **Lines 2634, 2643:** Same permission handler usage

**File:** `.github/scripts/speckit-trigger/copilot_generate.py`

- **Line 24:** `from copilot import CopilotClient, SubprocessConfig`
- **Line 25:** `from copilot.session import PermissionHandler`
- **Line 83:** `client = CopilotClient(SubprocessConfig(github_token=token))`
- **Lines 89, 104:** `on_permission_request=PermissionHandler.approve_all`

### Test Code

**File:** `tests/unit/cli/ci/github_provider/test_finalize_post_repair.py`

- **Lines 42-43, 46-47, 76-77, 80, 724, 1252:** Mock `SubprocessConfig`, `CopilotClient`, `PermissionHandler`

**File:** `tests/unit/cli/ci/github_provider/test__generate_commit_message_via_sdk.py`

- **Lines 57-58, 61, 213, 255:** Mock SDK classes

**File:** `tests/unit/cli/ci/github_provider/test__resolve_conflicted_file_content_via_sdk.py`

- **Lines 49-50, 53, 305:** Mock SDK classes

**File:** `tests/workflows/test_copilot_generate.py`

- **Lines 91-92, 159, 195, 493, 540:** Mock SDK classes and test contract

## User Scenarios & Testing

### User Story 1 - Upgrade dependency and imports (Priority: P1)

As a maintainer, I want all Copilot SDK imports and usage updated to v1 so CI jobs and runtime features use a single supported SDK contract.

**Acceptance Scenarios**:

1. **Given** `github-copilot-sdk>=1.0.0` is installed, **When** runtime paths that create Copilot clients execute, **Then** imports and client setup succeed without fallback logic.
2. **Given** all listed production call sites are updated, **When** CI checks run, **Then** there are no import errors or API-signature failures from SDK usage.

### User Story 2 - Remove compatibility shim (Priority: P1)

As a maintainer, I want PR #1753 compatibility fallback code removed so the codebase no longer carries SDK<1 compatibility behavior.

**Acceptance Scenarios**:

1. **Given** the v1 migration is complete, **When** the code is inspected, **Then** no `try/except ImportError` shim remains for `SubprocessConfig`.
2. **Given** updated tests run against v1, **When** fallback paths are absent, **Then** test expectations still pass via v1 import paths.

### User Story 3 - Keep external contracts stable (Priority: P2)

As a user of `agentic-devtools`, I want CLI/state behavior to remain stable while internal SDK compatibility shims are removed.

**Acceptance Scenarios**:

1. **Given** the SDK upgrade is complete, **When** existing CLI workflows are run, **Then** externally visible CLI/state contracts are unchanged.
2. **Given** SDK<1 support is intentionally dropped, **When** reviewing requirements, **Then** compatibility scope is explicitly limited to `agentic-devtools` public interfaces.

## Requirements

### Functional Requirements

- **FR-001**: The project MUST update `pyproject.toml` dependency constraints from `github-copilot-sdk>=0.1.0,<1.0.0` to `github-copilot-sdk>=1.0.0`.
- **FR-002**: All production imports and call sites listed in the SDK usage inventory MUST be updated to v1-correct import paths and signatures.
- **FR-003**: The `SubprocessConfig` compatibility fallback shim introduced in PR #1753 MUST be removed.
- **FR-004**: All listed unit/workflow tests that mock Copilot SDK classes MUST be updated to match v1 import paths/contracts.
- **FR-005**: Workflow smoke-check lines that import SDK classes in `.github/workflows/ai-pr-loop.yml` and `.github/workflows/speckit-phase-progression.yml` MUST be updated if retained.

### Non-Functional Requirements

- **NFR-001**: The upgrade MUST preserve existing `agentic-devtools` public CLI/state contracts.
- **NFR-002**: SDK<1 compatibility is intentionally dropped; no backward-compatibility requirement applies to pre-v1 `github-copilot-sdk` imports.
- **NFR-003**: The migrated implementation MUST pass relevant unit tests and CI workflow checks that exercise SDK integration paths.

## Success Criteria

- **SC-001**: `pyproject.toml` specifies `github-copilot-sdk>=1.0.0`.
- **SC-002**: 0% of listed inventory locations retain legacy `from copilot import` patterns after migration (all replaced with v1-correct import paths).
- **SC-003**: 0% of the codebase retains `try/except ImportError` shim blocks for `SubprocessConfig` (all removed).
- **SC-004**: 100% of relevant unit and workflow tests that exercise SDK integration paths pass with `github-copilot-sdk>=1.0.0` installed.
- **SC-005**: 100% of CI workflow checks for the upgraded paths succeed on the first post-migration PR.
