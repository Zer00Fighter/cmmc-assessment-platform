from __future__ import annotations

from datetime import timedelta

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


class ComplianceAutomationPolicy(models.Model):
    class Frequency(models.TextChoices):
        DAILY = "DAILY", "Daily"
        WEEKLY = "WEEKLY", "Weekly"

    class LastStatus(models.TextChoices):
        NEVER = "NEVER", "Never run"
        SUCCESS = "SUCCESS", "Successful"
        FAILED = "FAILED", "Failed"

    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, related_name="compliance_automation_policy"
    )
    enabled = models.BooleanField(default=False)
    frequency = models.CharField(
        max_length=10, choices=Frequency.choices, default=Frequency.DAILY
    )
    next_run_on = models.DateField(null=True, blank=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    last_status = models.CharField(
        max_length=10, choices=LastStatus.choices, default=LastStatus.NEVER
    )
    last_error = models.TextField(blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="updated_compliance_automation_policies",
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Compliance automation for {self.organization}"


class ComplianceAutomationRun(models.Model):
    class Status(models.TextChoices):
        RUNNING = "RUNNING", "Running"
        SUCCESS = "SUCCESS", "Successful"
        FAILED = "FAILED", "Failed"

    policy = models.ForeignKey(
        ComplianceAutomationPolicy, on_delete=models.CASCADE, related_name="runs"
    )
    status = models.CharField(max_length=10, choices=Status.choices)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    summary = models.TextField(blank=True)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ("-started_at",)


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


class LoginAttempt(models.Model):
    identifier = models.CharField(max_length=254)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    failures = models.PositiveSmallIntegerField(default=0)
    blocked_until = models.DateTimeField(null=True, blank=True)
    last_attempt_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=("identifier", "ip_address"), name="unique_login_attempt_source"
        )]


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
    source_filename = models.CharField(max_length=255, blank=True)
    source_sha256 = models.CharField(max_length=64, blank=True)
    is_omni_control_framework = models.BooleanField(
        default=False,
        help_text="Designates Omni's native mapping hub. Only one catalog version may be designated.",
    )

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=("is_omni_control_framework",),
            condition=models.Q(is_omni_control_framework=True),
            name="one_omni_control_framework_hub",
        )]

    def __str__(self) -> str:
        return f"{self.name} {self.version}"


class Requirement(models.Model):
    framework = models.ForeignKey(
        Framework, on_delete=models.CASCADE, related_name="requirements"
    )
    requirement_id = models.CharField(max_length=50)
    domain = models.CharField(max_length=100)
    title = models.CharField(max_length=300)
    statement = models.TextField()
    full_deduction = models.PositiveSmallIntegerField(default=1)
    risk_weight = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Framework-native relative control weight; Omni CCF uses 1–10, with 0 reserved for deprecated controls.",
    )
    partial_credit_allowed = models.BooleanField(default=False)
    source_reference = models.CharField(max_length=300, blank=True)
    source_page = models.PositiveIntegerField(null=True, blank=True)
    source_row = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ("requirement_id",)
        constraints = [
            models.UniqueConstraint(
                fields=("framework", "requirement_id"),
                name="unique_framework_requirement",
            ),
            models.CheckConstraint(
                condition=models.Q(risk_weight__isnull=True) | models.Q(risk_weight__lte=10),
                name="requirement_risk_weight_lte_10",
            ),
        ]

    def __str__(self) -> str:
        return self.requirement_id


class RequirementMapping(models.Model):
    class Relationship(models.TextChoices):
        EQUIVALENT = "EQUIVALENT", "Equivalent"
        PARTIAL = "PARTIAL", "Partially equivalent"
        RELATED = "RELATED", "Related"
        SUPPORTS = "SUPPORTS", "Supports"

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
    source_reference = models.CharField(max_length=300, blank=True)
    confidence = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="approved_requirement_mappings",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    lifecycle = models.CharField(max_length=15, choices=(("DRAFT", "Draft"), ("PENDING", "Pending review"), ("APPROVED", "Approved"), ("REJECTED", "Rejected"), ("SUPERSEDED", "Superseded"), ("RETIRED", "Retired")), default="APPROVED")
    revision = models.PositiveIntegerField(default=1)
    effective_date = models.DateField(null=True, blank=True)

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


class ImplementationActivity(models.Model):
    """Practical implementation guidance; never an authoritative requirement."""

    source_identifier = models.CharField(max_length=50)
    source_area = models.CharField(max_length=150)
    category = models.CharField(max_length=150, blank=True)
    activity = models.TextField()
    control_type = models.CharField(max_length=30, blank=True)
    source_filename = models.CharField(max_length=255)
    source_sha256 = models.CharField(max_length=64)
    source_sheet = models.CharField(max_length=100)
    source_row = models.PositiveIntegerField()
    source_metadata = models.JSONField(default=dict, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("source_area", "source_identifier")
        constraints = [models.UniqueConstraint(
            fields=("source_sha256", "source_sheet", "source_row"),
            name="unique_implementation_activity_source_row",
        )]

    def __str__(self) -> str:
        return f"{self.source_identifier}: {self.activity[:80]}"


class ImplementationActivityMapping(models.Model):
    """Reviewable relationship from an activity to an authoritative criterion."""

    class ReviewStatus(models.TextChoices):
        PROPOSED = "PROPOSED", "Proposed"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    activity = models.ForeignKey(
        ImplementationActivity, on_delete=models.CASCADE, related_name="criterion_mappings"
    )
    target_framework_code = models.CharField(max_length=50)
    target_requirement_id_text = models.CharField(max_length=50)
    target_requirement = models.ForeignKey(
        Requirement, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="implementation_activity_mappings",
    )
    relationship = models.CharField(
        max_length=15, choices=RequirementMapping.Relationship.choices,
        default=RequirementMapping.Relationship.SUPPORTS,
    )
    review_status = models.CharField(
        max_length=10, choices=ReviewStatus.choices, default=ReviewStatus.PROPOSED
    )
    confidence = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    rationale = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="reviewed_implementation_activity_mappings",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("activity__source_identifier", "target_requirement_id_text")
        constraints = [models.UniqueConstraint(
            fields=("activity", "target_framework_code", "target_requirement_id_text"),
            name="unique_implementation_activity_target",
        )]


class FrameworkImport(models.Model):
    class SourceFormat(models.TextChoices):
        CSV = "CSV", "CSV"
        XLSX = "XLSX", "Excel"
        PDF = "PDF", "PDF"

    class Status(models.TextChoices):
        PREVIEW = "PREVIEW", "Awaiting approval"
        IMPORTED = "IMPORTED", "Imported"
        REJECTED = "REJECTED", "Rejected"
        FAILED = "FAILED", "Failed validation"

    source_file = models.FileField(upload_to="private/framework-imports/%Y/%m/")
    source_filename = models.CharField(max_length=255)
    source_format = models.CharField(max_length=8, choices=SourceFormat.choices)
    source_sha256 = models.CharField(max_length=64)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PREVIEW)
    normalized_data = models.JSONField(default=dict)
    validation_report = models.JSONField(default=dict)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="framework_imports"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
        related_name="approved_framework_imports",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    imported_framework = models.ForeignKey(
        Framework, null=True, blank=True, on_delete=models.PROTECT, related_name="imports"
    )

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.source_filename} ({self.get_status_display()})"


class ExternalAuthority(models.Model):
    class Kind(models.TextChoices):
        STANDARD = "STANDARD", "Standard or framework"
        REGULATION = "REGULATION", "Regulation or law"
        CONTRACT = "CONTRACT", "Contractual or industry requirement"
        OTHER = "OTHER", "Other"

    code = models.SlugField(max_length=100, unique=True)
    canonical_name = models.CharField(max_length=300)
    version = models.CharField(max_length=100, blank=True)
    kind = models.CharField(max_length=15, choices=Kind.choices, default=Kind.STANDARD)
    issuer = models.CharField(max_length=250, blank=True)
    jurisdiction = models.CharField(max_length=150, blank=True)
    aliases = models.JSONField(default=list, blank=True)
    source_column = models.PositiveIntegerField(null=True, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ("canonical_name", "version")

    def __str__(self) -> str:
        return self.canonical_name


class AuthoritativeDocument(models.Model):
    class Quality(models.TextChoices):
        VALID = "VALID", "Valid"
        MISSING_URL = "MISSING_URL", "Missing URL"
        INVALID_URL = "INVALID_URL", "Invalid URL"
        DUPLICATE_ADI = "DUPLICATE_ADI", "Duplicate identifier"

    authority = models.ForeignKey(
        ExternalAuthority, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="authoritative_documents",
    )
    locale = models.CharField(max_length=100)
    ccf_column_header = models.CharField(max_length=300)
    authoritative_document_id = models.CharField(max_length=150)
    publisher = models.CharField(max_length=250)
    formal_name = models.CharField(max_length=500)
    official_url = models.URLField(max_length=1000, blank=True)
    source_url_text = models.TextField(blank=True)
    quality = models.CharField(max_length=20, choices=Quality.choices, default=Quality.VALID)
    superseded_by = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="supersedes"
    )
    active = models.BooleanField(default=True)
    source_row = models.PositiveIntegerField()
    source_filename = models.CharField(max_length=255)
    source_sha256 = models.CharField(max_length=64)
    last_link_check_at = models.DateTimeField(null=True, blank=True)
    last_link_status = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ("locale", "publisher", "formal_name")
        constraints = [models.UniqueConstraint(
            fields=("source_sha256", "source_row"), name="unique_authoritative_source_row"
        )]


class RiskCatalogEntry(models.Model):
    risk_id = models.CharField(max_length=30, unique=True)
    grouping = models.CharField(max_length=100)
    title = models.CharField(max_length=300)
    description = models.TextField()
    active = models.BooleanField(default=True)
    source_row = models.PositiveIntegerField()
    source_filename = models.CharField(max_length=255)
    source_sha256 = models.CharField(max_length=64)

    class Meta:
        ordering = ("grouping", "risk_id")

    def __str__(self) -> str:
        return f"{self.risk_id} — {self.title}"


class RequirementRiskMapping(models.Model):
    class ReviewStatus(models.TextChoices):
        PROPOSED = "PROPOSED", "Proposed"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    requirement = models.ForeignKey(
        Requirement, on_delete=models.CASCADE, related_name="risk_mappings"
    )
    risk = models.ForeignKey(
        RiskCatalogEntry, on_delete=models.PROTECT, related_name="control_mappings"
    )
    review_status = models.CharField(
        max_length=10, choices=ReviewStatus.choices, default=ReviewStatus.PROPOSED
    )
    rationale = models.TextField()
    source = models.CharField(max_length=30, default="MANUAL")
    confidence = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    proposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
        related_name="proposed_control_risks",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
        related_name="reviewed_control_risks",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("review_status", "requirement__framework__code", "requirement__requirement_id", "risk__risk_id")
        constraints = [models.UniqueConstraint(
            fields=("requirement", "risk"), name="unique_requirement_risk_mapping"
        )]


class MappingReference(models.Model):
    class Status(models.TextChoices):
        UNRESOLVED = "UNRESOLVED", "Unresolved"
        RESOLVED = "RESOLVED", "Resolved"
        IGNORED = "IGNORED", "Ignored"

    class ReviewStatus(models.TextChoices):
        PENDING = "PENDING", "Pending review"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    import_job = models.ForeignKey(
        FrameworkImport, on_delete=models.CASCADE, related_name="mapping_references"
    )
    source_requirement = models.ForeignKey(
        Requirement, null=True, blank=True, on_delete=models.CASCADE,
        related_name="catalog_mapping_references",
    )
    source_requirement_id_text = models.CharField(max_length=100)
    authority = models.ForeignKey(
        ExternalAuthority, on_delete=models.PROTECT, related_name="mapping_references"
    )
    raw_reference = models.TextField()
    parsed_reference = models.CharField(max_length=300, blank=True)
    target_requirement = models.ForeignKey(
        Requirement, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="incoming_catalog_references",
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.UNRESOLVED)
    relationship = models.CharField(
        max_length=15, choices=RequirementMapping.Relationship.choices,
        default=RequirementMapping.Relationship.RELATED,
    )
    review_status = models.CharField(
        max_length=10, choices=ReviewStatus.choices, default=ReviewStatus.PENDING
    )
    confidence = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    source_row = models.PositiveIntegerField(null=True, blank=True)
    source_column = models.PositiveIntegerField(null=True, blank=True)
    rationale = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
        related_name="reviewed_mapping_references",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("review_status", "authority__canonical_name", "source_requirement_id_text")
        constraints = [models.UniqueConstraint(
            fields=("import_job", "source_requirement_id_text", "authority", "raw_reference"),
            name="unique_import_mapping_reference",
        )]


class OmniEvidenceSourceRequest(models.Model):
    class Resolution(models.TextChoices):
        EXACT = "EXACT", "Exact canonical match"
        ALIAS = "ALIAS", "Approved alias"
        NEW_CANDIDATE = "NEW_CANDIDATE", "New-object candidate"
        REVIEW = "REVIEW", "Needs review"
        DISREGARDED = "DISREGARDED", "Disregarded"

    source_identifier = models.CharField(max_length=30, unique=True)
    area_of_focus = models.CharField(max_length=250)
    source_title = models.CharField(max_length=300)
    source_description = models.TextField()
    omni_control_ids = models.JSONField(default=list)
    source_cmmc_ids = models.JSONField(default=list)
    normalized_cmmc_ids = models.JSONField(default=list)
    canonical_evidence_code = models.CharField(max_length=30, blank=True)
    resolution = models.CharField(max_length=20, choices=Resolution.choices, default=Resolution.REVIEW)
    reviewer_rationale = models.TextField(blank=True)
    source_row = models.PositiveIntegerField()
    source_filename = models.CharField(max_length=255)
    source_sha256 = models.CharField(max_length=64)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="reviewed_omni_evidence_sources")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("area_of_focus", "source_identifier")


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
    risk_management_enabled = models.BooleanField(default=False)
    include_risk_in_reports = models.BooleanField(default=False)
    source_template = models.ForeignKey(
        "AssessmentTemplate", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assessments",
    )
    prior_assessment = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="successor_assessments",
    )

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


class AssessmentTemplate(models.Model):
    class Recurrence(models.TextChoices):
        NONE = "NONE", "Not recurring"
        MONTHLY = "MONTHLY", "Monthly"
        QUARTERLY = "QUARTERLY", "Quarterly"
        SEMIANNUAL = "SEMIANNUAL", "Every six months"
        ANNUAL = "ANNUAL", "Annual"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="assessment_templates"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    primary_framework = models.ForeignKey(
        Framework, on_delete=models.PROTECT, related_name="primary_assessment_templates"
    )
    frameworks = models.ManyToManyField(Framework, related_name="assessment_templates")
    scope_boundaries = models.TextField(blank=True)
    assessment_locations = models.TextField(blank=True)
    sampling_methodology = models.TextField(blank=True)
    evidence_request_blueprints = models.JSONField(default=list, blank=True)
    notifications_enabled = models.BooleanField(default=True)
    email_notifications_enabled = models.BooleanField(default=True)
    risk_management_enabled = models.BooleanField(default=False)
    include_risk_in_reports = models.BooleanField(default=False)
    recurrence = models.CharField(
        max_length=12, choices=Recurrence.choices, default=Recurrence.NONE
    )
    next_start_date = models.DateField(null=True, blank=True)
    default_duration_days = models.PositiveSmallIntegerField(default=30)
    active = models.BooleanField(default=True)
    created_from = models.ForeignKey(
        Assessment, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="derived_templates",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="created_assessment_templates",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        constraints = [models.UniqueConstraint(
            fields=("organization", "name"), name="unique_assessment_template_per_org"
        )]

    def __str__(self) -> str:
        return self.name


class AssessmentBaseline(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        APPROVED = "APPROVED", "Approved"
        RETIRED = "RETIRED", "Retired"

    assessment = models.ForeignKey(
        Assessment, on_delete=models.PROTECT, related_name="baselines"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    snapshot = models.JSONField(default=dict)
    checksum = models.CharField(max_length=64)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="created_assessment_baselines",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="approved_assessment_baselines",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    retired_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="retired_assessment_baselines",
    )
    retired_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [models.UniqueConstraint(
            fields=("assessment", "name"), name="unique_baseline_name_per_assessment"
        )]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if self.pk:
            original = type(self).objects.only("snapshot", "checksum").get(pk=self.pk)
            if self.snapshot != original.snapshot or self.checksum != original.checksum:
                raise ValueError("An assessment baseline snapshot and checksum are immutable.")
        super().save(*args, **kwargs)


class AssessmentReuseDecision(models.Model):
    class Basis(models.TextChoices):
        DIRECT = "DIRECT", "Direct mapping"
        OMNI_DERIVED = "OMNI_DERIVED", "Derived through Omni Control Framework"

    class Status(models.TextChoices):
        SUGGESTED = "SUGGESTED", "Suggested"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, related_name="reuse_decisions"
    )
    source_result = models.ForeignKey(
        "ControlAssessment", on_delete=models.CASCADE, related_name="reuse_sources"
    )
    target_result = models.ForeignKey(
        "ControlAssessment", on_delete=models.CASCADE, related_name="reuse_targets"
    )
    basis = models.CharField(max_length=20, choices=Basis.choices)
    relationship = models.CharField(max_length=15, choices=RequirementMapping.Relationship.choices)
    mapping_path = models.JSONField(default=list)
    reuse_evidence = models.BooleanField(default=True)
    reuse_testing = models.BooleanField(default=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SUGGESTED)
    rationale = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
        related_name="reviewed_assessment_reuse",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("status", "source_result__requirement__framework__code")
        constraints = [
            models.UniqueConstraint(
                fields=("assessment", "source_result", "target_result"),
                name="unique_assessment_reuse_direction",
            ),
            models.CheckConstraint(
                condition=~models.Q(source_result=models.F("target_result")),
                name="assessment_reuse_not_self",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.source_result} → {self.target_result} ({self.get_status_display()})"


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
    freshness_days = models.PositiveSmallIntegerField(
        default=0,
        help_text="Expected validity in days. Use 0 when this evidence does not expire.",
    )
    renewal_lead_days = models.PositiveSmallIntegerField(
        default=30,
        help_text="Open renewal work this many days before the evidence becomes stale.",
    )
    auto_renew = models.BooleanField(
        default=True,
        help_text="Allow Omni to create a renewal request before linked evidence expires.",
    )
    renewal_of = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="renewal_requests",
    )
    renewal_generated_at = models.DateTimeField(null=True, blank=True)
    consolidated_into = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="consolidated_requests"
    )

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
    effective_on = models.DateField(
        null=True, blank=True,
        help_text="Date the evidence became effective or was issued.",
    )
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    expires_on = models.DateField(null=True, blank=True)
    superseded_by = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="supersedes"
    )
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

    @property
    def freshness(self) -> str:
        if self.superseded_by_id:
            return "SUPERSEDED"
        deadline = self.freshness_deadline
        if deadline is None:
            return "UNDATED"
        if deadline < timezone.localdate():
            return "EXPIRED"
        if deadline <= timezone.localdate() + timedelta(days=self.renewal_lead_days):
            return "AGING"
        return "CURRENT"

    @property
    def freshness_reference_date(self):
        return self.effective_on or self.period_end or (
            self.created_at.date() if self.created_at else None
        )

    @property
    def freshness_deadline(self):
        if self.expires_on:
            return self.expires_on
        reference = self.freshness_reference_date
        if not reference or not self.pk:
            return None
        validity = [
            item.freshness_days for item in self.requests.all()
            if item.freshness_days
        ]
        return reference + timedelta(days=min(validity)) if validity else None

    @property
    def renewal_lead_days(self) -> int:
        if not self.pk:
            return 30
        lead_times = [item.renewal_lead_days for item in self.requests.all()]
        return max(lead_times) if lead_times else 30


class EvidenceApplicability(models.Model):
    class Applicability(models.TextChoices):
        FULL = "FULL", "Fully applicable"
        PARTIAL = "PARTIAL", "Partially applicable"
        NOT_APPLICABLE = "NOT_APPLICABLE", "Not applicable"
        ADDITIONAL_REQUIRED = "ADDITIONAL_REQUIRED", "Additional evidence required"

    artifact = models.ForeignKey(EvidenceArtifact, on_delete=models.CASCADE, related_name="applicability_reviews")
    control_result = models.ForeignKey(ControlAssessment, on_delete=models.CASCADE, related_name="evidence_applicability")
    applicability = models.CharField(max_length=25, choices=Applicability.choices)
    rationale = models.TextField(blank=True)
    scope_limitations = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="evidence_applicability_reviews")
    reviewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("artifact", "control_result"), name="unique_evidence_applicability")]


class TestReuseReference(models.Model):
    source_test = models.ForeignKey(TestExecution, on_delete=models.CASCADE, related_name="reuse_references")
    target_objective = models.ForeignKey(ObjectiveAssessment, on_delete=models.CASCADE, related_name="reused_tests")
    reuse_decision = models.ForeignKey(AssessmentReuseDecision, on_delete=models.PROTECT, related_name="test_references")
    limitations = models.TextField(blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="approved_test_reuse")
    approved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("source_test", "target_objective"), name="unique_test_reuse_target")]


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


class RiskRegisterEntry(models.Model):
    class Status(models.TextChoices):
        IDENTIFIED = "IDENTIFIED", "Identified"
        ANALYZING = "ANALYZING", "Analyzing"
        TREATING = "TREATING", "Treatment in progress"
        MONITORING = "MONITORING", "Monitoring"
        ACCEPTED = "ACCEPTED", "Accepted"
        CLOSED = "CLOSED", "Closed"

    class Treatment(models.TextChoices):
        UNDECIDED = "UNDECIDED", "Undecided"
        MITIGATE = "MITIGATE", "Mitigate"
        ACCEPT = "ACCEPT", "Accept"
        AVOID = "AVOID", "Avoid"
        TRANSFER = "TRANSFER", "Transfer"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="risk_register"
    )
    system = models.ForeignKey(
        System, null=True, blank=True, on_delete=models.CASCADE, related_name="risks"
    )
    assessment = models.ForeignKey(
        Assessment, null=True, blank=True, on_delete=models.SET_NULL, related_name="risks"
    )
    catalog_risk = models.ForeignKey(
        RiskCatalogEntry, null=True, blank=True, on_delete=models.PROTECT,
        related_name="register_entries",
    )
    risk_id = models.CharField(max_length=30)
    title = models.CharField(max_length=300)
    description = models.TextField()
    category = models.CharField(max_length=100)
    source = models.CharField(max_length=30, default="MANUAL")
    controls = models.ManyToManyField(ControlAssessment, related_name="risks", blank=True)
    remediation_plans = models.ManyToManyField(RemediationPlan, related_name="risks", blank=True)
    supporting_evidence = models.ManyToManyField(
        EvidenceArtifact, related_name="risks", blank=True
    )
    owner = models.ForeignKey(
        Membership, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="owned_risks",
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.IDENTIFIED)
    likelihood = models.PositiveSmallIntegerField(default=3)
    impact = models.PositiveSmallIntegerField(default=3)
    inherent_score = models.PositiveSmallIntegerField(default=9)
    treatment = models.CharField(
        max_length=12, choices=Treatment.choices, default=Treatment.UNDECIDED
    )
    treatment_plan = models.TextField(blank=True)
    target_date = models.DateField(null=True, blank=True)
    residual_likelihood = models.PositiveSmallIntegerField(null=True, blank=True)
    residual_impact = models.PositiveSmallIntegerField(null=True, blank=True)
    residual_score = models.PositiveSmallIntegerField(null=True, blank=True)
    acceptance_rationale = models.TextField(blank=True)
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
        related_name="accepted_risks",
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    acceptance_expires = models.DateField(null=True, blank=True)
    next_review_date = models.DateField(null=True, blank=True)
    review_frequency_days = models.PositiveSmallIntegerField(default=90)
    last_reviewed_at = models.DateTimeField(null=True, blank=True)
    trend = models.CharField(
        max_length=12,
        choices=(("UNKNOWN", "Unknown"), ("INCREASING", "Increasing"),
                 ("STABLE", "Stable"), ("DECREASING", "Decreasing")),
        default="UNKNOWN",
    )
    monitoring_notes = models.TextField(blank=True)
    trigger_events = models.TextField(blank=True)
    closure_rationale = models.TextField(blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
        related_name="closed_risks",
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_risks"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-inherent_score", "risk_id")
        constraints = [
            models.UniqueConstraint(fields=("organization", "risk_id"), name="unique_org_risk_id"),
            models.CheckConstraint(condition=models.Q(likelihood__gte=1, likelihood__lte=5), name="risk_likelihood_1_5"),
            models.CheckConstraint(condition=models.Q(impact__gte=1, impact__lte=5), name="risk_impact_1_5"),
            models.CheckConstraint(condition=models.Q(residual_likelihood__isnull=True) | models.Q(residual_likelihood__gte=1, residual_likelihood__lte=5), name="residual_likelihood_1_5"),
            models.CheckConstraint(condition=models.Q(residual_impact__isnull=True) | models.Q(residual_impact__gte=1, residual_impact__lte=5), name="residual_impact_1_5"),
        ]

    def save(self, *args, **kwargs):
        self.inherent_score = self.likelihood * self.impact
        self.residual_score = (
            self.residual_likelihood * self.residual_impact
            if self.residual_likelihood is not None and self.residual_impact is not None
            else None
        )
        super().save(*args, **kwargs)

    @property
    def rating(self):
        if self.inherent_score >= 20:
            return "Critical"
        if self.inherent_score >= 12:
            return "High"
        if self.inherent_score >= 6:
            return "Moderate"
        return "Low"

    def __str__(self):
        return f"{self.risk_id} — {self.title}"


class RiskRegisterHistory(models.Model):
    risk = models.ForeignKey(RiskRegisterEntry, on_delete=models.CASCADE, related_name="history")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=30)
    snapshot = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)


class RiskTolerancePolicy(models.Model):
    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, related_name="risk_tolerance_policy"
    )
    maximum_residual_score = models.PositiveSmallIntegerField(default=11)
    critical_acceptance_allowed = models.BooleanField(default=False)
    maximum_acceptance_days = models.PositiveSmallIntegerField(default=365)
    review_reminder_days = models.PositiveSmallIntegerField(default=14)
    acceptance_expiry_reminder_days = models.PositiveSmallIntegerField(default=30)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="updated_risk_tolerance_policies"
    )
    updated_at = models.DateTimeField(auto_now=True)


class RiskTreatmentAction(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = "NOT_STARTED", "Not started"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        BLOCKED = "BLOCKED", "Blocked"
        COMPLETE = "COMPLETE", "Complete"

    risk = models.ForeignKey(RiskRegisterEntry, on_delete=models.CASCADE, related_name="treatment_actions")
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(Membership, null=True, blank=True, on_delete=models.SET_NULL,
                              related_name="risk_treatment_actions")
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.NOT_STARTED)
    priority = models.CharField(max_length=10, choices=RemediationPlan.Priority.choices,
                                default=RemediationPlan.Priority.MEDIUM)
    planned_start = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    completed_date = models.DateField(null=True, blank=True)
    completion_notes = models.TextField(blank=True)
    remediation_plan = models.ForeignKey(RemediationPlan, null=True, blank=True,
                                         on_delete=models.SET_NULL, related_name="risk_treatment_actions")
    evidence = models.ManyToManyField(EvidenceArtifact, related_name="risk_treatment_actions", blank=True)
    dependencies = models.ManyToManyField("self", symmetrical=False, blank=True,
                                          related_name="dependent_actions")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                   related_name="created_risk_treatment_actions")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("status", "due_date", "id")


class RiskReassessment(models.Model):
    risk = models.ForeignKey(RiskRegisterEntry, on_delete=models.CASCADE, related_name="reassessments")
    previous_likelihood = models.PositiveSmallIntegerField()
    previous_impact = models.PositiveSmallIntegerField()
    new_likelihood = models.PositiveSmallIntegerField()
    new_impact = models.PositiveSmallIntegerField()
    rationale = models.TextField()
    evidence = models.ManyToManyField(EvidenceArtifact, related_name="risk_reassessments", blank=True)
    assessed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                    related_name="risk_reassessments")
    assessed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-assessed_at",)


class RiskAcceptanceRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"

    risk = models.ForeignKey(RiskRegisterEntry, on_delete=models.CASCADE, related_name="acceptance_requests")
    rationale = models.TextField()
    requested_expiration = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                     related_name="risk_acceptance_requests")
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.PROTECT, related_name="reviewed_risk_acceptance_requests")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_comment = models.TextField(blank=True)

    class Meta:
        ordering = ("status", "requested_at")


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
        FRAMEWORK_REPORT = "FRAMEWORK_REPORT", "Framework assessment report"
        CONSOLIDATED_REPORT = "CONSOLIDATED", "Consolidated multi-framework report"
        TRACEABILITY = "TRACEABILITY", "Cross-framework traceability matrix"

    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, related_name="generated_documents"
    )
    kind = models.CharField(max_length=25, choices=Kind.choices)
    framework = models.ForeignKey(Framework, null=True, blank=True, on_delete=models.PROTECT, related_name="generated_documents")
    status = models.CharField(max_length=10, choices=(("DRAFT", "Draft"), ("FINAL", "Final"), ("SUPERSEDED", "Superseded")), default="DRAFT")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="approved_omni_documents")
    approved_at = models.DateTimeField(null=True, blank=True)
    superseded_by = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="supersedes")
    stale = models.BooleanField(default=False)
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


class ReportingProfile(models.Model):
    framework = models.OneToOneField(Framework, on_delete=models.CASCADE, related_name="reporting_profile")
    report_title = models.CharField(max_length=250)
    template_version = models.CharField(max_length=50, default="1.0")
    required_sections = models.JSONField(default=list)
    status_labels = models.JSONField(default=dict, blank=True)
    require_objectives = models.BooleanField(default=True)
    require_evidence_applicability = models.BooleanField(default=True)
    active = models.BooleanField(default=True)


class MappingChangeRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending review"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    mapping = models.ForeignKey(RequirementMapping, on_delete=models.PROTECT, related_name="change_requests")
    proposed_relationship = models.CharField(max_length=15, choices=RequirementMapping.Relationship.choices)
    proposed_rationale = models.TextField()
    proposed_confidence = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="mapping_changes_requested")
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="mapping_changes_reviewed")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewer_comment = models.TextField(blank=True)


class MappingHistory(models.Model):
    mapping = models.ForeignKey(RequirementMapping, on_delete=models.PROTECT, related_name="history")
    revision = models.PositiveIntegerField()
    snapshot = models.JSONField()
    action = models.CharField(max_length=30)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="mapping_history_events")
    created_at = models.DateTimeField(auto_now_add=True)


class RevalidationTask(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        CONFIRMED = "CONFIRMED", "Revalidated"
        NO_ACTION = "NO_ACTION", "No action required"

    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="revalidation_tasks")
    change_request = models.ForeignKey(MappingChangeRequest, on_delete=models.CASCADE, related_name="revalidation_tasks")
    reuse_decision = models.ForeignKey(AssessmentReuseDecision, null=True, blank=True, on_delete=models.SET_NULL, related_name="revalidation_tasks")
    reason = models.TextField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)


class ControlMonitoringProfile(models.Model):
    control_result = models.OneToOneField(
        ControlAssessment, on_delete=models.CASCADE, related_name="monitoring_profile"
    )
    enabled = models.BooleanField(default=False)
    review_frequency_days = models.PositiveSmallIntegerField(default=90)
    next_review_date = models.DateField(null=True, blank=True)
    owner = models.ForeignKey(
        Membership, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="control_monitoring_profiles",
    )
    monitoring_notes = models.TextField(blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="updated_control_monitoring_profiles",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("next_review_date", "control_result__requirement__requirement_id")


class ControlMonitoringEvent(models.Model):
    class EventType(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Scheduled review"
        EVIDENCE = "EVIDENCE", "Evidence freshness"
        CHANGE = "CHANGE", "System or process change"
        INCIDENT = "INCIDENT", "Security or privacy incident"
        VULNERABILITY = "VULNERABILITY", "Vulnerability or threat"
        AUDIT = "AUDIT", "Audit or assessment finding"
        MANUAL = "MANUAL", "Manual observation"

    class Severity(models.TextChoices):
        LOW = "LOW", "Low"
        MODERATE = "MODERATE", "Moderate"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        REVIEWED = "REVIEWED", "Reviewed"
        DISMISSED = "DISMISSED", "Dismissed"

    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, related_name="monitoring_events"
    )
    title = models.CharField(max_length=250)
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    severity = models.CharField(
        max_length=12, choices=Severity.choices, default=Severity.MODERATE
    )
    occurred_on = models.DateField(default=timezone.localdate)
    description = models.TextField()
    source_reference = models.CharField(max_length=500, blank=True)
    source_key = models.CharField(max_length=200, blank=True)
    controls = models.ManyToManyField(
        ControlAssessment, related_name="monitoring_events"
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="reported_control_monitoring_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-occurred_on", "-created_at")
        constraints = [models.UniqueConstraint(
            fields=("assessment", "source_key"),
            condition=~models.Q(source_key=""), name="unique_monitoring_source_per_assessment",
        )]


class ControlReassessmentTask(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        COMPLETED = "COMPLETED", "Reassessed"
        NO_ACTION = "NO_ACTION", "No action required"

    event = models.ForeignKey(
        ControlMonitoringEvent, on_delete=models.CASCADE, related_name="reassessment_tasks"
    )
    control_result = models.ForeignKey(
        ControlAssessment, on_delete=models.CASCADE, related_name="reassessment_tasks"
    )
    assigned_to = models.ForeignKey(
        Membership, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="control_reassessment_tasks",
    )
    due_date = models.DateField(null=True, blank=True)
    reason = models.TextField()
    prior_conclusion = models.JSONField(default=dict)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.OPEN)
    resolution = models.TextField(blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="completed_control_reassessment_tasks",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("status", "due_date", "control_result__requirement__requirement_id")
        constraints = [models.UniqueConstraint(
            fields=("event", "control_result"), name="unique_reassessment_task_per_event_control"
        )]


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


class IntegrationPolicy(models.Model):
    class Delivery(models.TextChoices):
        IN_APP = "IN_APP", "In-app only"
        EMAIL = "EMAIL", "Email"
        EXTERNAL = "EXTERNAL", "External ticket"
        BOTH = "BOTH", "Email and external ticket"

    class Provider(models.TextChoices):
        NONE = "NONE", "Not configured"
        JIRA = "JIRA", "Jira"
        SERVICENOW = "SERVICENOW", "ServiceNow"
        OTHER = "OTHER", "Other ticketing platform"

    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, related_name="integration_policy"
    )
    delivery = models.CharField(max_length=12, choices=Delivery.choices, default=Delivery.IN_APP)
    provider = models.CharField(max_length=15, choices=Provider.choices, default=Provider.NONE)
    external_ticketing_enabled = models.BooleanField(default=False)
    create_for_evidence = models.BooleanField(default=False)
    create_for_findings = models.BooleanField(default=False)
    create_for_remediation = models.BooleanField(default=False)
    create_for_risk_treatment = models.BooleanField(default=False)
    create_for_monitoring = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Integration policy for {self.organization}"


class OutboundWorkItem(models.Model):
    class EventType(models.TextChoices):
        EVIDENCE = "EVIDENCE", "Evidence request"
        FINDING = "FINDING", "Finding"
        REMEDIATION = "REMEDIATION", "Remediation action"
        RISK = "RISK", "Risk treatment"
        MONITORING = "MONITORING", "Monitoring or reassessment"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        NOT_CONFIGURED = "NOT_CONFIGURED", "Connector not configured"
        QUEUED = "QUEUED", "Queued"
        SYNCED = "SYNCED", "Synchronized"
        FAILED = "FAILED", "Failed"
        CLOSED = "CLOSED", "Closed"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="outbound_work_items")
    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, related_name="outbound_work_items", null=True, blank=True
    )
    event_type = models.CharField(max_length=15, choices=EventType.choices)
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    object_type = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    assignee = models.ForeignKey(
        Membership, on_delete=models.SET_NULL, null=True, blank=True, related_name="outbound_work_items"
    )
    provider = models.CharField(
        max_length=15, choices=IntegrationPolicy.Provider.choices, default=IntegrationPolicy.Provider.NONE
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    external_ticket_id = models.CharField(max_length=100, blank=True)
    external_ticket_url = models.URLField(blank=True, max_length=1000)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=500, blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_outbound_work_items"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [models.UniqueConstraint(
            fields=("organization", "event_type", "object_type", "object_id"),
            name="unique_outbound_work_item_source",
        )]

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
