from scripts.pilot_report import build_report, pseudonym


def feedback(user, count, yes):
    answers = ["yes"] * yes + ["partly"] * (count - yes)
    return [
        {"id": f"{user}-{index}", "user_id": user, "resonance": answer, "created_at": f"2026-11-{index + 1:02d}T00:00:00Z"}
        for index, answer in enumerate(answers)
    ]


def test_report_uses_each_participants_first_ten_and_predeclared_thresholds():
    consents = [
        {"user_id": "a"},
        {"user_id": "b"},
        {"user_id": "withdrawn", "withdrawn_at": "2026-11-15T00:00:00Z"},
    ]
    rows = feedback("a", 11, 8) + feedback("b", 10, 6) + feedback("withdrawn", 3, 3)
    surveys = [
        {"user_id": "a", "continue_using": "yes", "submitted_at": "2026-11-20T00:00:00Z"},
        {"user_id": "b", "continue_using": "no", "submitted_at": "2026-11-20T00:00:00Z"},
    ]
    report = build_report(consents, rows, surveys, "2026-11-30T00:00:00Z", "salt")
    assert report["summary"]["completeParticipants"] == 2
    assert report["summary"]["medianFeelsLikeMeRate"] == 0.7
    assert report["summary"]["continueFraction"] == 0.5
    assert report["summary"]["resonanceThresholdMet"] is True
    assert report["summary"]["continueThresholdMet"] is True
    assert report["participants"][0]["reads"] == 10
    assert report["participants"][0]["answers"] == {"yes": 8, "partly": 2, "no": 0}
    assert report["participants"][0]["wilson95"]["low"] < 0.8


def test_report_pseudonyms_do_not_expose_ids():
    value = pseudonym("private-user-id", "secret-salt")
    assert value == pseudonym("private-user-id", "secret-salt")
    assert "private-user-id" not in value
