"""SOC 2 assessment scoping without leaking framework semantics into core models."""
from __future__ import annotations

from django.db import transaction

from .models import Assessment, ControlAssessment, Soc2AssessmentProfile
from .soc2_activity_import import TSC_FRAMEWORK_CODE

DOMAIN_CATEGORIES = {
    "Security — Common Criteria": Soc2AssessmentProfile.Category.SECURITY,
    "Availability": Soc2AssessmentProfile.Category.AVAILABILITY,
    "Processing Integrity": Soc2AssessmentProfile.Category.PROCESSING_INTEGRITY,
    "Confidentiality": Soc2AssessmentProfile.Category.CONFIDENTIALITY,
    "Privacy": Soc2AssessmentProfile.Category.PRIVACY,
}
AUTO_SCOPE_PREFIX = "SOC 2 category excluded by assessment profile:"


def has_tsc_framework(assessment: Assessment) -> bool:
    return assessment.frameworks.filter(code=TSC_FRAMEWORK_CODE).exists() or (
        assessment.framework_id and assessment.framework.code == TSC_FRAMEWORK_CODE
    )


@transaction.atomic
def synchronize_soc2_scope(profile: Soc2AssessmentProfile) -> dict:
    included = set(profile.included_categories)
    changed, in_scope, excluded = 0, 0, 0
    results = profile.assessment.control_results.filter(
        requirement__framework__code=TSC_FRAMEWORK_CODE
    ).select_related("requirement")
    for result in results:
        category = DOMAIN_CATEGORIES.get(result.requirement.domain)
        should_include = category in included
        if should_include:
            in_scope += 1
            if not result.in_scope and result.scope_rationale.startswith(AUTO_SCOPE_PREFIX):
                result.in_scope = True
                result.scope_rationale = ""
                result.status = ControlAssessment.Status.NOT_ASSESSED
                result.implementation_state = ControlAssessment.Implementation.UNASSESSED
                result.assessor_notes_findings = ""
                result.save(update_fields=(
                    "in_scope", "scope_rationale", "status", "implementation_state",
                    "assessor_notes_findings", "calculated_deduction", "updated_at",
                ))
                changed += 1
        else:
            excluded += 1
            rationale = f"{AUTO_SCOPE_PREFIX} {result.requirement.domain}."
            if (result.in_scope or result.scope_rationale != rationale
                    or result.status != ControlAssessment.Status.NOT_APPLICABLE):
                result.in_scope = False
                result.scope_rationale = rationale
                result.status = ControlAssessment.Status.NOT_APPLICABLE
                result.implementation_state = ControlAssessment.Implementation.NA
                if not result.assessor_notes_findings:
                    result.assessor_notes_findings = rationale
                result.save(update_fields=(
                    "in_scope", "scope_rationale", "status", "implementation_state",
                    "assessor_notes_findings", "calculated_deduction", "updated_at",
                ))
                changed += 1
    return {"changed": changed, "in_scope": in_scope, "excluded": excluded}
