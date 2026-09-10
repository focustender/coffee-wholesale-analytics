"""
Thin Shopify Admin GraphQL client authenticated via a Dev Dashboard app's
Client ID + Client Secret, exchanged at runtime for a short-lived Admin API
access token using the client credentials grant (Shopify's 2026 app model --
custom apps no longer expose a static token in the UI). Credentials are read
from SHOPIFY_STORE_DOMAIN / SHOPIFY_CLIENT_ID / SHOPIFY_CLIENT_SECRET
environment variables, never hardcoded. Designed to be copied into future
projects as-is: it has no dependency on this project's data or schema.

Setup: docs/reference/shopify-api-setup.md
"""
import os
import time
import requests

API_VERSION = "2025-01"

_token_cache = {"access_token": None, "expires_at": 0}


class ShopifyAuthError(RuntimeError):
    pass


def _config():
    domain = os.environ.get("SHOPIFY_STORE_DOMAIN")
    client_id = os.environ.get("SHOPIFY_CLIENT_ID")
    client_secret = os.environ.get("SHOPIFY_CLIENT_SECRET")
    if not domain or not client_id or not client_secret:
        raise ShopifyAuthError(
            "SHOPIFY_STORE_DOMAIN, SHOPIFY_CLIENT_ID, and SHOPIFY_CLIENT_SECRET "
            "must all be set. See docs/reference/shopify-api-setup.md."
        )
    return domain, client_id, client_secret


def _get_access_token():
    """
    Exchanges the app's Client ID + Secret for a 24-hour Admin API access
    token, caching it in memory and refreshing a minute before it expires
    so repeated calls within one process don't re-authenticate every time.
    """
    now = time.time()
    if _token_cache["access_token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["access_token"]

    domain, client_id, client_secret = _config()
    resp = requests.post(
        f"https://{domain}/admin/oauth/access_token",
        data={"grant_type": "client_credentials", "client_id": client_id,
              "client_secret": client_secret},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    resp.raise_for_status()
    body = resp.json()
    _token_cache["access_token"] = body["access_token"]
    _token_cache["expires_at"] = now + body.get("expires_in", 86399)
    return _token_cache["access_token"]


def graphql(query, variables=None):
    domain, _, _ = _config()
    token = _get_access_token()
    url = f"https://{domain}/admin/api/{API_VERSION}/graphql.json"
    resp = requests.post(
        url,
        json={"query": query, "variables": variables or {}},
        headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"},
    )
    resp.raise_for_status()
    body = resp.json()
    if "errors" in body:
        raise RuntimeError(body["errors"])
    return body["data"]


_CUSTOMER_CREATE = """
mutation CustomerCreate($input: CustomerInput!) {
  customerCreate(input: $input) {
    customer { id email }
    userErrors { field message }
  }
}
"""

_CUSTOMER_BY_EMAIL = """
query CustomerByEmail($query: String!) {
  customers(first: 1, query: $query) {
    edges { node { id email tags } }
  }
}
"""

_CUSTOMERS_PAGE = """
query CustomersPage($first: Int!, $after: String, $query: String) {
  customers(first: $first, after: $after, query: $query) {
    edges { node { id email tags } }
    pageInfo { hasNextPage endCursor }
  }
}
"""


def create_customer(email, first_name, last_name, tags=None, note=None, metafields=None):
    input_obj = {"email": email, "firstName": first_name, "lastName": last_name}
    if tags:
        input_obj["tags"] = tags
    if note:
        input_obj["note"] = note
    if metafields:
        input_obj["metafields"] = metafields
    data = graphql(_CUSTOMER_CREATE, {"input": input_obj})
    result = data["customerCreate"]
    if result["userErrors"]:
        raise RuntimeError(result["userErrors"])
    return result["customer"]


def find_customer_by_email(email):
    data = graphql(_CUSTOMER_BY_EMAIL, {"query": f"email:{email}"})
    edges = data["customers"]["edges"]
    return edges[0]["node"] if edges else None


def list_customers(query=None, page_size=50):
    customers = []
    after = None
    while True:
        data = graphql(_CUSTOMERS_PAGE, {"first": page_size, "after": after, "query": query})
        block = data["customers"]
        customers.extend(edge["node"] for edge in block["edges"])
        if not block["pageInfo"]["hasNextPage"]:
            break
        after = block["pageInfo"]["endCursor"]
        time.sleep(0.2)
    return customers


if __name__ == "__main__":
    data = graphql("{ shop { name email } }")
    print(data["shop"])
