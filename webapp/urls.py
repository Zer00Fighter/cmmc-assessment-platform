from django.urls import path

from . import views

urlpatterns = [
    path("", views.organization_list, name="organization-list"),
    path("frameworks/", views.framework_catalog, name="framework-catalog"),
    path("organizations/new/", views.organization_create, name="organization-create"),
    path("organizations/<slug:org_slug>/edit/", views.organization_edit, name="organization-edit"),
    path("organizations/<slug:org_slug>/members/", views.membership_list, name="membership-list"),
    path(
        "organizations/<slug:org_slug>/systems/", views.system_list, name="system-list"
    ),
    path("organizations/<slug:org_slug>/systems/new/", views.system_create, name="system-create"),
    path("organizations/<slug:org_slug>/systems/<int:system_id>/edit/", views.system_edit, name="system-edit"),
    path(
        "organizations/<slug:org_slug>/systems/<int:system_id>/assessments/",
        views.assessment_list,
        name="assessment-list",
    ),
    path(
        "organizations/<slug:org_slug>/systems/<int:system_id>/assessments/new/",
        views.assessment_create,
        name="assessment-create",
    ),
    path(
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/",
        views.assessment_dashboard,
        name="assessment-dashboard",
    ),
    path(
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/frameworks/",
        views.assessment_frameworks, name="assessment-frameworks",
    ),
    path("organizations/<slug:org_slug>/assessments/<int:assessment_id>/plan/", views.assessment_plan, name="assessment-plan"),
    path("organizations/<slug:org_slug>/assessments/<int:assessment_id>/execution/", views.assessment_execution, name="assessment-execution"),
    path("organizations/<slug:org_slug>/assessments/<int:assessment_id>/execution/objectives/<int:objective_result_id>/", views.objective_edit, name="objective-edit"),
    path("organizations/<slug:org_slug>/assessments/<int:assessment_id>/execution/interviews/new/", views.interview_create, name="interview-create"),
    path("organizations/<slug:org_slug>/assessments/<int:assessment_id>/execution/samples/new/", views.sample_create, name="sample-create"),
    path("organizations/<slug:org_slug>/assessments/<int:assessment_id>/execution/tests/new/", views.test_execution_create, name="test-execution-create"),
    path("organizations/<slug:org_slug>/assessments/<int:assessment_id>/quality-review/", views.quality_review, name="quality-review"),
    path("organizations/<slug:org_slug>/assessments/<int:assessment_id>/signoff/", views.assessment_signoff, name="assessment-signoff"),
    path("organizations/<slug:org_slug>/assessments/<int:assessment_id>/reopen/", views.assessment_reopen, name="assessment-reopen"),
    path(
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/controls/<int:result_id>/",
        views.control_edit,
        name="control-edit",
    ),
    path(
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/owners/",
        views.bulk_control_owners, name="bulk-control-owners",
    ),
    path(
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/evidence/",
        views.evidence_list, name="evidence-list",
    ),
    path(
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/evidence/requests/new/",
        views.evidence_request_create, name="evidence-request-create",
    ),
    path(
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/evidence/requests/generate/",
        views.evidence_request_generate, name="evidence-request-generate",
    ),
    path(
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/evidence/requests/<int:evidence_request_id>/",
        views.evidence_request_edit, name="evidence-request-edit",
    ),
    path(
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/evidence/artifacts/new/",
        views.evidence_artifact_create, name="evidence-artifact-create",
    ),
    path(
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/evidence/artifacts/<int:artifact_id>/",
        views.evidence_artifact_edit, name="evidence-artifact-edit",
    ),
    path(
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/evidence/artifacts/<int:artifact_id>/download/",
        views.evidence_artifact_download, name="evidence-artifact-download",
    ),
    path(
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/remediation/",
        views.remediation_list, name="remediation-list",
    ),
    path(
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/remediation/new/",
        views.remediation_create, name="remediation-create",
    ),
    path(
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/remediation/export/",
        views.remediation_export, name="remediation-export",
    ),
    path(
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/remediation/<int:plan_id>/",
        views.remediation_detail, name="remediation-detail",
    ),
    path(
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/remediation/<int:plan_id>/edit/",
        views.remediation_edit, name="remediation-edit",
    ),
    path(
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/remediation/<int:plan_id>/milestones/new/",
        views.remediation_milestone_create, name="remediation-milestone-create",
    ),
    path(
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/reports/",
        views.report_center, name="report-center",
    ),
    path(
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/reports/<str:kind>/",
        views.report_download, name="report-download",
    ),
]
