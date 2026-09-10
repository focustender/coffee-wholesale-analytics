"""
Thin Salesforce REST client authenticated via the Salesforce CLI (`sf`),
not a hardcoded OAuth client. Designed to be copied into future projects
as-is: it has no dependency on this project's data or schema.

Prerequisite: `sf org login web -a <alias> -d` has already been run once
for the target org (see docs/reference/salesforce-cli-setup.md). This
module never stores or hardcodes credentials -- it asks the CLI for a
fresh session every time, since the CLI transparently handles token
refresh using the OAuth refresh token it already holds.

Requires: `requests` (pip install requests). The `sf` CLI must be on PATH.
"""

import json
import subprocess

import requests

API_VERSION = "v67.0"


class SalesforceAuthError(RuntimeError):
    pass


def _get_session(target_org):
    """Ask the Salesforce CLI for a live instance URL + access token.

    Two separate CLI calls are needed: `org display` returns instanceUrl
    (not a secret) but redacts accessToken, while `org auth
    show-access-token` returns only the real accessToken. Both run
    entirely on the caller's machine via subprocess -- the token never
    passes through any LLM context, only through this local process.
    """
    display = subprocess.run(
        ["sf", "org", "display", "--target-org", target_org, "--json"],
        capture_output=True, text=True,
    )
    token_result = subprocess.run(
        ["sf", "org", "auth", "show-access-token", "--target-org", target_org, "--json"],
        capture_output=True, text=True,
    )
    if display.returncode != 0 or token_result.returncode != 0:
        raise SalesforceAuthError(
            f"Could not get a session for org '{target_org}'. "
            f"Run: sf org login web -a {target_org} -d\n"
            f"{display.stderr}\n{token_result.stderr}"
        )
    instance_url = json.loads(display.stdout)["result"]["instanceUrl"]
    access_token = json.loads(token_result.stdout)["result"]["accessToken"]
    return instance_url, access_token


def query(soql, target_org):
    """Run a SOQL query, return the list of records."""
    instance_url, access_token = _get_session(target_org)
    resp = requests.get(
        f"{instance_url}/services/data/{API_VERSION}/query",
        params={"q": soql},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    resp.raise_for_status()
    return resp.json()["records"]


def create(sobject, fields, target_org):
    """Create one record of the given sobject type (e.g. 'Account')."""
    instance_url, access_token = _get_session(target_org)
    resp = requests.post(
        f"{instance_url}/services/data/{API_VERSION}/sobjects/{sobject}",
        json=fields,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
    )
    resp.raise_for_status()
    return resp.json()


def update(sobject, record_id, fields, target_org):
    """Update one existing record by Id. Returns True on success."""
    instance_url, access_token = _get_session(target_org)
    resp = requests.patch(
        f"{instance_url}/services/data/{API_VERSION}/sobjects/{sobject}/{record_id}",
        json=fields,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
    )
    resp.raise_for_status()
    return resp.status_code == 204


if __name__ == "__main__":
    # Smoke test: prove the connection works end to end.
    records = query("SELECT Id, Name FROM Account LIMIT 5", target_org="wholesale-dev")
    for r in records:
        print(r["Id"], r["Name"])
