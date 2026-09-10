# HubSpot API setup (reusable)

How to connect a project to HubSpot for real script access, the same way
`docs/reference/salesforce-cli-setup.md` covers Salesforce.

## Why not just use the HubSpot MCP connector?

The HubSpot connector available in this session (`mcp__claude_ai_HubSpot__*` /
`mcp__hubspot__*`) works and is full-featured (contact/company CRUD, custom
properties, search). But it only exists inside a Claude chat session — a
standalone script (a cron job, a CI seed step, a tool handed to someone else)
can't call it. `integrations/hubspot_client.py` exists so the same seeding
logic can run with `python3 integrations/seed_hubspot.py` outside of any
chat, authenticated with its own durable credential.

## Use a dedicated test account per project

Don't reuse one HubSpot portal across multiple unrelated synthetic-data
projects. Free/starter portals cap out at 1,000 CONTACT records total, and
that ceiling is shared across everything ever seeded into that portal. This
project initially pointed at the same portal used for the Trade Signal
project, which already held ~750 contacts (mostly Trade Signal's own
synthetic data plus HubSpot's default demo contacts) — leaving no room for
this project's 500 new contacts and failing with `402 Payment Required:
"exceeded the limit of 1000"` on the very first create.

The fix, and the pattern to repeat for every future project: create a fresh,
free **HubSpot developer test account** per project (developers.hubspot.com
→ your developer account → **Test accounts** → **Create test account**),
the same way Salesforce gets its own dev org per project rather than one
shared org. Test accounts are free, instant, and isolated from each other.

## One-time setup

HubSpot is migrating away from Private Apps toward **Service Keys** (public
beta since February 2026) for exactly this use case — single-account,
system-to-system API access. Service Keys use the same Bearer-token auth as
a private app's access token, so `hubspot_client.py` needs no special
handling for either; use whichever your portal offers. Service Keys is the
one that will keep working as HubSpot's platform evolves, so prefer it.

**Service Keys path (preferred):**

1. In the target HubSpot portal: **Development** → **Keys** → **Service
   keys** → **Create service key**.
2. Name it something identifiable (e.g. "Coffee Wholesale Analytics").
3. **Add new scope** and select at minimum:
   - `crm.objects.contacts.read`
   - `crm.objects.contacts.write`
   - `crm.schemas.contacts.read` (needed to create the custom properties
     `seed_hubspot.py` uses)
4. Create the key and copy the token shown. It is shown once — HubSpot will
   not display it again (you'd have to rotate it).

**Legacy Private App path (if Service Keys isn't available on your
portal):** Settings → Integrations → Private Apps → Create a private app.
On newer portals this page shows "Your private apps have moved" — click
**Go to Legacy Apps**, then **I still want a legacy private app** to reach
the same creation flow, with the same scopes as above.

5. However you got the token, store it as an environment variable, never in
   a file that gets committed:
   ```bash
   echo 'export HUBSPOT_ACCESS_TOKEN="paste-here"' >> ~/.zshrc
   source ~/.zshrc
   ```
6. **Do not paste the raw token into a chat with an AI assistant.** Treat it
   like a password — set it directly in your shell profile.

## Verifying it worked

```bash
python3 integrations/hubspot_client.py
```

Should print the count of contacts already in the portal (0 on a fresh
portal) without raising `HubSpotAuthError`.

## Using it from a script

`hubspot_client.py` reads `HUBSPOT_ACCESS_TOKEN` from the environment at call
time via `os.environ`. Nothing about the token passes through an agent's
context — the same principle documented in the Salesforce runbook applies
here: never have an agent print or read the token value directly.

## Current connected portal

Portal name `focustender`, account ID `247275141`. Rate limit and object
caps depend on the portal's HubSpot tier — check **Settings → Account &
Billing** if `seed_hubspot.py` starts hitting 429s faster than expected.
