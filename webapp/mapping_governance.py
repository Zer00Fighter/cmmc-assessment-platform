from django.db import transaction
from django.utils import timezone

from .models import GeneratedDocument, MappingChangeRequest, MappingHistory, RevalidationTask


def snapshot(mapping):
    return {"revision": mapping.revision, "relationship": mapping.relationship,
            "notes": mapping.notes, "confidence": str(mapping.confidence or ""),
            "lifecycle": mapping.lifecycle, "source_reference": mapping.source_reference}


@transaction.atomic
def review_change(change, reviewer, approve, comment=""):
    if change.status != MappingChangeRequest.Status.PENDING:
        raise ValueError("Only pending mapping changes can be reviewed.")
    if change.requested_by_id == reviewer.id:
        raise ValueError("The mapping author cannot approve or reject their own change request.")
    mapping = change.mapping
    MappingHistory.objects.create(mapping=mapping, revision=mapping.revision,
                                  snapshot=snapshot(mapping), action="PRE_CHANGE", actor=reviewer)
    change.status = MappingChangeRequest.Status.APPROVED if approve else MappingChangeRequest.Status.REJECTED
    change.reviewed_by, change.reviewed_at, change.reviewer_comment = reviewer, timezone.now(), comment
    change.save(update_fields=("status", "reviewed_by", "reviewed_at", "reviewer_comment"))
    impacted = 0
    if approve:
        mapping.relationship = change.proposed_relationship
        mapping.notes = change.proposed_rationale
        mapping.confidence = change.proposed_confidence
        mapping.revision += 1
        mapping.lifecycle = "APPROVED"
        mapping.approved_by, mapping.approved_at = reviewer, timezone.now()
        mapping.save()
        ids = {mapping.source.requirement_id, mapping.target.requirement_id}
        from .models import AssessmentReuseDecision
        for decision in AssessmentReuseDecision.objects.select_related("assessment").all():
            if ids.intersection(decision.mapping_path):
                RevalidationTask.objects.get_or_create(
                    assessment=decision.assessment, change_request=change, reuse_decision=decision,
                    defaults={"reason": f"Mapping revision {mapping.revision} affects reused assessment work."},
                )
                decision.assessment.generated_documents.filter(status="DRAFT").update(stale=True)
                impacted += 1
    MappingHistory.objects.create(mapping=mapping, revision=mapping.revision,
                                  snapshot=snapshot(mapping), action=change.status, actor=reviewer)
    return impacted
