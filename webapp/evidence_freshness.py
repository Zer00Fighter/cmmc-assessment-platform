from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from .models import EvidenceArtifact, EvidenceRequest


@transaction.atomic
def create_renewal_requests(
    artifact: EvidenceArtifact, *, actor, force: bool = False
) -> list[EvidenceRequest]:
    """Create idempotent renewal work for an artifact's linked requests."""
    created: list[EvidenceRequest] = []
    deadline = artifact.freshness_deadline
    for source in artifact.requests.select_related("owner").prefetch_related("controls"):
        if not force and not source.auto_renew:
            continue
        existing = source.renewal_requests.exclude(
            status=EvidenceRequest.Status.ACCEPTED
        ).first()
        if existing:
            continue
        renewal = EvidenceRequest.objects.create(
            assessment=artifact.assessment,
            evidence_code=source.evidence_code,
            title=f"Renew: {source.title}",
            description=(
                f"Replace or revalidate “{artifact.title}”.\n\n{source.description}"
            ).strip(),
            owner=source.owner,
            due_date=deadline,
            created_by=actor,
            notify_owner=source.notify_owner,
            freshness_days=source.freshness_days,
            renewal_lead_days=source.renewal_lead_days,
            auto_renew=source.auto_renew,
            renewal_of=source,
        )
        renewal.controls.set(source.controls.all())
        created.append(renewal)
    if created:
        artifact.requests.update(renewal_generated_at=timezone.now())
    return created
