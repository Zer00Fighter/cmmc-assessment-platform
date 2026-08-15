from django.urls import path

from . import views

urlpatterns = [
    path("", views.organization_list, name="organization-list"),
    path("notifications/", views.notification_center, name="notification-center"),
    path("notifications/read-all/", views.notifications_read_all, name="notifications-read-all"),
    path("notifications/<int:notification_id>/read/", views.notification_read, name="notification-read"),
    path("notification-preferences/", views.notification_preferences, name="notification-preferences"),
    path("profile/", views.user_profile, name="user-profile"),
    path("invitations/<str:token>/accept/", views.invitation_accept, name="invitation-accept"),
    path("organizations/<slug:org_slug>/notification-policy/", views.notification_policy, name="notification-policy"),
    path("organizations/<slug:org_slug>/integrations/", views.integration_settings, name="integration-settings"),
    path("organizations/<slug:org_slug>/assessment-templates/", views.assessment_template_list, name="assessment-template-list"),
    path("organizations/<slug:org_slug>/assessment-templates/new/", views.assessment_template_create, name="assessment-template-create"),
    path("organizations/<slug:org_slug>/notification-policy/test/", views.notification_test_email, name="notification-test-email"),
    path("organizations/<slug:org_slug>/system-health/", views.system_health, name="system-health"),
    path("frameworks/", views.framework_catalog, name="framework-catalog"),
    path("frameworks/imports/", views.framework_import_list, name="framework-import-list"),
    path("frameworks/imports/new/", views.framework_import_upload, name="framework-import-upload"),
    path("frameworks/imports/<int:import_id>/", views.framework_import_preview, name="framework-import-preview"),
    path("frameworks/mapping-quality/", views.mapping_quality, name="mapping-quality"),
    path("frameworks/mapping-governance/", views.mapping_governance, name="mapping-governance"),
    path("frameworks/omni-evidence-catalog/", views.omni_evidence_catalog, name="omni-evidence-catalog"),
    path("frameworks/authoritative-sources/", views.authoritative_source_registry, name="authoritative-source-registry"),
    path("frameworks/risk-catalog/", views.risk_catalog_registry, name="risk-catalog-registry"),
    path("organizations/new/", views.organization_create, name="organization-create"),
    path("organizations/<slug:org_slug>/edit/", views.organization_edit, name="organization-edit"),
    path("organizations/<slug:org_slug>/members/", views.membership_list, name="membership-list"),
    path("organizations/<slug:org_slug>/members/<int:membership_id>/toggle/", views.membership_toggle, name="membership-toggle"),
    path("organizations/<slug:org_slug>/invitations/<int:invitation_id>/cancel/", views.invitation_cancel, name="invitation-cancel"),
    path("organizations/<slug:org_slug>/access-review/export/", views.access_review_export, name="access-review-export"),
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
        "organizations/<slug:org_slug>/systems/<int:system_id>/assessments/from-template/<int:template_id>/",
        views.assessment_from_template,
        name="assessment-from-template",
    ),
    path(
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/",
        views.assessment_dashboard,
        name="assessment-dashboard",
    ),
    path(
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/dashboard/export/",
        views.dashboard_export,
        name="dashboard-export",
    ),
    path(
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/frameworks/",
        views.assessment_frameworks, name="assessment-frameworks",
    ),
    path("organizations/<slug:org_slug>/assessments/<int:assessment_id>/plan/", views.assessment_plan, name="assessment-plan"),
    path("organizations/<slug:org_slug>/assessments/<int:assessment_id>/access/", views.assessment_access, name="assessment-access"),
    path("organizations/<slug:org_slug>/assessments/<int:assessment_id>/execution/", views.assessment_execution, name="assessment-execution"),
    path("organizations/<slug:org_slug>/assessments/<int:assessment_id>/harmonization/", views.assessment_harmonization, name="assessment-harmonization"),
    path("organizations/<slug:org_slug>/assessments/<int:assessment_id>/shared-work/", views.shared_work_workspace, name="shared-work-workspace"),
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
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/monitoring/",
        views.control_monitoring, name="control-monitoring",
    ),
    path(
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/monitoring/events/new/",
        views.control_monitoring_event_create, name="control-monitoring-event-create",
    ),
    path(
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/monitoring/controls/<int:control_id>/",
        views.control_monitoring_profile_edit, name="control-monitoring-profile-edit",
    ),
    path(
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/monitoring/tasks/<int:task_id>/",
        views.control_reassessment_task_edit, name="control-reassessment-task-edit",
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
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/evidence/artifacts/<int:artifact_id>/renew/",
        views.evidence_artifact_renew, name="evidence-artifact-renew",
    ),
    path(
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/evidence/artifacts/<int:artifact_id>/download/",
        views.evidence_artifact_download, name="evidence-artifact-download",
    ),
    path(
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/remediation/",
        views.remediation_list, name="remediation-list",
    ),
    path("organizations/<slug:org_slug>/assessments/<int:assessment_id>/risks/", views.risk_register_list, name="risk-register-list"),
    path("organizations/<slug:org_slug>/assessments/<int:assessment_id>/risks/new/", views.risk_register_create, name="risk-register-create"),
    path("organizations/<slug:org_slug>/assessments/<int:assessment_id>/risks/export/", views.risk_register_export, name="risk-register-export"),
    path("organizations/<slug:org_slug>/assessments/<int:assessment_id>/risks/<int:risk_id>/", views.risk_register_detail, name="risk-register-detail"),
    path("organizations/<slug:org_slug>/assessments/<int:assessment_id>/risks/<int:risk_id>/edit/", views.risk_register_edit, name="risk-register-edit"),
    path("organizations/<slug:org_slug>/assessments/<int:assessment_id>/risks/tolerance/", views.risk_tolerance_policy, name="risk-tolerance-policy"),
    path("organizations/<slug:org_slug>/assessments/<int:assessment_id>/risks/<int:risk_id>/actions/new/", views.risk_treatment_action_create, name="risk-treatment-action-create"),
    path("organizations/<slug:org_slug>/assessments/<int:assessment_id>/risks/<int:risk_id>/actions/<int:action_id>/edit/", views.risk_treatment_action_edit, name="risk-treatment-action-edit"),
    path("organizations/<slug:org_slug>/assessments/<int:assessment_id>/risks/<int:risk_id>/reassess/", views.risk_reassess, name="risk-reassess"),
    path("organizations/<slug:org_slug>/assessments/<int:assessment_id>/risks/<int:risk_id>/acceptance/request/", views.risk_acceptance_request, name="risk-acceptance-request"),
    path("organizations/<slug:org_slug>/assessments/<int:assessment_id>/risks/acceptance/<int:request_id>/review/", views.risk_acceptance_review, name="risk-acceptance-review"),
    path("organizations/<slug:org_slug>/assessments/<int:assessment_id>/risks/<int:risk_id>/close/", views.risk_close, name="risk-close"),
    path("organizations/<slug:org_slug>/assessments/<int:assessment_id>/risks/<int:risk_id>/reopen/", views.risk_reopen, name="risk-reopen"),
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
