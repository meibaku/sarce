"""Fail-closed pilot-readiness decision assembled from review, bank and delivery evidence."""

from __future__ import annotations

REQUIRED_BANK = {"baseline": 18, "instruction": 4, "immediate": 9, "day7": 18, "day28": 18}


def readiness_report(
    *, review: dict, bank: dict[str, int], phase1_merged: bool, greptile_score: int,
    local_ci_passed: bool, staging_url: str | None,
) -> dict:
    """Return explicit blockers; absence of evidence is never interpreted as ready."""
    bank_gates = {
        partition: {"approvedFamilies": int(bank.get(partition, 0)), "required": required,
                    "passed": int(bank.get(partition, 0)) >= required}
        for partition, required in REQUIRED_BANK.items()
    }
    gates = {
        "phase1MergedToStaging": phase1_merged,
        "greptileFiveOfFive": greptile_score == 5,
        "localCiPassed": local_ci_passed,
        "stagingDeployed": bool(staging_url),
        "reviewedPrecision": review.get("autoServeReady") is True,
        "reviewerAgreement": review.get("mandatoryHumanReviewCanEnd") is True,
        "approvedBank": all(gate["passed"] for gate in bank_gates.values()),
    }
    blockers = [name for name, passed in gates.items() if not passed]
    return {
        "readyForInvitedPilot": not blockers,
        "decision": "ready" if not blockers else "blocked",
        "blockers": blockers,
        "gates": gates,
        "bank": bank_gates,
        "review": review,
        "stagingUrl": staging_url,
    }
