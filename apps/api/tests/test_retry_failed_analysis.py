"""Operator retries must be complete and must not erase a newer failure."""

from types import SimpleNamespace

from scripts import retry_failed_analysis as retry


class RetryStore:
    def __init__(self, rows: list[dict]):
        self.rows = rows

    def table(self, _name):
        self.filters, self.bounds, self.values = [], None, None
        return self

    def select(self, *_args):
        return self

    def update(self, values):
        self.values = values
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def is_(self, column, value):
        self.filters.append((column, None if value == "null" else value))
        return self

    def order(self, *_args):
        return self

    def range(self, start, end):
        self.bounds = (start, end)
        return self

    def execute(self):
        matches = [row for row in self.rows if all(row.get(column) == value for column, value in self.filters)]
        if self.values is not None:
            for row in matches:
                row.update(self.values)
            return SimpleNamespace(data=[{"id": row["id"]} for row in matches])
        start, end = self.bounds or (0, len(matches) - 1)
        return SimpleNamespace(data=[dict(row) for row in matches[start : end + 1]])


def failed_row(index: int) -> dict:
    return {
        "id": f"g{index:04d}",
        "played_at": f"2026-01-{index % 28 + 1:02d}",
        "analysis_status": "failed",
        "analysis_attempts": 3,
        "analysis_error": "TimeoutError: bounded",
        "analysis_failed_at": f"2026-10-25T00:{index % 60:02d}:00+00:00",
    }


def test_candidates_paginates_past_postgrest_default(monkeypatch):
    store = RetryStore([failed_row(index) for index in range(1003)])
    monkeypatch.setattr(retry, "get_supabase", lambda: store)
    assert len(retry.candidates(None)) == 1003


def test_requeue_skips_a_failure_that_changed_after_preview(monkeypatch):
    rows = [failed_row(1), failed_row(2)]
    store = RetryStore(rows)
    monkeypatch.setattr(retry, "get_supabase", lambda: store)
    selected = retry.candidates(None)
    rows[1]["analysis_failed_at"] = "2026-10-26T01:00:00+00:00"

    assert retry.requeue(selected) == 1
    assert rows[0]["analysis_status"] == "pending"
    assert rows[1]["analysis_status"] == "failed" and rows[1]["analysis_attempts"] == 3
