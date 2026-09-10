"""
Covers reconcile()'s matching, value-map translation and fallback, and
source/target-only bucketing -- the generic engine behind
analysis/reconcile_hubspot.py's 45-of-500 finding.
"""
from reconcile_lifecycle import reconcile


def test_exact_match_without_value_map():
    matches, mismatches, source_only, target_only = reconcile(
        [{"id": "1", "stage": "customer"}],
        [{"id": "1", "status": "customer"}],
        key_field="id", source_value_field="stage", target_value_field="status",
    )
    assert len(matches) == 1
    assert mismatches == []


def test_mismatch_without_value_map():
    matches, mismatches, source_only, target_only = reconcile(
        [{"id": "1", "stage": "lead"}],
        [{"id": "1", "status": "customer"}],
        key_field="id", source_value_field="stage", target_value_field="status",
    )
    assert matches == []
    assert len(mismatches) == 1
    m = mismatches[0]
    assert (m.key, m.source_value, m.target_value) == ("1", "lead", "customer")


def test_value_map_translates_source_vocabulary_before_comparing():
    matches, mismatches, _, _ = reconcile(
        [{"id": "1", "stage": "Active Account"}],
        [{"id": "1", "status": "customer"}],
        key_field="id", source_value_field="stage", target_value_field="status",
        value_map={"Active Account": "customer"},
    )
    assert len(matches) == 1
    assert mismatches == []


def test_value_map_falls_back_to_raw_value_when_key_missing():
    """A source value absent from value_map compares against the target
    using its own raw value, not a KeyError."""
    matches, mismatches, _, _ = reconcile(
        [{"id": "1", "stage": "Trade"}],
        [{"id": "1", "status": "Trade"}],
        key_field="id", source_value_field="stage", target_value_field="status",
        value_map={"Lead": "lead"},
    )
    assert len(matches) == 1


def test_source_only_when_key_absent_from_target():
    matches, mismatches, source_only, target_only = reconcile(
        [{"id": "1", "stage": "lead"}],
        [],
        key_field="id", source_value_field="stage", target_value_field="status",
    )
    assert matches == mismatches == []
    assert source_only == ["1"]
    assert target_only == []


def test_target_only_when_key_absent_from_source():
    matches, mismatches, source_only, target_only = reconcile(
        [],
        [{"id": "1", "status": "customer"}],
        key_field="id", source_value_field="stage", target_value_field="status",
    )
    assert matches == mismatches == []
    assert target_only == ["1"]
    assert source_only == []


def test_mixed_batch_buckets_each_record_independently():
    source = [
        {"id": "1", "stage": "At-Risk"},   # mismatch (unmapped -> stays "At-Risk", target says "customer")
        {"id": "2", "stage": "Lead"},      # match, via value_map
        {"id": "3", "stage": "New Account"},  # source-only
    ]
    target = [
        {"id": "1", "status": "customer"},
        {"id": "2", "status": "lead"},
        {"id": "4", "status": "customer"},  # target-only
    ]
    matches, mismatches, source_only, target_only = reconcile(
        source, target, key_field="id", source_value_field="stage", target_value_field="status",
        value_map={"Lead": "lead"},
    )
    assert [m.key for m in matches] == ["2"]
    assert [m.key for m in mismatches] == ["1"]
    assert source_only == ["3"]
    assert target_only == ["4"]
