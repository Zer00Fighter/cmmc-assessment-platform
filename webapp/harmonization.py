"""Assessment-level mapping and governed work-reuse services."""
from __future__ import annotations

from collections import defaultdict

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import (
    Assessment, AssessmentReuseDecision, ControlAssessment, EvidenceArtifact,
    RequirementMapping,
)


def _strength(relationships) -> str:
    values = set(relationships)
    if values == {RequirementMapping.Relationship.EQUIVALENT}:
        return RequirementMapping.Relationship.EQUIVALENT
    if RequirementMapping.Relationship.PARTIAL in values:
        return RequirementMapping.Relationship.PARTIAL
    if RequirementMapping.Relationship.RELATED in values:
        return RequirementMapping.Relationship.RELATED
    return RequirementMapping.Relationship.SUPPORTS


def _work_score(result: ControlAssessment, primary_framework_id: int) -> tuple:
    return (
        result.evidence_artifacts.filter(review_status=EvidenceArtifact.ReviewStatus.ACCEPTED).count(),
        result.objective_results.exclude(status="NOT_ASSESSED").count(),
        int(result.status != ControlAssessment.Status.NOT_ASSESSED),
        int(result.requirement.framework_id == primary_framework_id),
        -result.pk,
    )


def _ordered_pair(left, right, primary_framework_id):
    if _work_score(right, primary_framework_id) > _work_score(left, primary_framework_id):
        return right, left
    return left, right


@transaction.atomic
def refresh_harmonization(assessment: Assessment) -> dict:
    """Create non-authoritative reuse suggestions from direct and Omni-hub mappings."""
    results = list(assessment.control_results.select_related("requirement__framework"))
    by_requirement = {item.requirement_id: item for item in results}
    selected_requirement_ids = set(by_requirement)
    suggestions = {}

    direct = RequirementMapping.objects.filter(
        source_id__in=selected_requirement_ids, target_id__in=selected_requirement_ids
    ).select_related("source__framework", "target__framework")
    for mapping in direct:
        left, right = by_requirement[mapping.source_id], by_requirement[mapping.target_id]
        source, target = _ordered_pair(left, right, assessment.framework_id)
        suggestions[(source.pk, target.pk)] = {
            "basis": AssessmentReuseDecision.Basis.DIRECT,
            "relationship": mapping.relationship,
            "mapping_path": [mapping.source.requirement_id, mapping.target.requirement_id],
        }

    hub_mappings = RequirementMapping.objects.filter(
        Q(source__framework__is_omni_control_framework=True)
        | Q(target__framework__is_omni_control_framework=True)
    ).select_related("source__framework", "target__framework")
    spokes = defaultdict(list)
    for mapping in hub_mappings:
        if mapping.source.framework.is_omni_control_framework:
            hub, spoke = mapping.source, mapping.target
        else:
            hub, spoke = mapping.target, mapping.source
        if spoke.pk in selected_requirement_ids:
            spokes[hub.pk].append((by_requirement[spoke.pk], mapping.relationship, hub))
        if hub.pk in selected_requirement_ids:
            spokes[hub.pk].append((by_requirement[hub.pk], mapping.relationship, hub))
    for connected in spokes.values():
        unique = {item[0].pk: item for item in connected}
        values = list(unique.values())
        for index, (left, left_rel, hub) in enumerate(values):
            for right, right_rel, _ in values[index + 1:]:
                if left.requirement.framework_id == right.requirement.framework_id:
                    continue
                source, target = _ordered_pair(left, right, assessment.framework_id)
                key = (source.pk, target.pk)
                if key in suggestions:  # A direct, traceable mapping is stronger provenance.
                    continue
                suggestions[key] = {
                    "basis": AssessmentReuseDecision.Basis.OMNI_DERIVED,
                    "relationship": _strength((left_rel, right_rel)),
                    "mapping_path": [
                        left.requirement.requirement_id,
                        hub.requirement_id,
                        right.requirement.requirement_id,
                    ],
                }

    created = 0
    for (source_id, target_id), defaults in suggestions.items():
        _, was_created = AssessmentReuseDecision.objects.get_or_create(
            assessment=assessment, source_result_id=source_id, target_result_id=target_id,
            defaults=defaults,
        )
        created += int(was_created)
    return {"candidates": len(suggestions), "created": created}


@transaction.atomic
def review_reuse(decision: AssessmentReuseDecision, user, approved: bool) -> int:
    """Approve/reject reuse; share accepted evidence, never compliance outcomes."""
    decision.status = (
        AssessmentReuseDecision.Status.APPROVED if approved
        else AssessmentReuseDecision.Status.REJECTED
    )
    decision.reviewed_by = user
    decision.reviewed_at = timezone.now()
    decision.save(update_fields=("status", "reviewed_by", "reviewed_at"))
    linked = 0
    if approved and decision.reuse_evidence:
        artifacts = decision.source_result.evidence_artifacts.filter(
            review_status=EvidenceArtifact.ReviewStatus.ACCEPTED
        )
        for artifact in artifacts:
            _, added = artifact.controls.through.objects.get_or_create(
                evidenceartifact_id=artifact.pk,
                controlassessment_id=decision.target_result_id,
            )
            linked += int(added)
    return linked


def harmonization_metrics(assessment: Assessment) -> dict:
    total = assessment.control_results.count()
    decisions = assessment.reuse_decisions.all()
    mapped_ids = set(decisions.values_list("source_result_id", flat=True)) | set(
        decisions.values_list("target_result_id", flat=True)
    )
    approved = decisions.filter(status=AssessmentReuseDecision.Status.APPROVED)
    evidence_ready = approved.filter(
        target_result__evidence_artifacts__review_status=EvidenceArtifact.ReviewStatus.ACCEPTED
    ).values("target_result_id").distinct().count()
    return {
        "total": total, "mapped": len(mapped_ids), "unmapped": max(total - len(mapped_ids), 0),
        "suggested": decisions.filter(status=AssessmentReuseDecision.Status.SUGGESTED).count(),
        "approved": approved.count(), "rejected": decisions.filter(
            status=AssessmentReuseDecision.Status.REJECTED
        ).count(), "evidence_ready": evidence_ready,
    }
