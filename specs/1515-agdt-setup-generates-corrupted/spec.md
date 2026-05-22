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

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Generate valid unified bundle (Priority: P1)

As a developer running `agdt-setup`, I need the generated
`unified-ca-bundle.pem` to contain valid PEM certificate blocks without blank
lines inside certificate data so TLS operations continue to work.

**Why this priority**: This is the core functional breakage and directly affects command reliability.

**Independent Test**: Run `agdt-setup` against certificate-chain input
containing blank lines in PEM bodies and verify each output certificate body is
contiguous base64 lines between BEGIN/END markers.

**Applies to**: FR-001, FR-004

**Acceptance Scenarios**:

1. **Given** certificate-chain output with blank lines inside a PEM block, **When** `_build_unified_ca_bundle` writes the unified bundle, **Then** blank lines inside certificate data are removed.
2. **Given** valid certificate-chain output without blank-line corruption, **When** the bundle is generated, **Then** certificates remain valid and parseable by standard TLS tooling.

---

### User Story 2 — Normalize at source extraction (Priority: P2)

As a maintainer, I need certificate-chain extraction to normalize PEM blocks early so later processing does not depend on fragile cleanup behavior.

**Why this priority**: Normalizing at the source prevents malformed input from propagating to multiple consumers.

**Independent Test**: Verify `fetch_certificate_chain_openssl` returns normalized PEM blocks even when raw `openssl` output contains extra blank lines.

**Applies to**: FR-002, FR-004

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

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST sanitize PEM blocks written by `_build_unified_ca_bundle` so blank lines inside certificate data are removed.
- **FR-002**: System MUST normalize PEM blocks parsed by `fetch_certificate_chain_openssl` before returning them to callers.
- **FR-003**: System MUST overwrite the existing `unified-ca-bundle.pem` on rerun so prior corruption is repaired automatically.
- **FR-004**: System MUST preserve certificate boundaries and marker lines (`-----BEGIN CERTIFICATE-----` and `-----END CERTIFICATE-----`) during normalization.

### Non-Functional Requirements

- **NFR-001**: Bundle generation MUST be deterministic for the same certificate-chain input.
- **NFR-002**: Normalization MUST not add external dependencies beyond existing tooling and standard library usage.
- **NFR-003**: Behavior MUST remain backward compatible for already-valid certificate-chain inputs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of certificates in generated `unified-ca-bundle.pem` parse successfully in targeted tests covering malformed blank-line input.
- **SC-002**: In tests with intentionally corrupted prior bundles, rerunning `agdt-setup` replaces the bundle and removes all blank lines inside PEM bodies.
- **SC-003**: Existing valid certificate-chain test cases continue to pass with no regressions after normalization changes.
