"""Parse wb-jira-app error reports and extract user/dataproduct information.

This script parses error message files from the wb-jira-app and extracts:
- Username
- Display name (from Jira API)
- Email address (from Jira API)
- User status (active/inactive/not found)
- Role (reporter/assignee)
- Dataproduct key

Output is saved as both JSON and CSV files.
"""

import csv
import json
import os
import re
from datetime import datetime

from .config import get_jira_base_url, get_jira_headers
from .helpers import _get_requests, _get_ssl_verify
from .state_helpers import get_jira_value

# Path to temp directory
TEMP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))),
    "temp",
)


def _get_user_details(username: str, base_url: str, headers: dict, requests, ssl_verify) -> dict:
    """Get user details from Jira API.

    Returns dict with: exists, active, displayName, emailAddress
    """
    url = f"{base_url}/rest/api/2/user?username={username}"
    response = requests.get(url, headers=headers, verify=ssl_verify)

    if response.status_code == 200:
        user_data = response.json()
        return {
            "exists": True,
            "active": user_data.get("active", False),
            "displayName": user_data.get("displayName", ""),
            "emailAddress": user_data.get("emailAddress", ""),
        }
    return {
        "exists": False,
        "active": False,
        "displayName": "",
        "emailAddress": "",
    }


def _parse_error_file(file_path: str) -> list[dict]:
    """Parse the error file and extract user/dataproduct associations.

    Returns list of dicts with: username, role, dataproduct, errorType
    """
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    results = []

    # Pattern to match error message blocks with their associated issues
    # The file structure has "errorMessage" followed by "issues" array
    error_block_pattern = re.compile(
        r'"errorMessage":\s*"([^"]+)"[^}]*"issues":\s*\[((?:[^\]]*\n)*?[^\]]*)\]', re.MULTILINE
    )

    for match in error_block_pattern.finditer(content):
        error_message = match.group(1)
        issues_block = match.group(2)

        # Decode unicode escapes in error message
        error_message = error_message.encode().decode("unicode_escape")

        # Extract dataproducts from issues block
        dataproduct_pattern = re.compile(r'customfield_16100 \(Externe Referenz\): ([^,}"]+)')
        dataproducts = dataproduct_pattern.findall(issues_block)

        # Parse error message for user info
        # Pattern 1: "Benutzer 'username' können keine Vorgänge zugewiesen werden" (assignee, inactive)
        # Pattern 2: "Der Benutzer 'username' existiert nicht" (assignee, not found)
        # Pattern 3: "Der angegebene Autor ist kein Benutzer" (reporter issue - but no username in this msg)

        # Check for assignee errors with username
        assignee_inactive_match = re.search(
            r"Benutzer '([^']+)' können keine Vorgänge zugewiesen werden", error_message
        )
        assignee_notfound_match = re.search(r"Der Benutzer '([^']+)' existiert nicht", error_message)

        # Check for reporter error (no username in message, but indicates reporter issue)
        has_reporter_error = "Der angegebene Autor ist kein Benutzer" in error_message

        for dp in dataproducts:
            dp = dp.strip()

            # Add assignee entry if found
            if assignee_inactive_match:
                results.append(
                    {
                        "username": assignee_inactive_match.group(1),
                        "role": "assignee",
                        "dataproduct": dp,
                        "errorType": "cannot_be_assigned",
                    }
                )
            elif assignee_notfound_match:
                results.append(
                    {
                        "username": assignee_notfound_match.group(1),
                        "role": "assignee",
                        "dataproduct": dp,
                        "errorType": "not_found",
                    }
                )

            # Note: Reporter errors don't include the username in the error message
            # We can only flag that there was a reporter issue
            if has_reporter_error and not assignee_inactive_match and not assignee_notfound_match:
                # This is a reporter-only error, but we don't know the username
                results.append(
                    {
                        "username": "(unknown - reporter error)",
                        "role": "reporter",
                        "dataproduct": dp,
                        "errorType": "not_a_user",
                    }
                )
            elif has_reporter_error:
                # Both reporter and assignee error - we know assignee username but not reporter
                # The assignee was already added above, add a note about reporter
                results.append(
                    {
                        "username": "(unknown - reporter error)",
                        "role": "reporter",
                        "dataproduct": dp,
                        "errorType": "not_a_user",
                    }
                )

    return results


def parse_jira_error_report() -> None:
    """Parse a wb-jira-app error report and generate a detailed table.

    Reads from state:
    - jira.error_file_path: Path to the error message file

    Output files (in scripts/temp/):
    - jira-error-report-<timestamp>.json: Full details in JSON format
    - jira-error-report-<timestamp>.csv: Table format for easy viewing

    Example usage:
        agdt-set jira.error_file_path "c:\\path\\to\\error-message.txt"
        agdt-parse-jira-error-report
    """
    file_path = get_jira_value("error_file_path")

    if not file_path:
        print("Error: error_file_path not set.")
        print("Use: agdt-set jira.error_file_path <PATH_TO_ERROR_FILE>")
        return

    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return

    print(f"\nParsing error file: {file_path}")
    print("=" * 60)

    # Parse the error file
    parsed_entries = _parse_error_file(file_path)

    if not parsed_entries:
        print("No error entries found in the file.")
        return

    print(f"Found {len(parsed_entries)} error entries")

    # Get unique usernames (excluding unknown reporter entries)
    unique_usernames = set(
        entry["username"] for entry in parsed_entries if not entry["username"].startswith("(unknown")
    )

    print(f"Unique users to look up: {len(unique_usernames)}")
    print()

    # Look up user details from Jira
    print("Looking up user details from Jira...")
    base_url = get_jira_base_url()
    headers = get_jira_headers()
    requests = _get_requests()
    ssl_verify = _get_ssl_verify()

    user_cache = {}
    for username in unique_usernames:
        details = _get_user_details(username, base_url, headers, requests, ssl_verify)
        user_cache[username] = details

        status = "ACTIVE" if details["active"] else ("INACTIVE" if details["exists"] else "NOT FOUND")
        print(f"  {username}: {status}")

    print()

    # Enrich entries with user details
    enriched_entries = []
    for entry in parsed_entries:
        username = entry["username"]
        if username.startswith("(unknown"):
            enriched_entry = {
                **entry,
                "displayName": "",
                "emailAddress": "",
                "userExists": False,
                "userActive": False,
                "userStatus": "unknown",
            }
        else:
            details = user_cache.get(username, {})
            if details.get("exists"):
                status = "active" if details.get("active") else "inactive"
            else:
                status = "not_found"

            enriched_entry = {
                **entry,
                "displayName": details.get("displayName", ""),
                "emailAddress": details.get("emailAddress", ""),
                "userExists": details.get("exists", False),
                "userActive": details.get("active", False),
                "userStatus": status,
            }
        enriched_entries.append(enriched_entry)

    # Generate summary by user
    print("=" * 60)
    print("SUMMARY BY USER")
    print("=" * 60)

    user_summary = {}
    for entry in enriched_entries:
        username = entry["username"]
        if username not in user_summary:
            user_summary[username] = {
                "displayName": entry["displayName"],
                "emailAddress": entry["emailAddress"],
                "userStatus": entry["userStatus"],
                "asReporter": set(),
                "asAssignee": set(),
            }
        if entry["role"] == "reporter":
            user_summary[username]["asReporter"].add(entry["dataproduct"])
        else:
            user_summary[username]["asAssignee"].add(entry["dataproduct"])

    # Print summary table
    print(f"\n{'Username':<25} {'Display Name':<30} {'Status':<12} {'Reporter':<10} {'Assignee':<10}")
    print("-" * 97)

    for username in sorted(user_summary.keys()):
        info = user_summary[username]
        display = info["displayName"][:28] if info["displayName"] else ""
        print(
            f"{username:<25} {display:<30} {info['userStatus']:<12} "
            f"{len(info['asReporter']):<10} {len(info['asAssignee']):<10}"
        )

    # Save output files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(TEMP_DIR, exist_ok=True)

    # Convert sets to lists for JSON serialization
    for username in user_summary:
        user_summary[username]["asReporter"] = sorted(user_summary[username]["asReporter"])
        user_summary[username]["asAssignee"] = sorted(user_summary[username]["asAssignee"])

    # JSON output
    json_output = {
        "timestamp": datetime.now().isoformat(),
        "sourceFile": file_path,
        "totalEntries": len(enriched_entries),
        "uniqueUsers": len(unique_usernames),
        "userSummary": user_summary,
        "entries": enriched_entries,
    }

    json_path = os.path.join(TEMP_DIR, f"jira-error-report-{timestamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_output, f, indent=2, ensure_ascii=False)

    # CSV output
    csv_path = os.path.join(TEMP_DIR, f"jira-error-report-{timestamp}.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["username", "displayName", "emailAddress", "userStatus", "role", "errorType", "dataproduct"]
        )
        writer.writeheader()
        for entry in enriched_entries:
            writer.writerow(
                {
                    "username": entry["username"],
                    "displayName": entry["displayName"],
                    "emailAddress": entry["emailAddress"],
                    "userStatus": entry["userStatus"],
                    "role": entry["role"],
                    "errorType": entry["errorType"],
                    "dataproduct": entry["dataproduct"],
                }
            )

    # User summary CSV
    user_csv_path = os.path.join(TEMP_DIR, f"jira-error-report-users-{timestamp}.csv")
    with open(user_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "username",
                "displayName",
                "emailAddress",
                "userStatus",
                "asReporterCount",
                "asReporter",
                "asAssigneeCount",
                "asAssignee",
            ],
        )
        writer.writeheader()
        for username in sorted(user_summary.keys()):
            info = user_summary[username]
            writer.writerow(
                {
                    "username": username,
                    "displayName": info["displayName"],
                    "emailAddress": info["emailAddress"],
                    "userStatus": info["userStatus"],
                    "asReporterCount": len(info["asReporter"]),
                    "asReporter": "; ".join(info["asReporter"]),
                    "asAssigneeCount": len(info["asAssignee"]),
                    "asAssignee": "; ".join(info["asAssignee"]),
                }
            )

    print()
    print("=" * 60)
    print("OUTPUT FILES")
    print("=" * 60)
    print(f"  Full report (JSON): {json_path}")
    print(f"  All entries (CSV):  {csv_path}")
    print(f"  User summary (CSV): {user_csv_path}")
