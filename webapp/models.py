from __future__ import annotations

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models


def evidence_upload_path(instance, filename: str) -> str:
    return f"evidence/org-{instance.organization_id}/assessment-{instance.assessment_id}/{filename}"


class Organization(models.Model):
    class Kind(models.TextChoices):
        RISC = "RISC", "R!SC"
        CLIENT = "CLIENT", "Client"

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    legal_name = models.CharField(max_length=250, blank=True)
    website = models.URLField(blank=True)
    industry = models.CharField(max_length=150, blank=True)
    address = models.TextField(blank=True)
    primary_contact_name = models.CharField(max_length=200, blank=True)
    primary_contact_email = models.EmailField(blank=True)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.CLIENT)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Membership(models.Model):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrator"
        ASSESSOR = "ASSESSOR", "Assessor"
        CLIENT = "CLIENT", "Client"
        VIEWER = "VIEWER", "Read only"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="omni_memberships",
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=12, choices=Role.choices)
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "organization"), name="unique_org_membership"
            )
        ]

    def __str__(self) -> str:
        display_name = self.user.get_full_name() or self.user.username
        return f"{display_name} ({self.get_role_display()})"


class System(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="systems"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    cage_code = models.CharField(max_length=20, blank=True)
    system_owner_name = models.CharField(max_length=200, blank=True)
    system_owner_email = models.EmailField(blank=True)
    location = models.CharField(max_length=250, blank=True)
    environment = models.CharField(max_length=100, blank=True)
    data_types = models.TextField(blank=True)
    scope = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "name"), name="unique_system_per_org"
            )
        ]

    def __str__(self) -> str:
        return self.name


class Framework(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    version = models.CharField(max_length=50)

    def __str__(self) -> str:
        return f"{self.name} {self.version}"


class Requirement(models.Model):
    framework = models.ForeignKey(
        Framework, on_delete=models.CASCADE, related_name="requirements"
    )
    requirement_id = models.CharField(max_length=50)
    domain = models.CharField(max_length=20)
    title = models.CharField(max_length=300)
    statement = models.TextField()
    full_deduction = models.PositiveSmallIntegerField(default=1)
    partial_credit_allowed = models.BooleanField(default=False)

    class Meta:
        ordering = ("requirement_id",)
        constraints = [
            models.UniqueConstraint(
                fields=("framework", "requirement_id"),
                name="unique_framework_requirement",
            )
        ]

    def __str__(self) -> str:
        return self.requirement_id


class Assessment(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        COMPLETE = "COMPLETE", "Complete"

    system = models.ForeignKey(
        System, on_delete=models.CASCADE, related_name="assessments"
    )
    framework = models.ForeignKey(
        Framework, on_delete=models.PROTECT, related_name="assessments"
    )
    name = models.CharField(max_length=200)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_assessments",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)

    def __str__(self) -> str:
        return self.name

    @property
    def current_score(self) -> int:
        return 110 - sum(
            self.control_results.values_list("calculated_deduction", flat=True)
        )


class ControlAssessment(models.Model):
    class Status(models.TextChoices):
        MET = "MET", "MET"
        NOT_MET = "NOT MET", "NOT MET"
        NOT_APPLICABLE = "NOT APPLICABLE", "NOT APPLICABLE"
        NOT_ASSESSED = "NOT ASSESSED", "NOT ASSESSED"

    class Implementation(models.TextChoices):
        FULL = "FULLY IMPLEMENTED", "Fully implemented"
        PARTIAL = "PARTIALLY IMPLEMENTED", "Partially implemented"
        NONE = "NOT IMPLEMENTED", "Not implemented"
        NA = "NOT APPLICABLE", "Not applicable"
        UNASSESSED = "NOT ASSESSED", "Not assessed"

    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, related_name="control_results"
    )
    requirement = models.ForeignKey(
        Requirement, on_delete=models.PROTECT, related_name="assessment_results"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.NOT_ASSESSED
    )
    implementation_state = models.CharField(
        max_length=30, choices=Implementation.choices, default=Implementation.UNASSESSED
    )
    assessor_notes_findings = models.TextField(blank=True)
    control_owner = models.CharField(max_length=200, blank=True)
    primary_owner = models.ForeignKey(
        Membership,
        on_delete=models.SET_NULL,
        related_name="primary_control_assignments",
        null=True,
        blank=True,
    )
    supporting_owners = models.ManyToManyField(
        Membership, related_name="supporting_control_assignments", blank=True
    )
    ssp_reference = models.CharField(max_length=300, blank=True)
    calculated_deduction = models.PositiveSmallIntegerField(default=0)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_control_results",
        null=True,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("requirement__requirement_id",)
        constraints = [
            models.UniqueConstraint(
                fields=("assessment", "requirement"),
                name="unique_assessment_requirement",
            )
        ]

    def __str__(self) -> str:
        return f"{self.requirement.requirement_id} — {self.requirement.title}"

    def calculate_deduction(self) -> int:
        if self.status != self.Status.NOT_MET:
            return 0
        if (
            self.requirement.partial_credit_allowed
            and self.implementation_state == self.Implementation.PARTIAL
        ):
            return 3
        return self.requirement.full_deduction

    def save(self, *args, **kwargs):
        self.calculated_deduction = self.calculate_deduction()
        super().save(*args, **kwargs)


class EvidenceRequest(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested"
        RECEIVED = "RECEIVED", "Received"
        UNDER_REVIEW = "UNDER_REVIEW", "Under review"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"

    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, related_name="evidence_requests"
    )
    evidence_code = models.CharField(max_length=30, blank=True)
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.REQUESTED
    )
    owner = models.ForeignKey(
        Membership, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="evidence_requests",
    )
    due_date = models.DateField(null=True, blank=True)
    controls = models.ManyToManyField(
        ControlAssessment, related_name="evidence_requests", blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="created_evidence_requests",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("status", "due_date", "title")

    def __str__(self) -> str:
        return self.title


class EvidenceArtifact(models.Model):
    class ReviewStatus(models.TextChoices):
        RECEIVED = "RECEIVED", "Received"
        UNDER_REVIEW = "UNDER_REVIEW", "Under review"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="evidence_artifacts"
    )
    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, related_name="evidence_artifacts"
    )
    title = models.CharField(max_length=300)
    file = models.FileField(
        upload_to=evidence_upload_path, blank=True,
        validators=[FileExtensionValidator(allowed_extensions=(
            "pdf", "doc", "docx", "xls", "xlsx", "csv", "txt", "png",
            "jpg", "jpeg", "zip", "json", "xml", "log",
        ))],
    )
    external_reference = models.URLField(blank=True)
    source = models.CharField(max_length=250, blank=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    review_status = models.CharField(
        max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.RECEIVED
    )
    assessor_notes = models.TextField(blank=True)
    controls = models.ManyToManyField(
        ControlAssessment, related_name="evidence_artifacts", blank=True
    )
    requests = models.ManyToManyField(
        EvidenceRequest, related_name="artifacts", blank=True
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="uploaded_evidence_artifacts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)

    def __str__(self) -> str:
        return self.title


class RemediationPlan(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        BLOCKED = "BLOCKED", "Blocked"
        READY_VALIDATION = "READY_VALIDATION", "Ready for validation"
        CLOSED = "CLOSED", "Closed"
        RISK_ACCEPTED = "RISK_ACCEPTED", "Risk accepted"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    class Likelihood(models.TextChoices):
        RARE = "RARE", "Rare"
        UNLIKELY = "UNLIKELY", "Unlikely"
        POSSIBLE = "POSSIBLE", "Possible"
        LIKELY = "LIKELY", "Likely"
        ALMOST_CERTAIN = "ALMOST_CERTAIN", "Almost certain"

    class ValidationStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        VALIDATED = "VALIDATED", "Validated"
        REJECTED = "REJECTED", "Rejected"

    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, related_name="remediation_plans"
    )
    remediation_id = models.CharField(max_length=30)
    title = models.CharField(max_length=300)
    controls = models.ManyToManyField(
        ControlAssessment, related_name="remediation_plans"
    )
    weakness_description = models.TextField()
    root_cause = models.TextField(blank=True)
    corrective_action = models.TextField(blank=True)
    compensating_controls = models.TextField(blank=True)
    closure_criteria = models.TextField(blank=True)
    owner = models.ForeignKey(
        Membership, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="owned_remediation_plans",
    )
    supporting_owners = models.ManyToManyField(
        Membership, related_name="supported_remediation_plans", blank=True
    )
    status = models.CharField(
        max_length=25, choices=Status.choices, default=Status.OPEN
    )
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM
    )
    severity = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM
    )
    likelihood = models.CharField(
        max_length=20, choices=Likelihood.choices, default=Likelihood.POSSIBLE
    )
    residual_risk = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM
    )
    date_identified = models.DateField()
    planned_completion = models.DateField(null=True, blank=True)
    actual_completion = models.DateField(null=True, blank=True)
    risk_acceptance_requested = models.BooleanField(default=False)
    risk_acceptance_rationale = models.TextField(blank=True)
    risk_accepted_by = models.ForeignKey(
        Membership, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="accepted_remediation_risks",
    )
    risk_acceptance_expires = models.DateField(null=True, blank=True)
    closure_evidence = models.ManyToManyField(
        EvidenceArtifact, related_name="remediation_plans", blank=True
    )
    validation_status = models.CharField(
        max_length=15, choices=ValidationStatus.choices,
        default=ValidationStatus.PENDING,
    )
    validation_notes = models.TextField(blank=True)
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="validated_remediation_plans",
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="created_remediation_plans",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("status", "-priority", "planned_completion", "remediation_id")
        constraints = [models.UniqueConstraint(
            fields=("assessment", "remediation_id"), name="unique_assessment_remediation_id"
        )]

    def __str__(self) -> str:
        return f"{self.remediation_id} — {self.title}"

    @property
    def risk_score(self) -> int:
        severity = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        likelihood = {
            "RARE": 1, "UNLIKELY": 2, "POSSIBLE": 3,
            "LIKELY": 4, "ALMOST_CERTAIN": 5,
        }
        return severity[self.severity] * likelihood[self.likelihood]


class RemediationMilestone(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = "NOT_STARTED", "Not started"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        COMPLETE = "COMPLETE", "Complete"
        BLOCKED = "BLOCKED", "Blocked"

    plan = models.ForeignKey(
        RemediationPlan, on_delete=models.CASCADE, related_name="milestones"
    )
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        Membership, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="remediation_milestones",
    )
    due_date = models.DateField(null=True, blank=True)
    completed_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.NOT_STARTED
    )
    sequence = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ("sequence", "due_date", "id")

    def __str__(self) -> str:
        return self.title


class AuditEvent(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="audit_events"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="omni_audit_events",
    )
    action = models.CharField(max_length=100)
    object_type = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    detail = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
