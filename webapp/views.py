from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    AssessmentForm,
    BulkControlOwnerForm,
    ControlAssessmentForm,
    MembershipForm,
    OrganizationForm,
    SystemForm,
)
from .models import (
    Assessment,
    AuditEvent,
    ControlAssessment,
    Membership,
    Organization,
    System,
)


def _organizations_for(user):
    if user.is_superuser:
        return Organization.objects.filter(active=True)
    return Organization.objects.filter(
        active=True, memberships__user=user, memberships__active=True
    ).distinct()


def _organization_for(user, slug: str) -> Organization:
    return get_object_or_404(_organizations_for(user), slug=slug)


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
    form = MembershipForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        membership, created = Membership.objects.update_or_create(
            user=form.user, organization=organization,
            defaults={"role": form.cleaned_data["role"], "active": True},
        )
        messages.success(request, "Team member added." if created else "Team member updated.")
        return redirect("membership-list", org_slug=org_slug)
    return render(request, "webapp/membership_list.html", {
        "organization": organization,
        "memberships": organization.memberships.select_related("user").order_by("user__username"),
        "form": form,
    })


@login_required
def assessment_list(
    request: HttpRequest, org_slug: str, system_id: int
) -> HttpResponse:
    organization = _organization_for(request.user, org_slug)
    system = get_object_or_404(System, id=system_id, organization=organization)
    return render(
        request,
        "webapp/assessment_list.html",
        {
            "organization": organization,
            "system": system,
            "assessments": system.assessments.all(),
            "can_admin": _is_org_admin(request.user, organization),
            "can_edit": _can_edit(request.user, organization),
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
            assessment.created_by = request.user
            assessment.status = Assessment.Status.IN_PROGRESS
            assessment.save()
            ControlAssessment.objects.bulk_create(
                [
                    ControlAssessment(assessment=assessment, requirement=requirement)
                    for requirement in assessment.framework.requirements.all()
                ]
            )
            AuditEvent.objects.create(
                organization=organization,
                actor=request.user,
                action="assessment.created",
                object_type="Assessment",
                object_id=str(assessment.id),
                detail={"framework": assessment.framework.code},
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
    results = assessment.control_results.select_related(
        "requirement", "primary_owner__user"
    ).prefetch_related("supporting_owners")
    counts = {
        value: results.filter(status=value).count()
        for value in ControlAssessment.Status.values
    }
    total = results.count()
    assessed = total - counts[ControlAssessment.Status.NOT_ASSESSED]
    deduction = results.aggregate(total=Sum("calculated_deduction"))["total"] or 0
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
            "score": 110 - deduction,
            "completion": round(assessed / total * 100, 1) if total else 0,
            "can_edit": _can_edit(request.user, organization),
        },
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
        {"organization": organization, "result": result, "form": form},
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
