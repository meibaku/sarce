"""Closeout benchmark checkpoint behavior."""

from scripts.benchmark_brilliant_v3 import ordered_checkpoint_results


def test_checkpoint_results_restore_sample_order_and_ignore_other_rows():
    identities = [("first", "1950.01.01"), ("second", "1951.01.01")]
    saved = {
        "second": {"result": {"moves": 2}, "engineVersion": "Stockfish 19"},
        "unrelated": {"result": {"moves": 99}, "engineVersion": "Stockfish 18"},
        "first": {"result": {"moves": 1}, "engineVersion": "Stockfish 19"},
    }

    results, engines = ordered_checkpoint_results(identities, saved)

    assert results == [{"moves": 1}, {"moves": 2}]
    assert engines == {"Stockfish 19"}
