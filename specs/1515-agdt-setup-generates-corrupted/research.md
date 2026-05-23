# Research: Fix corrupted `unified-ca-bundle.pem` (#1515)

## Problem Context

`agdt-setup` can write malformed PEM blocks when certificate text contains blank
or whitespace-only lines inside the certificate body.

## Findings

1. `fetch_certificate_chain_openssl` currently extracts PEM blocks using a regex
   and forwards matches without canonical cleanup.
2. `_build_unified_ca_bundle` currently writes extracted blocks directly, so
   malformed line structure is preserved.
3. Normalization must be structural only (whitespace/blank-line cleanup) and
   must not validate base64 payload semantics.
4. Deterministic output requires canonical marker lines, normalized content
   lines, and consistent newline handling during bundle assembly.

## Decision

Introduce shared `normalize_pem_block(pem: str) -> str` in
`agentic_devtools/cli/cert_utils.py` and call it from both extraction and bundle
assembly paths.

## Consequences

- Eliminates blank/whitespace-only lines within certificate content.
- Improves de-duplication stability by comparing canonical PEM block text.
- Preserves existing overwrite semantics of `agdt-setup` so reruns self-heal
  previously corrupted bundles.

---
*Generated for SpecKit Phase 3 (plan)*
