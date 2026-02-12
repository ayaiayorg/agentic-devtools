## ❌ SpecKit: Specification Generation Failed

An error occurred while generating the specification.

**Workflow Run**: [View logs](https://github.com/{{GITHUB_REPOSITORY}}/actions/runs/{{GITHUB_RUN_ID}})

### Troubleshooting

1. Check that the issue has a descriptive title and body
2. Verify that required secrets are configured (`ANTHROPIC_API_KEY` or `OPENAI_API_KEY`)
3. Review the workflow logs for detailed error messages

### Manual Alternative

You can manually create a specification by running:

```
/speckit.specify {{issue_title}}
```

---
_This comment was posted by the [SpecKit GitHub Action](https://github.com/{{GITHUB_REPOSITORY}}/actions/runs/{{GITHUB_RUN_ID}})._
