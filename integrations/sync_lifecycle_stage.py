"""
Writes the real 6-stage lifecycle_stage (and a value tier derived from real
business_type economics) from customers.csv into two new HubSpot custom
properties, joined by wholesale_customer_id.

Why this has to happen before any retention segmentation can be built:
seed_hubspot.py only ever writes HubSpot's native lifecyclestage as "lead" or
"customer" (see its docstring) -- a deliberate mirror of how real portals
behave, where that field advances once and is never revisited. That means
HubSpot's own data literally cannot distinguish New/Active/Established/
At-Risk/Churned right now. analysis/reconcile_hubspot.py already found the
consequence: 45 of 500 contacts (9%) still read "customer" despite having
gone quiet or churned. Rather than build a retention campaign on a field
already proven stale, this script writes the accurate stage directly.

value_tier comes from analysis/follow_on_analysis.py's real finding:
avg lifetime_value by business_type is cafe $8,185, hotel $4,769,
restaurant $3,517, gym $1,113 -- cafe stands alone as a High tier, hotel and
restaurant cluster as Mid, gym is Low. This isn't a guess; it's the same cut
used in the retention campaign content (docs/reference/retention-campaign-content.md).

Run after integrations/seed_hubspot.py has populated the portal:
    python3 integrations/sync_lifecycle_stage.py
"""
import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import hubspot_client as hs

DATA_DIR = Path(__file__).parent.parent / "data"

VALUE_TIER = {
    "cafe": "High",
    "hotel": "Mid",
    "restaurant": "Mid",
    "gym": "Low",
}

CUSTOM_PROPERTIES = [
    ("wholesale_lifecycle_stage", "Wholesale Lifecycle Stage"),
    ("wholesale_value_tier", "Wholesale Value Tier"),
]


def load_customers():
    with open(DATA_DIR / "customers.csv", newline="") as f:
        return list(csv.DictReader(f))


def load_hubspot_contact_ids():
    """Maps wholesale_customer_id -> HubSpot contact id, for every contact
    already seeded. One paged listing call instead of 500 individual
    searches."""
    contacts = hs.list_all_contacts(properties=["wholesale_customer_id"])
    return {
        c["properties"]["wholesale_customer_id"]: c["id"]
        for c in contacts
        if c["properties"].get("wholesale_customer_id")
    }


def main():
    for name, label in CUSTOM_PROPERTIES:
        hs.create_property("contacts", name, label)
        print(f"Property ready: {name}")

    customers = load_customers()
    contact_ids = load_hubspot_contact_ids()
    print(f"{len(customers)} ground-truth customers, {len(contact_ids)} contacts live in HubSpot")

    updated, not_seeded = 0, 0
    for cust in customers:
        contact_id = contact_ids.get(cust["customer_id"])
        if not contact_id:
            not_seeded += 1
            continue

        hs.update_contact(contact_id, {
            "wholesale_lifecycle_stage": cust["lifecycle_stage"],
            "wholesale_value_tier": VALUE_TIER[cust["business_type"]],
        })
        updated += 1
        if updated % 50 == 0:
            print(f"  ...{updated} updated")
        time.sleep(0.1)  # stay well under HubSpot's per-10-second rate limit

    print(f"Done. Updated {updated} contacts, {not_seeded} ground-truth customers not yet in HubSpot.")


if __name__ == "__main__":
    main()
