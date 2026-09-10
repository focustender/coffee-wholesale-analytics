# Shopify API setup (reusable)

How to connect a project to Shopify for real script access, the same way
`docs/reference/salesforce-cli-setup.md` covers Salesforce and
`docs/reference/hubspot-api-setup.md` covers HubSpot.

## Why not just use the Shopify MCP connector?

The Shopify connector available in this session (`mcp__claude_ai_Shopify__*`)
works and is full-featured. But like the HubSpot connector, it's chat-session
bound — a standalone script can't call it. `integrations/shopify_client.py`
exists so the same seeding logic can run with
`python3 integrations/seed_shopify.py` outside of any chat, authenticated
with its own durable credential.

## One-time setup

Shopify's 2026 app model (apps created via the **Dev Dashboard**) no longer
shows a static Admin API access token in the UI. Instead you get a
**Client ID + Client Secret** and exchange those programmatically for a
short-lived (24-hour) access token via the client credentials grant.
`shopify_client.py` does this exchange itself at runtime and caches the
result in memory, the same way `salesforce_client.py` shells out to `sf` for
a live session rather than trusting a long-lived static secret.

1. In the target Shopify admin: **Settings** → **Apps and sales channels**
   → **Develop apps** → **Create an app** → **Start from Dev Dashboard**,
   name it something identifiable (e.g. "Coffee Wholesale Analytics").
2. In the app's **Configuration** (or scope-selection step during creation),
   set Admin API scopes to at minimum:
   - `read_customers`
   - `write_customers`
3. Go to the app's **Settings** tab → **Credentials** section. Copy the
   **Client ID** (not secret) and reveal + copy the **Secret**.
4. Store the domain, client ID, and client secret as environment variables,
   never in a file that gets committed:
   ```bash
   echo 'export SHOPIFY_STORE_DOMAIN="your-store.myshopify.com"' >> ~/.zshrc
   echo 'export SHOPIFY_CLIENT_ID="paste-client-id-here"' >> ~/.zshrc
   echo 'export SHOPIFY_CLIENT_SECRET="paste-secret-here"' >> ~/.zshrc
   source ~/.zshrc
   ```
5. **Do not paste the raw secret into a chat with an AI assistant.** Treat it
   like a password — set it directly in your shell profile.

**Gotcha already solved, don't rediscover it:** the **App automation token**
shown on the same Settings page ("For CI/CD workflows only") is for
authenticating the *Shopify CLI* in non-interactive environments
(`SHOPIFY_APP_AUTOMATION_TOKEN`) — it is not an Admin API token and will
return a 401 if you try to use it as one. The Client ID + Secret exchange is
the correct path for a script calling the Admin API directly.

## Verifying it worked

```bash
python3 integrations/shopify_client.py
```

Should print `{'name': ..., 'email': ...}` for the connected store without
raising `ShopifyAuthError`.

## Using it from a script

`shopify_client.py` reads `SHOPIFY_STORE_DOMAIN` / `SHOPIFY_CLIENT_ID` /
`SHOPIFY_CLIENT_SECRET` from the environment at call time via `os.environ`,
and only ever exchanges them for an access token inside its own process.
Same principle as the Salesforce and HubSpot clients: never have an agent
print or read a live secret or access token directly.

## Protected customer data access

Even a custom app installed only on your own dev store needs explicit
**Protected customer data** approval before it can read or write anything
that touches customer PII (name, email, order history) — `customerCreate`
fails with `ACCESS_DENIED: "This app is not approved to access the Customer
object"` otherwise. Request it from the app's **API access** tab →
**Protected customer data access** → **Request access**, fill in the short
compliance form, and submit. This gate exists regardless of scopes already
granted in Configuration.

## Scope note: customers only, not orders

`seed_shopify.py` seeds Customers, not Orders. Shopify's Admin API doesn't
have a plain "create an order" mutation for arbitrary historical data — real
Order objects come from a checkout or a completed draft order, which doesn't
fit a scripted bulk-seed the way a plain object-create does. Customer
records plus tags (business_type, region) are the useful, achievable slice
here; a future project needing real order-level seeding should budget time
for the draft-order-complete flow specifically.

## Current connected store

`fireclaytile-project.myshopify.com` ("FireclayTile Project"), a development
store — no real payments process against it regardless of what's created.
This is the same store used for the Trade Signal project.
