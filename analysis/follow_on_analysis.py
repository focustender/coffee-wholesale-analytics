"""
Follow-on EDA from the dataset design spec's last section:
cohort retention, order frequency/LTV by segment, origin seasonality,
growth vectors, and decaf vs regular mix by business type.

Run: python3 analysis/follow_on_analysis.py
"""

import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def load():
    customers = pd.read_csv(DATA_DIR / "customers.csv", parse_dates=[
        "signup_date", "first_order_date", "last_order_date"])
    orders = pd.read_csv(DATA_DIR / "orders.csv", parse_dates=["order_date"])
    skus = pd.read_csv(DATA_DIR / "skus.csv")
    orders = orders.merge(skus, on="sku_id", how="left")
    today = pd.Timestamp.today().normalize()
    return customers, orders, skus, today


def cohort_retention(customers, today):
    print("\n=== 1. Cohort retention (signup quarter -> current stage) ===")
    df = customers.copy()
    df["cohort_quarter"] = df["signup_date"].dt.to_period("Q")
    df["is_active_now"] = df["lifecycle_stage"].isin(["Active Account", "Established Account"])

    rows = []
    for q, group in df.groupby("cohort_quarter"):
        cohort_age_days = (today - q.end_time).days
        rows.append({
            "cohort_quarter": str(q),
            "cohort_size": len(group),
            "pct_active_or_established_now": round(group["is_active_now"].mean() * 100, 1),
            "pct_lead_now": round((group["lifecycle_stage"] == "Lead").mean() * 100, 1),
            "cohort_age_days": cohort_age_days,
            "old_enough_for_1yr_read": cohort_age_days >= 365,
        })
    out = pd.DataFrame(rows).sort_values("cohort_quarter")
    print(out.to_string(index=False))
    return out


def frequency_and_ltv_by_segment(customers, today):
    print("\n=== 2. Order frequency & LTV by business_type ===")
    converted = customers[customers["total_orders"] > 0].copy()
    converted["tenure_days"] = (today - converted["first_order_date"]).dt.days.clip(lower=1)
    converted["orders_per_month"] = converted["total_orders"] / (converted["tenure_days"] / 30.44)

    by_type = converted.groupby("business_type").agg(
        n=("customer_id", "count"),
        avg_total_orders=("total_orders", "mean"),
        avg_orders_per_month=("orders_per_month", "mean"),
        avg_lifetime_value=("lifetime_value", "mean"),
        avg_order_value=("avg_order_value", "mean"),
    ).round(2).sort_values("avg_lifetime_value", ascending=False)
    print(by_type.to_string())

    print("\n=== 2b. Order frequency & LTV by acquisition_channel ===")
    by_channel = converted.groupby("acquisition_channel").agg(
        n=("customer_id", "count"),
        avg_total_orders=("total_orders", "mean"),
        avg_lifetime_value=("lifetime_value", "mean"),
        avg_order_value=("avg_order_value", "mean"),
    ).round(2).sort_values("avg_lifetime_value", ascending=False)
    print(by_channel.to_string())
    return by_type, by_channel


def origin_seasonality(orders):
    print("\n=== 3. Origin popularity & monthly order-volume trend ===")
    origin_counts = orders["origin"].value_counts()
    print("Order-line share by origin:")
    print((origin_counts / origin_counts.sum() * 100).round(1).to_string())

    orders["month"] = orders["order_date"].dt.to_period("M")
    monthly = orders.groupby("month").size()
    print(f"\nMonthly order-line volume: min={monthly.min()}, max={monthly.max()}, "
          f"mean={monthly.mean():.0f}, std={monthly.std():.0f}")
    return origin_counts, monthly


def growth_vectors(customers):
    print("\n=== 4. Growth vectors: new-account creation rate over time ===")
    converted = customers[customers["total_orders"] > 0].copy()
    converted["cohort_month"] = converted["first_order_date"].dt.to_period("M")
    monthly_new = converted.groupby("cohort_month").size()
    print(f"New accounts/month: min={monthly_new.min()}, max={monthly_new.max()}, "
          f"mean={monthly_new.mean():.1f}")
    print("First 6 months:")
    print(monthly_new.head(6).to_string())
    print("Last 6 months:")
    print(monthly_new.tail(6).to_string())

    print("\nCurrent-snapshot stage mix (churn/at-risk share):")
    stage_counts = customers["lifecycle_stage"].value_counts()
    print((stage_counts / stage_counts.sum() * 100).round(1).to_string())
    return monthly_new, stage_counts


def decaf_mix_by_business_type(orders):
    print("\n=== 5. Decaf vs regular mix by business_type ===")
    merged = orders.merge(
        pd.read_csv(DATA_DIR / "customers.csv")[["customer_id", "business_type"]],
        on="customer_id", how="left"
    )
    mix = merged.groupby(["business_type", "roast_type"])["quantity"].sum().unstack(fill_value=0)
    mix_pct = mix.div(mix.sum(axis=1), axis=0) * 100
    print(mix_pct.round(1).to_string())
    return mix_pct


if __name__ == "__main__":
    customers, orders, skus, today = load()
    print(f"Reference date: {today.date()}")
    cohort_retention(customers, today)
    frequency_and_ltv_by_segment(customers, today)
    origin_seasonality(orders)
    growth_vectors(customers)
    decaf_mix_by_business_type(orders)
