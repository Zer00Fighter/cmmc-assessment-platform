"""SOC 2 evidence planning and governed cross-framework test reuse."""
from __future__ import annotations

from collections import defaultdict

from django.db import transaction

from .models import (
    Assessment, AssessmentReuseDecision, EvidenceRequest,
    ImplementationActivityMapping, TestExecution, TestReuseReference,
)
from .soc2_activity_import import TSC_FRAMEWORK_CODE


def soc2_evidence_expectations(assessment: Assessment) -> list[dict]:
    """Return private implementation-guidance evidence suggestions for in-scope TSC criteria."""
    results = {
        item.requirement_id: item for item in assessment.control_results.filter(
            in_scope=True, requirement__framework__code=TSC_FRAMEWORK_CODE
        ).select_related("requirement")
    }
    mappings = ImplementationActivityMapping.objects.filter(
        target_requirement_id_text__in=[item.requirement.requirement_id for item in results.values()],
        target_framework_code=TSC_FRAMEWORK_CODE,
    ).exclude(
        review_status=ImplementationActivityMapping.ReviewStatus.REJECTED
    ).select_related("activity", "target_requirement")
    expectations = []
    for mapping in mappings:
        metadata = mapping.activity.source_metadata or {}
        title = str(metadata.get("Evidence Artifact") or "").strip()
        source = str(metadata.get("Evidence Source") or "").strip()
        if not title:
            continue
        target = results.get(mapping.target_requirement_id)
        if not target:
            continue
        expectations.append({
            "mapping_id": mapping.id,
            "control_result": target,
            "activity": mapping.activity,
            "title": title,
            "source": source,
            "frequency": str(metadata.get("Frequency") or "").strip(),
            "review_status": mapping.review_status,
            "confidence": mapping.confidence,
        })
    return expectations


@transaction.atomic
def create_soc2_evidence_requests(assessment: Assessment, mapping_ids, user) -> dict:
    """Create consolidated requests from assessor-selected SOC 2 evidence suggestions."""
    mapping_ids = set(mapping_ids)
    selected = [item for item in soc2_evidence_expectations(assessment)
                if item["mapping_id"] in mapping_ids]
    grouped = defaultdict(list)
    for item in selected:
        grouped[(item["title"], item["source"])].append(item)
    created = linked = 0
    for (title, source), items in grouped.items():
        request, was_created = EvidenceRequest.objects.get_or_create(
            assessment=assessment, title=title,
            defaults={
                "description": (
                    f"SOC 2 implementation-guidance evidence suggestion. "
                    f"Expected source: {source or 'to be determined by the assessor'}."
                ),
                "created_by": user,
            },
        )
        created += int(was_created)
        before = request.controls.count()
        request.controls.add(*(item["control_result"] for item in items))
        linked += request.controls.count() - before
    return {"selected": len(selected), "created": created, "control_links": linked}


@transaction.atomic
def approve_test_reuse(decision: AssessmentReuseDecision, source_test_id: int,
                       target_objective_id: int, user, limitations: str = ""):
    """Reference prior testing after validating the approved mapping boundary."""
    if decision.status != AssessmentReuseDecision.Status.APPROVED or not decision.reuse_testing:
        raise ValueError("Testing reuse must be enabled in an approved reuse decision.")
    source_test = TestExecution.objects.filter(
        pk=source_test_id, assessment=decision.assessment,
        objective_result__control_result=decision.source_result,
    ).first()
    target = decision.target_result.objective_results.filter(pk=target_objective_id).first()
    if not source_test or not target:
        raise ValueError("The source test and target objective must match the approved reuse decision.")
    reference, created = TestReuseReference.objects.get_or_create(
        source_test=source_test, target_objective=target,
        defaults={"reuse_decision": decision, "limitations": limitations, "approved_by": user},
    )
    return reference, created
