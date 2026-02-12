# End-to-End (E2E) Smoke Tests

This directory contains end-to-end smoke tests for CLI commands that
interact with external services like Azure DevOps and Jira.

## Purpose

These tests validate that CLI command entry points:

- Are correctly wired and callable
- Read state correctly
- Handle missing required parameters gracefully
- Work with realistic API response structures (using mocked responses)
- Provide appropriate error messages

## Test Coverage

### Jira Commands (5 tests)

**agdt-get-jira-issue:**

- ✅ Retrieves issue and saves response file
- ✅ Parses all expected fields (summary, description, labels,
  comments)
- ✅ Fails gracefully without issue key

**agdt-add-jira-comment:**

- ✅ Posts comment successfully with mocked API
- ✅ Returns expected response structure with author info

### Azure DevOps Commands (3 tests)

**agdt-create-pull-request:**

- ✅ Fails gracefully without required fields

**agdt-reply-to-pull-request-thread:**

- ✅ Requires pull_request_id state

**agdt-add-pull-request-comment:**

- ✅ Requires pull_request_id state

### Git Commands (5 tests)

**agdt-git-save-work:**

- ✅ Fails without commit message
- ✅ Reads commit message from state

**agdt-git-stage:**

- ✅ Command exists and is callable

**agdt-git-push:**

- ✅ Command exists and is callable

**agdt-git-force-push:**

- ✅ Command exists and is callable

## Running the Tests

```bash
# Run all E2E smoke tests
pytest tests/e2e_smoke/ -v

# Run specific test file
pytest tests/e2e_smoke/test_jira_commands_e2e.py -v

# Run specific test
pytest tests/e2e_smoke/test_jira_commands_e2e.py::TestJiraGetIssueE2E::
test_get_jira_issue_returns_valid_response -v
```

## Test Approach

### Mocking Strategy

Rather than using network-based cassette recording (VCR.py), these
tests use:

1. **Mock responses** - Realistic API response structures are created
   in test fixtures
2. **Patched dependencies** - HTTP libraries and external
   dependencies are mocked
3. **State isolation** - Each test uses a temporary state
   directory

This approach provides:

- ✅ Fast execution (no network delays)
- ✅ No external dependencies (no real API credentials needed)
- ✅ Deterministic results
- ✅ Easy to maintain and update

### Test Structure

Each test file follows this pattern:

```python
# Helper functions to create realistic mock responses
def _create_mock_jira_issue_response() -> dict:
    return {...}

# Test classes organized by CLI command
class TestJiraGetIssueE2E:
    def test_get_jira_issue_returns_valid_response(self, ...):
        # Arrange - set up state and mocks
        set_value("jira.issue_key", "DFLY-1234")
        mock_requests = MagicMock()

        # Act - call the command
        with patch("..._get_requests", return_value=mock_requests):
            get_commands.get_issue()

        # Assert - verify behavior
        assert response_file.exists()
```

## Fixtures

### Common Fixtures (conftest.py)

- **temp_state_dir** - Temporary directory for state files (isolates test state)
- **clean_state** - Clears state before each test
- **mock_jira_env** - Mock Jira environment variables
- **mock_azure_devops_env** - Mock Azure DevOps environment variables
- **temp_git_repo** - Temporary git repository (for git command tests)

### Cassette Fixtures (Not Used)

The `fixtures/cassettes/` directory contains example API response
structures in YAML format for reference, but tests use in-code mock
responses instead of cassette-based recording.

## CI Integration

E2E smoke tests run in CI as part of the `test.yml` workflow:

```yaml
- name: Run E2E smoke tests
  run: |
    pytest tests/e2e_smoke/ -v --no-cov
```

Tests run on:

- Python 3.11
- Python 3.12
- Ubuntu Latest

## Coverage Goals

While these are smoke tests (not comprehensive integration tests),
they contribute to:

- **CLI entry point coverage**: Validates command wiring and state
  reading
- **Error handling coverage**: Tests graceful failure scenarios
- **Overall project coverage**: Helps maintain 91%+ coverage threshold

Current coverage for tested modules:

- `cli/jira/get_commands.py`: 49%
- `cli/jira/comment_commands.py`: 66%
- `cli/azure_devops/commands.py`: 36%
- `cli/git/commands.py`: 31%

## Adding New Tests

To add a new E2E smoke test:

1. **Create mock response helper:**

   ```python
   def _create_mock_response() -> dict:
       return {"key": "value", ...}
   ```

2. **Write test with mocks:**

   ```python
   def test_command_succeeds(self, temp_state_dir, clean_state, mock_env):
       set_value("key", "value")
       mock_requests = MagicMock()
       mock_requests.post.return_value.json.return_value = _create_mock_response()

       with patch("module._get_requests", return_value=mock_requests):
           command_function()

       assert expected_behavior()
   ```

3. **Test error scenarios:**

   ```python
   def test_command_fails_without_required_state(self, ...):
       with pytest.raises(SystemExit) as exc_info:
           command_function()
       assert exc_info.value.code == 1
   ```

## Best Practices

1. **Keep tests focused** - Each test validates one specific behavior
2. **Use realistic mock data** - Mock responses should match real API structures
3. **Test happy path AND error scenarios** - Both success and failure cases
4. **Isolate state** - Use fixtures to ensure clean state per test
5. **Avoid actual I/O** - Mock file system, network, and external commands
6. **Fast execution** - All tests should complete in under 1 second total

## Maintenance

- Update mock responses when API structures change
- Add tests for new CLI commands as they're developed
- Keep fixtures organized and documented
- Review coverage reports to identify untested code paths
