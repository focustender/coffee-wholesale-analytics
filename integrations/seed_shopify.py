"""
Seeds the synthetic coffee wholesale customers into a real Shopify dev store
as Customers, via the custom-app-token client in shopify_client.py.

Run once SHOPIFY_STORE_DOMAIN / SHOPIFY_ACCESS_TOKEN are set (see
docs/reference/shopify-api-setup.md):
    python3 integrations/seed_shopify.py

Safe to re-run: skips any email already present in the store.

Order-line seeding is intentionally out of scope here: Shopify's Admin API
requires a checkout or draft-order-complete to produce a real Order object,
which doesn't fit a scripted bulk-seed the way a plain object-create does.
Customer + segment tagging is the useful, achievable slice for this project.
"""
import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import shopify_client as sc

DATA_DIR = Path(__file__).parent.parent / "data"


def load_customers():
    with open(DATA_DIR / "customers.csv", newline="") as f:
        return list(csv.DictReader(f))


def main():
    customers = load_customers()
    print(f"Loaded {len(customers)} customers from {DATA_DIR / 'customers.csv'}")

    created, skipped = 0, 0
    for cust in customers:
        if sc.find_customer_by_email(cust["email"]):
            skipped += 1
            continue

        sc.create_customer(
            email=cust["email"],
            first_name=cust["contact_first_name"],
            last_name=cust["contact_last_name"],
            tags=[cust["business_type"], cust["region"]],
            note=f"{cust['company_name']} -- synthetic wholesale account",
            metafields=[{
                "namespace": "wholesale",
                "key": "customer_id",
                "value": cust["customer_id"],
                "type": "single_line_text_field",
            }],
        )
        created += 1
        if created % 25 == 0:
            print(f"  ...{created} created")
        time.sleep(0.3)  # stay under the GraphQL cost-based rate limit

    print(f"Done. Created {created}, skipped {skipped} already-present customers.")


if __name__ == "__main__":
    main()
