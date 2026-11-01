from scripts.restore_deletion_check import owner_counts_match


def test_owner_counts_require_exact_nonnegative_table_map():
    source = {"profiles": 2, "games": 11, "pilot_consents": 2}
    assert owner_counts_match(source, dict(source)) is True
    assert owner_counts_match(source, {**source, "games": 10}) is False
    assert owner_counts_match(source, {**source, "extra": 0}) is False
    assert owner_counts_match({}, {}) is False
