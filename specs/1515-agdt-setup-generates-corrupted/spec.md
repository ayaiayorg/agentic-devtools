# Feature Specification: agdt-setup generates corrupted unified-ca-bundle.pem

**Feature Branch**: `speckit/1515/phase-1-specify`  
**Created**: 2026-05-22  
**Status**: Draft  
**Input**: User description: "agdt-setup generates corrupted unified-ca-bundle.pem with blank lines inside certificate blocks"  
**Source Issue**: #1515 (<https://github.com/ayaiayorg/agentic-devtools/issues/1515>)

## Problem Statement

`agdt-setup` can produce a corrupted `unified-ca-bundle.pem` because certificate blocks extracted from
`openssl s_client` output retain blank lines inside the PEM body. Those malformed blocks are written verbatim into
the unified bundle and can break TLS validation for downstream commands.

The root cause is in two locations:

1. `fetch_certificate_chain_openssl` in `agentic_devtools/cli/cert_utils.py` uses
   `re.findall(cert_pattern, output, re.DOTALL)` which captures blank lines within PEM
   blocks from noisy `openssl s_client` output.
2. `_build_unified_ca_bundle` in `agentic_devtools/cli/setup/commands.py` writes these captured blocks verbatim without sanitizing internal blank lines.

## Clarifications

### Session 2026-05-22

- Q1: What constitutes "normalization" of a PEM block — should it strip only blank lines, or also trailing whitespace on non-blank lines within the certificate body? → A: Normalization MUST remove
  blank lines (lines containing only whitespace) between `BEGIN CERTIFICATE` and `END CERTIFICATE` markers AND strip trailing whitespace from each base64 content line. Leading whitespace on content
  lines should also be stripped since valid base64 PEM lines never have leading whitespace. For marker lines, surrounding whitespace should be trimmed, then canonical marker text must be emitted
  exactly as `-----BEGIN CERTIFICATE-----` and `-----END CERTIFICATE-----`.
- Q2: Should the normalization helper be a shared utility (e.g., in `cert_utils.py`) reusable by both `fetch_certificate_chain_openssl` and `_build_unified_ca_bundle`, or should each location implement
  its own logic? → A: A single shared `normalize_pem_block(pem: str) -> str` function MUST be placed in `agentic_devtools/cli/cert_utils.py` and called by both `fetch_certificate_chain_openssl` and
  `_build_unified_ca_bundle` to avoid duplication and ensure consistent behavior.
- Q3: For FR-003 (self-heal), should the bundle be overwritten unconditionally on every `agdt-setup` run, or only when corruption is detected? → A: The bundle is ALREADY overwritten unconditionally on
  every run (existing behavior in `_build_unified_ca_bundle`). FR-003 simply requires that this overwrite uses normalized PEM blocks, which is satisfied by FR-001 and FR-002. No additional detection
  logic is needed.
- Q4: Should the normalization function validate that the base64 content between markers is actually valid base64, or only perform structural line cleanup? → A: Normalization MUST only perform
  structural line cleanup (remove blank lines, strip whitespace). It MUST NOT validate base64 encoding correctness — that is the responsibility of downstream TLS libraries. This keeps the fix minimal
  and avoids false-positive rejections.
- Q5: Does the de-duplication comparison in `_build_unified_ca_bundle` (which uses `set` membership) need to account for normalization — i.e., should two PEM blocks that differ only by blank lines be
  considered duplicates? → A: Yes. Since normalization is applied before de-duplication (via the shared helper called in `fetch_certificate_chain_openssl`), blocks that previously appeared different
  due to blank lines will naturally de-duplicate after normalization. The existing `set`-based comparison in `_build_unified_ca_bundle` requires no changes because inputs will already be normalized.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Generate valid unified bundle (Priority: P1)

As a developer running `agdt-setup`, I need the generated
`unified-ca-bundle.pem` to contain valid PEM certificate blocks without blank
lines inside certificate data so TLS operations continue to work.

**Why this priority**: This is the core functional breakage and directly affects command reliability.

**Independent Test**: Run `agdt-setup` against certificate-chain input
containing blank lines in PEM bodies and verify each output certificate body is
contiguous base64 lines between BEGIN/END markers.

**Applies to**: FR-001, FR-004, FR-006

**Acceptance Scenarios**:

1. **Given** certificate-chain output with blank lines inside a PEM block, **When** `_build_unified_ca_bundle` writes the unified bundle, **Then** blank lines inside certificate data are removed.
2. **Given** valid certificate-chain output without blank-line corruption, **When** the bundle is generated, **Then** certificates remain valid and parseable by standard TLS tooling.
3. **Given** PEM blocks with whitespace around marker lines and leading/trailing whitespace on base64 content lines, **When** normalization runs, **Then** output uses canonical marker lines exactly and
   trims surrounding whitespace from each content line.
4. **Given** a certificate bundle is being written on any platform, **When** `_build_unified_ca_bundle` writes the unified bundle, **Then** the output file uses Unix `\n` line endings
   (newline translation is disabled, e.g. opened with `newline='\n'`).

---

### User Story 2 — Normalize at source extraction (Priority: P2)

As a maintainer, I need certificate-chain extraction to normalize PEM blocks early so later processing does not depend on fragile cleanup behavior.

**Why this priority**: Normalizing at the source prevents malformed input from propagating to multiple consumers.

**Independent Test**: Verify `fetch_certificate_chain_openssl` returns normalized PEM blocks even when raw `openssl` output contains extra blank lines.

**Applies to**: FR-002, FR-004, FR-005

**Acceptance Scenarios**:

1. **Given** noisy `openssl s_client` output, **When** `fetch_certificate_chain_openssl` parses certificates, **Then** returned PEM blocks are normalized before any file write.

---

### User Story 3 — Self-heal existing corrupted bundles (Priority: P3)

As a developer who already has a corrupted bundle from a previous run, I need a subsequent `agdt-setup` run to overwrite and repair the bundle automatically.

**Why this priority**: Users should recover without manual cleanup or editing PEM files.

**Independent Test**: Seed a corrupted `unified-ca-bundle.pem`, run `agdt-setup` again, and confirm the output file is replaced with normalized certificate blocks.

**Applies to**: FR-003

**Acceptance Scenarios**:

1. **Given** an existing corrupted bundle on disk, **When** `agdt-setup` is re-run, **Then** the bundle is overwritten with valid normalized PEM blocks.

### Edge Cases

- Input contains multiple certificates where only some PEM blocks include blank lines.
- Input contains leading/trailing whitespace around PEM markers.
- Existing bundle is already valid; rerun must remain stable and not introduce changes beyond normalization rules.
- PEM block contains lines with only whitespace characters (spaces/tabs) that appear as blank lines visually but are not empty strings — these must also be removed.
- Certificate body contains Windows-style line endings (`\r\n`) — normalization must handle these consistently (output Unix-style `\n`).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST sanitize PEM blocks written by `_build_unified_ca_bundle` so blank lines (lines containing only whitespace) inside certificate data are removed.
- **FR-002**: System MUST normalize PEM blocks parsed by `fetch_certificate_chain_openssl` before returning them to callers, including removal of blank lines and trimming leading/trailing whitespace from
  base64 content lines between certificate markers.
- **FR-003**: System MUST overwrite the existing `unified-ca-bundle.pem` on rerun so prior corruption is repaired automatically. (Satisfied by existing unconditional-overwrite behavior combined with
  FR-001/FR-002.)
- **FR-004**: System MUST preserve certificate boundaries and canonical marker lines (`-----BEGIN CERTIFICATE-----` and `-----END CERTIFICATE-----`) during normalization. If input marker lines contain
  surrounding whitespace, that whitespace MUST be trimmed while preserving marker meaning.
- **FR-005**: System MUST implement normalization as a single shared function (`normalize_pem_block`) in `agentic_devtools/cli/cert_utils.py`, called by both `fetch_certificate_chain_openssl` and
  `_build_unified_ca_bundle`.
- **FR-006**: System MUST write `unified-ca-bundle.pem` using Unix `\n` line endings on every platform; file writes MUST disable platform newline translation (for example by opening with `newline='\n'`).

### Non-Functional Requirements

- **NFR-001**: Bundle generation MUST be deterministic — identical certificate-chain input MUST produce byte-for-byte identical `unified-ca-bundle.pem` output across runs.
- **NFR-002**: Normalization MUST not add external dependencies beyond existing tooling and standard library usage (only `re`, `str` methods, or equivalent stdlib).
- **NFR-003**: Behavior MUST remain backward compatible for already-normalized certificate-chain inputs — normalized output of a well-formed PEM block that already uses canonical marker lines and trimmed
  content lines MUST be byte-for-byte identical to the input.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of certificates in generated `unified-ca-bundle.pem` parse successfully in targeted tests covering malformed blank-line input.
- **SC-002**: In tests with intentionally corrupted prior bundles, rerunning `agdt-setup` replaces the bundle and removes all blank lines inside PEM bodies.
- **SC-003**: Existing valid certificate-chain test cases continue to pass with no regressions after normalization changes.
- **SC-004**: The shared `normalize_pem_block` function achieves 100% unit test coverage under the 1:1:1 test structure at `tests/unit/cli/cert_utils/test_normalize_pem_block.py`.

---
*Generated by Copilot SDK (claude-opus-4.6)*
