# Coffee Wholesale Analytics

A synthetic coffee wholesale business, built from scratch to practice lifecycle analysis, cohort tracking, and growth metrics, with real platform integrations layered on top instead of just spreadsheet exercises.

## What this is

500 fictional wholesale accounts (restaurants, cafes, hotels, gyms) buying whole bean coffee across four origins and two roast types, generated with realistic buying patterns: order frequency and size vary by business type, coffee origins rotate monthly like a real small roaster's sourcing calendar, and accounts naturally season into different lifecycle stages (Lead, New Account, Active Account, Established Account, At-Risk, Churned) based on how they actually ordered, not a label someone typed in.

Nothing here is real. Company names, emails, and order history are fabricated. Pricing is benchmarked against real specialty roasters (Sey, Sweet Bloom, Saint Frank, Arcade), and the regions customers are drawn from are researched against real third-wave coffee markets, but the dataset itself is synthetic.

## What's built

- **The dataset** (`data/`): a generator script and validator, both plain Python with no dependencies beyond the standard library. Full design rationale, including why the lifecycle stages are defined the way they are and how pricing was benchmarked, is in `docs/superpowers/specs/2026-09-09-coffee-wholesale-synthetic-dataset-design.md`.
- **Follow-on analysis** (`analysis/`): cohort retention by signup quarter, order frequency and lifetime value by business type and acquisition channel, origin popularity, and growth vectors. This is what turned up the strongest finding so far: business type predicts account value far better than acquisition channel does (cafes are worth roughly 6.7x what gyms are worth over their lifetime).
- **Real Salesforce, HubSpot, and Shopify connections** (`integrations/`): thin REST/GraphQL clients authenticated through each platform's own CLI or API credentials rather than hardcoded tokens, built to be reusable in future projects, not just this one. Setup instructions are in `docs/reference/salesforce-cli-setup.md`, `hubspot-api-setup.md`, and `shopify-api-setup.md`.
- **A cross-system lifecycle reconciliation** (`analysis/reconcile_hubspot.py`): all 500 synthetic accounts are seeded as real contacts in a HubSpot test portal and as real customers in a Shopify dev store. Comparing HubSpot's lifecyclestage against what the order data actually shows turns up the same kind of gap the Trade Signal project found: 45 of 500 contacts (9%) still read "customer" in HubSpot despite having gone quiet or dropped off entirely, because lifecyclestage gets set once on first sale and is never revisited. `analysis/reconcile_lifecycle.py` is a generic version of that diff, reusable for any future project that needs to check a CRM's recorded status against a source of truth.

## What's next

- Shopify integration currently covers customers only; order-level seeding would need the draft-order-complete flow rather than a plain create (see `docs/reference/shopify-api-setup.md`).

## Running it

```bash
python3 data/generate_dataset.py         # builds the 500-account dataset
python3 data/validate_dataset.py         # checks it for integrity
python3 analysis/follow_on_analysis.py   # runs the follow-on EDA
python3 integrations/seed_hubspot.py     # seeds contacts into a real HubSpot portal
python3 integrations/seed_shopify.py     # seeds customers into a real Shopify store
python3 analysis/reconcile_hubspot.py    # checks HubSpot's lifecyclestage against ground truth
```

The three `integrations/` and `reconcile_hubspot.py` commands need real credentials set up first — see `docs/reference/hubspot-api-setup.md` and `shopify-api-setup.md`.
