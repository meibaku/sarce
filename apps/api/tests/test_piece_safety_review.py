"""Independent annotation and automatic-serving gates for LE2 piece safety."""

from app.services.pattern_review import cohen_kappa, review_report


def row(status: str, first: str, second: str, review_set: str = "heldout") -> dict:
    return {
        "review_set": review_set,
        "review_status": status,
        "review_annotations": [{"decision": first}, {"decision": second}],
    }


def test_kappa_and_precision_preserve_disagreement():
    rows = [row("approved", "approve", "approve"), row("rejected", "approve", "reject"), row("rejected", "reject", "reject")]
    report = review_report(rows)
    assert report["precision"] == 1 / 3
    assert report["rawAgreement"] == 2 / 3
    assert round(report["cohenKappa"], 6) == 0.4
    assert report["autoServeReady"] is False


def test_automatic_serving_requires_sample_and_precision():
    ready = review_report([row("approved", "approve", "approve") for _ in range(50)])
    assert ready["autoServeReady"] is True
    assert ready["mandatoryHumanReviewCanEnd"] is True
    too_small = review_report([row("approved", "approve", "approve") for _ in range(49)])
    assert too_small["autoServeReady"] is False


def test_calibration_rows_never_count_toward_heldout_gate():
    report = review_report([row("approved", "approve", "approve", "calibration") for _ in range(60)])
    assert report["heldout"] == 0 and report["precision"] is None


def test_empty_kappa_is_explicitly_unknown():
    assert cohen_kappa([]) == (None, None)
