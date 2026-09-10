"""
Generates the three charts used on the site's Coffee Wholesale Analytics
project page, straight from customers.csv -- no manually re-typed numbers.
Matches the visual style already established by the Subscription Economics
project's charts (steelblue bars, tab:orange accent, white background,
light horizontal gridlines only).

Run: python3 analysis/generate_charts.py
Outputs to analysis/output/charts/, then copy into
~/focustender/focustenderPages/assets/photos/ for the site build.
"""
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
OUT_DIR = Path(__file__).parent / "output" / "charts"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BLUE = "steelblue"
ORANGE = "darkorange"
GRAY = "#b0b0b0"


def _clean_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)


def chart_ltv_by_business_type(customers):
    by_type = customers.groupby("business_type")["lifetime_value"].mean().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    bars = ax.bar(by_type.index.str.title(), by_type.values, color=BLUE, width=0.55)
    for bar, val in zip(bars, by_type.values):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 120, f"${val:,.0f}",
                 ha="center", va="bottom", fontsize=10)
    ax.set_ylabel("Average lifetime value ($)")
    ax.set_title("Average lifetime value by business type")
    _clean_axes(ax)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "coffeeWholesaleLtvByType.png", dpi=150)
    plt.close(fig)


def chart_reconciliation(customers):
    order = ["Lead", "New Account", "Active Account", "Established Account", "At-Risk", "Churned"]
    counts = customers["lifecycle_stage"].value_counts().reindex(order)
    stale = {"At-Risk", "Churned"}
    colors = [ORANGE if stage in stale else BLUE for stage in order]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    bars = ax.bar(order, counts.values, color=colors, width=0.6)
    for bar, val in zip(bars, counts.values):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 3, str(val), ha="center", va="bottom", fontsize=10)
    ax.set_ylabel("Accounts")
    ax.set_title('HubSpot\'s "lifecyclestage" is accurate for 4 of 6 stages, stale for 2')
    ax.set_xticklabels(order, rotation=20, ha="right")

    from matplotlib.patches import Patch
    ax.legend(handles=[
        Patch(color=BLUE, label="HubSpot reads correctly"),
        Patch(color=ORANGE, label='HubSpot still reads "customer" (stale)'),
    ], frameon=False, loc="upper right")

    _clean_axes(ax)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "coffeeWholesaleReconciliation.png", dpi=150)
    plt.close(fig)


def chart_at_risk_concentration(customers):
    at_risk = customers[customers["lifecycle_stage"] == "At-Risk"]
    by_type = at_risk.groupby("business_type").agg(n=("customer_id", "count"),
                                                     ltv=("lifetime_value", "sum"))
    by_type["pct_count"] = 100 * by_type["n"] / by_type["n"].sum()
    by_type["pct_ltv"] = 100 * by_type["ltv"] / by_type["ltv"].sum()
    by_type = by_type.sort_values("pct_ltv", ascending=False)

    x = range(len(by_type))
    width = 0.35
    fig, ax = plt.subplots(figsize=(10, 5.5))
    b1 = ax.bar([i - width / 2 for i in x], by_type["pct_count"], width, label="% of At-Risk accounts", color=BLUE)
    b2 = ax.bar([i + width / 2 for i in x], by_type["pct_ltv"], width, label="% of At-Risk revenue", color=ORANGE)
    for bars in (b1, b2):
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.8, f"{h:.1f}%", ha="center", va="bottom", fontsize=9)

    ax.set_xticks(list(x))
    ax.set_xticklabels([t.title() for t in by_type.index])
    ax.set_ylabel("Share of the At-Risk segment (%)")
    ax.set_title("Not every At-Risk account is worth the same response")
    ax.legend(frameon=False, loc="upper right")
    _clean_axes(ax)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "coffeeWholesaleAtRiskConcentration.png", dpi=150)
    plt.close(fig)


def main():
    customers = pd.read_csv(DATA_DIR / "customers.csv")
    chart_ltv_by_business_type(customers)
    chart_reconciliation(customers)
    chart_at_risk_concentration(customers)
    print(f"3 charts written to {OUT_DIR}")


if __name__ == "__main__":
    main()
