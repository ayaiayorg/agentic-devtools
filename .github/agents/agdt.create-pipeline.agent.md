---
description: "Create Pipeline: Create an Azure DevOps pipeline"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Create a new pipeline in Azure DevOps.

## Prerequisites

Before running the command, you **MUST** set the following state keys using `agdt-set`:

- Required:
  - `pipeline.name` – The name of the pipeline.
  - `pipeline.yaml_path` – Path to the pipeline YAML file (relative to the repo root), e.g. `azure-pipelines.yml`.
- Optional:
  - `pipeline.description` – Description of the pipeline.
  - `pipeline.folder` – Azure DevOps folder path for the pipeline (e.g. `\\MyFolder`).
  - `pipeline.branch` – The branch to associate with the pipeline (e.g. `refs/heads/main`).

Example:

```bash
agdt-set pipeline.name "My Pipeline"
agdt-set pipeline.yaml_path "azure-pipelines.yml"
# Optional:
agdt-set pipeline.description "Build and test pipeline"
agdt-set pipeline.folder "\\TeamPipelines"
agdt-set pipeline.branch "refs/heads/main"
```

## Actions

1. Run the command:

   ```bash
   agdt-create-pipeline
   ```

## Expected Outcome

A new pipeline is created (background task).

## Next Step

Command is complete.
