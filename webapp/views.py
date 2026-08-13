from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    AssessmentForm,
    BulkControlOwnerForm,
    ControlAssessmentForm,
    EvidenceArtifactForm,
    EvidenceRequestForm,
    MembershipForm,
    OrganizationForm,
    RemediationMilestoneForm,
    RemediationPlanForm,
    SystemForm,
)
from .models import (
    Assessment,
    AssessmentFramework,
    AuditEvent,
    ControlAssessment,
    EvidenceArtifact,
    EvidenceRequest,
    Framework,
    GeneratedDocument,
    Membership,
    Organization,
    RemediationMilestone,
    RemediationPlan,
    RequirementMapping,
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
def framework_catalog(request: HttpRequest) -> HttpResponse:
    frameworks = Framework.objects.filter(active=True).annotate(
        requirement_count=Count("requirements")
    ).order_by("name", "version")
    return render(request, "webapp/framework_catalog.html", {"frameworks": frameworks})


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
    all_results = assessment.control_results.select_related(
        "requirement__framework", "primary_owner__user"
    ).prefetch_related("supporting_owners")
    selected_frameworks = list(_selected_frameworks(assessment))
    framework_code = request.GET.get("framework", "").strip()
    active_framework = next(
        (item for item in selected_frameworks if item.code == framework_code), None
    )
    results = all_results.filter(requirement__framework=active_framework) if active_framework else all_results
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
        },
    )


def _assessment_for(user, org_slug: str, assessment_id: int):
    organization = _organization_for(user, org_slug)
    assessment = get_object_or_404(
        Assessment.objects.select_related("system", "framework"),
        id=assessment_id, system__organization=organization,
    )
    return organization, assessment


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
