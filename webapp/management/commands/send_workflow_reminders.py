from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from webapp.models import EvidenceRequest, Notification, RemediationMilestone, RemediationPlan
from webapp.notifications import notify


class Command(BaseCommand):
    help = "Create and optionally email due-soon and overdue Omni workflow reminders."

    def handle(self, *args, **options):
        today = timezone.localdate()
        created = 0

        def deliver(*, recipient, assessment, title, message, action_url, object_type, object_id, actor):
            nonlocal created
            if not recipient or Notification.objects.filter(
                recipient=recipient, category=Notification.Category.DEADLINE,
                object_type=object_type, object_id=str(object_id), title=title,
                created_at__date=today,
            ).exists():
                return
            notify(
                recipients=[recipient], organization=assessment.system.organization,
                assessment=assessment, category=Notification.Category.DEADLINE,
                title=title, message=message, action_url=action_url, actor=actor,
                object_type=object_type, object_id=object_id, event="deadline.reminder",
            )
            created += 1

        requests = EvidenceRequest.objects.filter(
            due_date__isnull=False, due_date__lte=today + timedelta(days=7)
        ).exclude(status=EvidenceRequest.Status.ACCEPTED).select_related(
            "owner__user", "assessment__system__organization", "created_by"
        )
        for item in requests:
            overdue = item.due_date < today
            deliver(
                recipient=item.owner.user if item.owner else None, assessment=item.assessment,
                title=f'Evidence request {"overdue" if overdue else "due soon"}',
                message=f'“{item.title}” is due {item.due_date:%b %d, %Y}.',
                action_url=f'/organizations/{item.assessment.system.organization.slug}/assessments/{item.assessment_id}/evidence/',
                object_type="EvidenceRequest", object_id=item.id, actor=item.created_by,
            )

        plans = RemediationPlan.objects.filter(
            planned_completion__isnull=False,
            planned_completion__lte=today + timedelta(days=7),
        ).exclude(status__in=(RemediationPlan.Status.CLOSED, RemediationPlan.Status.RISK_ACCEPTED)).select_related(
            "owner__user", "assessment__system__organization", "created_by"
        )
        for item in plans:
            overdue = item.planned_completion < today
            deliver(
                recipient=item.owner.user if item.owner else None, assessment=item.assessment,
                title=f'Remediation {"overdue" if overdue else "due soon"}: {item.remediation_id}',
                message=f'“{item.title}” is due {item.planned_completion:%b %d, %Y}.',
                action_url=f'/organizations/{item.assessment.system.organization.slug}/assessments/{item.assessment_id}/remediation/{item.id}/',
                object_type="RemediationPlan", object_id=item.id, actor=item.created_by,
            )

        milestones = RemediationMilestone.objects.filter(
            due_date__isnull=False, due_date__lte=today + timedelta(days=7),
        ).exclude(status=RemediationMilestone.Status.COMPLETE).select_related(
            "owner__user", "plan__assessment__system__organization", "plan__created_by"
        )
        for item in milestones:
            overdue = item.due_date < today
            assessment = item.plan.assessment
            deliver(
                recipient=item.owner.user if item.owner else None, assessment=assessment,
                title=f'Milestone {"overdue" if overdue else "due soon"}',
                message=f'“{item.title}” is due {item.due_date:%b %d, %Y}.',
                action_url=f'/organizations/{assessment.system.organization.slug}/assessments/{assessment.id}/remediation/{item.plan_id}/',
                object_type="RemediationMilestone", object_id=item.id, actor=item.plan.created_by,
            )
        self.stdout.write(self.style.SUCCESS(f"Created {created} workflow reminders."))
