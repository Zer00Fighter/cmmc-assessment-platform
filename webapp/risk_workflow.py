from __future__ import annotations

from .models import ControlAssessment, RequirementRiskMapping, RiskRegisterEntry


def finding_risk_suggestions(assessment):
    """Return approved catalog risks for findings, marked when already registered."""
    mappings = RequirementRiskMapping.objects.filter(
        requirement__assessment_results__assessment=assessment,
        requirement__assessment_results__status=ControlAssessment.Status.NOT_MET,
        review_status=RequirementRiskMapping.ReviewStatus.APPROVED,
        risk__active=True,
    ).select_related("risk", "requirement__framework").distinct()
    results_by_requirement = {
        item.requirement_id: item
        for item in assessment.control_results.filter(
            status=ControlAssessment.Status.NOT_MET
        ).select_related("requirement__framework")
    }
    registered = set(
        RiskRegisterEntry.objects.filter(
            assessment=assessment, catalog_risk__isnull=False
        ).values_list("controls__requirement_id", "catalog_risk_id")
    )
    suggestions = []
    for mapping in mappings:
        result = results_by_requirement.get(mapping.requirement_id)
        if not result:
            continue
        suggestions.append({
            "control": result,
            "risk": mapping.risk,
            "mapping": mapping,
            "registered": (mapping.requirement_id, mapping.risk_id) in registered,
        })
    return suggestions
