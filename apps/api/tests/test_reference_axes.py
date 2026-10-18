import json

from app.services import reference_axes
from app.services.reference_axes import axis_values


def test_axis_values_scale_traits_onto_0_100():
    axes = axis_values({"Sacrifice": 0.034, "Chaos": 0.2, "Calm": 0.9, "Initiative": 0.7, "Defence": 0.5})
    assert axes == {"Sacrifice rate": 3, "Chaos created": 20, "Calm under fire": 90, "Initiative kept": 100}
    assert axis_values({})["Chaos created"] is None


def test_references_reads_the_file_or_returns_nothing(tmp_path, monkeypatch):
    path = tmp_path / "reference_axes.json"
    monkeypatch.setattr(reference_axes, "PATH", path)
    reference_axes.references.cache_clear()
    assert reference_axes.references() == {}
    path.write_text(json.dumps({"Tal": {"games": 3, "axes": {"Chaos created": 41}}}))
    reference_axes.references.cache_clear()
    assert reference_axes.references()["Tal"]["axes"]["Chaos created"] == 41
    reference_axes.references.cache_clear()


def test_extract_pgns_splits_crlf_corpus(tmp_path):
    import zipfile

    from app.services.reference import ReferenceService

    game = '[Event "a"]\r\n[White "Tal, Mikhail"]\r\n\r\n1. e4 e5 1-0\r\n\r\n'
    path = tmp_path / "Tal.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("Tal.pgn", game * 3)
    assert len(ReferenceService._extract_pgns(path, 10)) == 3
