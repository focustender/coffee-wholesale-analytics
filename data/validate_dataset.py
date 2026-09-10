"""
Validates the generated coffee wholesale dataset against the design spec's
validation plan: distribution sanity checks, referential integrity between
customers/orders/skus, origin-calendar integrity, and a recompute-and-compare
check confirming customers.csv aggregates weren't allowed to drift from
orders.csv. Run after generate_dataset.py.
"""

import csv
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

from generate_dataset import build_origin_calendar, SEED, START_DATE

EXPECTED_BUSINESS_TYPES = {"restaurant", "cafe", "hotel", "gym"}
EXPECTED_REGIONS = {"Los Angeles, CA", "Bay Area, CA", "New York, NY", "Seattle, WA",
                    "Portland, OR", "Austin, TX", "Santa Barbara, CA"}
EXPECTED_STAGES = {"Lead", "New Account", "Active Account", "Established Account", "At-Risk", "Churned"}


def load_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date() if s else None


def check_referential_integrity(customers, orders, skus):
    problems = []
    customer_ids = {c["customer_id"] for c in customers}
    sku_ids = {s["sku_id"] for s in skus}
    for o in orders:
        if o["customer_id"] not in customer_ids:
            problems.append(f"order {o['order_id']} references unknown customer {o['customer_id']}")
        if o["sku_id"] not in sku_ids:
            problems.append(f"order {o['order_id']} references unknown sku {o['sku_id']}")
    return problems


def check_aggregates_match(customers, orders):
    problems = []
    by_customer = defaultdict(list)
    for o in orders:
        by_customer[o["customer_id"]].append(o)

    for c in customers:
        cust_orders = by_customer.get(c["customer_id"], [])
        expected_total = len({o["order_id"] for o in cust_orders})
        expected_ltv = round(sum(float(o["line_total"]) for o in cust_orders), 2)
        actual_total = int(c["total_orders"])
        actual_ltv = float(c["lifetime_value"]) if c["lifetime_value"] != "" else 0.0
        if expected_total != actual_total:
            problems.append(
                f"{c['customer_id']}: total_orders mismatch (csv={actual_total}, recomputed={expected_total})")
        if abs(expected_ltv - actual_ltv) > 0.01:
            problems.append(
                f"{c['customer_id']}: lifetime_value mismatch (csv={actual_ltv}, recomputed={expected_ltv})")
    return problems


def check_origin_calendar_integrity(orders, skus, calendar):
    problems = []
    sku_by_id = {s["sku_id"]: s for s in skus}
    for o in orders:
        order_date = _parse_date(o["order_date"])
        month_key = (order_date.year, order_date.month)
        month_origins = calendar.get(month_key)
        sku = sku_by_id.get(o["sku_id"])
        if not month_origins or not sku:
            problems.append(f"order {o['order_id']}: no calendar entry or unknown sku for month {month_key}")
            continue
        active = month_origins["regular"] if sku["roast_type"] == "regular" else [month_origins["decaf"]]
        if sku["origin"] not in active:
            problems.append(
                f"order {o['order_id']}: origin {sku['origin']} not active for {sku['roast_type']} in {month_key}")
    return problems


def check_valid_categories(customers, skus):
    problems = []
    if len(skus) != 16:
        problems.append(f"expected 16 SKUs, found {len(skus)}")
    for c in customers:
        if c["business_type"] not in EXPECTED_BUSINESS_TYPES:
            problems.append(f"{c['customer_id']}: unexpected business_type {c['business_type']}")
        if c["region"] not in EXPECTED_REGIONS:
            problems.append(f"{c['customer_id']}: unexpected region {c['region']}")
        if c["lifecycle_stage"] not in EXPECTED_STAGES:
            problems.append(f"{c['customer_id']}: unexpected lifecycle_stage {c['lifecycle_stage']}")
    return problems


def print_distributions(customers):
    total = len(customers)
    for label, key in [("Lifecycle stage", "lifecycle_stage"),
                       ("Business type", "business_type"), ("Region", "region")]:
        print(f"{label} distribution:")
        counts = Counter(c[key] for c in customers)
        for value, count in counts.most_common():
            print(f"  {value}: {count} ({count / total:.1%})")


def main():
    data_dir = Path(__file__).parent
    skus = load_csv(data_dir / "skus.csv")
    customers = load_csv(data_dir / "customers.csv")
    orders = load_csv(data_dir / "orders.csv")

    print_distributions(customers)

    calendar = build_origin_calendar(SEED, START_DATE, date.today())
    problems = []
    problems += check_valid_categories(customers, skus)
    problems += check_referential_integrity(customers, orders, skus)
    problems += check_aggregates_match(customers, orders)
    problems += check_origin_calendar_integrity(orders, skus, calendar)

    if problems:
        print(f"\n{len(problems)} problem(s) found:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)

    print(f"\nAll checks passed: {len(customers)} customers, {len(skus)} skus, {len(orders)} order lines.")


if __name__ == "__main__":
    main()
