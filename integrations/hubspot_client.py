"""
Thin HubSpot CRM REST client authenticated via a Private App access token
read from the HUBSPOT_ACCESS_TOKEN environment variable, never hardcoded.
Designed to be copied into future projects as-is: it has no dependency on
this project's data or schema.

Setup: docs/reference/hubspot-api-setup.md
"""
import os
import time
import requests

API_BASE = "https://api.hubapi.com"


class HubSpotAuthError(RuntimeError):
    pass


def _token():
    token = os.environ.get("HUBSPOT_ACCESS_TOKEN")
    if not token:
        raise HubSpotAuthError(
            "HUBSPOT_ACCESS_TOKEN is not set. See docs/reference/hubspot-api-setup.md "
            "to create a private app and export the token."
        )
    return token


def _headers():
    return {"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"}


def _request(method, path, **kwargs):
    resp = requests.request(method, f"{API_BASE}{path}", headers=_headers(), **kwargs)
    if resp.status_code == 429:
        time.sleep(1)
        resp = requests.request(method, f"{API_BASE}{path}", headers=_headers(), **kwargs)
    resp.raise_for_status()
    return resp.json() if resp.text else None


def get_property(object_type, name):
    try:
        return _request("GET", f"/crm/v3/properties/{object_type}/{name}")
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            return None
        raise


def create_property(object_type, name, label, field_type="text", prop_type="string",
                     group_name="contactinformation"):
    """Idempotent: returns the existing definition if the property already exists."""
    existing = get_property(object_type, name)
    if existing:
        return existing
    body = {"name": name, "label": label, "type": prop_type,
            "fieldType": field_type, "groupName": group_name}
    return _request("POST", f"/crm/v3/properties/{object_type}", json=body)


def search_contacts(filter_groups, properties=None, limit=100, after=None):
    body = {"filterGroups": filter_groups, "limit": limit}
    if properties:
        body["properties"] = properties
    if after:
        body["after"] = after
    return _request("POST", "/crm/v3/objects/contacts/search", json=body)


def find_contact_by_email(email, properties=None):
    result = search_contacts(
        [{"filters": [{"propertyName": "email", "operator": "EQ", "value": email}]}],
        properties=properties, limit=1,
    )
    results = result.get("results", [])
    return results[0] if results else None


def create_contact(properties):
    return _request("POST", "/crm/v3/objects/contacts", json={"properties": properties})


def update_contact(contact_id, properties):
    return _request("PATCH", f"/crm/v3/objects/contacts/{contact_id}", json={"properties": properties})


def list_all_contacts(properties=None):
    """Pages through every contact in the portal. Fine at this project's scale; be
    careful invoking this against a portal with a large existing contact base."""
    contacts = []
    after = None
    while True:
        params = {"limit": 100}
        if properties:
            params["properties"] = ",".join(properties)
        if after:
            params["after"] = after
        page = _request("GET", "/crm/v3/objects/contacts", params=params)
        contacts.extend(page.get("results", []))
        paging = page.get("paging")
        if not paging or not paging.get("next"):
            break
        after = paging["next"]["after"]
        time.sleep(0.1)
    return contacts


if __name__ == "__main__":
    contacts = list_all_contacts(properties=["email", "lifecyclestage"])
    print(f"{len(contacts)} contacts currently in the portal")
    for c in contacts[:5]:
        print(c["properties"].get("email"), c["properties"].get("lifecyclestage"))
