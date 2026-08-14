from __future__ import annotations

from collections import defaultdict

from .models import ControlAssessment, Framework


def build_weighted_risk_heatmap(results) -> dict:
    """Summarize weighted control exposure without inferring likelihood."""
    domains = defaultdict(lambda: {
        "total_weight": 0, "assessed_weight": 0, "exposure_weight": 0,
        "unknown_weight": 0, "controls": 0, "findings": 0,
    })
    source_labels = set()
    for result in results:
        framework = result.requirement.framework
        if framework.scoring_method == Framework.ScoringMethod.SPRS:
            weight = result.requirement.full_deduction
            source_labels.add("SPRS")
        elif framework.is_omni_control_framework and result.requirement.risk_weight is not None:
            weight = result.requirement.risk_weight
            source_labels.add("Omni 0–10")
        else:
            continue
        if result.status == ControlAssessment.Status.NOT_APPLICABLE:
            continue
        item = domains[result.requirement.domain or "Uncategorized"]
        item["controls"] += 1
        item["total_weight"] += weight
        if result.status == ControlAssessment.Status.NOT_ASSESSED:
            item["unknown_weight"] += weight
            continue
        item["assessed_weight"] += weight
        if result.status == ControlAssessment.Status.NOT_MET:
            item["findings"] += 1
            item["exposure_weight"] += (
                result.calculated_deduction
                if framework.scoring_method == Framework.ScoringMethod.SPRS
                else weight
            )

    cells = []
    for domain, item in sorted(domains.items()):
        exposure = round(item["exposure_weight"] / item["assessed_weight"] * 100) if item["assessed_weight"] else None
        if exposure is None:
            severity = "unknown"
        elif exposure == 0:
            severity = "none"
        elif exposure <= 25:
            severity = "low"
        elif exposure <= 50:
            severity = "moderate"
        elif exposure <= 75:
            severity = "high"
        else:
            severity = "critical"
        cells.append({"domain": domain, "exposure": exposure, "severity": severity, **item})
    return {"cells": cells, "sources": " + ".join(sorted(source_labels)),
            "available": bool(cells)}
