# Coffee Wholesale Dataset Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate a 500-account synthetic coffee wholesale dataset (three CSVs: `skus.csv`, `customers.csv`, `orders.csv`) plus a validation script, exactly matching the approved design spec.

**Architecture:** One stdlib-only Python module (`data/generate_dataset.py`) with pure, independently-testable functions for each generation phase (SKU catalog, origin rotation calendar, customer shells, order-line generation, lifecycle/aggregate computation, CSV writing), orchestrated by a `generate_dataset()` function. A separate `data/validate_dataset.py` re-reads the written CSVs from disk and checks them against the spec's validation plan, reusing `generate_dataset.py`'s deterministic calendar function rather than duplicating logic.

**Tech Stack:** Python 3.14 stdlib only (`csv`, `random`, `datetime`, `pathlib`, `collections`) for the generator and validator; `pytest` (dev-only) for tests.

**Spec:** `docs/superpowers/specs/2026-09-09-coffee-wholesale-synthetic-dataset-design.md`

## Global Constraints

- stdlib-only for `data/generate_dataset.py` and `data/validate_dataset.py` — no third-party runtime dependencies. `pytest` is a dev/test-only dependency, already installed (9.1.1).
- Fabricated emails always end in `@example.com` (RFC 2606) — nothing in this dataset can ever reach a real inbox.
- Fixed random seed (`SEED = 2026`) for full reproducibility.
- Dataset window: `START_DATE = date(2023, 9, 1)` through `date.today()` at generation time.
- Schema field names and order must exactly match the spec's Schema section: `skus.csv` (`sku_id, roast_type, origin, package_type, bag_size_g, unit_price`), `customers.csv` (`customer_id, company_name, business_type, contact_first_name, contact_last_name, email, acquisition_channel, region, signup_date, first_order_date, lifecycle_stage, total_orders, lifetime_value, last_order_date, avg_order_value, email_opt_in`), `orders.csv` (`order_id, customer_id, order_date, sku_id, quantity, unit_price, line_total`).
- Pricing must exactly match the spec's table (regular retail $14.00, decaf retail $15.50, regular wholesale $84.00, decaf wholesale $93.00); origin never affects price.
- Lifecycle-stage precedence must exactly match the spec: Lead > New Account (first order <90 days ago) > Churned (last order >365 days ago) / At-Risk (last order >180 days ago) > Established Account (tenure ≥365 days AND ≥6 orders) > Active Account (fallback).
- **Resolved ambiguity (spec didn't specify):** `total_orders` and `avg_order_value` count distinct `order_id` values, not raw `orders.csv` line rows — a single order can have 2 lines (a wholesale line plus a retail bonus line).

---

## Task 1: Project scaffolding + SKU catalog

**Files:**
- Create: `data/generate_dataset.py`
- Create: `conftest.py` (repo root)
- Test: `tests/test_generate_dataset.py`

**Interfaces:**
- Produces: `build_skus() -> list[dict]`, each dict with keys `sku_id, roast_type, origin, package_type, bag_size_g, unit_price`. Also produces module constants `ROASTS`, `ORIGINS`, `PRICE_TABLE`, `SEED`, `START_DATE` that later tasks import.

- [ ] **Step 1: Create directories and the test-import path**

```bash
mkdir -p data tests
```

Create `conftest.py` at the repo root:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "data"))
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_generate_dataset.py`:

```python
import generate_dataset as gd


def test_build_skus_has_sixteen_rows_and_correct_pricing():
    skus = gd.build_skus()
    assert len(skus) == 16
    assert len({s["sku_id"] for s in skus}) == 16

    prices = {(s["roast_type"], s["package_type"]): s["unit_price"] for s in skus}
    assert prices[("regular", "retail")] == 14.00
    assert prices[("decaf", "retail")] == 15.50
    assert prices[("regular", "wholesale")] == 84.00
    assert prices[("decaf", "wholesale")] == 93.00

    # origin must never affect price within a roast/package combo
    for roast in ("regular", "decaf"):
        for package in ("retail", "wholesale"):
            matching = [s["unit_price"] for s in skus
                        if s["roast_type"] == roast and s["package_type"] == package]
            assert len(set(matching)) == 1
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_generate_dataset.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'generate_dataset'`

- [ ] **Step 4: Write the implementation**

Create `data/generate_dataset.py`:

```python
import csv
import random
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

SEED = 2026
START_DATE = date(2023, 9, 1)

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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_generate_dataset.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add conftest.py data/generate_dataset.py tests/test_generate_dataset.py
git commit -m "Add SKU catalog generation"
```

---

## Task 2: Origin rotation calendar

**Files:**
- Modify: `data/generate_dataset.py`
- Test: `tests/test_generate_dataset.py`

**Interfaces:**
- Consumes: `ORIGINS` from Task 1.
- Produces: `build_origin_calendar(seed: int, start_date: date, end_date: date) -> dict[(int, int), dict]`, where each value is `{"regular": list[str], "decaf": str}` keyed by `(year, month)` tuples covering every month from `start_date` through `end_date` inclusive.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_generate_dataset.py`:

```python
from datetime import date


def test_build_origin_calendar_covers_full_range_with_valid_origins():
    start = date(2023, 9, 1)
    end = date(2026, 9, 1)
    calendar = gd.build_origin_calendar(seed=2026, start_date=start, end_date=end)

    expected_months = set()
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        expected_months.add((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    assert set(calendar.keys()) == expected_months

    for origins in calendar.values():
        assert 1 <= len(origins["regular"]) <= 2
        assert all(o in gd.ORIGINS for o in origins["regular"])
        assert origins["decaf"] in gd.ORIGINS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_generate_dataset.py -v`
Expected: FAIL with `AttributeError: module 'generate_dataset' has no attribute 'build_origin_calendar'`

- [ ] **Step 3: Write the implementation**

Append to `data/generate_dataset.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_generate_dataset.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data/generate_dataset.py tests/test_generate_dataset.py
git commit -m "Add monthly origin rotation calendar"
```

---

## Task 3: Lifecycle stage derivation

**Files:**
- Modify: `data/generate_dataset.py`
- Test: `tests/test_generate_dataset.py`

**Interfaces:**
- Produces: `derive_lifecycle_stage(total_orders: int, first_order_date: date | None, last_order_date: date | None, reference_date: date) -> str`, returning one of `"Lead"`, `"New Account"`, `"Active Account"`, `"Established Account"`, `"At-Risk"`, `"Churned"`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_generate_dataset.py`:

```python
from datetime import timedelta


def test_derive_lifecycle_stage_lead_has_zero_orders():
    ref = date(2026, 9, 9)
    assert gd.derive_lifecycle_stage(0, None, None, ref) == "Lead"


def test_derive_lifecycle_stage_new_account_within_90_days():
    ref = date(2026, 9, 9)
    first = ref - timedelta(days=30)
    assert gd.derive_lifecycle_stage(1, first, first, ref) == "New Account"


def test_derive_lifecycle_stage_new_account_takes_precedence_at_boundary():
    ref = date(2026, 9, 9)
    first_89 = ref - timedelta(days=89)
    assert gd.derive_lifecycle_stage(1, first_89, first_89, ref) == "New Account"
    first_90 = ref - timedelta(days=90)
    assert gd.derive_lifecycle_stage(1, first_90, first_90, ref) == "Active Account"


def test_derive_lifecycle_stage_established_requires_tenure_and_order_count():
    ref = date(2026, 9, 9)
    first = ref - timedelta(days=400)
    last = ref - timedelta(days=30)
    assert gd.derive_lifecycle_stage(8, first, last, ref) == "Established Account"
    assert gd.derive_lifecycle_stage(3, first, last, ref) == "Active Account"


def test_derive_lifecycle_stage_at_risk_and_churned_take_precedence_over_established():
    ref = date(2026, 9, 9)
    first = ref - timedelta(days=400)
    at_risk_last = ref - timedelta(days=200)
    churned_last = ref - timedelta(days=400)
    assert gd.derive_lifecycle_stage(8, first, at_risk_last, ref) == "At-Risk"
    assert gd.derive_lifecycle_stage(8, first, churned_last, ref) == "Churned"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_generate_dataset.py -v`
Expected: FAIL with `AttributeError: module 'generate_dataset' has no attribute 'derive_lifecycle_stage'`

- [ ] **Step 3: Write the implementation**

Append to `data/generate_dataset.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_generate_dataset.py -v`
Expected: PASS (all 6 tests so far)

- [ ] **Step 5: Commit**

```bash
git add data/generate_dataset.py tests/test_generate_dataset.py
git commit -m "Add lifecycle stage derivation with explicit precedence rules"
```

---

## Task 4: Customer shell generation

**Files:**
- Modify: `data/generate_dataset.py`
- Test: `tests/test_generate_dataset.py`

**Interfaces:**
- Produces: `build_customers(n: int, seed: int, start_date: date, end_date: date) -> list[dict]`, each dict with keys `customer_id, company_name, business_type, contact_first_name, contact_last_name, email, acquisition_channel, region, signup_date, email_opt_in`. Also produces module constants `BUSINESS_TYPES`, `REGIONS`, `BUSINESS_TYPE_PARAMS`-adjacent business_type list used by Task 5.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_generate_dataset.py`:

```python
def test_build_customers_produces_expected_shape_and_distribution():
    start = date(2023, 9, 1)
    end = date(2026, 9, 9)
    customers = gd.build_customers(500, seed=2026, start_date=start, end_date=end)

    assert len(customers) == 500
    assert len({c["customer_id"] for c in customers}) == 500
    assert all(c["email"].endswith("@example.com") for c in customers)
    assert all(start <= c["signup_date"] <= end for c in customers)
    assert all(c["region"] in gd.REGIONS for c in customers)
    assert all(c["business_type"] in gd.BUSINESS_TYPES for c in customers)
    assert all(c["email_opt_in"] in (0, 1) for c in customers)

    business_counts = {}
    for c in customers:
        business_counts[c["business_type"]] = business_counts.get(c["business_type"], 0) + 1
    # generous tolerance: this checks one random sample, not the RNG's long-run behavior
    assert abs(business_counts.get("restaurant", 0) / 500 - 0.40) < 0.08
    assert abs(business_counts.get("cafe", 0) / 500 - 0.30) < 0.08
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_generate_dataset.py -v`
Expected: FAIL with `AttributeError: module 'generate_dataset' has no attribute 'build_customers'`

- [ ] **Step 3: Write the implementation**

Append to `data/generate_dataset.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_generate_dataset.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data/generate_dataset.py tests/test_generate_dataset.py
git commit -m "Add wholesale customer shell generation"
```

---

## Task 5: Order-line generation

**Files:**
- Modify: `data/generate_dataset.py`
- Test: `tests/test_generate_dataset.py`

**Interfaces:**
- Consumes: `BUSINESS_TYPES` (Task 4), `build_origin_calendar` output shape (Task 2), `build_skus` output shape (Task 1).
- Produces: `build_orders(customers: list[dict], skus: list[dict], calendar: dict, seed: int, reference_date: date) -> list[dict]`, each dict with keys `order_id, customer_id, order_date, sku_id, quantity, unit_price, line_total`. Also produces module constant `BUSINESS_TYPE_PARAMS` used by validation/analysis later.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_generate_dataset.py`:

```python
def test_build_orders_respects_origin_calendar_and_business_type_ranges():
    start = date(2023, 9, 1)
    end = date(2026, 9, 9)
    skus = gd.build_skus()
    customers = gd.build_customers(50, seed=2026, start_date=start, end_date=end)
    calendar = gd.build_origin_calendar(seed=2026, start_date=start, end_date=end)
    orders = gd.build_orders(customers, skus, calendar, seed=2026, reference_date=end)

    assert len(orders) > 0
    sku_by_id = {s["sku_id"]: s for s in skus}
    customers_by_id = {c["customer_id"]: c for c in customers}

    for o in orders:
        sku = sku_by_id[o["sku_id"]]
        month_key = (o["order_date"].year, o["order_date"].month)
        active = (calendar[month_key]["regular"] if sku["roast_type"] == "regular"
                  else [calendar[month_key]["decaf"]])
        assert sku["origin"] in active

        cust = customers_by_id[o["customer_id"]]
        if sku["package_type"] == "wholesale":
            lo, hi = gd.BUSINESS_TYPE_PARAMS[cust["business_type"]]["bags_range"]
            assert lo <= o["quantity"] <= hi
        assert o["line_total"] == round(o["quantity"] * o["unit_price"], 2)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_generate_dataset.py -v`
Expected: FAIL with `AttributeError: module 'generate_dataset' has no attribute 'build_orders'`

- [ ] **Step 3: Write the implementation**

Append to `data/generate_dataset.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_generate_dataset.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data/generate_dataset.py tests/test_generate_dataset.py
git commit -m "Add order-line generation with business-type-driven frequency and origin rotation"
```

---

## Task 6: Aggregate computation

**Files:**
- Modify: `data/generate_dataset.py`
- Test: `tests/test_generate_dataset.py`

**Interfaces:**
- Consumes: `derive_lifecycle_stage` (Task 3).
- Produces: `compute_customer_aggregates(customers: list[dict], orders: list[dict], reference_date: date) -> list[dict]`, returning each input customer dict merged with `first_order_date, last_order_date, lifecycle_stage, total_orders, lifetime_value, avg_order_value`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_generate_dataset.py`:

```python
def test_compute_customer_aggregates_counts_distinct_orders_not_lines():
    ref = date(2026, 9, 9)
    customers = [{"customer_id": "WCUST-00001", "company_name": "Test Co"}]
    orders = [
        {"order_id": "ORD-000001", "customer_id": "WCUST-00001",
         "order_date": ref - timedelta(days=100), "sku_id": "REGULAR-COLOMBIA-WHOLESALE",
         "quantity": 5, "unit_price": 84.00, "line_total": 420.00},
        {"order_id": "ORD-000001", "customer_id": "WCUST-00001",
         "order_date": ref - timedelta(days=100), "sku_id": "REGULAR-COLOMBIA-RETAIL",
         "quantity": 2, "unit_price": 14.00, "line_total": 28.00},
        {"order_id": "ORD-000002", "customer_id": "WCUST-00001",
         "order_date": ref - timedelta(days=10), "sku_id": "DECAF-PERU-WHOLESALE",
         "quantity": 3, "unit_price": 93.00, "line_total": 279.00},
    ]
    enriched = gd.compute_customer_aggregates(customers, orders, ref)
    result = enriched[0]

    assert result["total_orders"] == 2  # two distinct order_ids, not three lines
    assert result["lifetime_value"] == 727.00
    assert result["avg_order_value"] == 363.50
    assert result["first_order_date"] == ref - timedelta(days=100)
    assert result["last_order_date"] == ref - timedelta(days=10)


def test_compute_customer_aggregates_handles_zero_orders():
    ref = date(2026, 9, 9)
    customers = [{"customer_id": "WCUST-00002", "company_name": "No Orders Yet"}]
    enriched = gd.compute_customer_aggregates(customers, [], ref)
    result = enriched[0]

    assert result["total_orders"] == 0
    assert result["lifecycle_stage"] == "Lead"
    assert result["first_order_date"] is None
    assert result["last_order_date"] is None
    assert result["lifetime_value"] == 0.0
    assert result["avg_order_value"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_generate_dataset.py -v`
Expected: FAIL with `AttributeError: module 'generate_dataset' has no attribute 'compute_customer_aggregates'`

- [ ] **Step 3: Write the implementation**

Append to `data/generate_dataset.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_generate_dataset.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data/generate_dataset.py tests/test_generate_dataset.py
git commit -m "Add order-derived aggregate computation and lifecycle assignment"
```

---

## Task 7: CSV writers + orchestration

**Files:**
- Modify: `data/generate_dataset.py`
- Test: `tests/test_generate_dataset.py`

**Interfaces:**
- Consumes: all functions from Tasks 1-6.
- Produces: `generate_dataset(n_customers=500, seed=SEED, out_dir=None) -> tuple[list[dict], list[dict], list[dict]]` (skus, customers, orders), plus module constants `SKU_FIELDS, CUSTOMER_FIELDS, ORDER_FIELDS` and a `write_csv(path, rows, fieldnames)` helper. This is what Task 8's validator and Task 9's real run both call.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_generate_dataset.py`:

```python
import csv as csv_module


def test_generate_dataset_writes_three_csvs(tmp_path):
    skus, customers, orders = gd.generate_dataset(n_customers=25, seed=2026, out_dir=tmp_path)

    assert (tmp_path / "skus.csv").exists()
    assert (tmp_path / "customers.csv").exists()
    assert (tmp_path / "orders.csv").exists()

    with open(tmp_path / "customers.csv", newline="") as f:
        rows = list(csv_module.DictReader(f))
    assert len(rows) == 25
    assert set(rows[0].keys()) == set(gd.CUSTOMER_FIELDS)

    with open(tmp_path / "skus.csv", newline="") as f:
        sku_rows = list(csv_module.DictReader(f))
    assert len(sku_rows) == 16
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_generate_dataset.py -v`
Expected: FAIL with `AttributeError: module 'generate_dataset' has no attribute 'generate_dataset'`

- [ ] **Step 3: Write the implementation**

Append to `data/generate_dataset.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_generate_dataset.py -v`
Expected: PASS (all tests in the file)

- [ ] **Step 5: Commit**

```bash
git add data/generate_dataset.py tests/test_generate_dataset.py
git commit -m "Add CSV writers and top-level dataset orchestration"
```

---

## Task 8: Validation script

**Files:**
- Create: `data/validate_dataset.py`
- Create: `tests/test_validate_dataset.py`

**Interfaces:**
- Consumes: `build_origin_calendar, SEED, START_DATE` from `data/generate_dataset.py` (Tasks 1-2).
- Produces: `check_referential_integrity(customers, orders, skus) -> list[str]`, `check_aggregates_match(customers, orders) -> list[str]`, `check_origin_calendar_integrity(orders, skus, calendar) -> list[str]`, `check_valid_categories(customers, skus) -> list[str]`, and a `main()` that loads the real CSVs, prints distributions, runs all checks, and exits nonzero on any problem.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_validate_dataset.py`:

```python
import validate_dataset as vd


def test_check_referential_integrity_flags_unknown_customer_and_sku():
    customers = [{"customer_id": "WCUST-00001"}]
    skus = [{"sku_id": "REGULAR-COLOMBIA-WHOLESALE"}]
    orders = [
        {"order_id": "ORD-000001", "customer_id": "WCUST-00001", "sku_id": "REGULAR-COLOMBIA-WHOLESALE"},
        {"order_id": "ORD-000002", "customer_id": "WCUST-99999", "sku_id": "REGULAR-COLOMBIA-WHOLESALE"},
        {"order_id": "ORD-000003", "customer_id": "WCUST-00001", "sku_id": "UNKNOWN-SKU"},
    ]
    problems = vd.check_referential_integrity(customers, orders, skus)
    assert len(problems) == 2
    assert any("WCUST-99999" in p for p in problems)
    assert any("UNKNOWN-SKU" in p for p in problems)


def test_check_referential_integrity_passes_clean_data():
    customers = [{"customer_id": "WCUST-00001"}]
    skus = [{"sku_id": "REGULAR-COLOMBIA-WHOLESALE"}]
    orders = [{"order_id": "ORD-000001", "customer_id": "WCUST-00001", "sku_id": "REGULAR-COLOMBIA-WHOLESALE"}]
    assert vd.check_referential_integrity(customers, orders, skus) == []


def test_check_aggregates_match_flags_mismatch():
    customers = [{"customer_id": "WCUST-00001", "total_orders": "1", "lifetime_value": "50.00"}]
    orders = [
        {"order_id": "ORD-000001", "customer_id": "WCUST-00001", "line_total": "84.00"},
        {"order_id": "ORD-000002", "customer_id": "WCUST-00001", "line_total": "14.00"},
    ]
    problems = vd.check_aggregates_match(customers, orders)
    assert len(problems) == 2


def test_check_aggregates_match_passes_correct_data():
    customers = [{"customer_id": "WCUST-00001", "total_orders": "2", "lifetime_value": "98.00"}]
    orders = [
        {"order_id": "ORD-000001", "customer_id": "WCUST-00001", "line_total": "84.00"},
        {"order_id": "ORD-000002", "customer_id": "WCUST-00001", "line_total": "14.00"},
    ]
    assert vd.check_aggregates_match(customers, orders) == []


def test_check_origin_calendar_integrity_flags_inactive_origin():
    calendar = {(2026, 8): {"regular": ["Peru", "Guatemala"], "decaf": "Peru"}}
    skus = [
        {"sku_id": "REGULAR-COLOMBIA-WHOLESALE", "roast_type": "regular", "origin": "Colombia"},
        {"sku_id": "DECAF-PERU-WHOLESALE", "roast_type": "decaf", "origin": "Peru"},
    ]
    orders = [
        {"order_id": "ORD-000001", "order_date": "2026-08-15", "sku_id": "REGULAR-COLOMBIA-WHOLESALE"},
        {"order_id": "ORD-000002", "order_date": "2026-08-15", "sku_id": "DECAF-PERU-WHOLESALE"},
    ]
    problems = vd.check_origin_calendar_integrity(orders, skus, calendar)
    assert len(problems) == 1
    assert "ORD-000001" in problems[0]


def test_check_valid_categories_flags_bad_business_type_and_wrong_sku_count():
    customers = [{"customer_id": "WCUST-00001", "business_type": "spaceship",
                  "region": "Los Angeles, CA", "lifecycle_stage": "Lead"}]
    skus = [{"sku_id": "X"}]  # only 1, not 16
    problems = vd.check_valid_categories(customers, skus)
    assert any("spaceship" in p for p in problems)
    assert any("expected 16 SKUs" in p for p in problems)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_validate_dataset.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'validate_dataset'`

- [ ] **Step 3: Write the implementation**

Create `data/validate_dataset.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_validate_dataset.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data/validate_dataset.py tests/test_validate_dataset.py
git commit -m "Add dataset validation script"
```

---

## Task 9: Generate the real dataset and verify

**Files:**
- Generate: `data/skus.csv`, `data/customers.csv`, `data/orders.csv`

- [ ] **Step 1: Run the full test suite**

Run: `pytest tests/ -v`
Expected: PASS (all tests across both test files)

- [ ] **Step 2: Generate the real 500-customer dataset**

Run: `python3 data/generate_dataset.py`
Expected output: `Wrote 16 SKUs, 500 customers, N order lines to .../data` (N will vary by run since it depends on `date.today()` — more elapsed time since Sept 2023 means more order lines)

- [ ] **Step 3: Run the validator against the real output**

Run: `python3 data/validate_dataset.py`
Expected: prints lifecycle stage / business type / region distributions, ends with `All checks passed: 500 customers, 16 skus, N order lines.` and exits 0. If any problems print, stop and fix the underlying generation logic (in `data/generate_dataset.py`) rather than patching the validator.

- [ ] **Step 4: Spot-check the distributions printed in Step 3**

Confirm: business type mix is roughly restaurant 40% / cafe 30% / hotel 15% / gym 15% (±5-8 points is fine, it's one random sample); region mix is roughly LA 22% / Bay Area 20% / NY 20% / Seattle 15% / Portland 10% / Austin 8% / Santa Barbara 5%; lifecycle stages include a mix of Lead, New Account, Active Account, Established Account, At-Risk, and Churned (not just one or two stages dominating).

- [ ] **Step 5: Commit the generated dataset**

```bash
git add data/skus.csv data/customers.csv data/orders.csv
git commit -m "Generate the 500-account coffee wholesale synthetic dataset"
```

## Verification

End-to-end: `pytest tests/ -v` (all unit tests pass) → `python3 data/generate_dataset.py` (writes the 3 real CSVs) → `python3 data/validate_dataset.py` (re-reads those exact files from disk and confirms zero integrity problems, prints distribution report) → manually skim `data/customers.csv` and `data/orders.csv` in a text editor or `csv.DictReader` to eyeball a few rows for plausibility (e.g., pick one `Established Account` row and confirm its `orders.csv` rows really do span 12+ months with 6+ distinct order_ids).
