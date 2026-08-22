from django.contrib import admin

from .models import (
    Assessment,
    AssessmentAccess,
    AssessmentReuseDecision,
    AssessmentObjective,
    AssessmentProcedure,
    AssessmentProcedureCustomization,
    AssessmentSample,
    AssessmentTeamMember,
    AssessmentTemplate,
    AuditEvent,
    AuthoritativeDocument,
    ControlAssessment,
    ControlMonitoringEvent,
    ControlMonitoringProfile,
    ControlReassessmentTask,
    EvidenceArtifact,
    EvidenceRequest,
    ExternalAuthority,
    EvidenceReviewHistory,
    Framework,
    FrameworkImport,
    GeneratedDocument,
    Membership,
    MappingReference,
    InterviewSession,
    Notification,
    NotificationPreference,
    NotificationPolicy,
    IntegrationPolicy,
    ImplementationActivity,
    ImplementationActivityMapping,
    OutboundWorkItem,
    ObjectiveAssessment,
    Organization,
    OrganizationInvitation,
    Requirement,
    RemediationMilestone,
    RemediationPlan,
    RequirementMapping,
    RequirementRiskMapping,
    RiskCatalogEntry,
    RiskRegisterEntry,
    RiskRegisterHistory,
    RiskAcceptanceRequest,
    RiskReassessment,
    RiskTolerancePolicy,
    RiskTreatmentAction,
    System,
    Soc2AssessmentProfile,
    Soc2PointOfFocus,
    TestExecution,
    WorkflowHistory,
    UserProfile,
    LoginAttempt,
)

admin.site.register(
    (
        Organization,
        Membership,
        System,
        Soc2AssessmentProfile,
        Soc2PointOfFocus,
        Framework,
        FrameworkImport,
        ExternalAuthority,
        AuthoritativeDocument,
        MappingReference,
        GeneratedDocument,
        Requirement,
        RemediationMilestone,
        RemediationPlan,
        RequirementMapping,
        RequirementRiskMapping,
        RiskCatalogEntry,
        RiskRegisterEntry,
        RiskRegisterHistory,
        RiskAcceptanceRequest,
        RiskReassessment,
        RiskTolerancePolicy,
        RiskTreatmentAction,
        Assessment,
        AssessmentAccess,
        AssessmentReuseDecision,
        AssessmentObjective,
        AssessmentProcedure,
        AssessmentProcedureCustomization,
        AssessmentSample,
        AssessmentTeamMember,
        AssessmentTemplate,
        InterviewSession,
        ObjectiveAssessment,
        TestExecution,
        ControlAssessment,
        ControlMonitoringEvent,
        ControlMonitoringProfile,
        ControlReassessmentTask,
        EvidenceArtifact,
        EvidenceRequest,
        EvidenceReviewHistory,
        Notification,
        NotificationPreference,
        NotificationPolicy,
        IntegrationPolicy,
        ImplementationActivity,
        ImplementationActivityMapping,
        OutboundWorkItem,
        WorkflowHistory,
        OrganizationInvitation,
        UserProfile,
        LoginAttempt,
    )
)


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "organization",
        "actor",
        "action",
        "object_type",
        "object_id",
    )
    list_filter = ("organization", "action", "object_type")
    search_fields = ("action", "object_type", "object_id", "actor__username")
    readonly_fields = (
        "organization",
        "actor",
        "action",
        "object_type",
        "object_id",
        "detail",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return bool(
            request.method in ("GET", "HEAD")
            and super().has_change_permission(request, obj)
        )

    def has_delete_permission(self, request, obj=None):
        return False
