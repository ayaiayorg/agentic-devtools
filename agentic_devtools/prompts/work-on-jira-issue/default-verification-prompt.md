# Work on Jira Issue - Verification Step

You are verifying work for Jira issue **{{issue_key}}**: {{issue_summary}}

## Your Task

Run quality checks to ensure the implementation is ready for commit:

## Quality Gates

### 1. Build Check

```bash
# For .NET projects
dotnet build

# For Python projects
pip install -e . && python -m py_compile <files>

# For frontend
npm run build
```

### 2. Test Suite

```bash
# For dfly-ai-helpers
dfly-test

# For .NET projects
dotnet test

# For frontend
npm test
```

### 3. Code Style

```bash
# For Python
ruff check . && ruff format --check .

# For .NET
dotnet format --verify-no-changes
```

### 4. Spell Check (if applicable)

```bash
cspell "**/*.{ts,py,md}"
```

## Verification Checklist

- [ ] Build succeeds without errors
- [ ] All tests pass
- [ ] No style/lint violations
- [ ] No spelling errors in new code
- [ ] Changes match acceptance criteria

## Next Action

When all checks pass, proceed to commit:

```bash
dfly-advance-workflow commit
```

If issues are found, return to implementation to fix them.

---

**Workflow Status**: Verification in progress. Advance to commit step when all
checks pass.
