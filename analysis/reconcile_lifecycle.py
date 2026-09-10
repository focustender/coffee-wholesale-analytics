"""
Generic cross-system record reconciliation: diffs two lifecycle-bearing
record sets by a shared key and reports where they disagree.

Not specific to HubSpot, Shopify, or this project's schema. Copy this
function into any future project that needs to check whether a CRM's
recorded stage/status still matches what a source-of-truth dataset shows.
"""
from collections import namedtuple

Mismatch = namedtuple("Mismatch", ["key", "source_value", "target_value"])


def reconcile(source, target, key_field, source_value_field, target_value_field,
              value_map=None):
    """
    source, target: iterables of dict-likes representing records.
    key_field: field name present on both sides, used to join records.
    source_value_field / target_value_field: the field on each side to compare.
    value_map: optional dict translating a source value into the target's
        vocabulary before comparing (e.g. a 6-stage taxonomy collapsed into
        a CRM's smaller lifecyclestage set), so a "match" means true
        agreement rather than an artifact of differing vocabularies.

    Returns (matches, mismatches, source_only, target_only), each a list.
    matches/mismatches hold Mismatch namedtuples; source_only/target_only
    hold bare keys present on only one side.
    """
    source_by_key = {r[key_field]: r for r in source}
    target_by_key = {r[key_field]: r for r in target}

    matches, mismatches = [], []
    for key, s_rec in source_by_key.items():
        t_rec = target_by_key.get(key)
        if t_rec is None:
            continue
        s_val = s_rec[source_value_field]
        t_val = t_rec[target_value_field]
        mapped = value_map.get(s_val, s_val) if value_map else s_val
        record = Mismatch(key, s_val, t_val)
        (matches if mapped == t_val else mismatches).append(record)

    source_only = [k for k in source_by_key if k not in target_by_key]
    target_only = [k for k in target_by_key if k not in source_by_key]
    return matches, mismatches, source_only, target_only
