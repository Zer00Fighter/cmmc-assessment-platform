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
    System,
)

admin.site.register(
    (
        Organization,
        Membership,
        System,
        Framework,
        Requirement,
        Assessment,
        ControlAssessment,
        EvidenceArtifact,
        EvidenceRequest,
        AuditEvent,
    )
)
