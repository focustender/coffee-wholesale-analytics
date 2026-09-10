"""
Synthetic coffee wholesale customer dataset generator.

Builds a 500-account wholesale dataset (customers, orders, sku catalog) for
lifecycle analysis, cohort tracking, and growth-metrics EDA practice.
Mirrors the approach of the prior Trade Signal synthetic HubSpot project:
stdlib-only, seeded random, fabricated names/emails always at @example.com
(RFC 2606, guarantees nothing can reach a real inbox).

See docs/superpowers/specs/2026-09-09-coffee-wholesale-synthetic-dataset-design.md
for the full design (pricing rationale, lifecycle taxonomy, region research).
"""

import csv
import random
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

SEED = 2026
START_DATE = date(2023, 9, 1)

# ---------------------------------------------------------------------------
# SKU catalog
# ---------------------------------------------------------------------------

ROASTS = ["regular", "decaf"]
ORIGINS = ["Colombia", "Peru", "Guatemala", "Blend"]
PACKAGES = [("retail", 220), ("wholesale", 2200)]
PRICE_TABLE = {
    ("regular", "retail"): 14.00,
    ("decaf", "retail"): 15.50,
    ("regular", "wholesale"): 84.00,
    ("decaf", "wholesale"): 93.00,
}


def build_skus():
    skus = []
    for roast in ROASTS:
        for origin in ORIGINS:
            for package_type, bag_size_g in PACKAGES:
                sku_id = f"{roast.upper()}-{origin.upper()}-{package_type.upper()}"
                skus.append({
                    "sku_id": sku_id,
                    "roast_type": roast,
                    "origin": origin,
                    "package_type": package_type,
                    "bag_size_g": bag_size_g,
                    "unit_price": PRICE_TABLE[(roast, package_type)],
                })
    return skus


# ---------------------------------------------------------------------------
# Monthly origin rotation calendar
# ---------------------------------------------------------------------------

def _month_range(start_date, end_date):
    year, month = start_date.year, start_date.month
    while (year, month) <= (end_date.year, end_date.month):
        yield (year, month)
        month += 1
        if month > 12:
            month = 1
            year += 1


def build_origin_calendar(seed, start_date, end_date):
    rng = random.Random(seed + 2)  # distinct stream from customer/order generation
    calendar = {}
    regular_origins = rng.sample(ORIGINS, rng.choice([1, 2]))
    decaf_origin = rng.choice(ORIGINS)
    regular_hold = rng.randint(1, 3)
    decaf_hold = rng.randint(1, 3)

    for month_key in _month_range(start_date, end_date):
        calendar[month_key] = {"regular": list(regular_origins), "decaf": decaf_origin}
        regular_hold -= 1
        decaf_hold -= 1
        if regular_hold <= 0:
            regular_origins = rng.sample(ORIGINS, rng.choice([1, 2]))
            regular_hold = rng.randint(1, 3)
        if decaf_hold <= 0:
            decaf_origin = rng.choice(ORIGINS)
            decaf_hold = rng.randint(1, 3)

    return calendar


# ---------------------------------------------------------------------------
# Lifecycle stage derivation
# ---------------------------------------------------------------------------

def derive_lifecycle_stage(total_orders, first_order_date, last_order_date, reference_date):
    if total_orders == 0:
        return "Lead"

    days_since_first = (reference_date - first_order_date).days
    if days_since_first < 90:
        return "New Account"

    days_since_last = (reference_date - last_order_date).days
    if days_since_last > 365:
        return "Churned"
    if days_since_last > 180:
        return "At-Risk"

    if days_since_first >= 365 and total_orders >= 6:
        return "Established Account"

    return "Active Account"


# ---------------------------------------------------------------------------
# Customer shell generation
# ---------------------------------------------------------------------------

BUSINESS_TYPES = ["restaurant", "cafe", "hotel", "gym"]
BUSINESS_TYPE_WEIGHTS = [0.40, 0.30, 0.15, 0.15]

ACQUISITION_CHANNELS = ["trade_show", "referral", "distributor_partner",
                        "cold_outreach", "inbound_web", "direct_relationship"]
ACQUISITION_WEIGHTS = [0.15, 0.25, 0.15, 0.15, 0.20, 0.10]

REGIONS = ["Los Angeles, CA", "Bay Area, CA", "New York, NY", "Seattle, WA",
           "Portland, OR", "Austin, TX", "Santa Barbara, CA"]
REGION_WEIGHTS = [0.22, 0.20, 0.20, 0.15, 0.10, 0.08, 0.05]

NAME_STEMS = ["Meridian", "Harbor", "Cedar", "Copper", "Lantern", "Golden Hour", "Blue Ridge",
              "Northside", "Wildflower", "Elm Street", "Sunset", "Horizon", "Ember", "Maple",
              "Ironwood", "Silver Creek", "Bramble", "Vantage", "Driftwood", "Foundry"]
SUFFIXES_BY_TYPE = {
    "restaurant": ["Bistro", "Kitchen", "Grill", "Table", "Eatery", "Diner"],
    "cafe": ["Coffee Co.", "Cafe", "Coffee House", "Espresso Bar", "Roasters"],
    "hotel": ["Hotel", "Inn", "Suites", "Lodge"],
    "gym": ["Fitness", "Gym", "Athletic Club", "Training Studio"],
}
FIRST_NAMES = ["Maria", "James", "Linda", "Robert", "Patricia", "John", "Jennifer", "Michael",
               "Elizabeth", "David", "Susan", "Richard", "Jessica", "Thomas", "Karen", "Daniel",
               "Lisa", "Andrew", "Priya", "Wei", "Fatima", "Diego", "Aisha", "Hiroshi", "Elena",
               "Carlos", "Yuki", "Amara", "Noah", "Sofia"]
LAST_NAMES = ["Garcia", "Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis",
              "Rodriguez", "Martinez", "Hernandez", "Lopez", "Wilson", "Anderson", "Thomas",
              "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White",
              "Harris", "Sanchez", "Clark", "Nguyen", "Patel", "Kim", "Chen"]
EMAIL_OPT_IN_RATE = 0.90
SIGNUP_GROWTH_EXPONENT = 0.6  # <1 skews signups toward more recent dates


def _weighted_choice(rng, options, weights):
    return rng.choices(options, weights=weights, k=1)[0]


def _signup_date(rng, start_date, end_date):
    total_days = (end_date - start_date).days
    r = rng.random() ** SIGNUP_GROWTH_EXPONENT
    return start_date + timedelta(days=int(r * total_days))


def build_customers(n, seed, start_date, end_date):
    rng = random.Random(seed)
    customers = []
    for i in range(1, n + 1):
        customer_id = f"WCUST-{i:05d}"
        business_type = _weighted_choice(rng, BUSINESS_TYPES, BUSINESS_TYPE_WEIGHTS)
        stem = rng.choice(NAME_STEMS)
        suffix = rng.choice(SUFFIXES_BY_TYPE[business_type])
        customers.append({
            "customer_id": customer_id,
            "company_name": f"{stem} {suffix}",
            "business_type": business_type,
            "contact_first_name": rng.choice(FIRST_NAMES),
            "contact_last_name": rng.choice(LAST_NAMES),
            "email": f"{customer_id.lower()}@example.com",
            "acquisition_channel": _weighted_choice(rng, ACQUISITION_CHANNELS, ACQUISITION_WEIGHTS),
            "region": _weighted_choice(rng, REGIONS, REGION_WEIGHTS),
            "signup_date": _signup_date(rng, start_date, end_date),
            "email_opt_in": 1 if rng.random() < EMAIL_OPT_IN_RATE else 0,
        })
    return customers


# ---------------------------------------------------------------------------
# Order-line generation
# ---------------------------------------------------------------------------

LEAD_PROBABILITY = 0.10
CHURN_PROBABILITY = 0.20
RETAIL_BONUS_PROBABILITY = 0.15
REGULAR_ROAST_PROBABILITY = 0.85

BUSINESS_TYPE_PARAMS = {
    "cafe":       {"interval_days": 21, "bags_range": (3, 8)},
    "restaurant": {"interval_days": 28, "bags_range": (2, 5)},
    "hotel":      {"interval_days": 35, "bags_range": (4, 10)},
    "gym":        {"interval_days": 56, "bags_range": (1, 3)},
}


def _pick_origin(rng, month_origins, roast):
    active = month_origins["regular"] if roast == "regular" else [month_origins["decaf"]]
    return rng.choice(active)


def _make_line(order_id, customer_id, order_date, sku, qty):
    return {
        "order_id": order_id,
        "customer_id": customer_id,
        "order_date": order_date,
        "sku_id": sku["sku_id"],
        "quantity": qty,
        "unit_price": sku["unit_price"],
        "line_total": round(qty * sku["unit_price"], 2),
    }


def _build_order_lines(rng, order_id, customer_id, order_date, month_origins, sku_lookup, params):
    lines = []
    roast = "regular" if rng.random() < REGULAR_ROAST_PROBABILITY else "decaf"
    origin = _pick_origin(rng, month_origins, roast)
    sku = sku_lookup[(roast, origin, "wholesale")]
    qty = rng.randint(*params["bags_range"])
    lines.append(_make_line(order_id, customer_id, order_date, sku, qty))

    if rng.random() < RETAIL_BONUS_PROBABILITY:
        retail_roast = "regular" if rng.random() < REGULAR_ROAST_PROBABILITY else "decaf"
        retail_origin = _pick_origin(rng, month_origins, retail_roast)
        retail_sku = sku_lookup[(retail_roast, retail_origin, "retail")]
        retail_qty = rng.randint(1, 3)
        lines.append(_make_line(order_id, customer_id, order_date, retail_sku, retail_qty))

    return lines


def build_orders(customers, skus, calendar, seed, reference_date):
    rng = random.Random(seed + 1)  # distinct stream from customer generation
    sku_lookup = {(s["roast_type"], s["origin"], s["package_type"]): s for s in skus}
    orders = []
    order_seq = 1

    for cust in customers:
        if rng.random() < LEAD_PROBABILITY:
            continue  # stays a Lead: zero orders

        params = BUSINESS_TYPE_PARAMS[cust["business_type"]]
        conversion_lag = rng.randint(0, 30)
        first_order_date = cust["signup_date"] + timedelta(days=conversion_lag)
        if first_order_date > reference_date:
            continue  # signed up too recently to have converted yet

        if rng.random() < CHURN_PROBABILITY:
            span = (reference_date - first_order_date).days
            if span >= 60:
                stop_after = rng.randint(30, span - 30)
                end_date = first_order_date + timedelta(days=stop_after)
            else:
                end_date = reference_date
        else:
            end_date = reference_date

        current_date = first_order_date
        while current_date <= end_date:
            month_key = (current_date.year, current_date.month)
            month_origins = calendar.get(month_key)
            if month_origins:
                order_id = f"ORD-{order_seq:06d}"
                order_seq += 1
                orders.extend(_build_order_lines(
                    rng, order_id, cust["customer_id"], current_date,
                    month_origins, sku_lookup, params))
            jitter_span = max(1, int(params["interval_days"] * 0.3))
            jitter = rng.randint(-jitter_span, jitter_span)
            current_date = current_date + timedelta(days=max(7, params["interval_days"] + jitter))

    return orders


# ---------------------------------------------------------------------------
# Aggregate computation
# ---------------------------------------------------------------------------

def compute_customer_aggregates(customers, orders, reference_date):
    orders_by_customer = defaultdict(list)
    for o in orders:
        orders_by_customer[o["customer_id"]].append(o)

    enriched = []
    for cust in customers:
        cust_orders = orders_by_customer.get(cust["customer_id"], [])
        distinct_order_ids = {o["order_id"] for o in cust_orders}
        total_orders = len(distinct_order_ids)

        if total_orders == 0:
            first_order_date = None
            last_order_date = None
            lifetime_value = 0.0
            avg_order_value = None
        else:
            dates = [o["order_date"] for o in cust_orders]
            first_order_date = min(dates)
            last_order_date = max(dates)
            lifetime_value = round(sum(o["line_total"] for o in cust_orders), 2)
            avg_order_value = round(lifetime_value / total_orders, 2)

        stage = derive_lifecycle_stage(total_orders, first_order_date, last_order_date, reference_date)
        enriched.append({
            **cust,
            "first_order_date": first_order_date,
            "last_order_date": last_order_date,
            "lifecycle_stage": stage,
            "total_orders": total_orders,
            "lifetime_value": lifetime_value,
            "avg_order_value": avg_order_value,
        })
    return enriched


# ---------------------------------------------------------------------------
# CSV writers + orchestration
# ---------------------------------------------------------------------------

SKU_FIELDS = ["sku_id", "roast_type", "origin", "package_type", "bag_size_g", "unit_price"]
CUSTOMER_FIELDS = ["customer_id", "company_name", "business_type", "contact_first_name",
                   "contact_last_name", "email", "acquisition_channel", "region", "signup_date",
                   "first_order_date", "lifecycle_stage", "total_orders", "lifetime_value",
                   "last_order_date", "avg_order_value", "email_opt_in"]
ORDER_FIELDS = ["order_id", "customer_id", "order_date", "sku_id", "quantity", "unit_price", "line_total"]


def _fmt(value):
    if value is None:
        return ""
    if isinstance(value, date):
        return value.isoformat()
    return value


def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _fmt(row.get(k)) for k in fieldnames})


def generate_dataset(n_customers=500, seed=SEED, out_dir=None):
    reference_date = date.today()
    skus = build_skus()
    customers = build_customers(n_customers, seed, START_DATE, reference_date)
    calendar = build_origin_calendar(seed, START_DATE, reference_date)
    orders = build_orders(customers, skus, calendar, seed, reference_date)
    customers = compute_customer_aggregates(customers, orders, reference_date)

    if out_dir:
        out_dir = Path(out_dir)
        write_csv(out_dir / "skus.csv", skus, SKU_FIELDS)
        write_csv(out_dir / "customers.csv", customers, CUSTOMER_FIELDS)
        write_csv(out_dir / "orders.csv", orders, ORDER_FIELDS)

    return skus, customers, orders


if __name__ == "__main__":
    out_dir = Path(__file__).parent
    skus, customers, orders = generate_dataset(n_customers=500, seed=SEED, out_dir=out_dir)
    print(f"Wrote {len(skus)} SKUs, {len(customers)} customers, {len(orders)} order lines to {out_dir}")
