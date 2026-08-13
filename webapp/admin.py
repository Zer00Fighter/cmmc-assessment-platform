from django.contrib import admin

from .models import (
    Assessment,
    AuditEvent,
    ControlAssessment,
    EvidenceArtifact,
    EvidenceRequest,
    Framework,
    Membership,
    Organization,
    Requirement,
    RemediationMilestone,
    RemediationPlan,
    System,
)

admin.site.register(
    (
        Organization,
        Membership,
        System,
        Framework,
        Requirement,
        RemediationMilestone,
        RemediationPlan,
        Assessment,
        ControlAssessment,
        EvidenceArtifact,
        EvidenceRequest,
        AuditEvent,
    )
)
