"""
Builds the real retention-campaign segments by reading them back live from
HubSpot (not just computing them locally), joining wholesale_lifecycle_stage
and wholesale_value_tier -- written by integrations/sync_lifecycle_stage.py
-- against customers.csv's lifetime_value for the dollar stats.

Reading segment membership back from the live portal, rather than trusting
the local CSV alone, is the point: it's what actually proves these are real,
queryable segments in the real system, not a spreadsheet exercise. Any
ground-truth customer not found live in HubSpot is reported, not silently
dropped -- same discipline as analysis/reconcile_hubspot.py.

Retention-relevant stages only (New/Active/Established/At-Risk/Churned).
Lead is deliberately excluded: that's an acquisition problem, a different
project. See docs/reference/retention-campaign-content.md for the actual
campaign copy these segments feed.

Run after integrations/sync_lifecycle_stage.py:
    python3 analysis/segment_retention_campaigns.py
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "integrations"))
import hubspot_client as hs

DATA_DIR = Path(__file__).parent.parent / "data"

RETENTION_STAGES = ["New Account", "Active Account", "Established Account", "At-Risk", "Churned"]


def load_ground_truth():
    with open(DATA_DIR / "customers.csv", newline="") as f:
        return {row["customer_id"]: row for row in csv.DictReader(f)}


def load_live_segments():
    """wholesale_customer_id -> live HubSpot properties, for every contact
    the sync script successfully tagged."""
    contacts = hs.list_all_contacts(properties=[
        "wholesale_customer_id", "wholesale_lifecycle_stage", "wholesale_value_tier",
        "company", "business_type",
    ])
    return {
        c["properties"]["wholesale_customer_id"]: c["properties"]
        for c in contacts
        if c["properties"].get("wholesale_customer_id") and c["properties"].get("wholesale_lifecycle_stage")
    }


def main():
    ground_truth = load_ground_truth()
    live = load_live_segments()
    not_live = [cid for cid in ground_truth if cid not in live]
    print(f"{len(ground_truth)} ground-truth customers, {len(live)} confirmed live in HubSpot "
          f"with a synced lifecycle stage.")
    if not_live:
        print(f"{len(not_live)} not found live -- excluded from every segment below, not silently included.\n")

    print("=== Retention segments (live-confirmed membership) ===")
    for stage in RETENTION_STAGES:
        member_ids = [cid for cid, props in live.items() if props["wholesale_lifecycle_stage"] == stage]
        members = [ground_truth[cid] for cid in member_ids]
        total_ltv = sum(float(m["lifetime_value"]) for m in members)
        examples = [live[cid]["company"] for cid in member_ids[:3]]
        print(f"\n{stage}: {len(members)} accounts, ${total_ltv:,.0f} combined lifetime value")
        print(f"  live examples: {', '.join(examples) if examples else '(none)'}")

    print("\n=== Flagship segment: At-Risk x cafe (High value tier) ===")
    at_risk_ids = [cid for cid, props in live.items() if props["wholesale_lifecycle_stage"] == "At-Risk"]
    at_risk = [ground_truth[cid] for cid in at_risk_ids]
    at_risk_cafe_ids = [cid for cid in at_risk_ids if live[cid]["business_type"] == "cafe"]
    at_risk_cafe = [ground_truth[cid] for cid in at_risk_cafe_ids]

    at_risk_ltv = sum(float(m["lifetime_value"]) for m in at_risk)
    cafe_ltv = sum(float(m["lifetime_value"]) for m in at_risk_cafe)
    pct_count = 100 * len(at_risk_cafe) / len(at_risk) if at_risk else 0
    pct_ltv = 100 * cafe_ltv / at_risk_ltv if at_risk_ltv else 0

    print(f"At-Risk total: {len(at_risk)} accounts, ${at_risk_ltv:,.0f} combined lifetime value")
    print(f"At-Risk cafes: {len(at_risk_cafe)} accounts ({pct_count:.1f}% of at-risk count), "
          f"${cafe_ltv:,.0f} combined lifetime value ({pct_ltv:.1f}% of at-risk revenue)")
    print(f"live examples: {', '.join(live[cid]['company'] for cid in at_risk_cafe_ids[:5])}")


if __name__ == "__main__":
    main()
