from __future__ import annotations

from django.urls import reverse
from django.utils import timezone

from .models import (
    AssessmentTemplate, ControlReassessmentTask, EvidenceArtifact, EvidenceRequest,
    RemediationMilestone, RemediationPlan, RiskRegisterEntry, RiskTreatmentAction,
)


CATEGORIES = (
    ("ASSESSMENT", "Assessment"),
    ("EVIDENCE", "Evidence"),
    ("REMEDIATION", "Remediation"),
    ("MONITORING", "Monitoring and reassessment"),
    ("RISK", "Risk"),
    ("RECURRENCE", "Recurring assessment"),
)


def compliance_calendar_events(
    assessments, *, organization, date_from, date_to, include_templates=False
) -> list[dict]:
    today = timezone.localdate()
    assessments = list(assessments.select_related("system"))
    assessment_ids = [item.id for item in assessments]
    events = []

    def add(*, date, category, title, assessment=None, status="", url="", detail=""):
        if not date or date < date_from or date > date_to:
            return
        events.append({
            "date": date, "category": category, "title": title,
            "assessment": assessment, "system": assessment.system if assessment else None,
            "status": status, "url": url, "detail": detail,
            "timing": "OVERDUE" if date < today and status not in {"COMPLETE", "CLOSED", "ACCEPTED"}
            else "TODAY" if date == today else "UPCOMING",
        })

    for assessment in assessments:
        base = (organization.slug, assessment.id)
        url = reverse("assessment-dashboard", args=base)
        add(date=assessment.engagement_start, category="ASSESSMENT",
            title=f"Assessment starts: {assessment.name}", assessment=assessment,
            status=assessment.status, url=url)
        add(date=assessment.engagement_end, category="ASSESSMENT",
            title=f"Assessment ends: {assessment.name}", assessment=assessment,
            status=assessment.status, url=url)

    requests = EvidenceRequest.objects.filter(
        assessment_id__in=assessment_ids, due_date__isnull=False
    ).exclude(status=EvidenceRequest.Status.ACCEPTED).select_related("assessment__system")
    for item in requests:
        add(date=item.due_date, category="EVIDENCE", title=item.title,
            assessment=item.assessment, status=item.status,
            url=reverse("evidence-list", args=(organization.slug, item.assessment_id)),
            detail="Evidence request")
    artifacts = EvidenceArtifact.objects.filter(
        assessment_id__in=assessment_ids, superseded_by__isnull=True
    ).select_related("assessment__system").prefetch_related("requests")
    for item in artifacts:
        add(date=item.freshness_deadline, category="EVIDENCE",
            title=f"Evidence validity: {item.title}", assessment=item.assessment,
            status=item.freshness,
            url=reverse("evidence-list", args=(organization.slug, item.assessment_id)),
            detail="Evidence expiration or policy-derived renewal date")

    plans = RemediationPlan.objects.filter(
        assessment_id__in=assessment_ids, planned_completion__isnull=False
    ).exclude(status__in=(RemediationPlan.Status.CLOSED, RemediationPlan.Status.RISK_ACCEPTED))
    for item in plans.select_related("assessment__system"):
        add(date=item.planned_completion, category="REMEDIATION",
            title=f"{item.remediation_id}: {item.title}", assessment=item.assessment,
            status=item.status,
            url=reverse("remediation-detail", args=(organization.slug, item.assessment_id, item.id)),
            detail="Remediation target")
    milestones = RemediationMilestone.objects.filter(
        plan__assessment_id__in=assessment_ids, due_date__isnull=False
    ).exclude(status=RemediationMilestone.Status.COMPLETE).select_related("plan__assessment__system")
    for item in milestones:
        assessment = item.plan.assessment
        add(date=item.due_date, category="REMEDIATION", title=item.title,
            assessment=assessment, status=item.status,
            url=reverse("remediation-detail", args=(organization.slug, assessment.id, item.plan_id)),
            detail=f"Milestone for {item.plan.remediation_id}")

    tasks = ControlReassessmentTask.objects.filter(
        control_result__assessment_id__in=assessment_ids, due_date__isnull=False
    ).exclude(status__in=(ControlReassessmentTask.Status.COMPLETED,
                         ControlReassessmentTask.Status.NO_ACTION)).select_related(
        "control_result__assessment__system", "control_result__requirement", "event"
    )
    for item in tasks:
        assessment = item.control_result.assessment
        add(date=item.due_date, category="MONITORING",
            title=f"Reassess {item.control_result.requirement.requirement_id}",
            assessment=assessment, status=item.status,
            url=reverse("control-reassessment-task-edit",
                        args=(organization.slug, assessment.id, item.id)),
            detail=item.event.title)

    risks = RiskRegisterEntry.objects.filter(
        assessment_id__in=assessment_ids, assessment__risk_management_enabled=True
    ).exclude(status=RiskRegisterEntry.Status.CLOSED).select_related("assessment__system")
    for item in risks:
        url = reverse("risk-register-detail", args=(organization.slug, item.assessment_id, item.id))
        add(date=item.next_review_date, category="RISK", title=f"Risk review: {item.risk_id}",
            assessment=item.assessment, status=item.status, url=url, detail=item.title)
        add(date=item.acceptance_expires, category="RISK",
            title=f"Risk acceptance expires: {item.risk_id}", assessment=item.assessment,
            status=item.status, url=url, detail=item.title)
    actions = RiskTreatmentAction.objects.filter(
        risk__assessment_id__in=assessment_ids, due_date__isnull=False,
        risk__assessment__risk_management_enabled=True,
    ).exclude(status=RiskTreatmentAction.Status.COMPLETE).select_related("risk__assessment__system")
    for item in actions:
        assessment = item.risk.assessment
        add(date=item.due_date, category="RISK", title=f"Risk treatment: {item.title}",
            assessment=assessment, status=item.status,
            url=reverse("risk-register-detail", args=(organization.slug, assessment.id, item.risk_id)),
            detail=item.risk.risk_id)

    if include_templates:
        templates = AssessmentTemplate.objects.filter(
            organization=organization, active=True, next_start_date__isnull=False
        )
        for item in templates:
            add(date=item.next_start_date, category="RECURRENCE",
                title=f"Recurring assessment due: {item.name}", status=item.recurrence,
                url=reverse("assessment-template-list", args=(organization.slug,)),
                detail=item.get_recurrence_display())
    return sorted(events, key=lambda item: (item["date"], item["category"], item["title"]))
