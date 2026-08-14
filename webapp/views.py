from __future__ import annotations

import csv
import hashlib
import secrets
from datetime import timedelta
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import transaction
from django.db import connection
from django.db.models import Count, Q, Sum
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import (
    AssessmentForm,
    AssessmentPlanForm,
    AssessmentSampleForm,
    AssessmentTeamForm,
    BulkControlOwnerForm,
    ControlAssessmentForm,
    EvidenceArtifactForm,
    EvidenceRequestForm,
    MembershipForm,
    InvitationAcceptForm,
    InvitationForm,
    UserProfileForm,
    AssessmentAccessForm,
    OrganizationForm,
    InterviewSessionForm,
    ObjectiveAssessmentForm,
    NotificationPreferenceForm,
    NotificationPolicyForm,
    QualityReviewForm,
    ReopenAssessmentForm,
    RemediationMilestoneForm,
    RemediationPlanForm,
    SystemForm,
    TestExecutionForm,
    FrameworkImportForm,
)
from .models import (
    Assessment,
    AssessmentAccess,
    AssessmentFramework,
    AssessmentProcedure,
    AssessmentSample,
    AssessmentTeamMember,
    AuditEvent,
    ControlAssessment,
    EvidenceArtifact,
    EvidenceRequest,
    Framework,
    FrameworkImport,
    GeneratedDocument,
    Membership,
    Notification,
    NotificationPreference,
    NotificationPolicy,
    InterviewSession,
    ObjectiveAssessment,
    Organization,
    OrganizationInvitation,
    RemediationMilestone,
    RemediationPlan,
    RequirementMapping,
    System,
    TestExecution,
    EvidenceReviewHistory,
    UserProfile,
)
from .framework_import import approve_import, parse_upload
from .notifications import assessment_url, notify, notify_assessment_team, organization_users


def _organizations_for(user):
    if user.is_superuser:
        return Organization.objects.filter(active=True)
    return Organization.objects.filter(
        active=True, memberships__user=user, memberships__active=True
    ).distinct()


def _organization_for(user, slug: str) -> Organization:
    return get_object_or_404(_organizations_for(user), slug=slug)


def _has_assessment_access(user, assessment: Assessment) -> bool:
    if user.is_superuser:
        return True
    membership = Membership.objects.filter(
        user=user, organization=assessment.system.organization, active=True
    ).first()
    if not membership:
        return False
    if membership.role == Membership.Role.ADMIN:
        return True
    if not assessment.access_grants.exists():
        return True
    return assessment.access_grants.filter(membership=membership).exists()


def _can_edit(user, organization: Organization) -> bool:
    if user.is_superuser:
        return True
    return Membership.objects.filter(
        user=user,
        organization=organization,
        active=True,
        role__in=(Membership.Role.ADMIN, Membership.Role.ASSESSOR),
    ).exists()


def _is_org_admin(user, organization: Organization) -> bool:
    if user.is_superuser:
        return True
    return Membership.objects.filter(
        user=user, organization=organization, active=True, role=Membership.Role.ADMIN
    ).exists()


def _can_manage_evidence(user, organization: Organization) -> bool:
    if user.is_superuser:
        return True
    return Membership.objects.filter(
        user=user, organization=organization, active=True,
        role__in=(Membership.Role.ADMIN, Membership.Role.ASSESSOR, Membership.Role.CLIENT),
    ).exists()


def _can_manage_remediation(user, organization: Organization, plan=None) -> bool:
    if _can_edit(user, organization):
        return True
    if plan is None:
        return False
    return Membership.objects.filter(
        user=user, organization=organization, active=True
    ).filter(Q(owned_remediation_plans=plan) | Q(remediation_milestones__plan=plan)).exists()


@login_required
def organization_list(request: HttpRequest) -> HttpResponse:
    organizations = _organizations_for(request.user).annotate(
        system_count=Count("systems", distinct=True),
        assessment_count=Count("systems__assessments", distinct=True),
    )
    return render(
        request, "webapp/organization_list.html", {"organizations": organizations}
    )


@login_required
def notification_center(request: HttpRequest) -> HttpResponse:
    notifications = request.user.omni_notifications.select_related(
        "organization", "assessment"
    )[:200]
    return render(request, "webapp/notification_center.html", {
        "notifications": notifications,
        "unread": request.user.omni_notifications.filter(read_at=None).count(),
    })


@login_required
def notification_read(request: HttpRequest, notification_id: int) -> HttpResponse:
    if request.method != "POST":
        raise Http404
    item = get_object_or_404(request.user.omni_notifications, id=notification_id)
    item.read_at = timezone.now()
    item.save(update_fields=("read_at",))
    return redirect(item.action_url or "notification-center")


@login_required
def notifications_read_all(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        raise Http404
    request.user.omni_notifications.filter(read_at=None).update(read_at=timezone.now())
    return redirect("notification-center")


@login_required
def notification_preferences(request: HttpRequest) -> HttpResponse:
    preference, _ = NotificationPreference.objects.get_or_create(user=request.user)
    form = NotificationPreferenceForm(request.POST or None, instance=preference)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Notification preferences saved.")
        return redirect("notification-preferences")
    return render(request, "webapp/notification_preferences.html", {"form": form})


@login_required
def user_profile(request: HttpRequest) -> HttpResponse:
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    form = UserProfileForm(request.POST or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("user-profile")
    return render(request, "webapp/user_profile.html", {"form": form})


@login_required
def notification_policy(request: HttpRequest, org_slug: str) -> HttpResponse:
    organization = _organization_for(request.user, org_slug)
    if not _is_org_admin(request.user, organization):
        raise Http404
    policy, _ = NotificationPolicy.objects.get_or_create(organization=organization)
    form = NotificationPolicyForm(request.POST or None, instance=policy)
    if request.method == "POST" and form.is_valid():
        form.save()
        AuditEvent.objects.create(
            organization=organization, actor=request.user, action="notification_policy.updated",
            object_type="NotificationPolicy", object_id=str(policy.id), detail={},
        )
        messages.success(request, "Notification governance settings saved.")
        return redirect("notification-policy", org_slug=org_slug)
    return render(request, "webapp/notification_policy.html", {
        "organization": organization, "form": form, "email_configured": settings.OMNI_EMAIL_ENABLED,
    })


@login_required
def notification_test_email(request: HttpRequest, org_slug: str) -> HttpResponse:
    if request.method != "POST":
        raise Http404
    organization = _organization_for(request.user, org_slug)
    if not _is_org_admin(request.user, organization):
        raise Http404
    if not settings.OMNI_EMAIL_ENABLED or not request.user.email:
        messages.error(request, "Email is not enabled or your Omni account has no email address.")
    else:
        delivered = send_mail(
            "Omni notification test",
            "Omni notification delivery is configured successfully. No client or assessment data is included.",
            settings.DEFAULT_FROM_EMAIL, [request.user.email], fail_silently=True,
        )
        AuditEvent.objects.create(
            organization=organization, actor=request.user, action="notification.test_email",
            object_type="NotificationPolicy", object_id=str(organization.id),
            detail={"delivered": bool(delivered)},
        )
        messages.success(request, "Test email sent." if delivered else "Test email delivery failed.")
    return redirect("notification-policy", org_slug=org_slug)


@login_required
def system_health(request: HttpRequest, org_slug: str) -> HttpResponse:
    organization = _organization_for(request.user, org_slug)
    if not _is_org_admin(request.user, organization):
        raise Http404
    from .readiness import deployment_readiness
    database_ok = True
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        database_ok = False
    return render(request, "webapp/system_health.html", {
        "organization": organization, "database_ok": database_ok,
        "readiness": deployment_readiness(),
        "failed_emails": organization.notifications.filter(
            email_status=Notification.EmailStatus.FAILED
        ).count(),
        "pending_invitations": organization.invitations.filter(
            status=OrganizationInvitation.Status.PENDING
        ).count(),
        "last_audit": organization.audit_events.first(),
    })


@login_required
def framework_catalog(request: HttpRequest) -> HttpResponse:
    frameworks = Framework.objects.filter(active=True).annotate(
        requirement_count=Count("requirements", distinct=True),
        mapped_requirement_count=Count(
            "requirements", filter=Q(requirements__outbound_mappings__isnull=False), distinct=True
        ),
    ).order_by("name", "version")
    return render(request, "webapp/framework_catalog.html", {"frameworks": frameworks})


@login_required
def framework_import_list(request: HttpRequest) -> HttpResponse:
    if not request.user.is_superuser:
        raise Http404
    return render(request, "webapp/framework_import_list.html", {
        "imports": FrameworkImport.objects.select_related("created_by", "approved_by", "imported_framework"),
    })


@login_required
def framework_import_upload(request: HttpRequest) -> HttpResponse:
    if not request.user.is_superuser:
        raise Http404
    form = FrameworkImportForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        upload = form.cleaned_data["source_file"]
        metadata = {key: form.cleaned_data.get(key, "") for key in (
            "code", "name", "version", "authority", "description"
        )}
        try:
            normalized, report, source_format, digest = parse_upload(upload, metadata)
        except (ValueError, OSError) as exc:
            form.add_error("source_file", str(exc))
        else:
            job = FrameworkImport.objects.create(
                source_file=upload, source_filename=upload.name, source_format=source_format,
                source_sha256=digest, normalized_data=normalized, validation_report=report,
                status=FrameworkImport.Status.PREVIEW if report["valid"] else FrameworkImport.Status.FAILED,
                created_by=request.user,
            )
            return redirect("framework-import-preview", import_id=job.pk)
    return render(request, "webapp/framework_import_upload.html", {"form": form})


@login_required
def framework_import_preview(request: HttpRequest, import_id: int) -> HttpResponse:
    if not request.user.is_superuser:
        raise Http404
    job = get_object_or_404(FrameworkImport, pk=import_id)
    if request.method == "POST":
        try:
            framework = approve_import(job, request.user)
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, f"{framework.name} {framework.version} imported and provenance recorded.")
            return redirect("framework-catalog")
    return render(request, "webapp/framework_import_preview.html", {
        "job": job, "requirements": job.normalized_data.get("requirements", [])[:100],
    })


@login_required
def organization_create(request: HttpRequest) -> HttpResponse:
    form = OrganizationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        organization = form.save()
        Membership.objects.create(
            user=request.user, organization=organization, role=Membership.Role.ADMIN
        )
        AuditEvent.objects.create(
            organization=organization, actor=request.user,
            action="organization.created", object_type="Organization",
            object_id=str(organization.id), detail={"name": organization.name},
        )
        messages.success(request, f"{organization.name} created.")
        return redirect("system-list", org_slug=organization.slug)
    return render(request, "webapp/entity_form.html", {
        "form": form, "title": "Create organization",
        "eyebrow": "Organization onboarding", "submit_label": "Create organization",
    })


@login_required
def organization_edit(request: HttpRequest, org_slug: str) -> HttpResponse:
    organization = _organization_for(request.user, org_slug)
    if not _is_org_admin(request.user, organization):
        raise Http404
    form = OrganizationForm(request.POST or None, instance=organization)
    if request.method == "POST" and form.is_valid():
        organization = form.save()
        messages.success(request, "Organization profile updated.")
        return redirect("system-list", org_slug=organization.slug)
    return render(request, "webapp/entity_form.html", {
        "form": form, "title": "Organization profile", "organization": organization,
        "eyebrow": "Organization settings", "submit_label": "Save profile",
    })
@login_required
def system_list(request: HttpRequest, org_slug: str) -> HttpResponse:
    organization = _organization_for(request.user, org_slug)
    systems = organization.systems.filter(active=True).annotate(
        assessment_count=Count("assessments")
    )
    return render(
        request,
        "webapp/system_list.html",
        {"organization": organization, "systems": systems,
         "can_admin": _is_org_admin(request.user, organization)},
    )


@login_required
def system_create(request: HttpRequest, org_slug: str) -> HttpResponse:
    organization = _organization_for(request.user, org_slug)
    if not _is_org_admin(request.user, organization):
        raise Http404
    form = SystemForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        system = form.save(commit=False)
        system.organization = organization
        system.save()
        AuditEvent.objects.create(
            organization=organization, actor=request.user, action="system.created",
            object_type="System", object_id=str(system.id), detail={"name": system.name},
        )
        messages.success(request, f"{system.name} created.")
        return redirect("assessment-list", org_slug=org_slug, system_id=system.id)
    return render(request, "webapp/entity_form.html", {
        "form": form, "title": "Add system", "organization": organization,
        "eyebrow": "System onboarding", "submit_label": "Create system",
    })


@login_required
def system_edit(request: HttpRequest, org_slug: str, system_id: int) -> HttpResponse:
    organization = _organization_for(request.user, org_slug)
    if not _is_org_admin(request.user, organization):
        raise Http404
    system = get_object_or_404(System, id=system_id, organization=organization)
    form = SystemForm(request.POST or None, instance=system)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "System profile updated.")
        return redirect("assessment-list", org_slug=org_slug, system_id=system.id)
    return render(request, "webapp/entity_form.html", {
        "form": form, "title": "System profile", "organization": organization,
        "eyebrow": system.name, "submit_label": "Save system",
    })


@login_required
def membership_list(request: HttpRequest, org_slug: str) -> HttpResponse:
    organization = _organization_for(request.user, org_slug)
    if not _is_org_admin(request.user, organization):
        raise Http404
    form = MembershipForm(request.POST or None) if request.POST.get("action") != "invite" else MembershipForm()
    invitation_form = InvitationForm(request.POST or None) if request.POST.get("action") == "invite" else InvitationForm()
    if request.method == "POST" and request.POST.get("action") in (None, "", "member") and form.is_valid():
        membership, created = Membership.objects.update_or_create(
            user=form.user, organization=organization,
            defaults={"role": form.cleaned_data["role"], "active": True},
        )
        messages.success(request, "Team member added." if created else "Team member updated.")
        return redirect("membership-list", org_slug=org_slug)
    if request.method == "POST" and request.POST.get("action") == "invite" and invitation_form.is_valid():
        raw_token = secrets.token_urlsafe(32)
        invitation = invitation_form.save(commit=False)
        invitation.organization = organization
        invitation.invited_by = request.user
        invitation.token_digest = hashlib.sha256(raw_token.encode()).hexdigest()
        invitation.expires_at = timezone.now() + timedelta(days=7)
        invitation.save()
        link = f'{settings.OMNI_BASE_URL}{reverse("invitation-accept", args=(raw_token,))}'
        send_mail(
            f"You are invited to Omni by R!SC",
            f"You were invited to join {organization.name} in Omni as {invitation.get_role_display()}.\n\nAccept within 7 days: {link}\n\nNo password or assessment data is included.",
            settings.DEFAULT_FROM_EMAIL, [invitation.email], fail_silently=True,
        )
        AuditEvent.objects.create(
            organization=organization, actor=request.user, action="invitation.created",
            object_type="OrganizationInvitation", object_id=str(invitation.id),
            detail={"role": invitation.role},
        )
        messages.success(request, "Invitation created and email delivery attempted.")
        return redirect("membership-list", org_slug=org_slug)
    return render(request, "webapp/membership_list.html", {
        "organization": organization,
        "memberships": organization.memberships.select_related("user").order_by("user__username"),
        "form": form, "invitation_form": invitation_form,
        "invitations": organization.invitations.all()[:50],
    })


def invitation_accept(request: HttpRequest, token: str) -> HttpResponse:
    digest = hashlib.sha256(token.encode()).hexdigest()
    invitation = get_object_or_404(
        OrganizationInvitation.objects.select_related("organization"), token_digest=digest
    )
    if not invitation.is_usable:
        return render(request, "webapp/invitation_invalid.html", status=410)
    existing = get_user_model().objects.filter(email__iexact=invitation.email).first()
    form = InvitationAcceptForm(request.POST or None) if not existing else None
    if request.method == "POST" and (existing or form.is_valid()):
        user = existing
        if not user:
            base = invitation.email.split("@", 1)[0]
            username, suffix = base, 2
            while get_user_model().objects.filter(username=username).exists():
                username, suffix = f"{base}{suffix}", suffix + 1
            user = get_user_model().objects.create_user(
                username=username, email=invitation.email,
                first_name=form.cleaned_data["first_name"], last_name=form.cleaned_data["last_name"],
                password=form.cleaned_data["password1"],
            )
        Membership.objects.update_or_create(
            user=user, organization=invitation.organization,
            defaults={"role": invitation.role, "active": True},
        )
        invitation.status = OrganizationInvitation.Status.ACCEPTED
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=("status", "accepted_at"))
        AuditEvent.objects.create(
            organization=invitation.organization, actor=user, action="invitation.accepted",
            object_type="OrganizationInvitation", object_id=str(invitation.id), detail={},
        )
        if existing:
            messages.success(request, "Invitation accepted. Sign in to continue.")
            return redirect("login")
        login(request, user)
        return redirect("organization-list")
    return render(request, "webapp/invitation_accept.html", {
        "invitation": invitation, "form": form, "existing": bool(existing),
    })


@login_required
def membership_toggle(request: HttpRequest, org_slug: str, membership_id: int) -> HttpResponse:
    if request.method != "POST":
        raise Http404
    organization = _organization_for(request.user, org_slug)
    if not _is_org_admin(request.user, organization):
        raise Http404
    membership = get_object_or_404(organization.memberships, id=membership_id)
    if membership.active and membership.role == Membership.Role.ADMIN and organization.memberships.filter(
        active=True, role=Membership.Role.ADMIN
    ).count() == 1:
        messages.error(request, "The last active organization administrator cannot be disabled.")
        return redirect("membership-list", org_slug=org_slug)
    assignment_count = (
        membership.primary_control_assignments.count()
        + membership.evidence_requests.count()
        + membership.owned_remediation_plans.count()
        + membership.remediation_milestones.count()
    )
    if membership.active and assignment_count and request.POST.get("confirm") != "yes":
        messages.error(request, f"This user has {assignment_count} active work assignments. Confirm deactivation after transferring work.")
        return redirect("membership-list", org_slug=org_slug)
    membership.active = not membership.active
    membership.save(update_fields=("active",))
    AuditEvent.objects.create(
        organization=organization, actor=request.user,
        action="membership.activated" if membership.active else "membership.deactivated",
        object_type="Membership", object_id=str(membership.id),
        detail={"assignment_count": assignment_count},
    )
    messages.success(request, "Membership activated." if membership.active else "Membership deactivated.")
    return redirect("membership-list", org_slug=org_slug)


@login_required
def invitation_cancel(request: HttpRequest, org_slug: str, invitation_id: int) -> HttpResponse:
    if request.method != "POST":
        raise Http404
    organization = _organization_for(request.user, org_slug)
    if not _is_org_admin(request.user, organization):
        raise Http404
    invitation = get_object_or_404(organization.invitations, id=invitation_id)
    invitation.status = OrganizationInvitation.Status.CANCELLED
    invitation.save(update_fields=("status",))
    AuditEvent.objects.create(
        organization=organization, actor=request.user, action="invitation.cancelled",
        object_type="OrganizationInvitation", object_id=str(invitation.id), detail={},
    )
    return redirect("membership-list", org_slug=org_slug)


@login_required
def assessment_access(request: HttpRequest, org_slug: str, assessment_id: int) -> HttpResponse:
    organization = _organization_for(request.user, org_slug)
    assessment = get_object_or_404(Assessment, id=assessment_id, system__organization=organization)
    if not _is_org_admin(request.user, organization):
        raise Http404
    form = AssessmentAccessForm(
        request.POST or None, organization=organization, assessment=assessment
    )
    if request.method == "POST" and form.is_valid():
        grant = form.save(commit=False)
        grant.assessment = assessment
        grant.granted_by = request.user
        grant.save()
        AuditEvent.objects.create(
            organization=organization, actor=request.user, action="assessment_access.granted",
            object_type="AssessmentAccess", object_id=str(grant.id), detail={"access": grant.access},
        )
        return redirect("assessment-access", org_slug=org_slug, assessment_id=assessment.id)
    return render(request, "webapp/assessment_access.html", {
        "organization": organization, "assessment": assessment, "form": form,
        "grants": assessment.access_grants.select_related("membership__user", "granted_by"),
    })


@login_required
def access_review_export(request: HttpRequest, org_slug: str) -> HttpResponse:
    organization = _organization_for(request.user, org_slug)
    if not _is_org_admin(request.user, organization):
        raise Http404
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["User", "Email", "Organization Role", "Active", "Last Login", "Assessment Access", "Outstanding Assignments"])
    for membership in organization.memberships.select_related("user").order_by("user__username"):
        grants = "; ".join(
            f"{grant.assessment.name} ({grant.get_access_display()})"
            for grant in membership.assessment_access.select_related("assessment")
        )
        assignments = (
            membership.primary_control_assignments.count() + membership.evidence_requests.count()
            + membership.owned_remediation_plans.count() + membership.remediation_milestones.count()
        )
        writer.writerow([
            membership.user.get_full_name() or membership.user.username,
            membership.user.email, membership.get_role_display(), membership.active,
            membership.user.last_login or "", grants, assignments,
        ])
    AuditEvent.objects.create(
        organization=organization, actor=request.user, action="access_review.exported",
        object_type="Organization", object_id=str(organization.id), detail={},
    )
    response = HttpResponse(output.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="omni-{organization.slug}-access-review.csv"'
    return response


@login_required
def assessment_list(
    request: HttpRequest, org_slug: str, system_id: int
) -> HttpResponse:
    organization = _organization_for(request.user, org_slug)
    system = get_object_or_404(System, id=system_id, organization=organization)
    assessments = system.assessments.all()
    membership = organization.memberships.filter(user=request.user, active=True).first()
    if membership and membership.role != Membership.Role.ADMIN:
        restricted_ids = AssessmentAccess.objects.filter(
            assessment__system=system
        ).values_list("assessment_id", flat=True).distinct()
        assessments = assessments.filter(
            Q(id__in=AssessmentAccess.objects.filter(membership=membership).values("assessment_id"))
            | ~Q(id__in=restricted_ids)
        )
    return render(
        request,
        "webapp/assessment_list.html",
        {
            "organization": organization,
            "system": system,
            "assessments": assessments,
            "can_admin": _is_org_admin(request.user, organization),
            "can_edit": _can_edit(request.user, organization),
            "can_admin": _is_org_admin(request.user, organization),
        },
    )


@login_required
def assessment_create(
    request: HttpRequest, org_slug: str, system_id: int
) -> HttpResponse:
    organization = _organization_for(request.user, org_slug)
    system = get_object_or_404(System, id=system_id, organization=organization)
    if not _can_edit(request.user, organization):
        raise Http404
    if request.method == "POST":
        form = AssessmentForm(request.POST)
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.system = system
            assessment.framework = form.cleaned_data["primary_framework"]
            assessment.created_by = request.user
            assessment.status = Assessment.Status.IN_PROGRESS
            assessment.save()
            AssessmentFramework.objects.bulk_create([
                AssessmentFramework(
                    assessment=assessment, framework=framework,
                    is_primary=framework == assessment.framework, added_by=request.user,
                )
                for framework in form.cleaned_data["frameworks"]
            ])
            ControlAssessment.objects.bulk_create(
                [
                    ControlAssessment(assessment=assessment, requirement=requirement)
                    for framework in form.cleaned_data["frameworks"]
                    for requirement in framework.requirements.all()
                ]
            )
            for result in assessment.control_results.select_related("requirement"):
                ObjectiveAssessment.objects.bulk_create([
                    ObjectiveAssessment(control_result=result, objective=objective)
                    for objective in result.requirement.objectives.all()
                ])
            AuditEvent.objects.create(
                organization=organization,
                actor=request.user,
                action="assessment.created",
                object_type="Assessment",
                object_id=str(assessment.id),
                detail={
                    "primary_framework": assessment.framework.code,
                    "frameworks": [item.code for item in form.cleaned_data["frameworks"]],
                },
            )
            return redirect(
                "assessment-dashboard", org_slug=org_slug, assessment_id=assessment.id
            )
    else:
        form = AssessmentForm()
    return render(
        request,
        "webapp/assessment_form.html",
        {"organization": organization, "system": system, "form": form},
    )


def _selected_frameworks(assessment: Assessment):
    selected = Framework.objects.filter(
        assessment_selections__assessment=assessment
    ).order_by("name", "version")
    return selected if selected.exists() else Framework.objects.filter(pk=assessment.framework_id)


def _framework_has_work(assessment: Assessment, framework: Framework) -> bool:
    results = assessment.control_results.filter(requirement__framework=framework)
    return results.filter(
        Q(status__in=(
            ControlAssessment.Status.MET,
            ControlAssessment.Status.NOT_MET,
            ControlAssessment.Status.NOT_APPLICABLE,
        ))
        | ~Q(assessor_notes_findings="")
        | ~Q(control_owner="")
        | Q(primary_owner__isnull=False)
        | Q(supporting_owners__isnull=False)
        | Q(updated_by__isnull=False)
        | ~Q(ssp_reference="")
        | Q(evidence_artifacts__isnull=False)
        | Q(evidence_requests__isnull=False)
        | Q(remediation_plans__isnull=False)
    ).exists()


@login_required
@transaction.atomic
def assessment_frameworks(
    request: HttpRequest, org_slug: str, assessment_id: int
) -> HttpResponse:
    organization, assessment = _assessment_for(request.user, org_slug, assessment_id)
    if not _can_edit(request.user, organization):
        raise Http404
    _require_unlocked(assessment)
    form = AssessmentForm(request.POST or None, instance=assessment)
    if request.method == "POST" and form.is_valid():
        selected = set(form.cleaned_data["frameworks"])
        current = set(_selected_frameworks(assessment))
        removed = current - selected
        blocked = [framework for framework in removed if _framework_has_work(assessment, framework)]
        if blocked:
            for framework in blocked:
                form.add_error(
                    "frameworks",
                    f"{framework} cannot be removed because assessment work is recorded.",
                )
        else:
            added = selected - current
            for framework in added:
                AssessmentFramework.objects.create(
                    assessment=assessment, framework=framework, added_by=request.user
                )
                ControlAssessment.objects.bulk_create([
                    ControlAssessment(assessment=assessment, requirement=requirement)
                    for requirement in framework.requirements.all()
                ])
                for result in assessment.control_results.filter(
                    requirement__framework=framework
                ).select_related("requirement"):
                    ObjectiveAssessment.objects.bulk_create([
                        ObjectiveAssessment(control_result=result, objective=objective)
                        for objective in result.requirement.objectives.all()
                    ])
            for framework in removed:
                assessment.control_results.filter(requirement__framework=framework).delete()
                AssessmentFramework.objects.filter(
                    assessment=assessment, framework=framework
                ).delete()
            primary = form.cleaned_data["primary_framework"]
            assessment.framework = primary
            assessment.name = form.cleaned_data["name"]
            assessment.save(update_fields=("framework", "name", "updated_at"))
            AssessmentFramework.objects.filter(assessment=assessment).update(is_primary=False)
            AssessmentFramework.objects.update_or_create(
                assessment=assessment, framework=primary,
                defaults={"is_primary": True, "added_by": request.user},
            )
            AuditEvent.objects.create(
                organization=organization, actor=request.user,
                action="assessment.frameworks_updated", object_type="Assessment",
                object_id=str(assessment.id), detail={
                    "primary": primary.code,
                    "added": sorted(item.code for item in added),
                    "removed": sorted(item.code for item in removed),
                },
            )
            messages.success(request, "Assessment frameworks updated.")
            return redirect("assessment-dashboard", org_slug=org_slug,
                            assessment_id=assessment.id)
    return render(request, "webapp/assessment_frameworks.html", {
        "organization": organization, "assessment": assessment, "form": form,
    })


@login_required
def assessment_dashboard(
    request: HttpRequest, org_slug: str, assessment_id: int
) -> HttpResponse:
    organization = _organization_for(request.user, org_slug)
    assessment = get_object_or_404(
        Assessment.objects.select_related("system", "framework"),
        id=assessment_id,
        system__organization=organization,
    )
    if not _has_assessment_access(request.user, assessment):
        raise Http404
    all_results = assessment.control_results.select_related(
        "requirement__framework", "primary_owner__user"
    ).prefetch_related("supporting_owners")
    selected_frameworks = list(_selected_frameworks(assessment))
    framework_code = request.GET.get("framework", "").strip()
    active_framework = next(
        (item for item in selected_frameworks if item.code == framework_code), None
    )
    results = all_results.filter(requirement__framework=active_framework) if active_framework else all_results
    domain_filter = request.GET.get("domain", "").strip()
    if domain_filter:
        results = results.filter(requirement__domain=domain_filter)
    counts = {
        value: results.filter(status=value).count()
        for value in ControlAssessment.Status.values
    }
    total = results.count()
    assessed = total - counts[ControlAssessment.Status.NOT_ASSESSED]
    framework_metrics = []
    for framework in selected_frameworks:
        framework_results = all_results.filter(requirement__framework=framework)
        framework_total = framework_results.count()
        framework_assessed = framework_results.exclude(
            status=ControlAssessment.Status.NOT_ASSESSED
        ).count()
        deduction = framework_results.aggregate(total=Sum("calculated_deduction"))["total"] or 0
        score = None
        if framework.scoring_method in (
            Framework.ScoringMethod.SPRS, Framework.ScoringMethod.DEDUCTION
        ) and framework.maximum_score is not None:
            score = framework.maximum_score - deduction
        framework_metrics.append({
            "framework": framework, "total": framework_total,
            "assessed": framework_assessed,
            "completion": round(framework_assessed / framework_total * 100, 1)
            if framework_total else 0, "score": score,
        })
    primary_metric = next(
        (item for item in framework_metrics if item["framework"].pk == assessment.framework_id),
        None,
    )
    evidence_counts = {
        value: assessment.evidence_requests.filter(status=value).count()
        for value in EvidenceRequest.Status.values
    }
    evidence_total = sum(evidence_counts.values())
    evidence_ready = evidence_counts[EvidenceRequest.Status.ACCEPTED]
    objective_results = ObjectiveAssessment.objects.filter(
        control_result__assessment=assessment
    )
    if active_framework:
        objective_results = objective_results.filter(
            control_result__requirement__framework=active_framework
        )
    if domain_filter:
        objective_results = objective_results.filter(
            control_result__requirement__domain=domain_filter
        )
    objective_counts = {
        value: objective_results.filter(status=value).count()
        for value in ObjectiveAssessment.Status.values
    }
    objective_total = sum(objective_counts.values())
    objective_complete = objective_total - objective_counts[ObjectiveAssessment.Status.NOT_ASSESSED]
    domain_metrics = list(
        results.values("requirement__domain")
        .annotate(
            total=Count("id"),
            met=Count("id", filter=Q(status=ControlAssessment.Status.MET)),
            not_met=Count("id", filter=Q(status=ControlAssessment.Status.NOT_MET)),
            unassessed=Count("id", filter=Q(status=ControlAssessment.Status.NOT_ASSESSED)),
            deduction=Sum("calculated_deduction"),
        )
        .order_by("requirement__domain")
    )
    for item in domain_metrics:
        item["completion"] = round(
            (item["total"] - item["unassessed"]) / item["total"] * 100, 1
        ) if item["total"] else 0
    all_domains = list(
        all_results.values_list("requirement__domain", flat=True).distinct().order_by("requirement__domain")
    )
    today = timezone.localdate()
    open_evidence = assessment.evidence_requests.exclude(status=EvidenceRequest.Status.ACCEPTED)
    evidence_overdue = open_evidence.filter(due_date__lt=today).count()
    remediation_active = assessment.remediation_plans.exclude(
        status__in=(RemediationPlan.Status.CLOSED, RemediationPlan.Status.RISK_ACCEPTED)
    )
    high_risk = remediation_active.filter(
        Q(priority__in=(RemediationPlan.Priority.HIGH, RemediationPlan.Priority.CRITICAL))
        | Q(severity__in=(RemediationPlan.Priority.HIGH, RemediationPlan.Priority.CRITICAL))
    ).count()
    owner_workload = list(
        results.exclude(primary_owner=None)
        .values("primary_owner__user__username", "primary_owner__user__first_name", "primary_owner__user__last_name")
        .annotate(
            assigned=Count("id"),
            completed=Count("id", filter=~Q(status=ControlAssessment.Status.NOT_ASSESSED)),
            findings=Count("id", filter=Q(status=ControlAssessment.Status.NOT_MET)),
        )
        .order_by("primary_owner__user__username")
    )
    for owner in owner_workload:
        owner["name"] = (
            f'{owner["primary_owner__user__first_name"]} {owner["primary_owner__user__last_name"]}'.strip()
            or owner["primary_owner__user__username"]
        )
        owner["completion"] = round(owner["completed"] / owner["assigned"] * 100, 1)
    blockers = []
    if objective_counts[ObjectiveAssessment.Status.NOT_ASSESSED]:
        blockers.append(f'{objective_counts[ObjectiveAssessment.Status.NOT_ASSESSED]} objectives remain unassessed')
    if assessment.quality_review_status != "APPROVED":
        blockers.append(f'Quality review is {assessment.get_quality_review_status_display().lower()}')
    if evidence_overdue:
        blockers.append(f'{evidence_overdue} evidence requests are overdue')
    readiness = round(max(0, 100 - (len(blockers) * 20)), 0)
    timeline = [
        {"label": "Engagement starts", "date": assessment.engagement_start},
        {"label": "Engagement ends", "date": assessment.engagement_end},
    ]
    timeline.extend(
        {"label": f"Evidence: {item.title}", "date": item.due_date}
        for item in open_evidence.filter(due_date__isnull=False).order_by("due_date")[:5]
    )
    timeline.extend(
        {"label": f"Remediation: {item.remediation_id}", "date": item.planned_completion}
        for item in remediation_active.filter(planned_completion__isnull=False).order_by("planned_completion")[:5]
    )
    timeline = sorted((item for item in timeline if item["date"]), key=lambda item: item["date"])[:8]
    return render(
        request,
        "webapp/assessment_dashboard.html",
        {
            "organization": organization,
            "assessment": assessment,
            "results": results,
            "counts": counts,
            "met_count": counts[ControlAssessment.Status.MET],
            "not_met_count": counts[ControlAssessment.Status.NOT_MET],
            "not_assessed_count": counts[ControlAssessment.Status.NOT_ASSESSED],
            "not_applicable_count": counts[ControlAssessment.Status.NOT_APPLICABLE],
            "score": primary_metric["score"] if primary_metric else None,
            "score_label": assessment.framework.get_scoring_method_display(),
            "completion": round(assessed / total * 100, 1) if total else 0,
            "framework_metrics": framework_metrics,
            "selected_frameworks": selected_frameworks,
            "active_framework": active_framework,
            "can_edit": _can_edit(request.user, organization),
            "can_manage_evidence": _can_manage_evidence(request.user, organization),
            "evidence_total": evidence_total,
            "evidence_ready": evidence_ready,
            "evidence_readiness": round(evidence_ready / evidence_total * 100, 1)
            if evidence_total else 0,
            "remediation_open": assessment.remediation_plans.exclude(
                status__in=(RemediationPlan.Status.CLOSED, RemediationPlan.Status.RISK_ACCEPTED)
            ).count(),
            "remediation_overdue": assessment.remediation_plans.filter(
                planned_completion__lt=timezone.localdate()
            ).exclude(status__in=(RemediationPlan.Status.CLOSED, RemediationPlan.Status.RISK_ACCEPTED)).count(),
            "objective_counts": objective_counts,
            "objective_total": objective_total,
            "objective_completion": round(objective_complete / objective_total * 100, 1)
            if objective_total else 0,
            "domain_metrics": domain_metrics,
            "all_domains": all_domains,
            "domain_filter": domain_filter,
            "evidence_overdue": evidence_overdue,
            "high_risk_remediation": high_risk,
            "owner_workload": owner_workload,
            "readiness_score": readiness,
            "readiness_blockers": blockers,
            "timeline": timeline,
        },
    )


@login_required
def dashboard_export(request: HttpRequest, org_slug: str, assessment_id: int) -> HttpResponse:
    organization, assessment = _assessment_for(request.user, org_slug, assessment_id)
    results = assessment.control_results.select_related("requirement__framework", "primary_owner__user")
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["Omni Executive Assessment Snapshot"])
    writer.writerow(["Organization", organization.name])
    writer.writerow(["System", assessment.system.name])
    writer.writerow(["Assessment", assessment.name])
    writer.writerow(["Status", assessment.get_status_display()])
    writer.writerow(["Quality Review", assessment.get_quality_review_status_display()])
    writer.writerow([])
    writer.writerow(["Framework", "Requirement", "Domain", "Status", "Deduction", "Owner", "Evidence"])
    for result in results.order_by("requirement__framework__code", "requirement__requirement_id"):
        owner = ""
        if result.primary_owner:
            owner = result.primary_owner.user.get_full_name() or result.primary_owner.user.username
        writer.writerow([
            result.requirement.framework.code, result.requirement.requirement_id,
            result.requirement.domain, result.status, result.calculated_deduction,
            owner, result.evidence_artifacts.count(),
        ])
    AuditEvent.objects.create(
        organization=organization, actor=request.user, action="dashboard.exported",
        object_type="Assessment", object_id=str(assessment.id),
        detail={"format": "CSV", "rows": results.count()},
    )
    response = HttpResponse(output.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="omni-{assessment.id}-executive-dashboard.csv"'
    return response


def _assessment_for(user, org_slug: str, assessment_id: int):
    organization = _organization_for(user, org_slug)
    assessment = get_object_or_404(
        Assessment.objects.select_related("system", "framework"),
        id=assessment_id, system__organization=organization,
    )
    if not _has_assessment_access(user, assessment):
        raise Http404
    return organization, assessment


def _require_unlocked(assessment: Assessment) -> None:
    if assessment.locked:
        raise Http404


@login_required
def assessment_plan(request: HttpRequest, org_slug: str, assessment_id: int) -> HttpResponse:
    organization, assessment = _assessment_for(request.user, org_slug, assessment_id)
    if not _can_edit(request.user, organization):
        raise Http404
    if request.method == "POST":
        _require_unlocked(assessment)
    plan_form = AssessmentPlanForm(request.POST or None, instance=assessment)
    team_form = AssessmentTeamForm(
        request.POST or None, organization=organization, prefix="team"
    )
    if request.method == "POST" and request.POST.get("action") == "plan" and plan_form.is_valid():
        plan_form.save()
        AuditEvent.objects.create(
            organization=organization, actor=request.user, action="assessment.plan_updated",
            object_type="Assessment", object_id=str(assessment.id), detail={},
        )
        messages.success(request, "Assessment plan updated.")
        return redirect("assessment-plan", org_slug=org_slug, assessment_id=assessment.id)
    if request.method == "POST" and request.POST.get("action") == "team" and team_form.is_valid():
        member = team_form.save(commit=False)
        member.assessment = assessment
        member.save()
        messages.success(request, "Assessment team member added.")
        return redirect("assessment-plan", org_slug=org_slug, assessment_id=assessment.id)
    return render(request, "webapp/assessment_plan.html", {
        "organization": organization, "assessment": assessment,
        "plan_form": plan_form, "team_form": team_form,
        "team": assessment.team_members.select_related("membership__user"),
    })


@login_required
def assessment_execution(request: HttpRequest, org_slug: str, assessment_id: int) -> HttpResponse:
    organization, assessment = _assessment_for(request.user, org_slug, assessment_id)
    results = assessment.control_results.select_related(
        "requirement__framework"
    ).prefetch_related("objective_results__objective", "objective_results__evidence")
    method = request.GET.get("method", "").upper()
    framework = request.GET.get("framework", "")
    assessor = request.GET.get("assessor", "")
    if framework:
        results = results.filter(requirement__framework__code=framework)
    objectives = ObjectiveAssessment.objects.filter(control_result__in=results).select_related(
        "objective", "control_result__requirement__framework", "assessed_by"
    ).prefetch_related("objective__procedures", "evidence")
    if method:
        objectives = objectives.filter(objective__procedures__method=method).distinct()
    if assessor.isdigit():
        objectives = objectives.filter(assessed_by_id=int(assessor))
    counts = {
        value: objectives.filter(status=value).count()
        for value in ObjectiveAssessment.Status.values
    }
    return render(request, "webapp/assessment_execution.html", {
        "organization": organization, "assessment": assessment,
        "objectives": objectives, "counts": counts,
        "total": objectives.count(), "frameworks": _selected_frameworks(assessment),
        "methods": AssessmentProcedure.Method.choices,
        "assessors": get_user_model().objects.filter(
            assessed_objectives__control_result__assessment=assessment
        ).distinct(),
        "filters": {"method": method, "framework": framework, "assessor": assessor},
        "can_edit": _can_edit(request.user, organization) and not assessment.locked,
    })


@login_required
def objective_edit(
    request: HttpRequest, org_slug: str, assessment_id: int, objective_result_id: int
) -> HttpResponse:
    organization, assessment = _assessment_for(request.user, org_slug, assessment_id)
    if not _can_edit(request.user, organization):
        raise Http404
    _require_unlocked(assessment)
    result = get_object_or_404(
        ObjectiveAssessment.objects.select_related(
            "objective__requirement", "control_result__requirement"
        ), id=objective_result_id, control_result__assessment=assessment,
    )
    form = ObjectiveAssessmentForm(request.POST or None, instance=result, assessment=assessment)
    if request.method == "POST" and form.is_valid():
        result = form.save(commit=False)
        result.assessed_by = request.user
        result.assessed_at = timezone.now()
        result.save()
        form.save_m2m()
        result.control_result.derive_from_objectives()
        AuditEvent.objects.create(
            organization=organization, actor=request.user, action="objective.assessed",
            object_type="ObjectiveAssessment", object_id=str(result.id),
            detail={"objective": str(result.objective), "status": result.status},
        )
        if result.status == ObjectiveAssessment.Status.NOT_MET:
            notify_assessment_team(
                assessment, category=Notification.Category.REMEDIATION,
                title=f"Finding recorded for {result.control_result.requirement.requirement_id}",
                message="An assessment objective was marked NOT MET and may require a remediation plan.",
                action_url=f'{assessment_url(assessment, "remediation-create")}?control={result.control_result_id}',
                actor=request.user, object_type="ObjectiveAssessment", object_id=result.id,
                event="finding.recorded", new_status=result.status,
            )
        messages.success(request, "Objective result saved; control outcome recalculated.")
        return redirect("assessment-execution", org_slug=org_slug, assessment_id=assessment.id)
    return render(request, "webapp/objective_form.html", {
        "organization": organization, "assessment": assessment, "result": result, "form": form,
    })


def _execution_create(request, org_slug, assessment_id, form_class, title, action):
    organization, assessment = _assessment_for(request.user, org_slug, assessment_id)
    if not _can_edit(request.user, organization):
        raise Http404
    _require_unlocked(assessment)
    kwargs = {"assessment": assessment}
    if form_class in (InterviewSessionForm, TestExecutionForm):
        kwargs["organization"] = organization
    form = form_class(request.POST or None, **kwargs)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.assessment = assessment
        item.save()
        form.save_m2m()
        AuditEvent.objects.create(
            organization=organization, actor=request.user, action=action,
            object_type=item.__class__.__name__, object_id=str(item.id), detail={},
        )
        messages.success(request, f"{title} saved.")
        return redirect("assessment-execution", org_slug=org_slug, assessment_id=assessment.id)
    return render(request, "webapp/entity_form.html", {
        "organization": organization, "form": form, "title": title,
        "eyebrow": assessment.name, "submit_label": f"Save {title.lower()}",
    })


@login_required
def interview_create(request, org_slug, assessment_id):
    return _execution_create(request, org_slug, assessment_id, InterviewSessionForm,
                             "Interview session", "interview.created")


@login_required
def sample_create(request, org_slug, assessment_id):
    return _execution_create(request, org_slug, assessment_id, AssessmentSampleForm,
                             "Assessment sample", "sample.created")


@login_required
def test_execution_create(request, org_slug, assessment_id):
    return _execution_create(request, org_slug, assessment_id, TestExecutionForm,
                             "Test execution", "test_execution.created")


@login_required
def quality_review(request: HttpRequest, org_slug: str, assessment_id: int) -> HttpResponse:
    organization, assessment = _assessment_for(request.user, org_slug, assessment_id)
    if not _can_edit(request.user, organization):
        raise Http404
    form = QualityReviewForm(request.POST or None, instance=assessment)
    if request.method == "POST":
        _require_unlocked(assessment)
        if form.is_valid():
            previous_status = assessment.quality_review_status
            form.save()
            AuditEvent.objects.create(
                organization=organization, actor=request.user, action="quality_review.updated",
                object_type="Assessment", object_id=str(assessment.id),
                detail={"status": assessment.quality_review_status},
            )
            notify_assessment_team(
                assessment, category=Notification.Category.QUALITY,
                title=f"Quality review: {assessment.get_quality_review_status_display()}",
                message="The assessment quality-review status changed. Open Omni to review the details.",
                action_url=assessment_url(assessment, "quality-review"), actor=request.user,
                object_type="Assessment", object_id=assessment.id,
                event="quality_review.transitioned", previous_status=previous_status,
                new_status=assessment.quality_review_status,
                comment=assessment.quality_review_notes,
            )
            messages.success(request, "Quality review updated.")
            return redirect("quality-review", org_slug=org_slug, assessment_id=assessment.id)
    unassessed = assessment.control_results.filter(
        objective_results__status=ObjectiveAssessment.Status.NOT_ASSESSED
    ).distinct().count()
    return render(request, "webapp/quality_review.html", {
        "organization": organization, "assessment": assessment, "form": form,
        "unassessed_objective_controls": unassessed,
    })


@login_required
def assessment_signoff(request: HttpRequest, org_slug: str, assessment_id: int) -> HttpResponse:
    if request.method != "POST":
        raise Http404
    organization, assessment = _assessment_for(request.user, org_slug, assessment_id)
    if not _can_edit(request.user, organization):
        raise Http404
    _require_unlocked(assessment)
    if assessment.quality_review_status != "APPROVED":
        messages.error(request, "Quality review must be approved before sign-off.")
    elif assessment.control_results.filter(
        objective_results__status=ObjectiveAssessment.Status.NOT_ASSESSED
    ).exists():
        messages.error(request, "All assessment objectives must be completed before sign-off.")
    else:
        assessment.status = Assessment.Status.COMPLETE
        assessment.locked = True
        assessment.signed_off_by = request.user
        assessment.signed_off_at = timezone.now()
        assessment.save()
        AuditEvent.objects.create(
            organization=organization, actor=request.user, action="assessment.signed_off",
            object_type="Assessment", object_id=str(assessment.id), detail={},
        )
        notify(
            recipients=organization_users(organization), organization=organization,
            assessment=assessment, category=Notification.Category.SYSTEM,
            title="Assessment signed off", message="The assessment was approved, signed off, and locked.",
            action_url=assessment_url(assessment), actor=request.user,
            object_type="Assessment", object_id=assessment.id,
            event="assessment.signoff_notified", previous_status=Assessment.Status.IN_PROGRESS,
            new_status=Assessment.Status.COMPLETE, mandatory=True,
        )
        messages.success(request, "Assessment signed off and locked.")
    return redirect("quality-review", org_slug=org_slug, assessment_id=assessment.id)


@login_required
def assessment_reopen(request: HttpRequest, org_slug: str, assessment_id: int) -> HttpResponse:
    organization, assessment = _assessment_for(request.user, org_slug, assessment_id)
    if not _is_org_admin(request.user, organization) or not assessment.locked:
        raise Http404
    form = ReopenAssessmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        assessment.locked = False
        assessment.status = Assessment.Status.IN_PROGRESS
        assessment.reopened_by = request.user
        assessment.reopened_at = timezone.now()
        assessment.reopen_reason = form.cleaned_data["reason"]
        assessment.save()
        AuditEvent.objects.create(
            organization=organization, actor=request.user, action="assessment.reopened",
            object_type="Assessment", object_id=str(assessment.id),
            detail={"reason": form.cleaned_data["reason"]},
        )
        notify_assessment_team(
            assessment, category=Notification.Category.SYSTEM,
            title="Assessment reopened", message="An administrator reopened the assessment. Sign-off is no longer final.",
            action_url=assessment_url(assessment), actor=request.user,
            object_type="Assessment", object_id=assessment.id,
            event="assessment.reopen_notified", previous_status=Assessment.Status.COMPLETE,
            new_status=Assessment.Status.IN_PROGRESS, comment=form.cleaned_data["reason"],
            mandatory=True,
        )
        messages.success(request, "Assessment reopened with an audit record.")
        return redirect("assessment-dashboard", org_slug=org_slug, assessment_id=assessment.id)
    return render(request, "webapp/entity_form.html", {
        "organization": organization, "form": form, "title": "Reopen assessment",
        "eyebrow": assessment.name, "submit_label": "Reopen assessment",
    })


def _generate_cmmc_drl(assessment: Assessment, framework: Framework | None = None):
    from src.evidence_requests.assessment_procedure_loader import AssessmentProcedureLoader
    from src.evidence_requests.catalog_compiler import CatalogCompiler
    from src.evidence_requests.request_generator import RequestGenerator
    from src.evidence_requests.request_optimizer import RequestOptimizer

    framework = framework or assessment.framework
    source = Path(settings.BASE_DIR) / "data" / "sp800-171a-assessment-procedures.xlsx"
    fallback = {
        "SC.L2-3.13.12": (
            "Prohibit remote activation of collaborative computing devices and "
            "provide indication of devices in use to users present at the device."
        )
    }
    loader = AssessmentProcedureLoader(
        framework_id=framework.code,
        framework_name=framework.name,
        framework_version=framework.version,
        source_document="NIST SP 800-171A",
        requirement_text_provider=fallback.get,
    )
    dataset = loader.load(source)
    knowledge = CatalogCompiler().compile(dataset.rows)
    raw = RequestGenerator().generate(
        knowledge, framework_id=framework.code,
        engagement_name=assessment.name,
        organization_name=assessment.system.organization.name,
    )
    return RequestOptimizer().optimize(raw)


@login_required
@transaction.atomic
def evidence_request_generate(
    request: HttpRequest, org_slug: str, assessment_id: int
) -> HttpResponse:
    if request.method != "POST":
        raise Http404
    organization, assessment = _assessment_for(request.user, org_slug, assessment_id)
    if not _can_edit(request.user, organization):
        raise Http404
    cmmc_framework = next(
        (item for item in _selected_frameworks(assessment)
         if item.code.upper().startswith("CMMC")), None
    )
    if cmmc_framework is None:
        messages.error(request, "Automatic evidence generation is not configured for this framework yet.")
        return redirect("evidence-list", org_slug=org_slug, assessment_id=assessment.id)
    collection = _generate_cmmc_drl(assessment, cmmc_framework)
    results_by_id = {
        item.requirement.requirement_id.casefold(): item
        for item in assessment.control_results.filter(
            requirement__framework=cmmc_framework
        ).select_related("requirement")
    }
    existing = {
        title.casefold() for title in assessment.evidence_requests.values_list("title", flat=True)
    }
    created_count = 0
    for generated in collection.requests:
        if generated.requested_item.casefold() in existing:
            continue
        item = EvidenceRequest.objects.create(
            assessment=assessment, title=generated.requested_item,
            description=generated.description, status=EvidenceRequest.Status.REQUESTED,
            created_by=request.user,
        )
        mapped = [
            results_by_id[control.control_id.casefold()]
            for control in generated.controls
            if control.control_id.casefold() in results_by_id
        ]
        item.controls.set(mapped)
        existing.add(generated.requested_item.casefold())
        created_count += 1
    AuditEvent.objects.create(
        organization=organization, actor=request.user,
        action="evidence_requests.generated", object_type="Assessment",
        object_id=str(assessment.id), detail={"created": created_count},
    )
    messages.success(request, f"Generated {created_count} optimized evidence requests.")
    return redirect("evidence-list", org_slug=org_slug, assessment_id=assessment.id)


@login_required
def evidence_list(request: HttpRequest, org_slug: str, assessment_id: int) -> HttpResponse:
    organization, assessment = _assessment_for(request.user, org_slug, assessment_id)
    evidence_requests = assessment.evidence_requests.select_related(
        "owner__user"
    ).prefetch_related("controls__requirement", "artifacts")
    artifacts = assessment.evidence_artifacts.select_related("uploaded_by").prefetch_related(
        "controls__requirement", "requests"
    )
    status = request.GET.get("status", "").strip()
    domain = request.GET.get("domain", "").strip()
    owner = request.GET.get("owner", "").strip()
    query = request.GET.get("q", "").strip()
    if status:
        evidence_requests = evidence_requests.filter(status=status)
    if domain:
        evidence_requests = evidence_requests.filter(
            controls__requirement__domain=domain
        ).distinct()
    if owner.isdigit():
        evidence_requests = evidence_requests.filter(owner_id=int(owner))
    if query:
        evidence_requests = evidence_requests.filter(title__icontains=query)
        artifacts = artifacts.filter(title__icontains=query)
    domains = assessment.control_results.values_list(
        "requirement__domain", flat=True
    ).distinct().order_by("requirement__domain")
    return render(request, "webapp/evidence_list.html", {
        "organization": organization, "assessment": assessment,
        "evidence_requests": evidence_requests, "artifacts": artifacts,
        "statuses": EvidenceRequest.Status.choices, "domains": domains,
        "memberships": organization.memberships.filter(active=True).select_related("user"),
        "filters": {"status": status, "domain": domain, "owner": owner, "q": query},
        "can_edit": _can_edit(request.user, organization),
        "can_manage_evidence": _can_manage_evidence(request.user, organization),
    })


@login_required
def evidence_request_create(
    request: HttpRequest, org_slug: str, assessment_id: int
) -> HttpResponse:
    organization, assessment = _assessment_for(request.user, org_slug, assessment_id)
    if not _can_edit(request.user, organization):
        raise Http404
    _require_unlocked(assessment)
    form = EvidenceRequestForm(
        request.POST or None, organization=organization, assessment=assessment
    )
    if request.method == "POST" and form.is_valid():
        evidence_request = form.save(commit=False)
        evidence_request.assessment = assessment
        evidence_request.created_by = request.user
        evidence_request.save()
        form.save_m2m()
        AuditEvent.objects.create(
            organization=organization, actor=request.user, action="evidence_request.created",
            object_type="EvidenceRequest", object_id=str(evidence_request.id),
            detail={"title": evidence_request.title, "controls": evidence_request.controls.count()},
        )
        if evidence_request.owner and evidence_request.notify_owner:
            notify(
                recipients=[evidence_request.owner.user], organization=organization,
                assessment=assessment, category=Notification.Category.ASSIGNMENT,
                title="Evidence request assigned", message=f'You were assigned: {evidence_request.title}',
                action_url=assessment_url(assessment, "evidence-list"), actor=request.user,
                object_type="EvidenceRequest", object_id=evidence_request.id,
                event="evidence_request.assigned", new_status=evidence_request.status,
            )
        messages.success(request, "Evidence request created.")
        return redirect("evidence-list", org_slug=org_slug, assessment_id=assessment.id)
    return render(request, "webapp/entity_form.html", {
        "form": form, "title": "New evidence request", "organization": organization,
        "eyebrow": assessment.name, "submit_label": "Create request",
    })


@login_required
def evidence_request_edit(
    request: HttpRequest, org_slug: str, assessment_id: int, evidence_request_id: int
) -> HttpResponse:
    organization, assessment = _assessment_for(request.user, org_slug, assessment_id)
    if not _can_edit(request.user, organization):
        raise Http404
    _require_unlocked(assessment)
    evidence_request = get_object_or_404(
        EvidenceRequest, id=evidence_request_id, assessment=assessment
    )
    previous_status = evidence_request.status
    form = EvidenceRequestForm(
        request.POST or None, instance=evidence_request,
        organization=organization, assessment=assessment,
    )
    if request.method == "POST" and form.is_valid():
        evidence_request = form.save()
        AuditEvent.objects.create(
            organization=organization, actor=request.user, action="evidence_request.updated",
            object_type="EvidenceRequest", object_id=str(evidence_request.id),
            detail={"previous_status": previous_status, "status": evidence_request.status},
        )
        recipients = [evidence_request.owner.user] if evidence_request.owner else organization_users(
            organization, roles=(Membership.Role.ADMIN, Membership.Role.ASSESSOR)
        )
        notify(
            recipients=recipients, organization=organization, assessment=assessment,
            category=Notification.Category.EVIDENCE,
            title=f"Evidence request {evidence_request.get_status_display()}",
            message=f'The status of “{evidence_request.title}” changed.',
            action_url=assessment_url(assessment, "evidence-list"), actor=request.user,
            object_type="EvidenceRequest", object_id=evidence_request.id,
            event="evidence_request.transitioned", previous_status=previous_status,
            new_status=evidence_request.status,
        )
        messages.success(request, "Evidence request updated.")
        return redirect("evidence-list", org_slug=org_slug, assessment_id=assessment.id)
    return render(request, "webapp/entity_form.html", {
        "form": form, "title": "Edit evidence request", "organization": organization,
        "eyebrow": assessment.name, "submit_label": "Save request",
    })


@login_required
def evidence_artifact_create(
    request: HttpRequest, org_slug: str, assessment_id: int
) -> HttpResponse:
    organization, assessment = _assessment_for(request.user, org_slug, assessment_id)
    if not _can_manage_evidence(request.user, organization):
        raise Http404
    _require_unlocked(assessment)
    can_review = _can_edit(request.user, organization)
    form = EvidenceArtifactForm(
        request.POST or None, request.FILES or None, assessment=assessment,
        can_review=can_review,
    )
    if request.method == "POST" and form.is_valid():
        artifact = form.save(commit=False)
        artifact.organization = organization
        artifact.assessment = assessment
        artifact.uploaded_by = request.user
        artifact.save()
        form.save_m2m()
        artifact.requests.filter(status=EvidenceRequest.Status.REQUESTED).update(
            status=EvidenceRequest.Status.RECEIVED
        )
        AuditEvent.objects.create(
            organization=organization, actor=request.user, action="evidence_artifact.created",
            object_type="EvidenceArtifact", object_id=str(artifact.id),
            detail={"title": artifact.title, "controls": artifact.controls.count()},
        )
        notify_assessment_team(
            assessment, category=Notification.Category.EVIDENCE,
            title="Evidence received", message=f'New evidence was registered: {artifact.title}',
            action_url=assessment_url(assessment, "evidence-list"), actor=request.user,
            object_type="EvidenceArtifact", object_id=artifact.id,
            event="evidence.received", new_status=artifact.review_status,
        )
        messages.success(request, "Evidence artifact registered.")
        return redirect("evidence-list", org_slug=org_slug, assessment_id=assessment.id)
    return render(request, "webapp/evidence_artifact_form.html", {
        "form": form, "assessment": assessment, "organization": organization,
        "title": "Register evidence artifact", "submit_label": "Save artifact",
    })


@login_required
def evidence_artifact_edit(
    request: HttpRequest, org_slug: str, assessment_id: int, artifact_id: int
) -> HttpResponse:
    organization, assessment = _assessment_for(request.user, org_slug, assessment_id)
    if not _can_manage_evidence(request.user, organization):
        raise Http404
    _require_unlocked(assessment)
    artifact = get_object_or_404(
        EvidenceArtifact, id=artifact_id, assessment=assessment, organization=organization
    )
    previous_status = artifact.review_status
    can_review = _can_edit(request.user, organization)
    form = EvidenceArtifactForm(
        request.POST or None, request.FILES or None, instance=artifact,
        assessment=assessment, can_review=can_review,
    )
    if request.method == "POST" and form.is_valid():
        artifact = form.save()
        if artifact.review_status in (
            EvidenceArtifact.ReviewStatus.ACCEPTED,
            EvidenceArtifact.ReviewStatus.REJECTED,
            EvidenceArtifact.ReviewStatus.UNDER_REVIEW,
        ):
            artifact.requests.update(status=artifact.review_status)
        if artifact.review_status != previous_status:
            EvidenceReviewHistory.objects.create(
                artifact=artifact, reviewer=request.user, previous_status=previous_status,
                new_status=artifact.review_status, comment=artifact.assessor_notes,
            )
        AuditEvent.objects.create(
            organization=organization, actor=request.user, action="evidence_artifact.updated",
            object_type="EvidenceArtifact", object_id=str(artifact.id),
            detail={"review_status": artifact.review_status},
        )
        owners = [item.owner.user for item in artifact.requests.select_related("owner__user") if item.owner]
        if not owners:
            owners = [artifact.uploaded_by]
        notify(
            recipients=owners, organization=organization, assessment=assessment,
            category=Notification.Category.EVIDENCE,
            title=f"Evidence {artifact.get_review_status_display()}",
            message=f'The evidence review status changed for “{artifact.title}”.',
            action_url=assessment_url(assessment, "evidence-list"), actor=request.user,
            object_type="EvidenceArtifact", object_id=artifact.id,
            event="evidence.reviewed", previous_status=previous_status,
            new_status=artifact.review_status, comment=artifact.assessor_notes,
        )
        messages.success(request, "Evidence artifact updated.")
        return redirect("evidence-list", org_slug=org_slug, assessment_id=assessment.id)
    return render(request, "webapp/evidence_artifact_form.html", {
        "form": form, "assessment": assessment, "organization": organization,
        "title": "Review evidence artifact", "submit_label": "Save changes",
    })


@login_required
def evidence_artifact_download(
    request: HttpRequest, org_slug: str, assessment_id: int, artifact_id: int
) -> FileResponse:
    organization, assessment = _assessment_for(request.user, org_slug, assessment_id)
    artifact = get_object_or_404(
        EvidenceArtifact, id=artifact_id, assessment=assessment, organization=organization
    )
    if not artifact.file:
        raise Http404
    AuditEvent.objects.create(
        organization=organization, actor=request.user, action="evidence_artifact.downloaded",
        object_type="EvidenceArtifact", object_id=str(artifact.id),
        detail={"title": artifact.title},
    )
    return FileResponse(
        artifact.file.open("rb"), as_attachment=True,
        filename=artifact.file.name.rsplit("/", 1)[-1],
    )


def _next_remediation_id(assessment: Assessment) -> str:
    existing = assessment.remediation_plans.values_list("remediation_id", flat=True)
    numbers = []
    for value in existing:
        try:
            numbers.append(int(value.rsplit("-", 1)[-1]))
        except (TypeError, ValueError):
            continue
    return f"RAP-{max(numbers, default=0) + 1:04d}"


@login_required
def remediation_list(request: HttpRequest, org_slug: str, assessment_id: int) -> HttpResponse:
    organization, assessment = _assessment_for(request.user, org_slug, assessment_id)
    plans = assessment.remediation_plans.select_related(
        "owner__user", "validated_by"
    ).prefetch_related("controls__requirement", "milestones")
    status = request.GET.get("status", "").strip()
    priority = request.GET.get("priority", "").strip()
    domain = request.GET.get("domain", "").strip()
    owner = request.GET.get("owner", "").strip()
    due = request.GET.get("due", "").strip()
    query = request.GET.get("q", "").strip()
    if status:
        plans = plans.filter(status=status)
    if priority:
        plans = plans.filter(priority=priority)
    if domain:
        plans = plans.filter(controls__requirement__domain=domain).distinct()
    if owner.isdigit():
        plans = plans.filter(owner_id=int(owner))
    if due == "overdue":
        plans = plans.filter(planned_completion__lt=timezone.localdate()).exclude(
            status__in=(RemediationPlan.Status.CLOSED, RemediationPlan.Status.RISK_ACCEPTED)
        )
    if query:
        plans = plans.filter(title__icontains=query)
    all_plans = assessment.remediation_plans.all()
    open_count = all_plans.exclude(
        status__in=(RemediationPlan.Status.CLOSED, RemediationPlan.Status.RISK_ACCEPTED)
    ).count()
    overdue_count = all_plans.filter(planned_completion__lt=timezone.localdate()).exclude(
        status__in=(RemediationPlan.Status.CLOSED, RemediationPlan.Status.RISK_ACCEPTED)
    ).count()
    domains = assessment.control_results.values_list(
        "requirement__domain", flat=True
    ).distinct().order_by("requirement__domain")
    return render(request, "webapp/remediation_list.html", {
        "organization": organization, "assessment": assessment, "plans": plans,
        "open_count": open_count, "overdue_count": overdue_count,
        "closed_count": all_plans.filter(status=RemediationPlan.Status.CLOSED).count(),
        "statuses": RemediationPlan.Status.choices,
        "priorities": RemediationPlan.Priority.choices, "domains": domains,
        "memberships": organization.memberships.filter(active=True).select_related("user"),
        "filters": {"status": status, "priority": priority, "domain": domain,
                    "owner": owner, "due": due, "q": query},
        "can_edit": _can_edit(request.user, organization),
    })


@login_required
@transaction.atomic
def remediation_create(request: HttpRequest, org_slug: str, assessment_id: int) -> HttpResponse:
    organization, assessment = _assessment_for(request.user, org_slug, assessment_id)
    if not _can_edit(request.user, organization):
        raise Http404
    _require_unlocked(assessment)
    initial = {}
    result_id = request.GET.get("control", "")
    if result_id.isdigit():
        result = get_object_or_404(
            assessment.control_results.select_related("requirement"), id=int(result_id)
        )
        initial = {
            "title": f"Remediate {result.requirement.requirement_id}",
            "weakness_description": result.assessor_notes_findings,
            "controls": [result],
        }
    form = RemediationPlanForm(
        request.POST or None, initial=initial, organization=organization,
        assessment=assessment, can_validate=True,
        can_accept_risk=_is_org_admin(request.user, organization),
    )
    if request.method == "POST" and form.is_valid():
        plan = form.save(commit=False)
        plan.assessment = assessment
        plan.remediation_id = _next_remediation_id(assessment)
        plan.created_by = request.user
        if plan.validation_status == RemediationPlan.ValidationStatus.VALIDATED:
            plan.validated_by = request.user
            plan.validated_at = timezone.now()
        plan.save()
        form.save_m2m()
        AuditEvent.objects.create(
            organization=organization, actor=request.user, action="remediation.created",
            object_type="RemediationPlan", object_id=str(plan.id),
            detail={"remediation_id": plan.remediation_id, "controls": plan.controls.count()},
        )
        if plan.owner and plan.notify_owner:
            notify(
                recipients=[plan.owner.user], organization=organization, assessment=assessment,
                category=Notification.Category.ASSIGNMENT,
                title=f"Remediation assigned: {plan.remediation_id}",
                message=f'You own the remediation plan “{plan.title}”.',
                action_url=reverse("remediation-detail", args=(org_slug, assessment.id, plan.id)),
                actor=request.user, object_type="RemediationPlan", object_id=plan.id,
                event="remediation.assigned", new_status=plan.status,
            )
        messages.success(request, f"{plan.remediation_id} created.")
        return redirect("remediation-detail", org_slug=org_slug,
                        assessment_id=assessment.id, plan_id=plan.id)
    return render(request, "webapp/remediation_form.html", {
        "organization": organization, "assessment": assessment, "form": form,
        "title": "New remediation plan", "submit_label": "Create remediation plan",
    })


@login_required
def remediation_detail(
    request: HttpRequest, org_slug: str, assessment_id: int, plan_id: int
) -> HttpResponse:
    organization, assessment = _assessment_for(request.user, org_slug, assessment_id)
    plan = get_object_or_404(
        RemediationPlan.objects.select_related("owner__user", "validated_by").prefetch_related(
            "controls__requirement", "supporting_owners__user", "closure_evidence", "milestones__owner__user"
        ), id=plan_id, assessment=assessment,
    )
    return render(request, "webapp/remediation_detail.html", {
        "organization": organization, "assessment": assessment, "plan": plan,
        "can_edit": _can_manage_remediation(request.user, organization, plan),
        "today": timezone.localdate(),
    })


@login_required
def remediation_edit(
    request: HttpRequest, org_slug: str, assessment_id: int, plan_id: int
) -> HttpResponse:
    organization, assessment = _assessment_for(request.user, org_slug, assessment_id)
    plan = get_object_or_404(RemediationPlan, id=plan_id, assessment=assessment)
    _require_unlocked(assessment)
    if not _can_manage_remediation(request.user, organization, plan):
        raise Http404
    can_validate = _can_edit(request.user, organization)
    previous = {"status": plan.status, "validation_status": plan.validation_status}
    form = RemediationPlanForm(
        request.POST or None, instance=plan, organization=organization,
        assessment=assessment, can_validate=can_validate,
        can_accept_risk=_is_org_admin(request.user, organization),
    )
    if request.method == "POST" and form.is_valid():
        plan = form.save(commit=False)
        if (can_validate and plan.validation_status == RemediationPlan.ValidationStatus.VALIDATED
                and previous["validation_status"] != plan.validation_status):
            plan.validated_by = request.user
            plan.validated_at = timezone.now()
        elif plan.validation_status != RemediationPlan.ValidationStatus.VALIDATED:
            plan.validated_by = None
            plan.validated_at = None
        plan.save()
        form.save_m2m()
        AuditEvent.objects.create(
            organization=organization, actor=request.user, action="remediation.updated",
            object_type="RemediationPlan", object_id=str(plan.id),
            detail={"previous": previous, "status": plan.status,
                    "validation_status": plan.validation_status},
        )
        recipients = [plan.owner.user] if plan.owner else organization_users(
            organization, roles=(Membership.Role.ADMIN, Membership.Role.ASSESSOR)
        )
        notify(
            recipients=recipients, organization=organization, assessment=assessment,
            category=Notification.Category.REMEDIATION,
            title=f"{plan.remediation_id} is {plan.get_status_display()}",
            message="A remediation plan status or validation state changed.",
            action_url=reverse("remediation-detail", args=(org_slug, assessment.id, plan.id)),
            actor=request.user, object_type="RemediationPlan", object_id=plan.id,
            event="remediation.transitioned", previous_status=previous["status"],
            new_status=plan.status, comment=plan.validation_notes,
        )
        messages.success(request, f"{plan.remediation_id} updated.")
        return redirect("remediation-detail", org_slug=org_slug,
                        assessment_id=assessment.id, plan_id=plan.id)
    return render(request, "webapp/remediation_form.html", {
        "organization": organization, "assessment": assessment, "form": form,
        "plan": plan, "title": f"Edit {plan.remediation_id}",
        "submit_label": "Save remediation plan",
    })


@login_required
def remediation_milestone_create(
    request: HttpRequest, org_slug: str, assessment_id: int, plan_id: int
) -> HttpResponse:
    organization, assessment = _assessment_for(request.user, org_slug, assessment_id)
    plan = get_object_or_404(RemediationPlan, id=plan_id, assessment=assessment)
    _require_unlocked(assessment)
    if not _can_manage_remediation(request.user, organization, plan):
        raise Http404
    form = RemediationMilestoneForm(request.POST or None, organization=organization)
    if request.method == "POST" and form.is_valid():
        milestone = form.save(commit=False)
        milestone.plan = plan
        milestone.save()
        AuditEvent.objects.create(
            organization=organization, actor=request.user, action="remediation_milestone.created",
            object_type="RemediationMilestone", object_id=str(milestone.id),
            detail={"remediation_id": plan.remediation_id, "title": milestone.title},
        )
        if milestone.owner and milestone.notify_owner:
            notify(
                recipients=[milestone.owner.user], organization=organization,
                assessment=assessment, category=Notification.Category.ASSIGNMENT,
                title=f"Remediation milestone assigned: {milestone.title}",
                message=f'You were assigned a milestone for {plan.remediation_id}.',
                action_url=reverse("remediation-detail", args=(org_slug, assessment.id, plan.id)),
                actor=request.user, object_type="RemediationMilestone", object_id=milestone.id,
                event="remediation_milestone.assigned", new_status=milestone.status,
            )
        messages.success(request, "Milestone added.")
        return redirect("remediation-detail", org_slug=org_slug,
                        assessment_id=assessment.id, plan_id=plan.id)
    return render(request, "webapp/entity_form.html", {
        "organization": organization, "form": form, "title": "Add milestone",
        "eyebrow": plan.remediation_id, "submit_label": "Add milestone",
    })


@login_required
def remediation_export(request: HttpRequest, org_slug: str, assessment_id: int) -> FileResponse:
    organization, assessment = _assessment_for(request.user, org_slug, assessment_id)
    from .remediation_export import build_remediation_workbook
    output = build_remediation_workbook(assessment)
    AuditEvent.objects.create(
        organization=organization, actor=request.user, action="remediation.exported",
        object_type="Assessment", object_id=str(assessment.id),
        detail={"plans": assessment.remediation_plans.count()},
    )
    return FileResponse(
        output, as_attachment=True,
        filename=f"Omni-{assessment.id}-Remediation-Action-Plan.xlsx",
    )


@login_required
def report_center(request: HttpRequest, org_slug: str, assessment_id: int) -> HttpResponse:
    organization, assessment = _assessment_for(request.user, org_slug, assessment_id)
    from .reporting import assessment_readiness
    readiness = assessment_readiness(assessment, require_template=True)
    return render(request, "webapp/report_center.html", {
        "organization": organization, "assessment": assessment,
        "readiness": readiness,
        "history": assessment.generated_documents.select_related("generated_by")[:50],
    })


def _generated_response(assessment, organization, user, kind, filename, content, readiness):
    from .reporting import digest
    record = GeneratedDocument.objects.create(
        assessment=assessment, kind=kind, filename=filename, version="1.0",
        readiness=readiness, content_sha256=digest(content), size_bytes=len(content),
        generated_by=user,
    )
    AuditEvent.objects.create(
        organization=organization, actor=user, action="document.generated",
        object_type="GeneratedDocument", object_id=str(record.id),
        detail={"kind": kind, "filename": filename, "size_bytes": len(content)},
    )
    response = HttpResponse(content, content_type={
        GeneratedDocument.Kind.WORKBOOK: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        GeneratedDocument.Kind.SSP: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        GeneratedDocument.Kind.REMEDIATION: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        GeneratedDocument.Kind.PACKAGE: "application/zip",
    }[kind])
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
def report_download(
    request: HttpRequest, org_slug: str, assessment_id: int, kind: str
) -> HttpResponse:
    organization, assessment = _assessment_for(request.user, org_slug, assessment_id)
    from .reporting import (
        ReportNotReady, assessment_readiness, build_assessment_workbook,
        build_package, build_word_ssp,
    )
    from .remediation_export import build_remediation_workbook
    normalized = kind.upper()
    if normalized not in GeneratedDocument.Kind.values:
        raise Http404
    readiness = assessment_readiness(
        assessment, require_template=normalized in (
            GeneratedDocument.Kind.SSP, GeneratedDocument.Kind.PACKAGE
        )
    )
    try:
        if normalized == GeneratedDocument.Kind.WORKBOOK:
            content = build_assessment_workbook(assessment)
            filename = f"Omni-{assessment.id}-Assessment-Workbook.xlsx"
        elif normalized == GeneratedDocument.Kind.REMEDIATION:
            content = build_remediation_workbook(assessment).getvalue()
            filename = f"Omni-{assessment.id}-Remediation-Action-Plan.xlsx"
        elif normalized == GeneratedDocument.Kind.SSP:
            workbook = build_assessment_workbook(assessment)
            content = build_word_ssp(assessment, workbook, request.user)
            filename = f"Omni-{assessment.id}-System-Security-Plan.docx"
        else:
            content, readiness = build_package(assessment, request.user)
            filename = f"Omni-{assessment.id}-Complete-Assessment-Package.zip"
    except ReportNotReady as error:
        for issue in error.issues[:10]:
            messages.error(request, issue)
        if len(error.issues) > 10:
            messages.error(request, f"{len(error.issues) - 10} additional blockers remain.")
        return redirect("report-center", org_slug=org_slug, assessment_id=assessment.id)
    return _generated_response(
        assessment, organization, request.user, normalized, filename, content, readiness
    )


@login_required
def control_edit(
    request: HttpRequest, org_slug: str, assessment_id: int, result_id: int
) -> HttpResponse:
    organization = _organization_for(request.user, org_slug)
    result = get_object_or_404(
        ControlAssessment.objects.select_related("assessment__system", "requirement"),
        id=result_id,
        assessment_id=assessment_id,
        assessment__system__organization=organization,
    )
    if not _can_edit(request.user, organization):
        raise Http404
    _require_unlocked(result.assessment)
    if request.method == "POST":
        previous = {"status": result.status, "deduction": result.calculated_deduction}
        form = ControlAssessmentForm(request.POST, instance=result, organization=organization)
        if form.is_valid():
            result = form.save(commit=False)
            result.updated_by = request.user
            result.save()
            AuditEvent.objects.create(
                organization=organization,
                actor=request.user,
                action="control_assessment.updated",
                object_type="ControlAssessment",
                object_id=str(result.id),
                detail={
                    "requirement_id": result.requirement.requirement_id,
                    "previous": previous,
                    "current": {
                        "status": result.status,
                        "deduction": result.calculated_deduction,
                    },
                },
            )
            messages.success(
                request,
                f"{result.requirement.requirement_id} saved. Dashboard updated.",
            )
            return redirect(
                "assessment-dashboard", org_slug=org_slug, assessment_id=assessment_id
            )
    else:
        form = ControlAssessmentForm(instance=result, organization=organization)
    return render(
        request,
        "webapp/control_form.html",
        {
            "organization": organization, "result": result, "form": form,
            "requirement_mappings": RequirementMapping.objects.filter(
                Q(source=result.requirement) | Q(target=result.requirement)
            ).select_related("source__framework", "target__framework"),
        },
    )


@login_required
def bulk_control_owners(
    request: HttpRequest, org_slug: str, assessment_id: int
) -> HttpResponse:
    organization = _organization_for(request.user, org_slug)
    assessment = get_object_or_404(
        Assessment, id=assessment_id, system__organization=organization
    )
    if not _can_edit(request.user, organization):
        raise Http404
    _require_unlocked(assessment)
    form = BulkControlOwnerForm(
        request.POST or None, organization=organization, assessment=assessment
    )
    if request.method == "POST" and form.is_valid():
        results = assessment.control_results.filter(
            requirement__domain=form.cleaned_data["domain"]
        )
        results.update(primary_owner=form.cleaned_data["primary_owner"])
        supporting = form.cleaned_data["supporting_owners"]
        for result in results:
            result.supporting_owners.set(supporting)
        AuditEvent.objects.create(
            organization=organization, actor=request.user,
            action="control_owners.bulk_assigned", object_type="Assessment",
            object_id=str(assessment.id),
            detail={"domain": form.cleaned_data["domain"], "controls": results.count()},
        )
        messages.success(request, f"Owners assigned to {results.count()} controls.")
        return redirect("assessment-dashboard", org_slug=org_slug, assessment_id=assessment.id)
    return render(request, "webapp/entity_form.html", {
        "form": form, "title": "Assign control owners", "organization": organization,
        "eyebrow": assessment.name, "submit_label": "Apply to control family",
    })
