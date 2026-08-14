from __future__ import annotations

from collections.abc import Iterable

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

from .models import (
    AssessmentTeamMember, AuditEvent, Membership, Notification, NotificationPolicy,
    NotificationPreference, WorkflowHistory,
)


def assessment_url(assessment, route="assessment-dashboard") -> str:
    return reverse(route, args=(assessment.system.organization.slug, assessment.id))


def organization_users(organization, roles=None):
    memberships = organization.memberships.filter(active=True).select_related("user")
    if roles:
        memberships = memberships.filter(role__in=roles)
    return [item.user for item in memberships]


def notify(
    *, recipients: Iterable, organization, assessment, category: str, title: str,
    message: str, action_url: str = "", actor=None, object_type: str = "",
    object_id: str = "", event: str = "notification.created", previous_status: str = "",
    new_status: str = "", comment: str = "", mandatory: bool = False,
):
    policy, _ = NotificationPolicy.objects.get_or_create(organization=organization)
    if not mandatory and (
        not policy.notifications_enabled
        or (assessment and not assessment.notifications_enabled)
    ):
        return []
    unique = {user.pk: user for user in recipients if user and user.pk}
    delivered = []
    for user in unique.values():
        preference, _ = NotificationPreference.objects.get_or_create(user=user)
        preference_field = {
            Notification.Category.ASSIGNMENT: "assignments",
            Notification.Category.EVIDENCE: "evidence",
            Notification.Category.REMEDIATION: "remediation",
            Notification.Category.QUALITY: "quality_review",
            Notification.Category.DEADLINE: "due_dates",
        }.get(category)
        if preference_field and not getattr(preference, preference_field):
            continue
        item = Notification.objects.create(
            recipient=user, organization=organization, assessment=assessment,
            category=category, title=title, message=message, action_url=action_url,
            object_type=object_type, object_id=str(object_id),
        )
        email_allowed = (
            settings.OMNI_EMAIL_ENABLED
            and policy.email_enabled
            and (not assessment or assessment.email_notifications_enabled)
            and user.email
        )
        if email_allowed and preference.delivery == NotificationPreference.Delivery.EMAIL:
            try:
                link = f"{settings.OMNI_BASE_URL}{action_url}" if action_url else settings.OMNI_BASE_URL
                send_mail(
                    subject=f"Omni: {title}",
                    message=f"{message}\n\nOpen Omni securely: {link}\n\nSensitive assessment content is not included in this email.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email], fail_silently=False,
                )
                item.email_status = Notification.EmailStatus.SENT
            except Exception as error:  # Delivery failure must never break workflow state.
                item.email_status = Notification.EmailStatus.FAILED
                item.email_error = str(error)[:500]
            item.save(update_fields=("email_status", "email_error"))
        elif email_allowed and preference.delivery in (
            NotificationPreference.Delivery.DAILY, NotificationPreference.Delivery.WEEKLY
        ):
            item.email_status = Notification.EmailStatus.QUEUED
            item.save(update_fields=("email_status",))
        delivered.append(user.username)
    if actor and assessment:
        WorkflowHistory.objects.create(
            organization=organization, assessment=assessment, actor=actor,
            event=event, object_type=object_type or "Assessment",
            object_id=str(object_id or assessment.id), previous_status=previous_status,
            new_status=new_status, comment=comment, recipients=delivered,
        )
        AuditEvent.objects.create(
            organization=organization, actor=actor, action=event,
            object_type=object_type or "Assessment", object_id=str(object_id or assessment.id),
            detail={"previous_status": previous_status, "new_status": new_status,
                    "notification_recipients": delivered},
        )
    return delivered


def escalation_users(assessment, owner=None):
    policy, _ = NotificationPolicy.objects.get_or_create(
        organization=assessment.system.organization
    )
    users = [owner] if owner else []
    if policy.escalation_recipients in (
        NotificationPolicy.Escalation.LEAD, NotificationPolicy.Escalation.CLIENT
    ):
        users.extend(
            item.membership.user for item in assessment.team_members.filter(
                role=AssessmentTeamMember.Role.LEAD
            ).select_related("membership__user")
        )
    return list({user.pk: user for user in users if user}.values())


def client_escalation_email(assessment) -> str:
    policy, _ = NotificationPolicy.objects.get_or_create(
        organization=assessment.system.organization
    )
    if policy.escalation_recipients != NotificationPolicy.Escalation.CLIENT:
        return ""
    return assessment.system.system_owner_email.strip()


def notify_assessment_team(assessment, **kwargs):
    recipients = [item.membership.user for item in assessment.team_members.select_related("membership__user")]
    if not recipients:
        recipients = organization_users(
            assessment.system.organization, roles=(Membership.Role.ADMIN, Membership.Role.ASSESSOR)
        )
    return notify(
        recipients=recipients, organization=assessment.system.organization,
        assessment=assessment, **kwargs,
    )
