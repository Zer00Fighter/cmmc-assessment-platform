from __future__ import annotations

from collections import defaultdict

from django.db.models import Q
from django.utils import timezone

from .models import (
    Assessment, ControlAssessment, ControlReassessmentTask, EvidenceRequest,
    RemediationPlan, RiskRegisterEntry,
)


def authorized_assessments(user, organization):
    assessments = Assessment.objects.filter(system__organization=organization)
    if user.is_superuser:
        return assessments
    membership = organization.memberships.filter(user=user, active=True).first()
    if not membership:
        return assessments.none()
    if membership.role == membership.Role.ADMIN:
        return assessments
    return assessments.filter(
        Q(access_grants__isnull=True) | Q(access_grants__membership=membership)
    ).distinct()


def portfolio_analytics(assessments, *, organization, today=None) -> dict:
    today = today or timezone.localdate()
    assessments = assessments.select_related("system", "framework").prefetch_related(
        "frameworks", "evidence_artifacts__requests"
    )
    assessment_ids = list(assessments.values_list("id", flat=True))
    controls = ControlAssessment.objects.filter(assessment_id__in=assessment_ids)
    evidence_requests = EvidenceRequest.objects.filter(assessment_id__in=assessment_ids)
    open_evidence = evidence_requests.exclude(status=EvidenceRequest.Status.ACCEPTED)
    remediations = RemediationPlan.objects.filter(assessment_id__in=assessment_ids)
    open_remediation = remediations.exclude(
        status__in=(RemediationPlan.Status.CLOSED, RemediationPlan.Status.RISK_ACCEPTED)
    )
    reassessments = ControlReassessmentTask.objects.filter(
        control_result__assessment_id__in=assessment_ids
    ).exclude(status__in=(
        ControlReassessmentTask.Status.COMPLETED,
        ControlReassessmentTask.Status.NO_ACTION,
    ))
    risks = RiskRegisterEntry.objects.filter(
        assessment_id__in=assessment_ids, assessment__risk_management_enabled=True
    ).exclude(status=RiskRegisterEntry.Status.CLOSED)
    artifacts = []
    assessment_list = list(assessments)
    by_system = defaultdict(list)
    for assessment in assessment_list:
        by_system[assessment.system_id].append(assessment)
    latest_ids = [
        max(items, key=lambda item: (item.updated_at, item.id)).id
        for items in by_system.values()
    ]
    posture_controls = controls.filter(assessment_id__in=latest_ids)
    posture_total = posture_controls.count()
    posture_assessed = posture_controls.exclude(
        status=ControlAssessment.Status.NOT_ASSESSED
    ).count()
    for assessment in assessment_list:
        artifacts.extend(assessment.evidence_artifacts.all())

    metrics = {
        "systems": len({item.system_id for item in assessment_list}),
        "assessments": len(assessment_list),
        "active_assessments": sum(item.status != Assessment.Status.COMPLETE for item in assessment_list),
        "completed_assessments": sum(item.status == Assessment.Status.COMPLETE for item in assessment_list),
        "controls": posture_total,
        "control_completion": round(posture_assessed / posture_total * 100, 1)
        if posture_total else 0,
        "findings": posture_controls.filter(status=ControlAssessment.Status.NOT_MET).count(),
        "unassessed": posture_controls.filter(status=ControlAssessment.Status.NOT_ASSESSED).count(),
        "evidence_overdue": open_evidence.filter(due_date__lt=today).count(),
        "evidence_expired": sum(item.freshness == "EXPIRED" for item in artifacts),
        "remediation_open": open_remediation.count(),
        "remediation_overdue": open_remediation.filter(planned_completion__lt=today).count(),
        "reassessments_open": reassessments.count(),
        "reassessments_overdue": reassessments.filter(due_date__lt=today).count(),
        "risks_open": risks.count(),
        "risks_critical": risks.filter(Q(inherent_score__gte=20) | Q(residual_score__gte=20)).count(),
    }

    system_rows = []
    for system_id, items in by_system.items():
        latest = max(items, key=lambda item: (item.updated_at, item.id))
        system_controls = controls.filter(assessment__system_id=system_id)
        latest_controls = system_controls.filter(assessment=latest)
        total = latest_controls.count()
        assessed = latest_controls.exclude(status=ControlAssessment.Status.NOT_ASSESSED).count()
        system_rows.append({
            "system": latest.system, "latest": latest, "assessment_count": len(items),
            "completion": round(assessed / total * 100, 1) if total else 0,
            "findings": latest_controls.filter(status=ControlAssessment.Status.NOT_MET).count(),
            "evidence_overdue": open_evidence.filter(
                assessment__system_id=system_id, due_date__lt=today
            ).count(),
            "remediation_open": open_remediation.filter(assessment__system_id=system_id).count(),
            "reassessments_open": reassessments.filter(
                control_result__assessment__system_id=system_id
            ).count(),
        })
    system_rows.sort(key=lambda item: (-item["findings"], item["system"].name.lower()))

    framework_rows = []
    framework_codes = sorted({
        code for assessment in assessment_list
        for code in ({assessment.framework.code}
                     | {framework.code for framework in assessment.frameworks.all()})
    })
    for code in framework_codes:
        framework_controls = controls.filter(requirement__framework__code=code)
        total = framework_controls.count()
        assessed = framework_controls.exclude(status=ControlAssessment.Status.NOT_ASSESSED).count()
        framework_rows.append({
            "code": code,
            "assessments": assessments.filter(
                Q(framework__code=code) | Q(frameworks__code=code)
            ).distinct().count(),
            "controls": total,
            "completion": round(assessed / total * 100, 1) if total else 0,
            "findings": framework_controls.filter(status=ControlAssessment.Status.NOT_MET).count(),
        })

    trend_rows = []
    for assessment in sorted(
        assessment_list, key=lambda item: (item.engagement_end or item.updated_at.date(), item.id),
        reverse=True,
    )[:20]:
        items = controls.filter(assessment=assessment)
        total = items.count()
        assessed = items.exclude(status=ControlAssessment.Status.NOT_ASSESSED).count()
        trend_rows.append({
            "assessment": assessment,
            "date": assessment.engagement_end or assessment.updated_at.date(),
            "completion": round(assessed / total * 100, 1) if total else 0,
            "findings": items.filter(status=ControlAssessment.Status.NOT_MET).count(),
            "score": assessment.current_score,
        })
    return {"metrics": metrics, "systems": system_rows,
            "frameworks": framework_rows, "trend": trend_rows}
