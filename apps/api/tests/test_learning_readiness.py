"""Pilot readiness stays fail-closed until every evidence source is present."""

from app.services.learning_readiness import REQUIRED_BANK, readiness_report


def test_readiness_requires_every_external_and_bank_gate():
    ready = readiness_report(
        review={"autoServeReady": True, "mandatoryHumanReviewCanEnd": True},
        bank=REQUIRED_BANK, phase1_merged=True,
        coderabbit_review_passed=True, codex_review_passed=True,
        local_ci_passed=True, staging_url="https://sarce-api-staging.example",
    )
    assert ready["readyForInvitedPilot"] is True
    assert ready["blockers"] == []


def test_missing_evidence_is_a_named_blocker_not_a_soft_pass():
    blocked = readiness_report(
        review={}, bank={"baseline": 17}, phase1_merged=False,
        coderabbit_review_passed=False, codex_review_passed=False,
        local_ci_passed=True, staging_url=None,
    )
    assert blocked["decision"] == "blocked"
    assert "phase1MergedToStaging" in blocked["blockers"]
    assert "codeRabbitReviewPassed" in blocked["blockers"]
    assert "codexReviewPassed" in blocked["blockers"]
    assert "approvedBank" in blocked["blockers"]
