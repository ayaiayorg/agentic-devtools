# CI Secrets Configuration

This document describes the GitHub Actions secrets used by the
`ai-pr-loop` workflow (`.github/workflows/ai-pr-loop.yml`).

## Secrets

| Secret | Purpose | Required |
|--------|---------|----------|
| `GITHUB_TOKEN` | Default token for merge, comments, and general API calls | Yes (auto-provided) |
| `COPILOT_GITHUB_TOKEN` | Token for Copilot review requests | Yes |
| `AGDT_PR_APPROVER_PAT` | Dedicated token for PR approvals from a separate identity | Yes |

## `AGDT_PR_APPROVER_PAT`

### Why a separate token?

GitHub prevents a user from approving their own pull request. When the
AI PR Loop creates a PR under the `GITHUB_TOKEN` identity and then
attempts to approve it with the same token, the approval is rejected.
A Personal Access Token from a **different** GitHub account is required
so the approval comes from a distinct identity.

### Required permissions

- **Token type**: Fine-grained Personal Access Token (recommended)
- **Repository access**: Only `ayaiayorg/agentic-devtools`
- **Permissions**: `Pull requests: Write`
- **Expiry**: 90 days (rotate before expiration)

### Setup steps

1. Sign in to the dedicated approver account (e.g., `ayaiayorg-pr-approver`).
2. Navigate to **Settings → Developer settings → Personal access tokens → Fine-grained tokens**.
3. Click **Generate new token**.
4. Configure:
   - **Name**: `AGDT_PR_APPROVER_PAT`
   - **Repository access**: Only select repositories → `ayaiayorg/agentic-devtools`
   - **Permissions**: `Pull requests: Write`
5. Copy the generated token.
6. In the repository, go to **Settings → Secrets and variables → Actions**.
7. Create a new secret named `AGDT_PR_APPROVER_PAT` with the token value.

### Rotation procedure

1. Generate a new token following the setup steps above.
2. Update the `AGDT_PR_APPROVER_PAT` secret in repository settings.
3. The old token is invalidated automatically once the new one is saved.
4. No workflow changes are required — the secret name stays the same.

### Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `AGDT_PR_APPROVER_PAT is not configured` (warning) | Secret not set in repository | Add the secret per setup steps |
| `HTTP 401: Bad credentials` | Token expired or revoked | Rotate the token |
| `HTTP 403` | Insufficient permissions or wrong repo scope | Regenerate with correct permissions |
| Approval rejected (self-approval) | Token belongs to the same account as PR author | Use a different account's token |
