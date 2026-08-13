from django.contrib import admin

from .models import (
    Assessment,
    AuditEvent,
    ControlAssessment,
    EvidenceArtifact,
    EvidenceRequest,
    Framework,
    GeneratedDocument,
    Membership,
    Organization,
    Requirement,
    RemediationMilestone,
    RemediationPlan,
    RequirementMapping,
    System,
)

admin.site.register(
    (
        Organization,
        Membership,
        System,
        Framework,
        GeneratedDocument,
        Requirement,
        RemediationMilestone,
        RemediationPlan,
        RequirementMapping,
        Assessment,
        ControlAssessment,
        EvidenceArtifact,
        EvidenceRequest,
        AuditEvent,
    )
)
