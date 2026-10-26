"""Pilot readiness stays fail-closed until every evidence source is present."""

from app.services.learning_readiness import REQUIRED_BANK, readiness_report


def test_readiness_requires_every_external_and_bank_gate():
    ready = readiness_report(
        review={"autoServeReady": True, "mandatoryHumanReviewCanEnd": True},
        bank=REQUIRED_BANK, phase1_merged=True, greptile_score=5,
        local_ci_passed=True, staging_url="https://sarce-api-staging.example",
    )
    assert ready["readyForInvitedPilot"] is True
    assert ready["blockers"] == []


def test_missing_evidence_is_a_named_blocker_not_a_soft_pass():
    blocked = readiness_report(
        review={}, bank={"baseline": 17}, phase1_merged=False, greptile_score=0,
        local_ci_passed=True, staging_url=None,
    )
    assert blocked["decision"] == "blocked"
    assert "phase1MergedToStaging" in blocked["blockers"]
    assert "greptileFiveOfFive" in blocked["blockers"]
    assert "approvedBank" in blocked["blockers"]
