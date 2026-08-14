from __future__ import annotations

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone


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


class NotificationPolicy(models.Model):
    class Escalation(models.TextChoices):
        OWNER = "OWNER", "Owner only"
        LEAD = "LEAD", "Owner and lead assessor"
        CLIENT = "CLIENT", "Owner, lead assessor, and System Owner"

    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, related_name="notification_policy"
    )
    notifications_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=True)
    first_reminder_days = models.PositiveSmallIntegerField(default=7)
    second_reminder_days = models.PositiveSmallIntegerField(default=3)
    notify_on_due_date = models.BooleanField(default=True)
    overdue_escalation_days = models.PositiveSmallIntegerField(default=1)
    repeat_overdue_days = models.PositiveSmallIntegerField(default=7)
    escalation_recipients = models.CharField(
        max_length=10, choices=Escalation.choices, default=Escalation.LEAD
    )

    def __str__(self) -> str:
        return f"Notification policy for {self.organization}"


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


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="omni_profile"
    )
    job_title = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    time_zone = models.CharField(max_length=60, default="America/Los_Angeles")

    def __str__(self) -> str:
        return f"Profile for {self.user}"


class OrganizationInvitation(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        CANCELLED = "CANCELLED", "Cancelled"
        EXPIRED = "EXPIRED", "Expired"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="invitations"
    )
    email = models.EmailField()
    role = models.CharField(max_length=12, choices=Membership.Role.choices)
    token_digest = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sent_omni_invitations"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    @property
    def is_usable(self):
        return self.status == self.Status.PENDING and self.expires_at > timezone.now()


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
    class ScoringMethod(models.TextChoices):
        NONE = "NONE", "No numeric score"
        SPRS = "SPRS", "SPRS"
        DEDUCTION = "DEDUCTION", "Maximum less deductions"

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    version = models.CharField(max_length=50)
    authority = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    effective_date = models.DateField(null=True, blank=True)
    scoring_method = models.CharField(
        max_length=15, choices=ScoringMethod.choices, default=ScoringMethod.NONE
    )
    maximum_score = models.IntegerField(null=True, blank=True)
    active = models.BooleanField(default=True)

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


class RequirementMapping(models.Model):
    class Relationship(models.TextChoices):
        EQUIVALENT = "EQUIVALENT", "Equivalent"
        PARTIAL = "PARTIAL", "Partially equivalent"
        RELATED = "RELATED", "Related"

    source = models.ForeignKey(
        Requirement, on_delete=models.CASCADE, related_name="outbound_mappings"
    )
    target = models.ForeignKey(
        Requirement, on_delete=models.CASCADE, related_name="inbound_mappings"
    )
    relationship = models.CharField(
        max_length=15, choices=Relationship.choices, default=Relationship.RELATED
    )
    mapping_reference = models.CharField(max_length=300, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("source__framework__code", "source__requirement_id")
        constraints = [
            models.UniqueConstraint(
                fields=("source", "target"), name="unique_requirement_mapping_direction"
            ),
            models.CheckConstraint(
                condition=~models.Q(source=models.F("target")),
                name="requirement_mapping_not_self",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.source} → {self.target} ({self.get_relationship_display()})"


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
    frameworks = models.ManyToManyField(
        Framework, through="AssessmentFramework", related_name="multi_assessments"
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
    engagement_start = models.DateField(null=True, blank=True)
    engagement_end = models.DateField(null=True, blank=True)
    assessment_locations = models.TextField(blank=True)
    scope_boundaries = models.TextField(blank=True)
    sampling_methodology = models.TextField(blank=True)
    quality_review_status = models.CharField(
        max_length=20,
        choices=(("NOT_STARTED", "Not started"), ("IN_REVIEW", "In review"),
                 ("APPROVED", "Approved"), ("CHANGES_REQUIRED", "Changes required")),
        default="NOT_STARTED",
    )
    quality_review_notes = models.TextField(blank=True)
    signed_off_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="signed_off_assessments",
    )
    signed_off_at = models.DateTimeField(null=True, blank=True)
    locked = models.BooleanField(default=False)
    reopened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="reopened_assessments",
    )
    reopened_at = models.DateTimeField(null=True, blank=True)
    reopen_reason = models.TextField(blank=True)
    notifications_enabled = models.BooleanField(default=True)
    email_notifications_enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ("-updated_at",)

    def __str__(self) -> str:
        return self.name

    @property
    def current_score(self) -> int | None:
        if self.framework.maximum_score is None:
            return None
        return self.framework.maximum_score - sum(
            self.control_results.filter(requirement__framework=self.framework)
            .values_list("calculated_deduction", flat=True)
        )


class AssessmentFramework(models.Model):
    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, related_name="framework_selections"
    )
    framework = models.ForeignKey(
        Framework, on_delete=models.PROTECT, related_name="assessment_selections"
    )
    is_primary = models.BooleanField(default=False)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="added_assessment_frameworks", null=True, blank=True,
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-is_primary", "framework__name", "framework__version")
        constraints = [
            models.UniqueConstraint(
                fields=("assessment", "framework"), name="unique_assessment_framework"
            ),
            models.UniqueConstraint(
                fields=("assessment",), condition=models.Q(is_primary=True),
                name="one_primary_framework_per_assessment",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.assessment}: {self.framework}"


class AssessmentAccess(models.Model):
    class Access(models.TextChoices):
        VIEW = "VIEW", "View only"
        CONTRIBUTE = "CONTRIBUTE", "Contribute"

    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, related_name="access_grants"
    )
    membership = models.ForeignKey(
        Membership, on_delete=models.CASCADE, related_name="assessment_access"
    )
    access = models.CharField(max_length=12, choices=Access.choices, default=Access.VIEW)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="granted_assessment_access"
    )
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=("assessment", "membership"), name="unique_assessment_access"
        )]


class AssessmentTeamMember(models.Model):
    class Role(models.TextChoices):
        LEAD = "LEAD", "Lead assessor"
        ASSESSOR = "ASSESSOR", "Assessor"
        REVIEWER = "REVIEWER", "Quality reviewer"
        SME = "SME", "Subject-matter expert"

    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, related_name="team_members"
    )
    membership = models.ForeignKey(
        Membership, on_delete=models.PROTECT, related_name="assessment_team_assignments"
    )
    role = models.CharField(max_length=12, choices=Role.choices)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=("assessment", "membership"), name="unique_assessment_team_member"
        )]

    def __str__(self) -> str:
        return f"{self.membership} — {self.get_role_display()}"


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

    def derive_from_objectives(self) -> bool:
        results = list(self.objective_results.all())
        if not results:
            return False
        statuses = {item.status for item in results}
        if ObjectiveAssessment.Status.NOT_MET in statuses:
            status = self.Status.NOT_MET
            implementation = self.Implementation.PARTIAL
        elif statuses == {ObjectiveAssessment.Status.NOT_APPLICABLE}:
            status = self.Status.NOT_APPLICABLE
            implementation = self.Implementation.NA
        elif ObjectiveAssessment.Status.NOT_ASSESSED in statuses:
            status = self.Status.NOT_ASSESSED
            implementation = self.Implementation.UNASSESSED
        else:
            status = self.Status.MET
            implementation = self.Implementation.FULL
        changed = self.status != status or self.implementation_state != implementation
        if changed:
            self.status, self.implementation_state = status, implementation
            self.save(update_fields=("status", "implementation_state", "calculated_deduction", "updated_at"))
        return changed


class AssessmentObjective(models.Model):
    requirement = models.ForeignKey(
        Requirement, on_delete=models.CASCADE, related_name="objectives"
    )
    objective_id = models.CharField(max_length=50)
    text = models.TextField()
    source_document = models.CharField(max_length=250, blank=True)
    source_version = models.CharField(max_length=50, blank=True)
    source_page_start = models.PositiveIntegerField(null=True, blank=True)
    source_page_end = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ("requirement__requirement_id", "objective_id")
        constraints = [models.UniqueConstraint(
            fields=("requirement", "objective_id"), name="unique_requirement_objective"
        )]

    def __str__(self) -> str:
        return f"{self.requirement.requirement_id}[{self.objective_id}]"


class AssessmentProcedure(models.Model):
    class Method(models.TextChoices):
        EXAMINE = "EXAMINE", "Examine"
        INTERVIEW = "INTERVIEW", "Interview"
        TEST = "TEST", "Test"
        OBSERVE = "OBSERVE", "Observe"

    requirement = models.ForeignKey(
        Requirement, on_delete=models.CASCADE, related_name="assessment_procedures"
    )
    objective = models.ForeignKey(
        AssessmentObjective, on_delete=models.CASCADE, related_name="procedures",
        null=True, blank=True,
    )
    method = models.CharField(max_length=12, choices=Method.choices)
    sequence = models.PositiveSmallIntegerField(default=1)
    assessment_object = models.TextField()
    source_page_start = models.PositiveIntegerField(null=True, blank=True)
    source_page_end = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ("method", "sequence")
        constraints = [models.UniqueConstraint(
            fields=("requirement", "objective", "method", "sequence"),
            name="unique_assessment_procedure",
        )]


class ObjectiveAssessment(models.Model):
    class Status(models.TextChoices):
        MET = "MET", "MET"
        NOT_MET = "NOT_MET", "NOT MET"
        NOT_APPLICABLE = "NOT_APPLICABLE", "NOT APPLICABLE"
        NOT_ASSESSED = "NOT_ASSESSED", "NOT ASSESSED"

    control_result = models.ForeignKey(
        ControlAssessment, on_delete=models.CASCADE, related_name="objective_results"
    )
    objective = models.ForeignKey(
        AssessmentObjective, on_delete=models.PROTECT, related_name="assessment_results"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_ASSESSED)
    assessor_notes = models.TextField(blank=True)
    evidence = models.ManyToManyField(
        "EvidenceArtifact", related_name="objective_results", blank=True
    )
    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="assessed_objectives",
    )
    assessed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=("control_result", "objective"), name="unique_control_objective_result"
        )]

    def __str__(self) -> str:
        return f"{self.objective} — {self.get_status_display()}"


class InterviewSession(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="interviews")
    title = models.CharField(max_length=250)
    scheduled_at = models.DateTimeField()
    location_or_link = models.CharField(max_length=500, blank=True)
    participants = models.TextField(help_text="Names, titles, and organizational roles.")
    interviewer = models.ForeignKey(
        Membership, on_delete=models.PROTECT, related_name="led_interviews"
    )
    objectives = models.ManyToManyField(ObjectiveAssessment, related_name="interviews", blank=True)
    notes = models.TextField(blank=True)
    completed = models.BooleanField(default=False)


class AssessmentSample(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="samples")
    name = models.CharField(max_length=250)
    population_description = models.TextField()
    population_size = models.PositiveIntegerField()
    sample_size = models.PositiveIntegerField()
    selection_method = models.TextField()
    rationale = models.TextField(blank=True)
    selected_items = models.TextField(blank=True)
    objectives = models.ManyToManyField(ObjectiveAssessment, related_name="samples", blank=True)


class TestExecution(models.Model):
    class Outcome(models.TextChoices):
        PASS = "PASS", "Pass"
        FAIL = "FAIL", "Fail"
        INCONCLUSIVE = "INCONCLUSIVE", "Inconclusive"

    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="test_executions")
    objective_result = models.ForeignKey(
        ObjectiveAssessment, on_delete=models.CASCADE, related_name="test_executions"
    )
    procedure = models.ForeignKey(
        AssessmentProcedure, on_delete=models.PROTECT, related_name="executions",
        null=True, blank=True,
    )
    performed_by = models.ForeignKey(
        Membership, on_delete=models.PROTECT, related_name="test_executions"
    )
    performed_at = models.DateTimeField()
    steps_performed = models.TextField()
    expected_result = models.TextField(blank=True)
    actual_result = models.TextField()
    outcome = models.CharField(max_length=15, choices=Outcome.choices)
    evidence = models.ManyToManyField("EvidenceArtifact", related_name="test_executions", blank=True)


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
    notify_owner = models.BooleanField(default=True)

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
    notify_owner = models.BooleanField(default=True)

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
    notify_owner = models.BooleanField(default=True)

    class Meta:
        ordering = ("sequence", "due_date", "id")

    def __str__(self) -> str:
        return self.title


class GeneratedDocument(models.Model):
    class Kind(models.TextChoices):
        WORKBOOK = "WORKBOOK", "Assessment workbook"
        SSP = "SSP", "Word Security Plan"
        REMEDIATION = "REMEDIATION", "Remediation workbook"
        PACKAGE = "PACKAGE", "Complete assessment package"

    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, related_name="generated_documents"
    )
    kind = models.CharField(max_length=15, choices=Kind.choices)
    filename = models.CharField(max_length=300)
    version = models.CharField(max_length=30, default="1.0")
    readiness = models.JSONField(default=dict, blank=True)
    content_sha256 = models.CharField(max_length=64, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="generated_omni_documents",
    )
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-generated_at",)

    def __str__(self) -> str:
        return self.filename


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


class NotificationPreference(models.Model):
    class Delivery(models.TextChoices):
        IN_APP = "IN_APP", "In-app only"
        EMAIL = "EMAIL", "In-app and immediate email"
        DAILY = "DAILY", "In-app and daily email digest"
        WEEKLY = "WEEKLY", "In-app and weekly email digest"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="omni_notification_preference",
    )
    delivery = models.CharField(max_length=10, choices=Delivery.choices, default=Delivery.IN_APP)
    assignments = models.BooleanField(default=True)
    evidence = models.BooleanField(default=True)
    remediation = models.BooleanField(default=True)
    quality_review = models.BooleanField(default=True)
    due_dates = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"Notification preferences for {self.user}"


class Notification(models.Model):
    class Category(models.TextChoices):
        ASSIGNMENT = "ASSIGNMENT", "Assignment"
        EVIDENCE = "EVIDENCE", "Evidence"
        REMEDIATION = "REMEDIATION", "Remediation"
        QUALITY = "QUALITY", "Quality review"
        DEADLINE = "DEADLINE", "Deadline"
        SYSTEM = "SYSTEM", "System"

    class EmailStatus(models.TextChoices):
        NOT_REQUESTED = "NOT_REQUESTED", "Not requested"
        QUEUED = "QUEUED", "Queued for digest"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="omni_notifications"
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="notifications"
    )
    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, related_name="notifications", null=True, blank=True
    )
    category = models.CharField(max_length=15, choices=Category.choices)
    title = models.CharField(max_length=250)
    message = models.TextField()
    action_url = models.CharField(max_length=500, blank=True)
    object_type = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=100, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    email_status = models.CharField(
        max_length=15, choices=EmailStatus.choices, default=EmailStatus.NOT_REQUESTED
    )
    email_error = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return self.title


class WorkflowHistory(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="workflow_history"
    )
    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, related_name="workflow_history"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="omni_workflow_actions"
    )
    event = models.CharField(max_length=100)
    object_type = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    previous_status = models.CharField(max_length=50, blank=True)
    new_status = models.CharField(max_length=50, blank=True)
    comment = models.TextField(blank=True)
    recipients = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)


class EvidenceReviewHistory(models.Model):
    artifact = models.ForeignKey(
        EvidenceArtifact, on_delete=models.CASCADE, related_name="review_history"
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="evidence_reviews"
    )
    previous_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
