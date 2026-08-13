from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Sum
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    AssessmentForm,
    BulkControlOwnerForm,
    ControlAssessmentForm,
    EvidenceArtifactForm,
    EvidenceRequestForm,
    MembershipForm,
    OrganizationForm,
    SystemForm,
)
from .models import (
    Assessment,
    AuditEvent,
    ControlAssessment,
    EvidenceArtifact,
    EvidenceRequest,
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


def _can_manage_evidence(user, organization: Organization) -> bool:
    if user.is_superuser:
        return True
    return Membership.objects.filter(
        user=user, organization=organization, active=True,
        role__in=(Membership.Role.ADMIN, Membership.Role.ASSESSOR, Membership.Role.CLIENT),
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
    evidence_counts = {
        value: assessment.evidence_requests.filter(status=value).count()
        for value in EvidenceRequest.Status.values
    }
    evidence_total = sum(evidence_counts.values())
    evidence_ready = evidence_counts[EvidenceRequest.Status.ACCEPTED]
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
            "can_manage_evidence": _can_manage_evidence(request.user, organization),
            "evidence_total": evidence_total,
            "evidence_ready": evidence_ready,
            "evidence_readiness": round(evidence_ready / evidence_total * 100, 1)
            if evidence_total else 0,
        },
    )


def _assessment_for(user, org_slug: str, assessment_id: int):
    organization = _organization_for(user, org_slug)
    assessment = get_object_or_404(
        Assessment.objects.select_related("system", "framework"),
        id=assessment_id, system__organization=organization,
    )
    return organization, assessment


def _generate_cmmc_drl(assessment: Assessment):
    from src.evidence_requests.assessment_procedure_loader import AssessmentProcedureLoader
    from src.evidence_requests.catalog_compiler import CatalogCompiler
    from src.evidence_requests.request_generator import RequestGenerator
    from src.evidence_requests.request_optimizer import RequestOptimizer

    source = Path(settings.BASE_DIR) / "data" / "sp800-171a-assessment-procedures.xlsx"
    fallback = {
        "SC.L2-3.13.12": (
            "Prohibit remote activation of collaborative computing devices and "
            "provide indication of devices in use to users present at the device."
        )
    }
    loader = AssessmentProcedureLoader(
        framework_id=assessment.framework.code,
        framework_name=assessment.framework.name,
        framework_version=assessment.framework.version,
        source_document="NIST SP 800-171A",
        requirement_text_provider=fallback.get,
    )
    dataset = loader.load(source)
    knowledge = CatalogCompiler().compile(dataset.rows)
    raw = RequestGenerator().generate(
        knowledge, framework_id=assessment.framework.code,
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
    if not assessment.framework.code.upper().startswith("CMMC"):
        messages.error(request, "Automatic evidence generation is not configured for this framework yet.")
        return redirect("evidence-list", org_slug=org_slug, assessment_id=assessment.id)
    collection = _generate_cmmc_drl(assessment)
    results_by_id = {
        item.requirement.requirement_id.casefold(): item
        for item in assessment.control_results.select_related("requirement")
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
    artifact = get_object_or_404(
        EvidenceArtifact, id=artifact_id, assessment=assessment, organization=organization
    )
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
        AuditEvent.objects.create(
            organization=organization, actor=request.user, action="evidence_artifact.updated",
            object_type="EvidenceArtifact", object_id=str(artifact.id),
            detail={"review_status": artifact.review_status},
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
