from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from webapp.models import (
    AuditEvent, ControlReassessmentTask, EvidenceArtifact, EvidenceRequest, Notification,
    NotificationPolicy, Organization, RemediationMilestone, RemediationPlan,
    RiskRegisterEntry, RiskRegisterHistory, RiskTreatmentAction,
)
from webapp.notifications import client_escalation_email, escalation_users, notify
from webapp.evidence_freshness import create_renewal_requests
from webapp.control_monitoring import generate_automated_monitoring_events


class Command(BaseCommand):
    help = "Send policy-governed due-soon, due-date, and overdue workflow reminders."

    def add_arguments(self, parser):
        parser.add_argument(
            "--organization", dest="organization_slug",
            help="Limit workflow processing to one organization slug.",
        )

    def handle(self, *args, **options):
        today = timezone.localdate()
        organization = None
        if options.get("organization_slug"):
            organization = Organization.objects.get(slug=options["organization_slug"])
        created = 0
        renewals_created = 0
        monitoring_events_created = 0
        reassessments_created = 0

        def due_event(due_date, policy):
            delta = (due_date - today).days
            if delta == policy.first_reminder_days:
                return "first reminder"
            if delta == policy.second_reminder_days:
                return "second reminder"
            if delta == 0 and policy.notify_on_due_date:
                return "due today"
            overdue = -delta
            if overdue >= policy.overdue_escalation_days and (
                overdue == policy.overdue_escalation_days
                or (overdue - policy.overdue_escalation_days) % policy.repeat_overdue_days == 0
            ):
                return "overdue escalation"
            return ""

        def deliver(*, owner, assessment, due_date, title, message, action_url,
                    object_type, object_id, actor, notify_owner=True, reminder_days=None):
            nonlocal created
            if not notify_owner or not owner:
                return
            policy, _ = NotificationPolicy.objects.get_or_create(
                organization=assessment.system.organization
            )
            if reminder_days is None:
                event = due_event(due_date, policy)
            else:
                delta = (due_date - today).days
                event = ("reminder" if delta == reminder_days else "due today" if delta == 0
                         else "overdue escalation" if delta < 0 else "")
            if not event:
                return
            recipients = escalation_users(assessment, owner) if event == "overdue escalation" else [owner]
            notice_title = f"{title} - {event}"
            if Notification.objects.filter(
                recipient__in=recipients, category=Notification.Category.DEADLINE,
                object_type=object_type, object_id=str(object_id), title=notice_title,
                created_at__date=today,
            ).exists():
                return
            notify(
                recipients=recipients, organization=assessment.system.organization,
                assessment=assessment, category=Notification.Category.DEADLINE,
                title=notice_title, message=message, action_url=action_url, actor=actor,
                object_type=object_type, object_id=object_id, event="deadline.reminder",
            )
            external = client_escalation_email(assessment) if event == "overdue escalation" else ""
            if (external and settings.OMNI_EMAIL_ENABLED and policy.email_enabled
                    and assessment.email_notifications_enabled):
                send_mail(
                    f"Omni: {notice_title}",
                    f"{message}\n\nOpen Omni securely: {settings.OMNI_BASE_URL}{action_url}\n\nSensitive assessment content is not included in this email.",
                    settings.DEFAULT_FROM_EMAIL, [external], fail_silently=True,
                )
            created += 1

        artifacts = EvidenceArtifact.objects.filter(
            superseded_by__isnull=True, requests__auto_renew=True
        ).select_related("assessment__system__organization", "uploaded_by").prefetch_related(
            "requests__owner__user", "requests__controls"
        ).distinct()
        if organization is not None:
            artifacts = artifacts.filter(organization=organization)
        for artifact in artifacts:
            if artifact.freshness not in {"AGING", "EXPIRED"}:
                continue
            renewals = create_renewal_requests(artifact, actor=artifact.uploaded_by)
            renewals_created += len(renewals)
            for renewal in renewals:
                if renewal.owner and renewal.notify_owner:
                    notify(
                        recipients=[renewal.owner.user],
                        organization=artifact.organization, assessment=artifact.assessment,
                        category=Notification.Category.EVIDENCE,
                        title="Evidence renewal requested",
                        message=f'Please renew “{artifact.title}”.',
                        action_url=f'/organizations/{artifact.organization.slug}/assessments/{artifact.assessment_id}/evidence/',
                        actor=artifact.uploaded_by, object_type="EvidenceRequest",
                        object_id=renewal.id, event="evidence.renewal_requested",
                        new_status=renewal.status,
                    )

        monitoring_events, reassessment_tasks = generate_automated_monitoring_events(
            today, organization=organization
        )
        monitoring_events_created = len(monitoring_events)
        reassessments_created = len(reassessment_tasks)
        for event in monitoring_events:
            AuditEvent.objects.create(
                organization=event.assessment.system.organization,
                actor=event.reported_by, action="monitoring_event.generated",
                object_type="ControlMonitoringEvent", object_id=str(event.id),
                detail={"type": event.event_type, "controls": event.controls.count()},
            )
        for task in reassessment_tasks:
            if task.assigned_to:
                assessment = task.control_result.assessment
                notify(
                    recipients=[task.assigned_to.user],
                    organization=assessment.system.organization, assessment=assessment,
                    category=Notification.Category.ASSIGNMENT,
                    title="Control reassessment assigned",
                    message=f'{task.control_result.requirement.requirement_id}: {task.event.title}',
                    action_url=f'/organizations/{assessment.system.organization.slug}/assessments/{assessment.id}/monitoring/',
                    actor=task.event.reported_by, object_type="ControlReassessmentTask",
                    object_id=task.id, event="monitoring.reassessment_assigned",
                    new_status=task.status,
                )

        requests = EvidenceRequest.objects.filter(due_date__isnull=False).exclude(
            status=EvidenceRequest.Status.ACCEPTED
        ).select_related("owner__user", "assessment__system__organization", "created_by")
        if organization is not None:
            requests = requests.filter(assessment__system__organization=organization)
        for item in requests:
            deliver(
                owner=item.owner.user if item.owner else None, assessment=item.assessment,
                due_date=item.due_date, title="Evidence request",
                message=f'“{item.title}” is due {item.due_date:%b %d, %Y}.',
                action_url=f'/organizations/{item.assessment.system.organization.slug}/assessments/{item.assessment_id}/evidence/',
                object_type="EvidenceRequest", object_id=item.id, actor=item.created_by,
                notify_owner=item.notify_owner,
            )
        reassessments = ControlReassessmentTask.objects.filter(
            due_date__isnull=False,
            status__in=(ControlReassessmentTask.Status.OPEN,
                        ControlReassessmentTask.Status.IN_PROGRESS),
        ).select_related(
            "assigned_to__user", "event__reported_by",
            "control_result__assessment__system__organization",
            "control_result__requirement",
        )
        if organization is not None:
            reassessments = reassessments.filter(
                control_result__assessment__system__organization=organization
            )
        for item in reassessments:
            assessment = item.control_result.assessment
            deliver(
                owner=item.assigned_to.user if item.assigned_to else None,
                assessment=assessment, due_date=item.due_date,
                title="Control reassessment",
                message=(f'“{item.control_result.requirement.requirement_id}” '
                         f'is due for reassessment {item.due_date:%b %d, %Y}.'),
                action_url=f'/organizations/{assessment.system.organization.slug}/assessments/{assessment.id}/monitoring/tasks/{item.id}/',
                object_type="ControlReassessmentTask", object_id=item.id,
                actor=item.event.reported_by,
            )
        plans = RemediationPlan.objects.filter(planned_completion__isnull=False).exclude(
            status__in=(RemediationPlan.Status.CLOSED, RemediationPlan.Status.RISK_ACCEPTED)
        ).select_related("owner__user", "assessment__system__organization", "created_by")
        if organization is not None:
            plans = plans.filter(assessment__system__organization=organization)
        for item in plans:
            deliver(
                owner=item.owner.user if item.owner else None, assessment=item.assessment,
                due_date=item.planned_completion, title=f"Remediation {item.remediation_id}",
                message=f'“{item.title}” is due {item.planned_completion:%b %d, %Y}.',
                action_url=f'/organizations/{item.assessment.system.organization.slug}/assessments/{item.assessment_id}/remediation/{item.id}/',
                object_type="RemediationPlan", object_id=item.id, actor=item.created_by,
                notify_owner=item.notify_owner,
            )
        milestones = RemediationMilestone.objects.filter(due_date__isnull=False).exclude(
            status=RemediationMilestone.Status.COMPLETE
        ).select_related("owner__user", "plan__assessment__system__organization", "plan__created_by")
        if organization is not None:
            milestones = milestones.filter(plan__assessment__system__organization=organization)
        for item in milestones:
            assessment = item.plan.assessment
            deliver(
                owner=item.owner.user if item.owner else None, assessment=assessment,
                due_date=item.due_date, title="Remediation milestone",
                message=f'“{item.title}” is due {item.due_date:%b %d, %Y}.',
                action_url=f'/organizations/{assessment.system.organization.slug}/assessments/{assessment.id}/remediation/{item.plan_id}/',
                object_type="RemediationMilestone", object_id=item.id,
                actor=item.plan.created_by, notify_owner=item.notify_owner,
            )
        actions = RiskTreatmentAction.objects.filter(
            due_date__isnull=False, risk__assessment__risk_management_enabled=True
        ).exclude(status=RiskTreatmentAction.Status.COMPLETE).select_related(
            "owner__user", "risk__assessment__system__organization", "risk__created_by"
        )
        if organization is not None:
            actions = actions.filter(risk__assessment__system__organization=organization)
        for item in actions:
            assessment = item.risk.assessment
            deliver(owner=item.owner.user if item.owner else None, assessment=assessment,
                    due_date=item.due_date, title=f"Risk treatment {item.risk.risk_id}",
                    message=f'“{item.title}” is due {item.due_date:%b %d, %Y}.',
                    action_url=f'/organizations/{assessment.system.organization.slug}/assessments/{assessment.id}/risks/{item.risk_id}/',
                    object_type="RiskTreatmentAction", object_id=item.id, actor=item.risk.created_by)
        risks = RiskRegisterEntry.objects.filter(
            assessment__risk_management_enabled=True
        ).exclude(status=RiskRegisterEntry.Status.CLOSED).select_related(
            "owner__user", "assessment__system__organization", "created_by", "accepted_by"
        )
        if organization is not None:
            risks = risks.filter(assessment__system__organization=organization)
        for risk in risks:
            risk_policy = getattr(risk.organization, "risk_tolerance_policy", None)
            if risk.next_review_date:
                deliver(owner=risk.owner.user if risk.owner else None, assessment=risk.assessment,
                        due_date=risk.next_review_date, title=f"Risk review {risk.risk_id}",
                        message=f'“{risk.title}” requires periodic review.',
                        action_url=f'/organizations/{risk.organization.slug}/assessments/{risk.assessment_id}/risks/{risk.id}/',
                        object_type="RiskRegisterEntry", object_id=risk.id, actor=risk.created_by,
                        reminder_days=(risk_policy.review_reminder_days if risk_policy else 14))
            if risk.status == RiskRegisterEntry.Status.ACCEPTED and risk.acceptance_expires:
                deliver(owner=risk.owner.user if risk.owner else None, assessment=risk.assessment,
                        due_date=risk.acceptance_expires, title=f"Risk acceptance {risk.risk_id}",
                        message=f'Acceptance for “{risk.title}” expires {risk.acceptance_expires:%b %d, %Y}.',
                        action_url=f'/organizations/{risk.organization.slug}/assessments/{risk.assessment_id}/risks/{risk.id}/',
                        object_type="RiskRegisterEntry", object_id=risk.id, actor=risk.accepted_by or risk.created_by,
                        reminder_days=(risk_policy.acceptance_expiry_reminder_days if risk_policy else 30))
                if risk.acceptance_expires < today:
                    risk.status = RiskRegisterEntry.Status.MONITORING
                    risk.next_review_date = today
                    risk.save(update_fields=("status", "next_review_date", "updated_at"))
                    RiskRegisterHistory.objects.create(
                        risk=risk, actor=risk.accepted_by or risk.created_by,
                        action="ACCEPTANCE_EXPIRED", snapshot={"expired": str(risk.acceptance_expires)},
                    )
        self.stdout.write(self.style.SUCCESS(
            f"Created {created} workflow reminders, {renewals_created} evidence renewals, "
            f"{monitoring_events_created} monitoring events, and {reassessments_created} reassessments."
        ))
