"""
Covers derive_lifecycle_stage's six-branch precedence logic, including the
boundary interaction documented (but previously untested) in
docs/superpowers/specs/2026-09-09-coffee-wholesale-synthetic-dataset-design.md:
an account within 90 days of its first order also trivially satisfies
Active Account's looser condition, but New Account takes precedence.
"""
from datetime import date, timedelta

from generate_dataset import derive_lifecycle_stage

REF = date(2026, 1, 1)


def _days_ago(n):
    return REF - timedelta(days=n)


def test_zero_orders_is_lead():
    assert derive_lifecycle_stage(0, None, None, REF) == "Lead"


def test_new_account_just_inside_90_days():
    assert derive_lifecycle_stage(1, _days_ago(89), _days_ago(89), REF) == "New Account"


def test_new_account_precedence_over_active():
    """The documented boundary case: a fresh account's last order is also
    recent enough to satisfy Active Account's condition, but New Account
    (evaluated first) must still win."""
    assert derive_lifecycle_stage(1, _days_ago(1), _days_ago(1), REF) == "New Account"


def test_active_account_at_exactly_90_days_tenure():
    """90 days is not < 90, so New Account no longer applies; falls through
    to Active Account since Established's 365-day tenure floor isn't met."""
    assert derive_lifecycle_stage(1, _days_ago(90), _days_ago(0), REF) == "Active Account"


def test_active_account_at_exactly_180_days_since_last_order():
    """180 is not > 180, so At-Risk doesn't apply; stays Active."""
    assert derive_lifecycle_stage(3, _days_ago(400), _days_ago(180), REF) == "Active Account"


def test_at_risk_at_181_days_since_last_order():
    assert derive_lifecycle_stage(3, _days_ago(400), _days_ago(181), REF) == "At-Risk"


def test_at_risk_at_exactly_365_days_since_last_order():
    """365 is not > 365, so Churned doesn't apply; still At-Risk."""
    assert derive_lifecycle_stage(3, _days_ago(500), _days_ago(365), REF) == "At-Risk"


def test_churned_at_366_days_since_last_order():
    assert derive_lifecycle_stage(3, _days_ago(500), _days_ago(366), REF) == "Churned"


def test_established_requires_both_tenure_and_order_count():
    assert derive_lifecycle_stage(6, _days_ago(365), _days_ago(10), REF) == "Established Account"


def test_active_when_tenure_meets_365_but_orders_below_6():
    assert derive_lifecycle_stage(5, _days_ago(400), _days_ago(10), REF) == "Active Account"


def test_active_when_orders_meet_6_but_tenure_below_365():
    assert derive_lifecycle_stage(6, _days_ago(364), _days_ago(10), REF) == "Active Account"


def test_churned_takes_precedence_over_established_criteria():
    """A long-tenured, high-order account that's gone quiet is Churned, not
    Established -- recency rules are checked before the tenure/order rule."""
    assert derive_lifecycle_stage(10, _days_ago(900), _days_ago(400), REF) == "Churned"
