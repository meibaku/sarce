from scripts.pilot_ops_check import memory_used_percent, recent_5xx


def test_memory_percentage_uses_available_memory():
    assert memory_used_percent("MemTotal: 1000 kB\nMemAvailable: 250 kB\n") == 75.0


def test_recent_5xx_ignores_bad_lines_and_counts_server_errors(tmp_path):
    log = tmp_path / "access.json"
    log.write_text(
        '{"status":200}\nnot-json\n{"status":503}\n{"status":404}\n{"status":500}\n',
        encoding="utf-8",
    )
    assert recent_5xx(log) == 2
    assert recent_5xx(tmp_path / "missing.json") == 0
