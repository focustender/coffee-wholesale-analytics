"""
Applies reconcile_lifecycle.reconcile() to a real question: does HubSpot's
lifecyclestage still reflect reality, once accounts have been in the system
long enough to churn or go quiet?

Ground truth is customers.csv's lifecycle_stage, recomputed fresh from actual
order history every time the dataset regenerates. HubSpot's lifecyclestage
was set once at seed time by a simple heuristic (see
integrations/seed_hubspot.py) that only ever writes "lead" or "customer" --
which is how most real HubSpot portals actually behave, since lifecyclestage
usually advances forward on a sale and isn't revisited afterward.

Run after integrations/seed_hubspot.py has populated the portal:
    python3 analysis/reconcile_hubspot.py
"""
import csv
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "integrations"))
import hubspot_client as hs
from reconcile_lifecycle import reconcile

DATA_DIR = Path(__file__).parent.parent / "data"

# Only map the stages HubSpot's "lead"/"customer" heuristic actually gets
# right: an account that has ordered at all is genuinely a customer while
# it's New/Active/Established. At-Risk and Churned are deliberately left
# unmapped -- HubSpot's lifecyclestage never gets revisited after the first
# sale, so it still reads "customer" for these accounts even though they've
# gone quiet or dropped off, and that gap is exactly the finding this script
# is built to surface.
STAGE_MAP = {
    "Lead": "lead",
    "New Account": "customer",
    "Active Account": "customer",
    "Established Account": "customer",
}


def load_ground_truth():
    with open(DATA_DIR / "customers.csv", newline="") as f:
        return list(csv.DictReader(f))


def load_hubspot_contacts():
    contacts = hs.list_all_contacts(properties=["email", "lifecyclestage", "wholesale_customer_id"])
    return [
        {"customer_id": c["properties"].get("wholesale_customer_id"),
         "lifecyclestage": c["properties"].get("lifecyclestage")}
        for c in contacts if c["properties"].get("wholesale_customer_id")
    ]


def main():
    ground_truth = load_ground_truth()
    hubspot_contacts = load_hubspot_contacts()
    print(f"{len(ground_truth)} ground-truth customers, {len(hubspot_contacts)} matched HubSpot contacts")

    matches, mismatches, source_only, _ = reconcile(
        ground_truth, hubspot_contacts,
        key_field="customer_id",
        source_value_field="lifecycle_stage",
        target_value_field="lifecyclestage",
        value_map=STAGE_MAP,
    )

    total = len(matches) + len(mismatches)
    rate = len(mismatches) / total * 100 if total else 0
    print(f"\n{len(mismatches)} of {total} contacts ({rate:.1f}%) have a stale HubSpot lifecyclestage.")

    breakdown = Counter(m.source_value for m in mismatches)
    print("\nMismatches by true stage:")
    for stage, count in breakdown.most_common():
        print(f"  {stage}: {count}")

    if source_only:
        print(f"\n{len(source_only)} ground-truth customers not yet seeded into HubSpot.")


if __name__ == "__main__":
    main()
