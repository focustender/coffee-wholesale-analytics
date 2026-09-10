# Reusable components log

Running inventory of tooling built during this project (or others) that's
designed to be copied into future projects rather than rebuilt from scratch.
Update this whenever a new reusable piece is built, whether or not it
started life here.

| Component | Lives at | What it does | Status | Built for | Also usable in |
|---|---|---|---|---|---|
| Salesforce CLI setup runbook | `docs/reference/salesforce-cli-setup.md` (this repo) | Step-by-step for connecting a project to Salesforce via the `sf` CLI, working around the broken claude.ai Salesforce Beta MCP connector. Covers install gotchas, login, and the token-redaction split. | Done, verified working (2026-09-09) | Coffee Wholesale Analytics | Any future project needing Salesforce data access |
| `salesforce_client.py` | `integrations/salesforce_client.py` (this repo) | Thin Salesforce REST client (query/create/update) authenticated via the `sf` CLI at runtime, never hardcodes credentials. | Done, smoke-tested against a real Developer Edition org | Coffee Wholesale Analytics | Any future project — copy the file as-is, no project-specific code in it |
| `generate_dataset.py` pattern (stdlib-only, seeded, weighted-distribution synthetic generator) | `data/generate_dataset.py` (this repo), originally from `~/fireclayTile/trade-signal/data/generate_dataset.py` | The general approach (not the file itself, since fields are business-specific): stdlib-only Python, fixed random seed, weighted categorical distributions, fabricated `@example.com` emails. | Reused once already (Trade Signal to this project) | Trade Signal (Fireclay) | Any future synthetic-dataset project — reuse the *pattern*, not the code |

## Planned, not built yet

- **HubSpot client**: same shape as `salesforce_client.py` — a thin wrapper for seeding/reading contacts, once we get to the HubSpot integration step.
- **Shopify client**: same shape, likely wrapping `graphql_mutation`/`graphql_query` calls for order/customer creation on a dev store.
- **Cross-system reconciliation utility**: a generic "diff two lifecycle-bearing record sets by a shared key, report mismatches" function. This is the one most worth generalizing well, since it's the core of the planned HubSpot/Salesforce lifecycle-stage reconciliation and isn't specific to any one pair of platforms.
