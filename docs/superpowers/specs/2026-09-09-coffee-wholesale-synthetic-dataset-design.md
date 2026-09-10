# Coffee Wholesale Synthetic Dataset — Design

## Purpose

A 500-account synthetic wholesale coffee customer dataset, structured to support lifecycle analysis, cohort/retention tracking, growth metrics, and general EDA practice. Mirrors the structure and generation approach of the prior "Trade Signal" synthetic HubSpot project (`~/fireclayTile/trade-signal/data/`), adapted for a coffee wholesale business instead of tile.

## Reference project

`~/fireclayTile/trade-signal/data/generate_dataset.py` and `generate_hubspot_import.py`: stdlib-only Python, seeded `random`, weighted distributions per segment, fabricated names/emails always at `@example.com` (RFC 2606, guarantees nothing can reach a real inbox), validation via row/segment count printouts against targets. This project follows the same tooling and safety practice, dropped the parts that don't apply here (no SQLite db, no Salesforce seed, no deliberately-messy CRM-reconciliation export — those existed for Trade Signal's specific CRM-reconciliation narrative, not needed here).

## Business model

**Products:** coffee sold as whole bean only (no ground SKUs). Two axes cross to form the catalog:
- **Roast type:** regular, decaf
- **Origin:** Colombia, Peru, Guatemala, Blend

Each roast type × origin combination is sold in two package sizes:
- Retail bag, 220g
- Wholesale bag, 2200g

This gives **16 SKUs** (4 origins × 2 roast types × 2 package sizes). Origin does not affect price — price is set purely by roast type × package size.

**Origin availability is monthly, not permanent.** The business sources one or two origins for regular coffee and one origin for decaf in any given month (e.g., August: Peru + Guatemala for regular, Peru for decaf; May: Colombia for regular, Colombia for decaf). All 16 SKUs exist in `skus.csv` as a static catalog, but only the SKUs matching that month's active origin(s) can appear on an order placed in that month. A 3-year rotation calendar is generated internally by the build script (not a separate output file) covering Sept 2023 through today, cycling through Colombia/Peru/Guatemala/Blend in a plausible pattern consistent with the given examples.

**Pricing** (benchmarked against live specialty-roaster retail pricing — Sey ~$22-23/12oz, Sweet Bloom ~$20.50-26.25/10oz, Saint Frank decaf ~$22, Arcade ~$14-18/12oz; wholesale terms are quote-only industry-wide, confirmed via Sey's own wholesale page, so the wholesale discount is modeled on the standard 30-45% specialty-coffee trade discount rather than sourced):

| Roast | Package | Price | Per-gram |
|---|---|---|---|
| Regular | Retail 220g | $14.00 | $0.0636/g |
| Decaf | Retail 220g | $15.50 | $0.0705/g |
| Regular | Wholesale 2200g | $84.00 | $0.0382/g |
| Decaf | Wholesale 2200g | $93.00 | $0.0423/g |

Decaf carries a ~10% premium over regular at both package sizes, reflecting real decaf-processing cost. Wholesale per-gram price sits ~40% below retail per-gram, consistent with standard trade-discount practice.

**Customers:** 500 wholesale accounts. Business types: restaurant (40%, ~200 accounts), cafe (30%, ~150), hotel (15%, ~75), gym (15%, ~75). Regions are metro areas where third-wave/specialty coffee has real market presence, not a generic all-US spread (see `region` below).

## Lifecycle stage taxonomy

Derived from order history at a fixed snapshot/reference date (today, at generation time) — not independently randomized, so it can never drift out of sync with the actual order data:

| Stage | Rule |
|---|---|
| Lead | Zero orders placed |
| New Account | 1+ orders, first order within the last 90 days |
| Active Account | 1+ orders, last order within 180 days, but doesn't yet meet Established criteria |
| Established Account | 12+ months tenure since first order, 6+ total orders, last order within 180 days |
| At-Risk | Last order 180-365 days ago |
| Churned | Last order 365+ days ago |

Rules are evaluated top-to-bottom in the table order above; the first matching rule wins. This matters at one boundary: an account within 90 days of its first order also trivially satisfies Active Account's looser condition, but New Account takes precedence. No other rule pairs overlap (Established's tenure floor of 12 months is mutually exclusive with New Account's 90-day ceiling; At-Risk/Churned are defined purely by last-order recency and take precedence over Established/Active whenever last order exceeds 180 days).

## Schema

**`skus.csv`** (16 rows) — static product catalog:
`sku_id, roast_type, origin, package_type, bag_size_g, unit_price`

**`customers.csv`** (500 rows) — one row per wholesale account:
`customer_id, company_name, business_type, contact_first_name, contact_last_name, email, acquisition_channel, region, signup_date, first_order_date, lifecycle_stage, total_orders, lifetime_value, last_order_date, avg_order_value, email_opt_in`

- `business_type`: restaurant / cafe / gym / hotel
- `acquisition_channel`: trade_show / referral / distributor_partner / cold_outreach / inbound_web / direct_relationship
- `region`: metro area, not a US state (unlike the Trade Signal project's 20-state list) — state-level codes can't distinguish LA from Bay Area from Santa Barbara (all California). Researched against real third-wave coffee presence (Portland: Stumptown's 1999 founding; Seattle: the historically dominant US coffee city; Bay Area: birthplace of the "third wave coffee" term itself, Wrecking Ball/Ritual/Andytown/Farley's; LA: Verve, Dayglow, Arcade; Austin: Cuvée, Greater Goods, Houndstooth; Santa Barbara: smaller boutique scene, Handlebar Coffee Roasters). Weights modeled on relative metro size and specialty-coffee density, not sourced from a specific dataset:

  | Region | Weight |
  |---|---|
  | Los Angeles, CA | 22% |
  | Bay Area, CA | 20% |
  | New York, NY | 20% |
  | Seattle, WA | 15% |
  | Portland, OR | 10% |
  | Austin, TX | 8% |
  | Santa Barbara, CA | 5% |
- `email`: fabricated, always `@example.com`
- Aggregate fields (`total_orders`, `lifetime_value`, `last_order_date`, `avg_order_value`) are computed from `orders.csv` at generation time, not independently randomized, so the two tables can't drift apart
- `first_order_date`, `last_order_date`, `avg_order_value` are null for Leads (zero orders)

**`orders.csv`** (order-line grain, several thousand rows) — one row per SKU line within an order:
`order_id, customer_id, order_date, sku_id, quantity, unit_price, line_total`

- `order_date` must fall within a month where the referenced SKU's origin was active per the rotation calendar
- `unit_price` is a snapshot of the SKU's price at order time (pricing held flat across the whole window — no inflation modeled, kept simple deliberately)

## Generation approach

Dataset window: **2023-09 through today (2026-09-09)**, giving three full years for tenure-based lifecycle stages to develop naturally (enough runway for accounts to season into Established, and for full churn cycles — quiet 12-24 months ago — to show up as Churned rather than just barely crossing a threshold).

Signup dates are spread across the window with a growth curve (fewer early accounts, more recent, mimicking real customer acquisition) but weighted so enough early cohorts exist to actually populate Established/At-Risk/Churned, not just New/Active.

Order frequency and size vary by `business_type` (median days between orders, wholesale bags per order — see table below), with per-customer jitter around the type's median. ~15% of orders also include a retail-size (220g) line (front-desk resale), independent of the wholesale cadence. Each order line's origin is chosen from that month's active origin(s) for its roast type.

| Business type | Weight | Order interval (median) | Bags/order (wholesale) |
|---|---|---|---|
| Cafe | 30% | ~21 days | 3-8 (mean ~5) |
| Restaurant | 40% | ~28 days | 2-5 (mean ~3) |
| Hotel | 15% | ~35 days | 4-10 (mean ~6, high variance) |
| Gym | 15% | ~56 days | 1-3 (mean ~2) |

Tooling: stdlib-only Python (`csv`, `random` with a fixed seed, `datetime`), one script (`generate_dataset.py`), mirroring the prior project's approach exactly.

Customer IDs: `WCUST-00001`-`WCUST-00500`. Order IDs: `ORD-000001` incrementing. SKU IDs: descriptive slugs, e.g. `REG-COLOMBIA-RETAIL`, `DECAF-BLEND-WHOLESALE`.

## Validation plan

Mirrors the prior project's lean approach (print-based, no separate reconciliation layer):
- Row count and distribution printouts: business_type mix, lifecycle stage mix, region mix, against targets
- Referential integrity: every `orders.csv` `customer_id` resolves in `customers.csv`, every `sku_id` resolves in `skus.csv`
- Origin-calendar integrity: every order's SKU origin was actually active in that order's month
- Recompute-and-compare: `customers.csv` aggregate fields (`total_orders`, `lifetime_value`, `last_order_date`, `avg_order_value`) match values recomputed fresh from `orders.csv`

## Output

Three CSVs in `data/`: `skus.csv`, `customers.csv`, `orders.csv`, plus the generator script `data/generate_dataset.py`. No SQLite db, no platform-specific (HubSpot/Salesforce) export variants — out of scope per the "core CSVs only" decision.

## Follow-on analysis (not built yet, recommended after dataset review)

Framed as question-driven EDA, consistent with the user's preferred Udacity-style project structure (Ask Questions → Assess/Clean → EDA-per-question → Conclusions):
- Cohort retention: of accounts acquired in a given quarter, what fraction are still Active/Established a year later?
- Order frequency and lifetime value by `business_type` and `acquisition_channel`
- Origin popularity and seasonality: does the monthly origin rotation correlate with order volume shifts?
- Growth vectors: New Account creation rate over time, churn rate over time, net account growth
- Decaf vs regular mix by business_type
