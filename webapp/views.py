from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import AssessmentForm, ControlAssessmentForm
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
def system_list(request: HttpRequest, org_slug: str) -> HttpResponse:
    organization = _organization_for(request.user, org_slug)
    systems = organization.systems.filter(active=True).annotate(
        assessment_count=Count("assessments")
    )
    return render(
        request,
        "webapp/system_list.html",
        {"organization": organization, "systems": systems},
    )


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
    results = assessment.control_results.select_related("requirement")
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
        form = ControlAssessmentForm(request.POST, instance=result)
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
        form = ControlAssessmentForm(instance=result)
    return render(
        request,
        "webapp/control_form.html",
        {"organization": organization, "result": result, "form": form},
    )
