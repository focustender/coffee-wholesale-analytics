# Coffee Wholesale Analytics

A synthetic coffee wholesale business, built from scratch to practice lifecycle analysis, cohort tracking, and growth metrics, with real platform integrations layered on top instead of just spreadsheet exercises.

## What this is

500 fictional wholesale accounts (restaurants, cafes, hotels, gyms) buying whole bean coffee across four origins and two roast types, generated with realistic buying patterns: order frequency and size vary by business type, coffee origins rotate monthly like a real small roaster's sourcing calendar, and accounts naturally season into different lifecycle stages (Lead, New Account, Active Account, Established Account, At-Risk, Churned) based on how they actually ordered, not a label someone typed in.

Nothing here is real. Company names, emails, and order history are fabricated. Pricing is benchmarked against real specialty roasters (Sey, Sweet Bloom, Saint Frank, Arcade), and the regions customers are drawn from are researched against real third-wave coffee markets, but the dataset itself is synthetic.

## What's built

- **The dataset** (`data/`): a generator script and validator, both plain Python with no dependencies beyond the standard library. Full design rationale, including why the lifecycle stages are defined the way they are and how pricing was benchmarked, is in `docs/superpowers/specs/2026-09-09-coffee-wholesale-synthetic-dataset-design.md`.
- **Follow-on analysis** (`analysis/`): cohort retention by signup quarter, order frequency and lifetime value by business type and acquisition channel, origin popularity, and growth vectors. This is what turned up the strongest finding so far: business type predicts account value far better than acquisition channel does (cafes are worth roughly 6.7x what gyms are worth over their lifetime).
- **A real Salesforce connection** (`integrations/`): a small REST client authenticated through the Salesforce CLI rather than hardcoded credentials, built to be reusable in future projects, not just this one. Setup instructions are in `docs/reference/salesforce-cli-setup.md`.

## What's next

- Seeding the dataset into HubSpot and Shopify, the same way it's already connected to Salesforce.
- A lifecycle-stage reconciliation across systems: does what a CRM says about an account match what the order data actually shows? That mismatch, when it shows up, tends to be the most useful finding in a project like this.

## Running it

```bash
python3 data/generate_dataset.py         # builds the 500-account dataset
python3 data/validate_dataset.py         # checks it for integrity
python3 analysis/follow_on_analysis.py   # runs the follow-on EDA
```
