# Feature Specification: Upgrade to github-copilot-sdk v1

**Feature Branch**: `speckit/1755/phase-2-clarify`
**Created**: 2026-06-03
**Status**: Draft
**Input**: GitHub Issue #1755 — Upgrade to github-copilot-sdk v1
**Source Issue**: #1755 (<https://github.com/ayaiayorg/agentic-devtools/issues/1755>)

## Problem Statement

`agentic-devtools` currently pins `github-copilot-sdk` to `<1.0.0` and includes compatibility fallback logic
introduced in PR #1753 to support changed import paths. This leaves the codebase carrying temporary shim behavior
and blocks adoption of stable v1 SDK APIs.

## Summary

Upgrade the `github-copilot-sdk` dependency from `<1.0.0` to `>=1.0.0,<2.0.0` and update all import paths and API usage to match the v1 API.

## Clarifications

### Session 2026-06-03

- Q: What are the correct v1 import paths for `SubprocessConfig`? The spec mentions updating to "v1-correct import paths" but does not explicitly state them. → A: Based on the existing fallback code
  (which already targets v1), the v1 import paths are: `from copilot import CopilotClient`, `from copilot.config import SubprocessConfig`, and `from copilot.session import PermissionHandler`. The
  `SubprocessConfig` moved from `copilot` (top-level) to `copilot.config` in v1.
- Q: Should the version constraint use a ceiling pin (e.g., `>=1.0.0,<2.0.0`) or an open floor pin (`>=1.0.0`)? → A: Use `>=1.0.0,<2.0.0` to protect against future breaking changes in a hypothetical
  v2. This follows defensive dependency management best practices.
- Q: Should there be any graceful degradation (SDK-unavailable fallback) retained for environments where the SDK is not installed, or should all SDK-unavailable paths be removed? → A: Retain the
  existing `except Exception` → log-warning-and-return-None pattern for SDK-unavailable scenarios. Only the `try/except ImportError` shim that handles v0→v1 path differences should be removed. The SDK
  is still an optional runtime dependency (CI environments may not have it).
- Q: Does the `PermissionHandler.approve_all` API signature remain the same in v1, or does it need updating? → A: Based on the research and existing fallback code (which successfully imports `from
  copilot.session import PermissionHandler` for v1), the `PermissionHandler.approve_all` signature is unchanged in v1. No signature update is required for this symbol.
- Q: Should the `CopilotClient(SubprocessConfig(github_token=token))` instantiation pattern be verified against v1 constructor changes, or is it confirmed unchanged? → A: The constructor pattern
  `CopilotClient(SubprocessConfig(github_token=token))` is confirmed unchanged in v1 based on the research session and the fact that the existing fallback code (which targets v1 paths) uses this exact
  pattern successfully.

## Context

PR #1753 introduced a fallback for `SubprocessConfig` because its import path changed in v1. Rather than maintaining compatibility shims, we should fully upgrade to v1.

## Research

- [Deep research session: SDK v1 upgrade](https://github.com/ayaiayorg/agentic-devtools/tasks/bc797954-fac6-41ec-a129-4ed8ff51fb29)

## SDK Usage Inventory (all locations that need updating)

### Production Code

**File:** `agentic_devtools/cli/ci/github_provider.py`

- **Line 1497-1498:** `from copilot import CopilotClient, SubprocessConfig` / `from copilot.session import PermissionHandler`
  - **v1 replacement:** `from copilot import CopilotClient` / `from copilot.config import SubprocessConfig` / `from copilot.session import PermissionHandler`
- **Line 1529:** `client = CopilotClient(SubprocessConfig(github_token=token))` — unchanged in v1
- **Lines 1534, 1543:** `on_permission_request=PermissionHandler.approve_all` — unchanged in v1
- **Line 1613-1614:** Same import pattern (second call site)
- **Line 1647:** Same `CopilotClient(SubprocessConfig(...))` pattern
- **Lines 1652, 1661:** Same `PermissionHandler.approve_all` usage
- **Line 2551-2552:** Same import pattern (third call site)
- **Line 2573:** Same client instantiation
- **Lines 2578, 2587:** Same permission handler usage
- **Line 2678-2679:** Same import pattern (fourth call site)
- **Line 2699:** Same client instantiation
- **Lines 2704, 2713:** Same permission handler usage

**File:** `.github/scripts/speckit-trigger/copilot_generate.py`

- **Line 24:** `from copilot import CopilotClient, SubprocessConfig`
  - **v1 replacement:** `from copilot import CopilotClient` / `from copilot.config import SubprocessConfig`
- **Line 25:** `from copilot.session import PermissionHandler` — unchanged in v1
- **Line 83:** `client = CopilotClient(SubprocessConfig(github_token=token))` — unchanged in v1
- **Lines 89, 104:** `on_permission_request=PermissionHandler.approve_all` — unchanged in v1

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

1. **Given** `github-copilot-sdk>=1.0.0,<2.0.0` is installed, **When** runtime paths that create Copilot clients execute,
   **Then** imports and client setup succeed without the v0→v1 import-path fallback shim.
2. **Given** all listed production call sites are updated, **When** CI checks run, **Then** there are no import errors or API-signature failures from SDK usage.

### User Story 2 - Remove compatibility shim (Priority: P1)

As a maintainer, I want PR #1753 compatibility fallback code removed so the codebase no longer carries SDK<1 compatibility behavior.

**Acceptance Scenarios**:

1. **Given** the v1 migration is complete, **When** the code is inspected, **Then** no `try/except ImportError` shim remains for `SubprocessConfig` path differences between v0 and v1.
2. **Given** updated tests run against v1, **When** fallback paths are absent, **Then** test expectations still pass via v1 import paths.
3. **Given** the SDK is an optional runtime dependency, **When** it is not installed, **Then** the existing `except Exception` → log-warning-and-return-None graceful degradation pattern is retained
   (only the v0→v1 path shim is removed).

### User Story 3 - Keep external contracts stable (Priority: P2)

As a user of `agentic-devtools`, I want CLI/state behavior to remain stable while internal SDK compatibility shims are removed.

**Acceptance Scenarios**:

1. **Given** the SDK upgrade is complete, **When** existing CLI workflows are run, **Then** externally visible CLI/state contracts are unchanged.
2. **Given** SDK<1 support is intentionally dropped, **When** reviewing requirements, **Then** compatibility scope is explicitly limited to `agentic-devtools` public interfaces.

## Requirements

### Functional Requirements

- **FR-001**: The project MUST update the `github-copilot-sdk` constraint in `pyproject.toml` under
  `[project.optional-dependencies].copilot-sdk` from `>=0.1.0,<1.0.0` to `>=1.0.0,<2.0.0`
  (without changing `[project.dependencies]`).
- **FR-002**: All production imports and call sites listed in the SDK usage inventory MUST be updated to
  v1-correct import paths: `from copilot import CopilotClient`, `from copilot.config import SubprocessConfig`,
  `from copilot.session import PermissionHandler`. The `CopilotClient(SubprocessConfig(github_token=token))`
  instantiation pattern and `PermissionHandler.approve_all` usage remain unchanged.
- **FR-003**: The `SubprocessConfig` compatibility fallback shim (the `try: from copilot import SubprocessConfig / except: from copilot.config import SubprocessConfig` pattern) introduced in PR #1753
  MUST be removed. The outer `except Exception` → log-warning-and-return-None fallback for SDK-unavailable environments MUST be retained.
- **FR-004**: All listed unit/workflow tests that mock Copilot SDK classes MUST be updated to mock v1 import paths (`copilot.config.SubprocessConfig` instead of `copilot.SubprocessConfig`). Test
  fixtures exercising the v0→v1 fallback path MUST be removed.
- **FR-005**: Workflow smoke-check lines that import SDK classes in `.github/workflows/ai-pr-loop.yml` and `.github/workflows/speckit-phase-progression.yml` MUST be updated to use v1 import paths
  (`from copilot.config import SubprocessConfig`).

### Non-Functional Requirements

- **NFR-001**: The upgrade MUST preserve existing `agentic-devtools` public CLI/state contracts. No externally observable behavior change is permitted.
- **NFR-002**: SDK<1 compatibility is intentionally dropped; no backward-compatibility requirement applies to pre-v1 `github-copilot-sdk` imports.
- **NFR-003**: The migrated implementation MUST pass 100% of relevant unit tests and CI workflow checks that exercise SDK integration paths with `github-copilot-sdk>=1.0.0,<2.0.0` installed.

## Success Criteria

- **SC-001**: `pyproject.toml` specifies `github-copilot-sdk>=1.0.0,<2.0.0`.
- **SC-002**: 0% of listed inventory locations retain legacy `from copilot import CopilotClient, SubprocessConfig`
  combined-import patterns after migration (all replaced with separate `from copilot import CopilotClient` and
  `from copilot.config import SubprocessConfig` statements).
- **SC-003**: 0% of the codebase retains `try/except ImportError` shim blocks that handle v0→v1 `SubprocessConfig` path differences (all removed). The outer SDK-unavailable `except Exception` fallback
  is retained.
- **SC-004**: 100% of relevant unit and workflow tests that exercise SDK integration paths pass with `github-copilot-sdk>=1.0.0,<2.0.0` installed.
- **SC-005**: 100% of CI workflow checks for the upgraded paths succeed on the first post-migration PR.

---
*Generated by Copilot SDK (claude-opus-4.6)*
