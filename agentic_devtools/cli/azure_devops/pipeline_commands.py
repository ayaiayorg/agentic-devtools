"""Azure DevOps pipeline runner commands.

These commands queue, create, and update Azure DevOps pipelines.
"""

import json
import os
import sys
from typing import Optional

from ...state import get_value, is_dry_run, set_value
from ..subprocess_utils import run_safe
from .auth import get_pat
from .config import AzureDevOpsConfig
from .helpers import verify_az_cli


def _parse_bool_param(value: Optional[str], default: bool = False) -> bool:
    """Parse a boolean parameter from state value."""
    if value is None:
        return default
    return str(value).lower() in ("1", "true", "yes")


def run_e2e_tests_synapse() -> None:
    """
    Queue the mgmt-e2e-tests-synapse pipeline.

    State keys read:
        - branch: Source branch to test (required)
        - e2e.stage: DEV or INT (default: DEV)
        - dry_run: If true, only print what would be done

    Raises:
        SystemExit: On validation or execution errors.
    """
    config = AzureDevOpsConfig.from_state()
    dry_run = is_dry_run()

    # Get branch from state
    branch = get_value("branch")
    if not branch:
        print(
            "Error: 'branch' is required. Set it with: agdt-set branch <branch-name>",
            file=sys.stderr,
        )
        sys.exit(1)

    # Get stage parameter (default DEV)
    stage = get_value("e2e.stage") or "DEV"
    stage = stage.upper()

    if stage not in ("DEV", "INT"):
        print(f"Error: e2e.stage must be 'DEV' or 'INT'. Got: '{stage}'", file=sys.stderr)
        sys.exit(1)

    pipeline = "mgmt-e2e-tests-synapse"

    if dry_run:
        print(f"DRY-RUN: Would queue pipeline '{pipeline}' with:")
        print(f"  Branch : {branch}")
        print(f"  Stage  : {stage}")
        print(f"  Org    : {config.organization}")
        print(f"  Project: {config.project}")
        return

    # Verify az CLI and PAT
    verify_az_cli()
    pat = get_pat()

    # Set PAT for az CLI
    import os

    env = os.environ.copy()
    env["AZURE_DEVOPS_EXT_PAT"] = pat

    print(f"Queuing '{pipeline}' for branch '{branch}' with stage '{stage}'...")

    args = [
        "az",
        "pipelines",
        "run",
        "--name",
        pipeline,
        "--branch",
        branch,
        "--parameters",
        f"stage={stage}",
        "--organization",
        config.organization,
        "--project",
        config.project,
        "--output",
        "json",
    ]

    result = run_safe(args, capture_output=True, text=True, env=env)

    if result.returncode != 0:
        print(f"Error queuing pipeline: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    try:
        run_data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Error parsing response: {result.stdout}", file=sys.stderr)
        sys.exit(1)

    print("Pipeline queued successfully.")
    print(f"Run Id: {run_data.get('id', 'unknown')}")
    if run_data.get("_links", {}).get("web", {}).get("href"):
        print(f"Logs: {run_data['_links']['web']['href']}")
    elif run_data.get("url"):
        print(f"URL: {run_data['url']}")


def run_e2e_tests_fabric() -> None:
    """
    Queue the mgmt-e2e-tests-fabric pipeline (DEV only).

    State keys read:
        - branch: Source branch to test (required)
        - dry_run: If true, only print what would be done

    Note: Fabric E2E tests only run in DEV (Fabric DAP is not deployed to INT).

    Raises:
        SystemExit: On validation or execution errors.
    """
    config = AzureDevOpsConfig.from_state()
    dry_run = is_dry_run()

    # Get branch from state
    branch = get_value("branch")
    if not branch:
        print(
            "Error: 'branch' is required. Set it with: agdt-set branch <branch-name>",
            file=sys.stderr,
        )
        sys.exit(1)

    pipeline = "mgmt-e2e-tests-fabric"

    if dry_run:
        print(f"DRY-RUN: Would queue pipeline '{pipeline}' with:")
        print(f"  Branch : {branch}")
        print("  Stage  : DEV (Fabric tests are DEV-only)")
        print(f"  Org    : {config.organization}")
        print(f"  Project: {config.project}")
        return

    # Verify az CLI and PAT
    verify_az_cli()
    pat = get_pat()

    # Set PAT for az CLI
    env = os.environ.copy()
    env["AZURE_DEVOPS_EXT_PAT"] = pat

    print(f"Queuing '{pipeline}' for branch '{branch}' (DEV stage)...")

    args = [
        "az",
        "pipelines",
        "run",
        "--name",
        pipeline,
        "--branch",
        branch,
        "--parameters",
        "stage=DEV",
        "--organization",
        config.organization,
        "--project",
        config.project,
        "--output",
        "json",
    ]

    result = run_safe(args, capture_output=True, text=True, env=env)

    if result.returncode != 0:
        print(f"Error queuing pipeline: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    try:
        run_data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Error parsing response: {result.stdout}", file=sys.stderr)
        sys.exit(1)

    print("Pipeline queued successfully.")
    print(f"Run Id: {run_data.get('id', 'unknown')}")
    if run_data.get("_links", {}).get("web", {}).get("href"):
        print(f"Logs: {run_data['_links']['web']['href']}")
    elif run_data.get("url"):
        print(f"URL: {run_data['url']}")


def run_wb_patch() -> None:
    """
    Queue the wb-patch pipeline.

    State keys read:
        - branch: Source branch (required)
        - wb_patch.workbench: Workbench key like STND, TESR (required)
        - wb_patch.helper_lib_version: Version string (default: latest)
        - wb_patch.plan_only: Boolean (default: true)
        - wb_patch.deploy_helper_lib: Boolean (default: false)
        - wb_patch.deploy_synapse_dap: Boolean (default: false)
        - wb_patch.deploy_fabric_dap: Boolean (default: false)
        - dry_run: If true, only print what would be done

    Raises:
        SystemExit: On validation or execution errors.
    """
    config = AzureDevOpsConfig.from_state()
    dry_run = is_dry_run()

    # Get required parameters
    branch = get_value("branch")
    if not branch:
        print(
            "Error: 'branch' is required. Set it with: agdt-set branch <branch-name>",
            file=sys.stderr,
        )
        sys.exit(1)

    workbench = get_value("wb_patch.workbench")
    if not workbench:
        print(
            "Error: 'wb_patch.workbench' is required. Set it with: agdt-set wb_patch.workbench <WORKBENCH>",
            file=sys.stderr,
        )
        sys.exit(1)

    # Get optional parameters with defaults
    helper_lib_version = get_value("wb_patch.helper_lib_version") or "latest"
    plan_only = _parse_bool_param(get_value("wb_patch.plan_only"), default=True)
    deploy_helper_lib = _parse_bool_param(get_value("wb_patch.deploy_helper_lib"), default=False)
    deploy_synapse_dap = _parse_bool_param(get_value("wb_patch.deploy_synapse_dap"), default=False)
    deploy_fabric_dap = _parse_bool_param(get_value("wb_patch.deploy_fabric_dap"), default=False)

    pipeline = "wb-patch"

    if dry_run:
        print(f"DRY-RUN: Would queue pipeline '{pipeline}' with:")
        print(f"  Workbench         : {workbench}")
        print(f"  Helper Lib Version: {helper_lib_version}")
        print(f"  Plan Only         : {str(plan_only).lower()}")
        print(f"  Deploy Helper Lib : {str(deploy_helper_lib).lower()}")
        print(f"  Deploy Synapse DAP: {str(deploy_synapse_dap).lower()}")
        print(f"  Deploy Fabric DAP : {str(deploy_fabric_dap).lower()}")
        print(f"  Branch            : {branch}")
        print(f"  Org               : {config.organization}")
        print(f"  Project           : {config.project}")
        return

    # Verify az CLI and PAT
    verify_az_cli()
    pat = get_pat()

    # Set PAT for az CLI
    import os

    env = os.environ.copy()
    env["AZURE_DEVOPS_EXT_PAT"] = pat

    print(f"Queuing '{pipeline}' for workbench '{workbench}' on branch '{branch}'...")

    # Build parameter string - az CLI expects parameters after --parameters flag
    # as separate key=value arguments
    args = [
        "az",
        "pipelines",
        "run",
        "--name",
        pipeline,
        "--parameters",
        f"workbench={workbench}",
        f"helper_lib_version={helper_lib_version}",
        f"plan_only={str(plan_only).lower()}",
        f"deploy_helper_lib={str(deploy_helper_lib).lower()}",
        f"deploy_synapse_dap={str(deploy_synapse_dap).lower()}",
        f"deploy_fabric_dap={str(deploy_fabric_dap).lower()}",
        "--branch",
        branch,
        "--organization",
        config.organization,
        "--project",
        config.project,
        "--output",
        "json",
    ]

    print("Parameter payload:")
    print(f"  workbench={workbench}")
    print(f"  helper_lib_version={helper_lib_version}")
    print(f"  plan_only={str(plan_only).lower()}")
    print(f"  deploy_helper_lib={str(deploy_helper_lib).lower()}")
    print(f"  deploy_synapse_dap={str(deploy_synapse_dap).lower()}")
    print(f"  deploy_fabric_dap={str(deploy_fabric_dap).lower()}")

    result = run_safe(args, capture_output=True, text=True, env=env)

    if result.returncode != 0:
        print(f"Error queuing pipeline: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    try:
        run_data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Error parsing response: {result.stdout}", file=sys.stderr)
        sys.exit(1)

    print("Pipeline queued successfully.")
    print(f"Run Id: {run_data.get('id', 'unknown')}")
    if run_data.get("_links", {}).get("web", {}).get("href"):
        print(f"Logs: {run_data['_links']['web']['href']}")
    elif run_data.get("url"):
        print(f"URL: {run_data['url']}")


def list_pipelines() -> None:
    """
    List Azure DevOps pipelines, optionally filtered by name.

    State keys read:
        - pipeline.name_filter: Name or prefix to filter (optional, supports wildcards like "mgmt*")
        - dry_run: If true, only print what would be done

    Raises:
        SystemExit: On validation or execution errors.
    """
    config = AzureDevOpsConfig.from_state()
    dry_run = is_dry_run()

    name_filter = get_value("pipeline.name_filter")

    if dry_run:
        print("DRY-RUN: Would list pipelines with:")
        print(f"  Name Filter: {name_filter or '(none)'}")
        print(f"  Org        : {config.organization}")
        print(f"  Project    : {config.project}")
        return

    verify_az_cli()
    pat = get_pat()

    env = os.environ.copy()
    env["AZURE_DEVOPS_EXT_PAT"] = pat

    args = [
        "az",
        "pipelines",
        "list",
        "--organization",
        config.organization,
        "--project",
        config.project,
        "--output",
        "json",
    ]

    if name_filter:
        args.extend(["--name", name_filter])

    print(f"Listing pipelines{' matching ' + repr(name_filter) if name_filter else ''}...")

    result = run_safe(args, capture_output=True, text=True, env=env)

    if result.returncode != 0:
        print(f"Error listing pipelines: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    try:
        pipelines = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Error parsing response: {result.stdout}", file=sys.stderr)
        sys.exit(1)

    if not pipelines:
        print("No pipelines found.")
        return

    print(f"\nFound {len(pipelines)} pipeline(s):\n")
    print(f"{'ID':<10} {'Name':<50} {'Path'}")
    print("-" * 80)
    for p in pipelines:
        print(f"{p.get('id', '?'):<10} {p.get('name', '?'):<50} {p.get('path', '/')}")


def get_pipeline_id() -> None:
    """
    Get the ID of a pipeline by exact name.

    State keys read:
        - pipeline.name: Exact name of the pipeline (required)
        - dry_run: If true, only print what would be done

    State keys written:
        - pipeline.id: The pipeline ID if found

    Raises:
        SystemExit: On validation or execution errors.
    """
    config = AzureDevOpsConfig.from_state()
    dry_run = is_dry_run()

    pipeline_name = get_value("pipeline.name")
    if not pipeline_name:
        print(
            "Error: 'pipeline.name' is required. Set it with: agdt-set pipeline.name <name>",
            file=sys.stderr,
        )
        sys.exit(1)

    if dry_run:
        print("DRY-RUN: Would get pipeline ID for:")
        print(f"  Name   : {pipeline_name}")
        print(f"  Org    : {config.organization}")
        print(f"  Project: {config.project}")
        return

    verify_az_cli()
    pat = get_pat()

    env = os.environ.copy()
    env["AZURE_DEVOPS_EXT_PAT"] = pat

    args = [
        "az",
        "pipelines",
        "list",
        "--name",
        pipeline_name,
        "--organization",
        config.organization,
        "--project",
        config.project,
        "--output",
        "json",
    ]

    print(f"Looking up pipeline '{pipeline_name}'...")

    result = run_safe(args, capture_output=True, text=True, env=env)

    if result.returncode != 0:  # pragma: no cover
        print(f"Error listing pipelines: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    try:
        pipelines = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Error parsing response: {result.stdout}", file=sys.stderr)
        sys.exit(1)

    # Find exact match
    exact_match = None
    for p in pipelines:
        if p.get("name") == pipeline_name:
            exact_match = p
            break

    if not exact_match:
        print(f"Error: Pipeline '{pipeline_name}' not found.", file=sys.stderr)
        if pipelines:
            print(f"Found {len(pipelines)} pipeline(s) with similar names:", file=sys.stderr)
            for p in pipelines[:5]:
                print(f"  - {p.get('name')} (id: {p.get('id')})", file=sys.stderr)
        sys.exit(1)

    pipeline_id = exact_match.get("id")
    print(f"Pipeline '{pipeline_name}' has ID: {pipeline_id}")

    # Store in state for subsequent commands
    set_value("pipeline.id", str(pipeline_id))
    print(f"Stored pipeline.id = {pipeline_id}")


def create_pipeline() -> None:
    """
    Create a new Azure DevOps pipeline from a YAML file.

    State keys read:
        - pipeline.name: Name for the new pipeline (required)
        - pipeline.yaml_path: Path to YAML file in repo (required, e.g., "/mgmt-frontend/azure-pipelines/file.yml")
        - pipeline.description: Description for the pipeline (optional)
        - pipeline.folder_path: Folder to create pipeline in (optional, default: root)
        - pipeline.skip_first_run: Whether to skip first run (optional, default: true)
        - branch: Branch to associate with pipeline (optional, default: main)
        - dry_run: If true, only print what would be done

    State keys written:
        - pipeline.id: The created pipeline's ID

    Raises:
        SystemExit: On validation or execution errors.
    """
    config = AzureDevOpsConfig.from_state()
    dry_run = is_dry_run()

    # Get required parameters
    pipeline_name = get_value("pipeline.name")
    if not pipeline_name:
        print(
            "Error: 'pipeline.name' is required. Set it with: agdt-set pipeline.name <name>",
            file=sys.stderr,
        )
        sys.exit(1)

    yaml_path = get_value("pipeline.yaml_path")
    if not yaml_path:
        print(
            "Error: 'pipeline.yaml_path' is required. Set it with: agdt-set pipeline.yaml_path <path>",
            file=sys.stderr,
        )
        sys.exit(1)

    # Get optional parameters
    description = get_value("pipeline.description") or ""
    folder_path = get_value("pipeline.folder_path")
    skip_first_run = _parse_bool_param(get_value("pipeline.skip_first_run"), default=True)
    branch = get_value("branch") or "main"

    if dry_run:
        print("DRY-RUN: Would create pipeline with:")
        print(f"  Name          : {pipeline_name}")
        print(f"  YAML Path     : {yaml_path}")
        print(f"  Description   : {description or '(none)'}")
        print(f"  Folder        : {folder_path or '(root)'}")
        print(f"  Branch        : {branch}")
        print(f"  Skip First Run: {skip_first_run}")
        print(f"  Org           : {config.organization}")
        print(f"  Project       : {config.project}")
        return

    verify_az_cli()
    pat = get_pat()

    env = os.environ.copy()
    env["AZURE_DEVOPS_EXT_PAT"] = pat

    args = [
        "az",
        "pipelines",
        "create",
        "--name",
        pipeline_name,
        "--yml-path",
        yaml_path,
        "--branch",
        branch,
        "--repository",
        config.repository,
        "--repository-type",
        "tfsgit",
        "--skip-first-run",
        str(skip_first_run).lower(),
        "--organization",
        config.organization,
        "--project",
        config.project,
        "--output",
        "json",
    ]

    if description:
        args.extend(["--description", description])

    if folder_path:
        args.extend(["--folder-path", folder_path])

    print(f"Creating pipeline '{pipeline_name}' from '{yaml_path}'...")

    result = run_safe(args, capture_output=True, text=True, env=env)

    if result.returncode != 0:
        print(f"Error creating pipeline: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    try:
        pipeline_data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Error parsing response: {result.stdout}", file=sys.stderr)
        sys.exit(1)

    pipeline_id = pipeline_data.get("id")
    print("Pipeline created successfully.")
    print(f"Pipeline ID: {pipeline_id}")
    print(f"Pipeline Name: {pipeline_data.get('name', pipeline_name)}")

    if pipeline_data.get("_links", {}).get("web", {}).get("href"):
        print(f"URL: {pipeline_data['_links']['web']['href']}")

    # Store in state for subsequent commands
    set_value("pipeline.id", str(pipeline_id))
    print(f"Stored pipeline.id = {pipeline_id}")


def update_pipeline() -> None:
    """
    Update an existing Azure DevOps pipeline (rename, change YAML path, move folder).

    State keys read:
        - pipeline.id: ID of pipeline to update (required, use dfly-get-pipeline-id first)
        - pipeline.new_name: New name for the pipeline (optional)
        - pipeline.yaml_path: New YAML file path (optional)
        - pipeline.new_folder_path: New folder to move pipeline to (optional)
        - pipeline.description: New description (optional)
        - dry_run: If true, only print what would be done

    At least one of new_name, yaml_path, new_folder_path, or description must be provided.

    Raises:
        SystemExit: On validation or execution errors.
    """
    config = AzureDevOpsConfig.from_state()
    dry_run = is_dry_run()

    # Get required parameter
    pipeline_id = get_value("pipeline.id")
    if not pipeline_id:
        print(
            "Error: 'pipeline.id' is required. "
            "Run dfly-get-pipeline-id first, or set it with: agdt-set pipeline.id <id>",
            file=sys.stderr,
        )
        sys.exit(1)

    # Get optional update parameters
    new_name = get_value("pipeline.new_name")
    yaml_path = get_value("pipeline.yaml_path")
    new_folder_path = get_value("pipeline.new_folder_path")
    description = get_value("pipeline.description")

    if not any([new_name, yaml_path, new_folder_path, description]):
        print(
            "Error: At least one update parameter is required. Set one of:",
            file=sys.stderr,
        )
        print("  agdt-set pipeline.new_name <name>", file=sys.stderr)
        print("  agdt-set pipeline.yaml_path <path>", file=sys.stderr)
        print("  agdt-set pipeline.new_folder_path <folder>", file=sys.stderr)
        print("  agdt-set pipeline.description <description>", file=sys.stderr)
        sys.exit(1)

    if dry_run:
        print(f"DRY-RUN: Would update pipeline ID {pipeline_id} with:")
        if new_name:
            print(f"  New Name       : {new_name}")
        if yaml_path:
            print(f"  New YAML Path  : {yaml_path}")
        if new_folder_path:
            print(f"  New Folder     : {new_folder_path}")
        if description:
            print(f"  New Description: {description}")
        print(f"  Org            : {config.organization}")
        print(f"  Project        : {config.project}")
        return

    verify_az_cli()
    pat = get_pat()

    env = os.environ.copy()
    env["AZURE_DEVOPS_EXT_PAT"] = pat

    args = [
        "az",
        "pipelines",
        "update",
        "--id",
        str(pipeline_id),
        "--organization",
        config.organization,
        "--project",
        config.project,
        "--output",
        "json",
    ]

    if new_name:
        args.extend(["--new-name", new_name])

    if yaml_path:
        args.extend(["--yml-path", yaml_path])

    if new_folder_path:
        args.extend(["--new-folder-path", new_folder_path])

    if description:  # pragma: no cover
        args.extend(["--description", description])

    updates = []
    if new_name:
        updates.append(f"name -> {new_name}")
    if yaml_path:
        updates.append(f"yaml -> {yaml_path}")
    if new_folder_path:
        updates.append(f"folder -> {new_folder_path}")
    if description:  # pragma: no cover
        updates.append("description updated")

    print(f"Updating pipeline {pipeline_id}: {', '.join(updates)}...")

    result = run_safe(args, capture_output=True, text=True, env=env)

    if result.returncode != 0:
        print(f"Error updating pipeline: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    try:
        pipeline_data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Error parsing response: {result.stdout}", file=sys.stderr)
        sys.exit(1)

    print("Pipeline updated successfully.")
    print(f"Pipeline ID: {pipeline_data.get('id', pipeline_id)}")
    print(f"Pipeline Name: {pipeline_data.get('name', '?')}")

    if pipeline_data.get("_links", {}).get("web", {}).get("href"):
        print(f"URL: {pipeline_data['_links']['web']['href']}")
