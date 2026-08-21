from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import (
    ControlMonitoringEvent, ControlMonitoringProfile, ControlReassessmentTask,
    EvidenceArtifact,
)


def conclusion_snapshot(control) -> dict:
    return {
        "status": control.status,
        "implementation_state": control.implementation_state,
        "calculated_deduction": control.calculated_deduction,
        "assessor_notes_findings": control.assessor_notes_findings,
        "updated_at": control.updated_at.isoformat() if control.updated_at else "",
    }


@transaction.atomic
def create_reassessment_tasks(event: ControlMonitoringEvent) -> list[ControlReassessmentTask]:
    created = []
    for control in event.controls.select_related("primary_owner", "assessment"):
        profile = ControlMonitoringProfile.objects.filter(control_result=control).first()
        owner = profile.owner if profile and profile.owner else control.primary_owner
        task, was_created = ControlReassessmentTask.objects.get_or_create(
            event=event, control_result=control,
            defaults={
                "assigned_to": owner,
                "due_date": event.occurred_on + timedelta(days=14),
                "reason": event.description,
                "prior_conclusion": conclusion_snapshot(control),
            },
        )
        if was_created:
            created.append(task)
    return created


@transaction.atomic
def generate_automated_monitoring_events(today=None, organization=None) -> tuple[list, list]:
    """Create duplicate-safe events for scheduled reviews and stale evidence."""
    today = today or timezone.localdate()
    events, tasks = [], []
    profiles = ControlMonitoringProfile.objects.filter(
        enabled=True, next_review_date__lte=today
    ).select_related(
        "control_result__assessment__system__organization",
        "control_result__assessment__created_by",
    )
    if organization is not None:
        profiles = profiles.filter(control_result__assessment__system__organization=organization)
    for profile in profiles:
        control = profile.control_result
        source_key = f"schedule:{profile.id}:{profile.next_review_date.isoformat()}"
        event, created = ControlMonitoringEvent.objects.get_or_create(
            assessment=control.assessment, source_key=source_key,
            defaults={
                "title": f"Scheduled review: {control.requirement.requirement_id}",
                "event_type": ControlMonitoringEvent.EventType.SCHEDULED,
                "severity": ControlMonitoringEvent.Severity.MODERATE,
                "occurred_on": today,
                "description": "The control reached its configured periodic review date.",
                "reported_by": control.assessment.created_by,
            },
        )
        if created:
            event.controls.add(control)
            events.append(event)
            tasks.extend(create_reassessment_tasks(event))
            while profile.next_review_date <= today:
                profile.next_review_date += timedelta(days=profile.review_frequency_days)
            profile.save(update_fields=("next_review_date", "updated_at"))

    artifacts = EvidenceArtifact.objects.filter(
        superseded_by__isnull=True
    ).select_related("assessment__created_by", "uploaded_by").prefetch_related(
        "controls", "requests"
    )
    if organization is not None:
        artifacts = artifacts.filter(organization=organization)
    for artifact in artifacts:
        if artifact.freshness != "EXPIRED" or not artifact.controls.exists():
            continue
        deadline = artifact.freshness_deadline
        source_key = f"evidence:{artifact.id}:{deadline.isoformat() if deadline else 'unknown'}"
        event, created = ControlMonitoringEvent.objects.get_or_create(
            assessment=artifact.assessment, source_key=source_key,
            defaults={
                "title": f"Expired evidence: {artifact.title}",
                "event_type": ControlMonitoringEvent.EventType.EVIDENCE,
                "severity": ControlMonitoringEvent.Severity.HIGH,
                "occurred_on": today,
                "description": "Linked evidence expired and the affected controls require reassessment.",
                "source_reference": f"EA-{artifact.id:04d}",
                "reported_by": artifact.uploaded_by,
            },
        )
        if created:
            event.controls.set(artifact.controls.all())
            events.append(event)
            tasks.extend(create_reassessment_tasks(event))
    return events, tasks
