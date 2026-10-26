"""Independent-review metrics for the LE2 item bank; no efficacy statistics live here."""

from __future__ import annotations

from collections import Counter

MIN_HELDOUT = 50
PRECISION_GATE = 0.90
KAPPA_TARGET = 0.80


def cohen_kappa(pairs: list[tuple[str, str]]) -> tuple[float | None, float | None]:
    """Return raw agreement and categorical Cohen's kappa for two independent reviewers."""
    if not pairs:
        return None, None
    observed = sum(a == b for a, b in pairs) / len(pairs)
    left, right = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    categories = set(left) | set(right)
    expected = sum((left[c] / len(pairs)) * (right[c] / len(pairs)) for c in categories)
    kappa = 1.0 if expected == 1.0 and observed == 1.0 else (observed - expected) / (1.0 - expected)
    return observed, kappa


def review_report(rows: list[dict]) -> dict:
    """Precision uses adjudicated status; agreement always preserves the first two independent votes."""
    heldout = [row for row in rows if row.get("review_set") == "heldout"]
    adjudicated = [row for row in heldout if row.get("review_status") in {"approved", "rejected"}]
    approved = sum(row.get("review_status") == "approved" for row in adjudicated)
    pairs = []
    for row in heldout:
        decisions = [item.get("decision") for item in row.get("review_annotations") or [] if item.get("decision")]
        if len(decisions) >= 2:
            pairs.append((decisions[0], decisions[1]))
    agreement, kappa = cohen_kappa(pairs)
    precision = approved / len(adjudicated) if adjudicated else None
    auto_ready = len(adjudicated) >= MIN_HELDOUT and precision is not None and precision >= PRECISION_GATE
    return {
        "heldout": len(heldout),
        "adjudicated": len(adjudicated),
        "approved": approved,
        "precision": precision,
        "doubleAnnotated": len(pairs),
        "rawAgreement": agreement,
        "cohenKappa": kappa,
        "autoServeReady": auto_ready,
        "mandatoryHumanReviewCanEnd": auto_ready and kappa is not None and kappa >= KAPPA_TARGET,
        "gates": {"minimumHeldout": MIN_HELDOUT, "precision": PRECISION_GATE, "kappaTarget": KAPPA_TARGET},
    }
