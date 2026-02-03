"""Jira project role management commands.

Commands for listing project roles and adding users to project roles.

API Reference:
- GET /rest/api/2/project/{projectIdOrKey}/role - List all roles for a project
- GET /rest/api/2/project/{projectIdOrKey}/role/{id} - Get role details with actors
- POST /rest/api/2/project/{projectIdOrKey}/role/{id} - Add users/groups to role
- GET /rest/api/2/user?username=... - Check if user exists
"""

import json
import os
import re
from datetime import datetime

from .config import get_jira_base_url, get_jira_headers
from .helpers import _get_requests, _get_ssl_verify, _parse_comma_separated
from .state_helpers import get_jira_value
from .vpn_wrapper import with_jira_vpn_context

# Path to temp directory for storing non-existent users
TEMP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))),
    "temp",
)


def _check_user_exists(username: str, base_url: str, headers: dict, requests, ssl_verify) -> tuple[bool, str | None]:
    """Check if a user exists in Jira.

    Args:
        username: The username to check
        base_url: Jira base URL
        headers: Request headers
        requests: Requests module
        ssl_verify: SSL verification setting

    Returns:
        Tuple of (exists: bool, display_name: str | None)
    """
    url = f"{base_url}/rest/api/2/user?username={username}"
    response = requests.get(url, headers=headers, verify=ssl_verify)

    if response.status_code == 200:
        user_data = response.json()
        display_name = user_data.get("displayName", username)
        active = user_data.get("active", False)
        if not active:
            return False, f"{display_name} (INACTIVE)"
        return True, display_name
    return False, None


@with_jira_vpn_context
def check_user_exists() -> None:
    """Check if a single user exists in Jira.

    Reads from state:
    - jira.username: The username to check

    Example usage:
        agdt-set jira.username "amarsnik"
        agdt-check-user-exists
    """
    username = get_jira_value("username")

    if not username:
        print("Error: username not set. Use: agdt-set jira.username <USERNAME>")
        return

    base_url = get_jira_base_url()
    headers = get_jira_headers()
    requests = _get_requests()
    ssl_verify = _get_ssl_verify()

    print(f"\nChecking if user '{username}' exists in Jira...")

    exists, display_name = _check_user_exists(username, base_url, headers, requests, ssl_verify)

    if exists:
        print(f"✓ User exists: {display_name}")
    elif display_name:
        # User exists but is inactive
        print(f"⚠ User found but inactive: {display_name}")
    else:
        print(f"✗ User '{username}' does not exist in Jira")


@with_jira_vpn_context
def check_users_exist() -> None:
    """Check if multiple users exist in Jira.

    Reads from state:
    - jira.users: Comma-separated list of usernames to check

    Users that don't exist are saved to temp/nonexistent-users-<timestamp>.json

    Example usage:
        agdt-set jira.users "user1,user2,user3.EXT"
        agdt-check-users-exist
    """
    users_raw = get_jira_value("users")

    if not users_raw:
        print("Error: users not set. Use: agdt-set jira.users 'user1,user2,user3'")
        return

    users = _parse_comma_separated(users_raw)
    if not users:
        print("Error: No valid usernames provided.")
        return

    base_url = get_jira_base_url()
    headers = get_jira_headers()
    requests = _get_requests()
    ssl_verify = _get_ssl_verify()

    print(f"\nChecking {len(users)} user(s) in Jira...\n")

    existing_users = []
    nonexistent_users = []
    inactive_users = []

    for user in users:
        exists, display_name = _check_user_exists(user, base_url, headers, requests, ssl_verify)
        if exists:
            print(f"  ✓ {user} ({display_name})")
            existing_users.append({"username": user, "displayName": display_name})
        elif display_name and "INACTIVE" in display_name:
            print(f"  ⚠ {user} - {display_name}")
            inactive_users.append({"username": user, "status": "inactive", "displayName": display_name})
        else:
            print(f"  ✗ {user} - NOT FOUND")
            nonexistent_users.append(user)

    print(f"\n{'=' * 50}")
    print(f"Summary: {len(existing_users)} exist, {len(inactive_users)} inactive, {len(nonexistent_users)} not found")

    # Save non-existent and inactive users to temp file if any
    if nonexistent_users or inactive_users:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"nonexistent-users-{timestamp}.json"
        filepath = os.path.join(TEMP_DIR, filename)

        os.makedirs(TEMP_DIR, exist_ok=True)

        output_data = {
            "timestamp": datetime.now().isoformat(),
            "total_checked": len(users),
            "existing_count": len(existing_users),
            "inactive_count": len(inactive_users),
            "nonexistent_count": len(nonexistent_users),
            "nonexistent_users": nonexistent_users,
            "inactive_users": inactive_users,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)

        print(f"\n⚠ Non-existent/inactive users saved to: {filepath}")

    if existing_users:
        print(f"\nUsers that CAN be added to roles ({len(existing_users)}):")
        usernames = [u["username"] for u in existing_users]
        print(f"  {','.join(usernames)}")
        print("\nTo add these users to a role, run:")
        print(f'  agdt-set jira.users "{",".join(usernames)}"')
        print("  agdt-add-users-to-project-role")


@with_jira_vpn_context
def list_project_roles() -> None:
    """List all project roles for a given project.

    Reads project_id_or_key from state (jira.project_id_or_key).
    Outputs a table of role names and their IDs.
    """
    project_id_or_key = get_jira_value("project_id_or_key")
    if not project_id_or_key:
        print("Error: project_id_or_key not set. Use: agdt-set jira.project_id_or_key <PROJECT_KEY_OR_ID>")
        return

    base_url = get_jira_base_url()
    headers = get_jira_headers()
    requests = _get_requests()
    ssl_verify = _get_ssl_verify()

    url = f"{base_url}/rest/api/2/project/{project_id_or_key}/role"

    response = requests.get(url, headers=headers, verify=ssl_verify)

    if response.status_code != 200:
        print(f"Error: Failed to get project roles. Status: {response.status_code}")
        print(f"Response: {response.text}")
        return

    roles_data = response.json()

    # roles_data is a dict like {"RoleName": "https://jira.example.com/rest/api/2/project/KEY/role/12345", ...}
    print(f"\nProject Roles for '{project_id_or_key}':\n")
    print(f"{'Role Name':<40} {'Role ID':<15}")
    print("-" * 55)

    for role_name, role_url in sorted(roles_data.items()):
        # Extract role ID from URL (last path segment)
        role_id_match = re.search(r"/role/(\d+)$", role_url)
        role_id = role_id_match.group(1) if role_id_match else "unknown"
        print(f"{role_name:<40} {role_id:<15}")

    print(f"\nTotal: {len(roles_data)} roles")
    print("\nTo see role details, use: agdt-get-project-role-details")


@with_jira_vpn_context
def get_project_role_details() -> None:
    """Get detailed information about a specific project role including its actors.

    Reads from state:
    - jira.project_id_or_key: The project key or ID
    - jira.role_id: The role ID to get details for
    """
    project_id_or_key = get_jira_value("project_id_or_key")
    role_id = get_jira_value("role_id")

    if not project_id_or_key:
        print("Error: project_id_or_key not set. Use: agdt-set jira.project_id_or_key <PROJECT_KEY_OR_ID>")
        return
    if not role_id:
        print("Error: role_id not set. Use: agdt-set jira.role_id <ROLE_ID>")
        print("Tip: Use dfly-list-project-roles to see available roles and their IDs.")
        return

    base_url = get_jira_base_url()
    headers = get_jira_headers()
    requests = _get_requests()
    ssl_verify = _get_ssl_verify()

    url = f"{base_url}/rest/api/2/project/{project_id_or_key}/role/{role_id}"

    response = requests.get(url, headers=headers, verify=ssl_verify)

    if response.status_code != 200:
        print(f"Error: Failed to get role details. Status: {response.status_code}")
        print(f"Response: {response.text}")
        return

    role_data = response.json()

    print(f"\nRole Details for '{role_data.get('name', 'Unknown')}':\n")
    print(f"  ID: {role_data.get('id')}")
    print(f"  Description: {role_data.get('description', 'N/A')}")

    actors = role_data.get("actors", [])
    print(f"\nActors ({len(actors)}):")

    if not actors:
        print("  (No actors assigned)")
    else:
        user_actors = [a for a in actors if a.get("type") == "atlassian-user-role-actor"]
        group_actors = [a for a in actors if a.get("type") == "atlassian-group-role-actor"]

        if user_actors:
            print(f"\n  Users ({len(user_actors)}):")
            for actor in user_actors:
                display_name = actor.get("displayName", "Unknown")
                actor_user = actor.get("actorUser", {})
                # Server uses 'name', Cloud uses 'accountId'
                user_key = actor_user.get("name") or actor_user.get("accountId") or "N/A"
                print(f"    - {display_name} ({user_key})")

        if group_actors:
            print(f"\n  Groups ({len(group_actors)}):")
            for actor in group_actors:
                display_name = actor.get("displayName", "Unknown")
                actor_group = actor.get("actorGroup", {})
                group_name = actor_group.get("name", "N/A")
                print(f"    - {display_name} ({group_name})")


@with_jira_vpn_context
def add_users_to_project_role() -> None:
    """Add users to a project role.

    Reads from state:
    - jira.project_id_or_key: The project key or ID
    - jira.role_id: The role ID to add users to
    - jira.users: Comma-separated list of usernames to add

    Example usage:
        agdt-set jira.project_id_or_key 21703
        agdt-set jira.role_id 10500
        agdt-set jira.users "user1,user2,user3.EXT"
        agdt-add-users-to-project-role

    API: POST /rest/api/2/project/{projectIdOrKey}/role/{id}
    Body: {"user": ["username1", "username2"]}
    """
    project_id_or_key = get_jira_value("project_id_or_key")
    role_id = get_jira_value("role_id")
    users_raw = get_jira_value("users")

    if not project_id_or_key:
        print("Error: project_id_or_key not set. Use: agdt-set jira.project_id_or_key <PROJECT_KEY_OR_ID>")
        return
    if not role_id:
        print("Error: role_id not set. Use: agdt-set jira.role_id <ROLE_ID>")
        print("Tip: Use dfly-list-project-roles to see available roles and their IDs.")
        return
    if not users_raw:
        print("Error: users not set. Use: agdt-set jira.users 'user1,user2,user3'")
        return

    users = _parse_comma_separated(users_raw)
    if not users:
        print("Error: No valid usernames provided.")
        return

    base_url = get_jira_base_url()
    headers = get_jira_headers()
    headers["Content-Type"] = "application/json"
    requests = _get_requests()
    ssl_verify = _get_ssl_verify()

    url = f"{base_url}/rest/api/2/project/{project_id_or_key}/role/{role_id}"

    # Build request body
    payload = {"user": users}

    print(f"\nAdding {len(users)} user(s) to project role...")
    print(f"  Project: {project_id_or_key}")
    print(f"  Role ID: {role_id}")
    print(f"  Users: {', '.join(users)}")
    print()

    response = requests.post(url, headers=headers, json=payload, verify=ssl_verify)

    if response.status_code == 200:
        print("✓ Successfully added users to project role!")
        role_data = response.json()
        print(f"\nRole '{role_data.get('name', 'Unknown')}' now has {len(role_data.get('actors', []))} actors.")
    elif response.status_code == 400:
        print("✗ Bad Request - Some users may not exist or are invalid.")
        print(f"Response: {response.text}")
    elif response.status_code == 401:
        print("✗ Unauthorized - Check your Jira credentials.")
    elif response.status_code == 404:
        print("✗ Not Found - Project or role does not exist.")
        print(f"Response: {response.text}")
    else:
        print(f"✗ Error: Status {response.status_code}")
        print(f"Response: {response.text}")


@with_jira_vpn_context
def add_users_to_project_role_batch() -> None:
    """Add users to a project role in batches, with user existence check.

    This function first verifies that each user exists in Jira before attempting
    to add them to the role. Users that don't exist are saved to a temp file.

    Reads from state:
    - jira.project_id_or_key: The project key or ID
    - jira.role_id: The role ID to add users to
    - jira.users: Comma-separated list of usernames to add

    Example usage:
        agdt-set jira.project_id_or_key DH
        agdt-set jira.role_id 10100
        agdt-set jira.users "user1,user2,user3.EXT,nonexistent_user"
        agdt-add-users-to-project-role-batch

    Output files (in scripts/temp/):
    - nonexistent-users-<timestamp>.json: Users that don't exist in Jira
    """
    project_id_or_key = get_jira_value("project_id_or_key")
    role_id = get_jira_value("role_id")
    users_raw = get_jira_value("users")

    if not project_id_or_key:
        print("Error: project_id_or_key not set. Use: agdt-set jira.project_id_or_key <PROJECT_KEY_OR_ID>")
        return
    if not role_id:
        print("Error: role_id not set. Use: agdt-set jira.role_id <ROLE_ID>")
        print("Tip: Use dfly-list-project-roles to see available roles and their IDs.")
        return
    if not users_raw:
        print("Error: users not set. Use: agdt-set jira.users 'user1,user2,user3'")
        return

    users = _parse_comma_separated(users_raw)
    if not users:
        print("Error: No valid usernames provided.")
        return

    base_url = get_jira_base_url()
    headers = get_jira_headers()
    headers["Content-Type"] = "application/json"
    requests = _get_requests()
    ssl_verify = _get_ssl_verify()

    url = f"{base_url}/rest/api/2/project/{project_id_or_key}/role/{role_id}"

    print(f"\nProcessing {len(users)} user(s) for project role assignment...")
    print(f"  Project: {project_id_or_key}")
    print(f"  Role ID: {role_id}")
    print()

    # Phase 1: Check user existence
    print("Phase 1: Checking user existence in Jira...\n")
    existing_users = []
    nonexistent_users = []
    inactive_users = []

    for user in users:
        exists, display_name = _check_user_exists(user, base_url, headers, requests, ssl_verify)
        if exists:
            print(f"  ✓ {user} ({display_name})")
            existing_users.append({"username": user, "displayName": display_name})
        elif display_name and "INACTIVE" in display_name:
            print(f"  ⚠ {user} - INACTIVE")
            inactive_users.append({"username": user, "status": "inactive", "displayName": display_name})
        else:
            print(f"  ✗ {user} - NOT FOUND")
            nonexistent_users.append(user)

    print(f"\n{'=' * 50}")
    print(
        f"User Check: {len(existing_users)} exist, {len(inactive_users)} inactive, {len(nonexistent_users)} not found"
    )

    # Save non-existent and inactive users to temp file
    if nonexistent_users or inactive_users:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"nonexistent-users-{project_id_or_key}-{timestamp}.json"
        filepath = os.path.join(TEMP_DIR, filename)

        os.makedirs(TEMP_DIR, exist_ok=True)

        output_data = {
            "timestamp": datetime.now().isoformat(),
            "project": project_id_or_key,
            "role_id": role_id,
            "total_requested": len(users),
            "existing_count": len(existing_users),
            "inactive_count": len(inactive_users),
            "nonexistent_count": len(nonexistent_users),
            "nonexistent_users": nonexistent_users,
            "inactive_users": inactive_users,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)

        print(f"\n⚠ Non-existent/inactive users saved to:\n   {filepath}")

    if not existing_users:
        print("\n✗ No valid users to add to the role.")
        return

    # Phase 2: Add existing users to role
    print(f"\nPhase 2: Adding {len(existing_users)} user(s) to project role...\n")

    successful = []
    failed = []

    for user_info in existing_users:
        user = user_info["username"]
        payload = {"user": [user]}
        response = requests.post(url, headers=headers, json=payload, verify=ssl_verify)

        if response.status_code == 200:
            print(f"  ✓ {user}")
            successful.append(user)
        else:
            error_msg = response.text[:100] if response.text else f"Status {response.status_code}"
            print(f"  ✗ {user} - {error_msg}")
            failed.append((user, response.status_code, response.text))

    print(f"\n{'=' * 50}")
    print("FINAL SUMMARY")
    print(f"{'=' * 50}")
    print(f"  Total requested:    {len(users)}")
    print(f"  Non-existent:       {len(nonexistent_users)}")
    print(f"  Inactive:           {len(inactive_users)}")
    print(f"  Successfully added: {len(successful)}")
    print(f"  Failed to add:      {len(failed)}")

    if successful:
        print(f"\n✓ Successfully added ({len(successful)}):")
        for user in successful:
            print(f"    {user}")

    if failed:
        print(f"\n✗ Failed to add ({len(failed)}):")
        for user, status, error in failed:
            print(f"    {user}: {status} - {error[:80]}")


@with_jira_vpn_context
def find_role_id_by_name() -> None:
    """Find the role ID for a given role name.

    Reads from state:
    - jira.project_id_or_key: The project key or ID
    - jira.role_name: The role name to search for (case-insensitive partial match)

    Outputs the role ID if found.
    """
    project_id_or_key = get_jira_value("project_id_or_key")
    role_name = get_jira_value("role_name")

    if not project_id_or_key:
        print("Error: project_id_or_key not set. Use: agdt-set jira.project_id_or_key <PROJECT_KEY_OR_ID>")
        return
    if not role_name:
        print("Error: role_name not set. Use: agdt-set jira.role_name 'Projektmitarbeiter'")
        return

    base_url = get_jira_base_url()
    headers = get_jira_headers()
    requests = _get_requests()
    ssl_verify = _get_ssl_verify()

    url = f"{base_url}/rest/api/2/project/{project_id_or_key}/role"

    response = requests.get(url, headers=headers, verify=ssl_verify)

    if response.status_code != 200:
        print(f"Error: Failed to get project roles. Status: {response.status_code}")
        print(f"Response: {response.text}")
        return

    roles_data = response.json()
    role_name_lower = role_name.lower()

    matches = []
    for name, url in roles_data.items():
        if role_name_lower in name.lower():
            role_id_match = re.search(r"/role/(\d+)$", url)
            role_id = role_id_match.group(1) if role_id_match else "unknown"
            matches.append((name, role_id))

    if not matches:
        print(f"No roles found matching '{role_name}'")
        print("\nAvailable roles:")
        for name in sorted(roles_data.keys()):
            print(f"  - {name}")
        return

    if len(matches) == 1:
        name, role_id = matches[0]
        print(f"\nFound role: {name}")
        print(f"Role ID: {role_id}")
        print(f"\nTo use this role, run: agdt-set jira.role_id {role_id}")
    else:
        print(f"\nMultiple roles match '{role_name}':")
        for name, role_id in matches:
            print(f"  {name}: {role_id}")
        print("\nPlease use a more specific search or set the role_id directly.")
