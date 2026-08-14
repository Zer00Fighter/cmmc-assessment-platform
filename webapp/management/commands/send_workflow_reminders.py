from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from webapp.models import (
    EvidenceRequest, Notification, NotificationPolicy, RemediationMilestone, RemediationPlan,
    RiskRegisterEntry, RiskRegisterHistory, RiskTreatmentAction,
)
from webapp.notifications import client_escalation_email, escalation_users, notify


class Command(BaseCommand):
    help = "Send policy-governed due-soon, due-date, and overdue workflow reminders."

    def handle(self, *args, **options):
        today = timezone.localdate()
        created = 0

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

        requests = EvidenceRequest.objects.filter(due_date__isnull=False).exclude(
            status=EvidenceRequest.Status.ACCEPTED
        ).select_related("owner__user", "assessment__system__organization", "created_by")
        for item in requests:
            deliver(
                owner=item.owner.user if item.owner else None, assessment=item.assessment,
                due_date=item.due_date, title="Evidence request",
                message=f'“{item.title}” is due {item.due_date:%b %d, %Y}.',
                action_url=f'/organizations/{item.assessment.system.organization.slug}/assessments/{item.assessment_id}/evidence/',
                object_type="EvidenceRequest", object_id=item.id, actor=item.created_by,
                notify_owner=item.notify_owner,
            )
        plans = RemediationPlan.objects.filter(planned_completion__isnull=False).exclude(
            status__in=(RemediationPlan.Status.CLOSED, RemediationPlan.Status.RISK_ACCEPTED)
        ).select_related("owner__user", "assessment__system__organization", "created_by")
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
        self.stdout.write(self.style.SUCCESS(f"Created {created} workflow reminders."))
