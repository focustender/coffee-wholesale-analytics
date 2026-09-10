"""
Seeds the synthetic coffee wholesale customers into a real HubSpot portal as
Contacts, via the private-app-token client in hubspot_client.py.

Run once HUBSPOT_ACCESS_TOKEN is set (see docs/reference/hubspot-api-setup.md):
    python3 integrations/seed_hubspot.py

Safe to re-run: skips any email already present in the portal.
"""
import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import hubspot_client as hs

DATA_DIR = Path(__file__).parent.parent / "data"

CUSTOM_PROPERTIES = [
    ("business_type", "Business Type"),
    ("acquisition_channel", "Acquisition Channel"),
    ("wholesale_customer_id", "Wholesale Customer ID"),
]


def _region_to_city_state(region):
    city, _, state = region.partition(",")
    return city.strip(), state.strip()


def _lifecyclestage_heuristic(total_orders):
    """
    Mirrors how a real sales/marketing team typically maintains lifecyclestage
    in practice: it advances forward on first sale and is rarely revisited
    after, so it never reflects churn or at-risk status the way this
    project's order-derived ground truth (customers.csv's lifecycle_stage)
    does. That gap is exactly what analysis/reconcile_hubspot.py surfaces.
    """
    return "lead" if int(total_orders) == 0 else "customer"


def load_customers():
    with open(DATA_DIR / "customers.csv", newline="") as f:
        return list(csv.DictReader(f))


def main():
    for name, label in CUSTOM_PROPERTIES:
        hs.create_property("contacts", name, label)
        print(f"Property ready: {name}")

    customers = load_customers()
    print(f"Loaded {len(customers)} customers from {DATA_DIR / 'customers.csv'}")

    created, skipped = 0, 0
    for cust in customers:
        if hs.find_contact_by_email(cust["email"], properties=["email"]):
            skipped += 1
            continue

        city, state = _region_to_city_state(cust["region"])
        properties = {
            "email": cust["email"],
            "firstname": cust["contact_first_name"],
            "lastname": cust["contact_last_name"],
            "company": cust["company_name"],
            "city": city,
            "state": state,
            "business_type": cust["business_type"],
            "acquisition_channel": cust["acquisition_channel"],
            "wholesale_customer_id": cust["customer_id"],
            "lifecyclestage": _lifecyclestage_heuristic(cust["total_orders"]),
        }
        hs.create_contact(properties)
        created += 1
        if created % 25 == 0:
            print(f"  ...{created} created")
        time.sleep(0.1)  # stay well under HubSpot's per-10-second rate limit

    print(f"Done. Created {created}, skipped {skipped} already-present contacts.")


if __name__ == "__main__":
    main()
