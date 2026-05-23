# Quickstart: Validate PEM normalization plan (#1515)

## 1. Review scope

- `agentic_devtools/cli/cert_utils.py`
- `agentic_devtools/cli/setup/commands.py`
- `tests/unit/cli/cert_utils/`
- `tests/unit/cli/setup/commands/`

## 2. Implement in TDD order

1. Add failing tests for `normalize_pem_block`.
2. Implement `normalize_pem_block` in `cert_utils.py`.
3. Integrate normalization into extraction and bundle assembly call sites.
4. Update integration tests for deterministic normalized output.

## 3. Validate

```bash
agdt-test-pattern tests/unit/cli/cert_utils/test_normalize_pem_block.py -v
agdt-test-pattern tests/unit/cli/cert_utils/test_fetch_certificate_chain_openssl.py -v
agdt-test-pattern tests/unit/cli/setup/commands/test__build_unified_ca_bundle.py -v
agdt-test
agdt-task-wait
bash scripts/run-pr-checks.sh
```

## 4. Expected outcome

- Generated `unified-ca-bundle.pem` contains canonical PEM blocks without blank
  internal lines.
- Output is deterministic and uses Unix `\n` line endings.

---
*Generated for SpecKit Phase 3 (plan)*
