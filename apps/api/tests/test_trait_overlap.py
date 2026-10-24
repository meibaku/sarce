"""Trait overlap check (scripts/trait_overlap.py, review F10a)."""

from scripts.trait_overlap import matrix, pearson, spread


def test_pearson():
    assert round(pearson([1, 2, 3, 4], [2, 4, 6, 8]), 6) == 1.0
    assert round(pearson([1, 2, 3, 4], [8, 6, 4, 2]), 6) == -1.0
    assert pearson([1, 2], [1, 2]) is None and pearson([1, 1, 1], [1, 2, 3]) is None


def test_matrix_skips_windows_where_a_trait_is_dashed():
    windows = [{"Chaos": c, "Initiative": c / 2, "Fight": f} for c, f in [(0.1, None), (0.2, 0.3), (0.3, 0.1), (0.4, 0.2)]]
    m = matrix(windows)
    r, n = m[("Chaos", "Initiative")]
    assert round(r, 6) == 1.0 and n == 4
    assert m[("Chaos", "Fight")][1] == 3
    assert spread(windows)["Fight"] == {"n": 3, "min": 0.1, "median": 0.2, "max": 0.3}
