from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from datetime import timedelta
from django.utils.text import slugify

from src.evidence.evidence_knowledge import EVIDENCE_KNOWLEDGE

from .models import (
    Assessment, AssessmentAccess, AssessmentBaseline, AssessmentFramework, AssessmentProcedure, AssessmentProcedureCustomization, AssessmentReuseDecision, AssessmentSample, AssessmentTeamMember, AssessmentTemplate,
    ComplianceAutomationPolicy, ControlAssessment, ControlMonitoringEvent, ControlMonitoringProfile,
    ControlReassessmentTask, EvidenceApplicability, EvidenceArtifact, EvidenceRequest, Framework, MappingReference,
    InterviewSession, Membership, ObjectiveAssessment, Organization,
    NotificationPreference,
    NotificationPolicy, IntegrationPolicy,
    OrganizationInvitation, UserProfile,
    LoginAttempt,
    RemediationMilestone, RemediationPlan, RequirementMapping, RequirementRiskMapping,
    MappingChangeRequest, RiskAcceptanceRequest, RiskReassessment, RiskRegisterEntry,
    RiskTolerancePolicy, RiskTreatmentAction, Soc2AssessmentProfile, System, TestExecution,
)
from .soc2_assessment import synchronize_soc2_scope


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = (
            "name", "legal_name", "kind", "website", "industry", "address",
            "primary_contact_name", "primary_contact_email",
        )
        widgets = {"address": forms.Textarea(attrs={"rows": 3})}

    def save(self, commit=True):
        instance = super().save(commit=False)
        base = slugify(instance.name) or "organization"
        candidate, suffix = base, 2
        while Organization.objects.exclude(pk=instance.pk).filter(slug=candidate).exists():
            candidate, suffix = f"{base}-{suffix}", suffix + 1
        instance.slug = candidate
        if commit:
            instance.save()
        return instance


class FrameworkImportForm(forms.Form):
    source_file = forms.FileField(
        help_text="CSV, Excel (.xlsx/.xlsm), or text-based PDF. Scanned PDFs require OCR first."
    )
    code = forms.CharField(max_length=50, help_text="Unique, version-specific catalog code.")
    name = forms.CharField(max_length=200)
    version = forms.CharField(max_length=50)
    authority = forms.CharField(max_length=200, required=False)
    description = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)
    is_omni_control_framework = forms.BooleanField(
        required=False,
        label="Designate as the Omni Control Framework mapping hub",
        help_text="Use only for Omni's native framework, not for an imported external authority.",
    )

    def clean_source_file(self):
        upload = self.cleaned_data["source_file"]
        suffix = upload.name.rsplit(".", 1)[-1].lower() if "." in upload.name else ""
        if suffix not in {"csv", "xlsx", "xlsm", "pdf"}:
            raise forms.ValidationError("Choose a CSV, XLSX, XLSM, or PDF file.")
        if upload.size > 30 * 1024 * 1024:
            raise forms.ValidationError("Framework source files must be 30 MB or smaller.")
        return upload


class AssessmentReuseDecisionForm(forms.ModelForm):
    class Meta:
        model = AssessmentReuseDecision
        fields = ("reuse_evidence", "reuse_testing", "rationale")
        widgets = {"rationale": forms.Textarea(attrs={"rows": 3})}


class MappingReferenceReviewForm(forms.ModelForm):
    class Meta:
        model = MappingReference
        fields = ("relationship", "confidence", "rationale")
        widgets = {"rationale": forms.Textarea(attrs={"rows": 2})}


class RequirementRiskMappingForm(forms.ModelForm):
    class Meta:
        model = RequirementRiskMapping
        fields = ("requirement", "risk", "confidence", "rationale")
        widgets = {"rationale": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["requirement"].queryset = self.fields["requirement"].queryset.select_related(
            "framework"
        ).order_by("framework__code", "requirement_id")
        self.fields["risk"].queryset = self.fields["risk"].queryset.filter(active=True)


class MappingChangeRequestForm(forms.ModelForm):
    class Meta:
        model = MappingChangeRequest
        fields = ("mapping", "proposed_relationship", "proposed_confidence", "proposed_rationale", "reason")
        widgets = {"proposed_rationale": forms.Textarea(attrs={"rows": 3}), "reason": forms.Textarea(attrs={"rows": 3})}


class OmniAuthenticationForm(AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        "locked": "Too many unsuccessful attempts. Try again later.",
    }

    def clean(self):
        identifier = (self.data.get("username") or "").strip().casefold()
        forwarded = self.request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip_address = (forwarded.split(",", 1)[0].strip() if forwarded else self.request.META.get("REMOTE_ADDR")) or None
        attempt, _ = LoginAttempt.objects.get_or_create(
            identifier=identifier[:254], ip_address=ip_address
        )
        if attempt.blocked_until and attempt.blocked_until > timezone.now():
            raise forms.ValidationError(self.error_messages["locked"], code="locked")
        try:
            cleaned = super().clean()
        except forms.ValidationError:
            from django.conf import settings
            attempt.failures += 1
            if attempt.failures >= settings.OMNI_LOGIN_FAILURE_LIMIT:
                attempt.blocked_until = timezone.now() + timedelta(
                    minutes=settings.OMNI_LOGIN_LOCKOUT_MINUTES
                )
            attempt.save()
            raise
        attempt.failures = 0
        attempt.blocked_until = None
        attempt.save(update_fields=("failures", "blocked_until", "last_attempt_at"))
        return cleaned


class SystemForm(forms.ModelForm):
    class Meta:
        model = System
        fields = (
            "name", "description", "cage_code", "system_owner_name",
            "system_owner_email", "location", "environment", "data_types", "scope",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "data_types": forms.Textarea(attrs={"rows": 3}),
            "scope": forms.Textarea(attrs={"rows": 4}),
        }


class MembershipForm(forms.ModelForm):
    username_or_email = forms.CharField(
        label="Existing user", help_text="Enter the user's username or email address."
    )

    class Meta:
        model = Membership
        fields = ("username_or_email", "role")

    def clean_username_or_email(self):
        value = self.cleaned_data["username_or_email"].strip()
        users = get_user_model().objects.filter(username__iexact=value)
        if not users.exists():
            users = get_user_model().objects.filter(email__iexact=value)
        if users.count() != 1:
            raise forms.ValidationError("No unique Omni account matches that username or email.")
        self.user = users.get()
        return value


class InvitationForm(forms.ModelForm):
    class Meta:
        model = OrganizationInvitation
        fields = ("email", "role")


class InvitationAcceptForm(forms.Form):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    password1 = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

    def clean_password1(self):
        password = self.cleaned_data["password1"]
        validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            self.add_error("password2", "Passwords do not match.")
        return cleaned


class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()

    class Meta:
        model = UserProfile
        fields = ("first_name", "last_name", "email", "job_title", "phone", "time_zone")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].initial = self.instance.user.first_name
        self.fields["last_name"].initial = self.instance.user.last_name
        self.fields["email"].initial = self.instance.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save(update_fields=("first_name", "last_name", "email"))
            profile.save()
        return profile


class AssessmentAccessForm(forms.ModelForm):
    class Meta:
        model = AssessmentAccess
        fields = ("membership", "access")

    def __init__(self, *args, organization, assessment, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["membership"].queryset = organization.memberships.filter(
            active=True
        ).exclude(assessment_access__assessment=assessment).select_related("user")


class BulkControlOwnerForm(forms.Form):
    domain = forms.ChoiceField()
    primary_owner = forms.ModelChoiceField(
        queryset=Membership.objects.none(), required=False
    )
    supporting_owners = forms.ModelMultipleChoiceField(
        queryset=Membership.objects.none(), required=False,
        widget=forms.CheckboxSelectMultiple(),
    )

    def __init__(self, *args, organization, assessment, **kwargs):
        super().__init__(*args, **kwargs)
        members = Membership.objects.filter(
            organization=organization, active=True
        ).select_related("user").order_by("user__first_name", "user__username")
        domains = assessment.control_results.values_list(
            "requirement__domain", flat=True
        ).distinct().order_by("requirement__domain")
        self.fields["domain"].choices = [(value, value) for value in domains]
        self.fields["primary_owner"].queryset = members
        self.fields["supporting_owners"].queryset = members


class EvidenceRequestForm(forms.ModelForm):
    catalog_object = forms.ChoiceField(
        required=False, label="Omni evidence object",
        help_text="Optional: select a curated, framework-agnostic evidence object.",
        choices=[("", "Custom request")] + [
            (item.evidence_id, f"{item.evidence_id} — {item.canonical_name}")
            for item in EVIDENCE_KNOWLEDGE
        ],
    )

    class Meta:
        model = EvidenceRequest
        fields = (
            "catalog_object", "title", "description", "status", "owner",
            "due_date", "notify_owner", "freshness_days", "renewal_lead_days",
            "auto_renew", "controls",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "controls": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, organization, assessment, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["title"].required = False
        self.fields["freshness_days"].required = False
        self.fields["renewal_lead_days"].required = False
        if self.instance.pk and self.instance.evidence_code:
            self.fields["catalog_object"].initial = self.instance.evidence_code
        self.fields["owner"].queryset = Membership.objects.filter(
            organization=organization, active=True
        ).select_related("user").order_by("user__first_name", "user__username")
        self.fields["controls"].queryset = assessment.control_results.select_related(
            "requirement"
        )

    def clean(self):
        cleaned = super().clean()
        cleaned["freshness_days"] = cleaned.get("freshness_days") or 0
        if cleaned.get("renewal_lead_days") is None:
            cleaned["renewal_lead_days"] = 30
        code = cleaned.get("catalog_object")
        if code:
            evidence = next(item for item in EVIDENCE_KNOWLEDGE if item.evidence_id == code)
            if not (cleaned.get("title") or "").strip():
                cleaned["title"] = evidence.canonical_name
            if not (cleaned.get("description") or "").strip():
                cleaned["description"] = evidence.description
        elif not (cleaned.get("title") or "").strip():
            self.add_error("title", "Enter a title for a custom evidence request.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        code = self.cleaned_data.get("catalog_object", "")
        if code:
            evidence = next(item for item in EVIDENCE_KNOWLEDGE if item.evidence_id == code)
            instance.evidence_code = code
            if not instance.title.strip():
                instance.title = evidence.canonical_name
            if not instance.description.strip():
                instance.description = evidence.description
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class EvidenceArtifactForm(forms.ModelForm):
    class Meta:
        model = EvidenceArtifact
        fields = (
            "title", "file", "external_reference", "source", "period_start",
            "period_end", "effective_on", "expires_on", "superseded_by",
            "review_status", "assessor_notes", "requests", "controls",
        )
        widgets = {
            "period_start": forms.DateInput(attrs={"type": "date"}),
            "period_end": forms.DateInput(attrs={"type": "date"}),
            "effective_on": forms.DateInput(attrs={"type": "date"}),
            "expires_on": forms.DateInput(attrs={"type": "date"}),
            "assessor_notes": forms.Textarea(attrs={"rows": 4}),
            "requests": forms.CheckboxSelectMultiple(),
            "controls": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, assessment, can_review=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["requests"].queryset = assessment.evidence_requests.all()
        self.fields["controls"].queryset = assessment.control_results.select_related(
            "requirement"
        )
        if not can_review:
            self.fields["review_status"].disabled = True
            self.fields["assessor_notes"].disabled = True
        self.fields["superseded_by"].queryset = assessment.evidence_artifacts.exclude(pk=self.instance.pk)

    def clean_file(self):
        uploaded = self.cleaned_data.get("file")
        if uploaded and uploaded.size > 25 * 1024 * 1024:
            raise forms.ValidationError("Evidence files cannot exceed 25 MB.")
        return uploaded

    def clean(self):
        cleaned = super().clean()
        existing_file = self.instance.file if self.instance.pk else None
        if not cleaned.get("file") and not existing_file and not cleaned.get("external_reference"):
            self.add_error("file", "Upload a file or provide an external reference.")
        start, end = cleaned.get("period_start"), cleaned.get("period_end")
        if start and end and end < start:
            self.add_error("period_end", "The period end cannot precede the start.")
        effective, expires = cleaned.get("effective_on"), cleaned.get("expires_on")
        if effective and expires and expires < effective:
            self.add_error("expires_on", "The expiration date cannot precede the effective date.")
        if (cleaned.get("review_status") == EvidenceArtifact.ReviewStatus.REJECTED
                and not (cleaned.get("assessor_notes") or "").strip()):
            self.add_error("assessor_notes", "Explain why the evidence was rejected.")
        return cleaned


class ControlMonitoringEventForm(forms.ModelForm):
    class Meta:
        model = ControlMonitoringEvent
        fields = (
            "title", "event_type", "severity", "occurred_on", "description",
            "source_reference", "controls",
        )
        widgets = {
            "occurred_on": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 4}),
            "controls": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, assessment, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["controls"].queryset = assessment.control_results.select_related(
            "requirement__framework"
        )


class AssessmentBaselineForm(forms.ModelForm):
    class Meta:
        model = AssessmentBaseline
        fields = ("name", "description")
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class ComplianceAutomationPolicyForm(forms.ModelForm):
    class Meta:
        model = ComplianceAutomationPolicy
        fields = ("enabled", "frequency", "next_run_on")
        widgets = {"next_run_on": forms.DateInput(attrs={"type": "date"})}

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("enabled") and not cleaned.get("next_run_on"):
            self.add_error("next_run_on", "Set the first automation run date.")
        return cleaned


class ControlMonitoringProfileForm(forms.ModelForm):
    class Meta:
        model = ControlMonitoringProfile
        fields = (
            "enabled", "review_frequency_days", "next_review_date", "owner",
            "monitoring_notes",
        )
        widgets = {
            "next_review_date": forms.DateInput(attrs={"type": "date"}),
            "monitoring_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, assessment, organization, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["owner"].queryset = organization.memberships.filter(
            active=True
        ).select_related("user")

    def clean(self):
        cleaned = super().clean()
        if (cleaned.get("review_frequency_days") or 0) < 1:
            self.add_error("review_frequency_days", "Review frequency must be at least one day.")
        if cleaned.get("enabled") and not cleaned.get("next_review_date"):
            self.add_error("next_review_date", "Set the first review date when monitoring is enabled.")
        return cleaned


class ControlReassessmentTaskForm(forms.ModelForm):
    class Meta:
        model = ControlReassessmentTask
        fields = ("status", "assigned_to", "due_date", "resolution")
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "resolution": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, organization, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = organization.memberships.filter(
            active=True
        ).select_related("user")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("status") in {
            ControlReassessmentTask.Status.COMPLETED,
            ControlReassessmentTask.Status.NO_ACTION,
        } and not (cleaned.get("resolution") or "").strip():
            self.add_error("resolution", "Document the reassessment outcome or no-action rationale.")
        return cleaned


class EvidenceApplicabilityForm(forms.ModelForm):
    class Meta:
        model = EvidenceApplicability
        fields = ("applicability", "rationale", "scope_limitations")
        widgets = {"rationale": forms.Textarea(attrs={"rows": 2}), "scope_limitations": forms.Textarea(attrs={"rows": 2})}


class RemediationPlanForm(forms.ModelForm):
    class Meta:
        model = RemediationPlan
        fields = (
            "title", "controls", "weakness_description", "root_cause",
            "corrective_action", "compensating_controls", "closure_criteria",
            "owner", "supporting_owners", "status", "priority", "severity",
            "likelihood", "residual_risk", "date_identified", "planned_completion",
            "actual_completion", "risk_acceptance_requested",
            "risk_acceptance_rationale", "risk_accepted_by",
            "risk_acceptance_expires", "closure_evidence", "validation_status",
            "validation_notes", "notify_owner",
        )
        widgets = {
            "controls": forms.CheckboxSelectMultiple(),
            "supporting_owners": forms.CheckboxSelectMultiple(),
            "closure_evidence": forms.CheckboxSelectMultiple(),
            "date_identified": forms.DateInput(attrs={"type": "date"}),
            "planned_completion": forms.DateInput(attrs={"type": "date"}),
            "actual_completion": forms.DateInput(attrs={"type": "date"}),
            "risk_acceptance_expires": forms.DateInput(attrs={"type": "date"}),
            "weakness_description": forms.Textarea(attrs={"rows": 4}),
            "root_cause": forms.Textarea(attrs={"rows": 3}),
            "corrective_action": forms.Textarea(attrs={"rows": 4}),
            "compensating_controls": forms.Textarea(attrs={"rows": 3}),
            "closure_criteria": forms.Textarea(attrs={"rows": 3}),
            "risk_acceptance_rationale": forms.Textarea(attrs={"rows": 3}),
            "validation_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, organization, assessment, can_validate=False,
                 can_accept_risk=False, **kwargs):
        super().__init__(*args, **kwargs)
        members = Membership.objects.filter(
            organization=organization, active=True
        ).select_related("user").order_by("user__first_name", "user__username")
        self.fields["owner"].queryset = members
        self.fields["supporting_owners"].queryset = members
        self.fields["risk_accepted_by"].queryset = members.filter(role=Membership.Role.ADMIN)
        self.fields["controls"].queryset = assessment.control_results.select_related(
            "requirement"
        )
        self.fields["closure_evidence"].queryset = assessment.evidence_artifacts.all()
        if not self.instance.pk:
            self.fields["date_identified"].initial = timezone.localdate()
        if not can_validate:
            self.fields["validation_status"].disabled = True
            self.fields["validation_notes"].disabled = True
        if not can_accept_risk:
            self.fields["risk_accepted_by"].disabled = True

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        if status in (RemediationPlan.Status.READY_VALIDATION, RemediationPlan.Status.CLOSED):
            for field in ("root_cause", "corrective_action", "closure_criteria"):
                if not (cleaned.get(field) or "").strip():
                    self.add_error(field, "Required before validation or closure.")
        if status == RemediationPlan.Status.CLOSED:
            if cleaned.get("validation_status") != RemediationPlan.ValidationStatus.VALIDATED:
                self.add_error("status", "Only a validated remediation plan may be closed.")
            if not cleaned.get("actual_completion"):
                self.add_error("actual_completion", "Required when the plan is closed.")
            if not cleaned.get("closure_evidence"):
                self.add_error("closure_evidence", "At least one closure artifact is required.")
        if cleaned.get("risk_acceptance_requested"):
            if not (cleaned.get("risk_acceptance_rationale") or "").strip():
                self.add_error("risk_acceptance_rationale", "Explain the risk acceptance request.")
            if not cleaned.get("risk_acceptance_expires"):
                self.add_error("risk_acceptance_expires", "An expiration date is required.")
        if status == RemediationPlan.Status.RISK_ACCEPTED and not cleaned.get("risk_accepted_by"):
            self.add_error("risk_accepted_by", "An organization administrator must accept the risk.")
        identified = cleaned.get("date_identified")
        planned = cleaned.get("planned_completion")
        actual = cleaned.get("actual_completion")
        if identified and planned and planned < identified:
            self.add_error("planned_completion", "Cannot precede the identification date.")
        if identified and actual and actual < identified:
            self.add_error("actual_completion", "Cannot precede the identification date.")
        return cleaned


class RiskRegisterForm(forms.ModelForm):
    SCALE = [(value, label) for value, label in (
        (1, "1 — Rare / Negligible"), (2, "2 — Unlikely / Minor"),
        (3, "3 — Possible / Moderate"), (4, "4 — Likely / Major"),
        (5, "5 — Almost certain / Severe"),
    )]

    class Meta:
        model = RiskRegisterEntry
        fields = (
            "catalog_risk", "title", "description", "category", "controls",
            "remediation_plans", "supporting_evidence", "owner", "status", "likelihood", "impact",
            "treatment", "treatment_plan", "target_date", "residual_likelihood",
            "residual_impact", "acceptance_rationale", "acceptance_expires",
            "next_review_date", "review_frequency_days", "trend", "monitoring_notes", "trigger_events",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "controls": forms.CheckboxSelectMultiple(),
            "remediation_plans": forms.CheckboxSelectMultiple(),
            "supporting_evidence": forms.CheckboxSelectMultiple(),
            "treatment_plan": forms.Textarea(attrs={"rows": 4}),
            "acceptance_rationale": forms.Textarea(attrs={"rows": 3}),
            "target_date": forms.DateInput(attrs={"type": "date"}),
            "acceptance_expires": forms.DateInput(attrs={"type": "date"}),
            "next_review_date": forms.DateInput(attrs={"type": "date"}),
            "monitoring_notes": forms.Textarea(attrs={"rows": 3}),
            "trigger_events": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, organization, assessment, can_accept=False, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("likelihood", "impact", "residual_likelihood", "residual_impact"):
            self.fields[name].widget = forms.Select(choices=[("", "—")] + self.SCALE)
        self.fields["likelihood"].widget.choices = self.SCALE
        self.fields["impact"].widget.choices = self.SCALE
        self.fields["owner"].queryset = organization.memberships.filter(active=True).select_related("user")
        self.fields["controls"].queryset = assessment.control_results.select_related("requirement")
        self.fields["remediation_plans"].queryset = assessment.remediation_plans.all()
        self.fields["supporting_evidence"].queryset = assessment.evidence_artifacts.all()
        self.fields["review_frequency_days"].required = False
        self.fields["trend"].required = False
        self.can_accept = can_accept

    def clean(self):
        cleaned = super().clean()
        cleaned["review_frequency_days"] = (
            cleaned.get("review_frequency_days") or self.instance.review_frequency_days or 90
        )
        cleaned["trend"] = cleaned.get("trend") or self.instance.trend or "UNKNOWN"
        residual_likelihood = cleaned.get("residual_likelihood")
        residual_impact = cleaned.get("residual_impact")
        if (residual_likelihood is None) != (residual_impact is None):
            self.add_error("residual_impact", "Enter both residual likelihood and impact, or leave both blank.")
        treatment = cleaned.get("treatment")
        if treatment != RiskRegisterEntry.Treatment.UNDECIDED and not (cleaned.get("treatment_plan") or "").strip():
            self.add_error("treatment_plan", "Describe how this treatment decision will be implemented.")
        if treatment == RiskRegisterEntry.Treatment.ACCEPT:
            if not self.can_accept:
                self.add_error("treatment", "Only an organization administrator may accept risk.")
            if not (cleaned.get("acceptance_rationale") or "").strip():
                self.add_error("acceptance_rationale", "Risk acceptance requires a rationale.")
            if not cleaned.get("acceptance_expires"):
                self.add_error("acceptance_expires", "Risk acceptance requires an expiration date.")
        return cleaned


class RiskTolerancePolicyForm(forms.ModelForm):
    class Meta:
        model = RiskTolerancePolicy
        fields = ("maximum_residual_score", "critical_acceptance_allowed",
                  "maximum_acceptance_days", "review_reminder_days",
                  "acceptance_expiry_reminder_days")

    def clean_maximum_residual_score(self):
        value = self.cleaned_data["maximum_residual_score"]
        if not 1 <= value <= 25:
            raise forms.ValidationError("Use a residual-risk threshold from 1 to 25.")
        return value


class RiskTreatmentActionForm(forms.ModelForm):
    class Meta:
        model = RiskTreatmentAction
        fields = ("title", "description", "owner", "status", "priority", "planned_start",
                  "due_date", "completed_date", "completion_notes", "remediation_plan",
                  "evidence", "dependencies")
        widgets = {"description": forms.Textarea(attrs={"rows": 3}),
                   "completion_notes": forms.Textarea(attrs={"rows": 3}),
                   "planned_start": forms.DateInput(attrs={"type": "date"}),
                   "due_date": forms.DateInput(attrs={"type": "date"}),
                   "completed_date": forms.DateInput(attrs={"type": "date"}),
                   "evidence": forms.CheckboxSelectMultiple(),
                   "dependencies": forms.CheckboxSelectMultiple()}

    def __init__(self, *args, organization, assessment, risk, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["owner"].queryset = organization.memberships.filter(active=True).select_related("user")
        self.fields["remediation_plan"].queryset = assessment.remediation_plans.all()
        self.fields["evidence"].queryset = assessment.evidence_artifacts.all()
        self.fields["dependencies"].queryset = risk.treatment_actions.exclude(pk=self.instance.pk)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("status") == RiskTreatmentAction.Status.COMPLETE:
            if not cleaned.get("completed_date"):
                self.add_error("completed_date", "Required when the action is complete.")
            if not (cleaned.get("completion_notes") or "").strip():
                self.add_error("completion_notes", "Document the completed treatment work.")
        if cleaned.get("planned_start") and cleaned.get("due_date") and cleaned["due_date"] < cleaned["planned_start"]:
            self.add_error("due_date", "Cannot precede the planned start.")
        return cleaned


class RiskReassessmentForm(forms.ModelForm):
    class Meta:
        model = RiskReassessment
        fields = ("new_likelihood", "new_impact", "rationale", "evidence")
        widgets = {"rationale": forms.Textarea(attrs={"rows": 4}),
                   "evidence": forms.CheckboxSelectMultiple()}

    def __init__(self, *args, assessment, **kwargs):
        super().__init__(*args, **kwargs)
        choices = [(i, str(i)) for i in range(1, 6)]
        self.fields["new_likelihood"].widget = forms.Select(choices=choices)
        self.fields["new_impact"].widget = forms.Select(choices=choices)
        self.fields["evidence"].queryset = assessment.evidence_artifacts.all()


class RiskAcceptanceRequestForm(forms.ModelForm):
    class Meta:
        model = RiskAcceptanceRequest
        fields = ("rationale", "requested_expiration")
        widgets = {"rationale": forms.Textarea(attrs={"rows": 4}),
                   "requested_expiration": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, policy, **kwargs):
        super().__init__(*args, **kwargs)
        self.policy = policy

    def clean_requested_expiration(self):
        value = self.cleaned_data["requested_expiration"]
        if value <= timezone.localdate():
            raise forms.ValidationError("Acceptance must expire in the future.")
        if value > timezone.localdate() + timedelta(days=self.policy.maximum_acceptance_days):
            raise forms.ValidationError("The requested period exceeds the organization's maximum.")
        return value


class RiskClosureForm(forms.Form):
    closure_rationale = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), min_length=10)


class RemediationMilestoneForm(forms.ModelForm):
    class Meta:
        model = RemediationMilestone
        fields = ("title", "description", "owner", "due_date", "completed_date", "status", "sequence", "notify_owner")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "completed_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, organization, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["owner"].queryset = Membership.objects.filter(
            organization=organization, active=True
        ).select_related("user")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("status") == RemediationMilestone.Status.COMPLETE and not cleaned.get("completed_date"):
            self.add_error("completed_date", "Required for a completed milestone.")
        return cleaned


class AssessmentForm(forms.ModelForm):
    frameworks = forms.ModelMultipleChoiceField(
        queryset=Framework.objects.none(), widget=forms.CheckboxSelectMultiple(),
        help_text="Select every framework included in this assessment.",
    )
    primary_framework = forms.ModelChoiceField(
        queryset=Framework.objects.none(),
        help_text="The primary framework controls the default view and primary scoring context.",
    )

    class Meta:
        model = Assessment
        fields = ("name",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        frameworks = Framework.objects.filter(active=True).order_by("name", "version")
        self.fields["frameworks"].queryset = frameworks
        self.fields["primary_framework"].queryset = frameworks
        if self.instance.pk:
            selected = self.instance.frameworks.all()
            self.fields["frameworks"].initial = selected
            self.fields["primary_framework"].initial = self.instance.framework

    def clean(self):
        cleaned = super().clean()
        frameworks = cleaned.get("frameworks")
        primary = cleaned.get("primary_framework")
        if frameworks is not None and primary is not None and primary not in frameworks:
            self.add_error("primary_framework", "The primary framework must also be selected.")
        return cleaned


class Soc2AssessmentProfileForm(forms.Form):
    examination_type = forms.ChoiceField(
        choices=Soc2AssessmentProfile.ExaminationType.choices, required=False,
        initial=Soc2AssessmentProfile.ExaminationType.TYPE_II,
        label="SOC 2 examination type",
    )
    optional_categories = forms.MultipleChoiceField(
        choices=(
            (Soc2AssessmentProfile.Category.AVAILABILITY, "Availability"),
            (Soc2AssessmentProfile.Category.PROCESSING_INTEGRITY, "Processing Integrity"),
            (Soc2AssessmentProfile.Category.CONFIDENTIALITY, "Confidentiality"),
            (Soc2AssessmentProfile.Category.PRIVACY, "Privacy"),
        ), required=False, widget=forms.CheckboxSelectMultiple,
        help_text="Security is always included. Select any additional categories in scope.",
    )
    as_of_date = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"}),
        help_text="Required only for Type I.",
    )
    period_start = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"}),
        help_text="Required only for Type II.",
    )
    period_end = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"}),
        help_text="Required only for Type II.",
    )
    service_commitments = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Describe the service commitments and system requirements presented to users.",
    )
    system_boundaries = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Describe the services, infrastructure, software, people, procedures, and data in scope.",
    )
    scope_notes = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Document category-scoping rationale and other examination-specific limitations.",
    )

    def __init__(self, *args, profile=None, required_profile=False, **kwargs):
        self.profile = profile
        self.required_profile = required_profile
        if profile and not args and "initial" not in kwargs:
            kwargs["initial"] = {
                "examination_type": profile.examination_type,
                "optional_categories": [item for item in profile.included_categories
                                        if item != Soc2AssessmentProfile.Category.SECURITY],
                "as_of_date": profile.as_of_date,
                "period_start": profile.period_start,
                "period_end": profile.period_end,
                "service_commitments": profile.service_commitments,
                "system_boundaries": profile.system_boundaries,
                "scope_notes": profile.scope_notes,
            }
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        if not self.required_profile:
            return cleaned
        examination_type = cleaned.get("examination_type")
        if not examination_type:
            self.add_error("examination_type", "Choose Type I or Type II.")
        if examination_type == Soc2AssessmentProfile.ExaminationType.TYPE_I:
            if not cleaned.get("as_of_date"):
                self.add_error("as_of_date", "Type I requires an as-of date.")
            if cleaned.get("period_start") or cleaned.get("period_end"):
                self.add_error("period_start", "Type I does not use an examination period.")
        if examination_type == Soc2AssessmentProfile.ExaminationType.TYPE_II:
            start, end = cleaned.get("period_start"), cleaned.get("period_end")
            if not start:
                self.add_error("period_start", "Type II requires a period start.")
            if not end:
                self.add_error("period_end", "Type II requires a period end.")
            if start and end and end < start:
                self.add_error("period_end", "The Type II period end cannot precede its start.")
            if cleaned.get("as_of_date"):
                self.add_error("as_of_date", "Type II uses a period, not an as-of date.")
        return cleaned

    def save(self, assessment, user):
        examination_type = self.cleaned_data["examination_type"]
        categories = [Soc2AssessmentProfile.Category.SECURITY]
        categories.extend(self.cleaned_data.get("optional_categories") or [])
        profile = self.profile or Soc2AssessmentProfile(assessment=assessment)
        profile.examination_type = examination_type
        profile.included_categories = categories
        profile.as_of_date = (self.cleaned_data.get("as_of_date")
                              if examination_type == Soc2AssessmentProfile.ExaminationType.TYPE_I else None)
        profile.period_start = (self.cleaned_data.get("period_start")
                                if examination_type == Soc2AssessmentProfile.ExaminationType.TYPE_II else None)
        profile.period_end = (self.cleaned_data.get("period_end")
                              if examination_type == Soc2AssessmentProfile.ExaminationType.TYPE_II else None)
        profile.service_commitments = self.cleaned_data.get("service_commitments", "")
        profile.system_boundaries = self.cleaned_data.get("system_boundaries", "")
        profile.scope_notes = self.cleaned_data.get("scope_notes", "")
        profile.updated_by = user
        profile.save()
        synchronize_soc2_scope(profile)
        return profile


class AssessmentTemplateForm(forms.ModelForm):
    class Meta:
        model = AssessmentTemplate
        fields = (
            "name", "description", "primary_framework", "frameworks",
            "scope_boundaries", "assessment_locations", "sampling_methodology",
            "notifications_enabled", "email_notifications_enabled",
            "risk_management_enabled", "include_risk_in_reports", "recurrence",
            "next_start_date", "default_duration_days", "active",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "scope_boundaries": forms.Textarea(attrs={"rows": 4}),
            "assessment_locations": forms.Textarea(attrs={"rows": 3}),
            "sampling_methodology": forms.Textarea(attrs={"rows": 4}),
            "frameworks": forms.CheckboxSelectMultiple(),
            "next_start_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        frameworks = Framework.objects.filter(active=True).order_by("name", "version")
        self.fields["primary_framework"].queryset = frameworks
        self.fields["frameworks"].queryset = frameworks

    def clean(self):
        cleaned = super().clean()
        frameworks, primary = cleaned.get("frameworks"), cleaned.get("primary_framework")
        if frameworks is not None and primary is not None and primary not in frameworks:
            self.add_error("primary_framework", "The primary framework must also be selected.")
        if cleaned.get("include_risk_in_reports") and not cleaned.get("risk_management_enabled"):
            self.add_error("include_risk_in_reports", "Enable risk management before including it in reports.")
        if cleaned.get("recurrence") != AssessmentTemplate.Recurrence.NONE and not cleaned.get("next_start_date"):
            self.add_error("next_start_date", "Set the first start date for a recurring template.")
        return cleaned


class TemplateAssessmentForm(forms.Form):
    name = forms.CharField(max_length=200)
    engagement_start = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    engagement_end = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    prior_assessment = forms.ModelChoiceField(
        queryset=Assessment.objects.none(), required=False,
        help_text="Optional lineage only. Prior conclusions and evidence are not copied.",
    )

    def __init__(self, *args, system, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["prior_assessment"].queryset = system.assessments.order_by("-created_at")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("engagement_end") and cleaned.get("engagement_start") and cleaned["engagement_end"] < cleaned["engagement_start"]:
            self.add_error("engagement_end", "Cannot precede the engagement start.")
        return cleaned


class IntegrationPolicyForm(forms.ModelForm):
    class Meta:
        model = IntegrationPolicy
        fields = (
            "delivery", "provider", "external_ticketing_enabled", "create_for_evidence",
            "create_for_findings", "create_for_remediation", "create_for_risk_treatment",
            "create_for_monitoring",
        )

    def clean(self):
        cleaned = super().clean()
        external = cleaned.get("external_ticketing_enabled")
        delivery = cleaned.get("delivery")
        provider = cleaned.get("provider")
        if external and provider == IntegrationPolicy.Provider.NONE:
            self.add_error("provider", "Choose the future ticketing provider.")
        if delivery in (IntegrationPolicy.Delivery.EXTERNAL, IntegrationPolicy.Delivery.BOTH) and not external:
            self.add_error("external_ticketing_enabled", "Enable external ticketing for this delivery method.")
        return cleaned


class AssessmentPlanForm(forms.ModelForm):
    class Meta:
        model = Assessment
        fields = (
            "engagement_start", "engagement_end", "scope_boundaries",
            "assessment_locations", "sampling_methodology",
            "notifications_enabled", "email_notifications_enabled",
            "risk_management_enabled", "include_risk_in_reports",
        )
        widgets = {
            "engagement_start": forms.DateInput(attrs={"type": "date"}),
            "engagement_end": forms.DateInput(attrs={"type": "date"}),
            "scope_boundaries": forms.Textarea(attrs={"rows": 4}),
            "assessment_locations": forms.Textarea(attrs={"rows": 3}),
            "sampling_methodology": forms.Textarea(attrs={"rows": 4}),
        }

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("engagement_start"), cleaned.get("engagement_end")
        if start and end and end < start:
            self.add_error("engagement_end", "Cannot precede the engagement start.")
        if cleaned.get("include_risk_in_reports") and not cleaned.get("risk_management_enabled"):
            self.add_error("include_risk_in_reports", "Enable risk management before including it in reports.")
        return cleaned


class AssessmentTeamForm(forms.ModelForm):
    class Meta:
        model = AssessmentTeamMember
        fields = ("membership", "role")

    def __init__(self, *args, organization, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["membership"].queryset = organization.memberships.filter(
            active=True
        ).select_related("user")


class ObjectiveAssessmentForm(forms.ModelForm):
    class Meta:
        model = ObjectiveAssessment
        fields = (
            "status", "design_conclusion", "implementation_conclusion",
            "operating_effectiveness_conclusion", "assessor_notes", "evidence",
        )
        widgets = {
            "assessor_notes": forms.Textarea(attrs={"rows": 5}),
            "evidence": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, assessment, **kwargs):
        super().__init__(*args, **kwargs)
        self.assessment = assessment
        self.fields["evidence"].queryset = assessment.evidence_artifacts.all()
        self.is_soc2 = self.instance.control_result.requirement.framework.code == "AICPA-TSC-2017-RPOF-2022"
        self.soc2_type = getattr(getattr(assessment, "soc2_profile", None), "examination_type", None)
        # These conclusions extend SOC 2 execution. Keep the established,
        # framework-neutral objective form backward compatible for every other
        # framework; SOC 2 completeness is enforced explicitly in clean().
        for field_name in (
            "design_conclusion", "implementation_conclusion",
            "operating_effectiveness_conclusion",
        ):
            self.fields[field_name].required = False
        if self.is_soc2 and self.soc2_type == Soc2AssessmentProfile.ExaminationType.TYPE_I:
            self.fields["operating_effectiveness_conclusion"].disabled = True
            self.fields["operating_effectiveness_conclusion"].initial = (
                ObjectiveAssessment.OperatingConclusion.NOT_APPLICABLE
            )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("status") != ObjectiveAssessment.Status.NOT_ASSESSED and not (
            cleaned.get("assessor_notes") or ""
        ).strip():
            self.add_error("assessor_notes", "Document the objective-level conclusion.")
        if self.is_soc2 and cleaned.get("status") != ObjectiveAssessment.Status.NOT_ASSESSED:
            if cleaned.get("design_conclusion") == ObjectiveAssessment.Conclusion.NOT_ASSESSED:
                self.add_error("design_conclusion", "Record the design conclusion.")
            if cleaned.get("implementation_conclusion") == ObjectiveAssessment.Conclusion.NOT_ASSESSED:
                self.add_error("implementation_conclusion", "Record the implementation conclusion.")
            if (self.soc2_type == Soc2AssessmentProfile.ExaminationType.TYPE_II
                    and cleaned.get("operating_effectiveness_conclusion") == ObjectiveAssessment.OperatingConclusion.NOT_TESTED):
                self.add_error(
                    "operating_effectiveness_conclusion",
                    "Type II requires an operating-effectiveness conclusion.",
                )
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.is_soc2 and self.soc2_type == Soc2AssessmentProfile.ExaminationType.TYPE_I:
            instance.operating_effectiveness_conclusion = (
                ObjectiveAssessment.OperatingConclusion.NOT_APPLICABLE
            )
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class AssessmentProcedureCustomizationForm(forms.ModelForm):
    class Meta:
        model = AssessmentProcedureCustomization
        fields = ("base_procedure", "method", "procedure_text", "enabled")
        widgets = {"procedure_text": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, objective_result, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["base_procedure"].queryset = AssessmentProcedure.objects.filter(
            requirement=objective_result.control_result.requirement
        ).order_by("method", "sequence")


class InterviewSessionForm(forms.ModelForm):
    class Meta:
        model = InterviewSession
        fields = (
            "title", "scheduled_at", "location_or_link", "participants",
            "interviewer", "objectives", "notes", "completed",
        )
        widgets = {
            "scheduled_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "participants": forms.Textarea(attrs={"rows": 3}),
            "objectives": forms.CheckboxSelectMultiple(),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, organization, assessment, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["interviewer"].queryset = organization.memberships.filter(active=True)
        self.fields["objectives"].queryset = ObjectiveAssessment.objects.filter(
            control_result__assessment=assessment
        ).select_related("objective", "control_result__requirement")


class AssessmentSampleForm(forms.ModelForm):
    class Meta:
        model = AssessmentSample
        fields = (
            "name", "population_description", "population_size", "sample_size",
            "period_start", "period_end",
            "selection_method", "rationale", "selected_items", "objectives",
        )
        widgets = {
            "population_description": forms.Textarea(attrs={"rows": 3}),
            "selection_method": forms.Textarea(attrs={"rows": 3}),
            "rationale": forms.Textarea(attrs={"rows": 3}),
            "selected_items": forms.Textarea(attrs={"rows": 4}),
            "period_start": forms.DateInput(attrs={"type": "date"}),
            "period_end": forms.DateInput(attrs={"type": "date"}),
            "objectives": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, assessment, **kwargs):
        super().__init__(*args, **kwargs)
        self.assessment = assessment
        self.fields["objectives"].queryset = ObjectiveAssessment.objects.filter(
            control_result__assessment=assessment
        ).select_related("objective")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("sample_size", 0) > cleaned.get("population_size", 0):
            self.add_error("sample_size", "Cannot exceed the population size.")
        start, end = cleaned.get("period_start"), cleaned.get("period_end")
        if start and end and end < start:
            self.add_error("period_end", "Cannot precede the sample period start.")
        profile = getattr(self.assessment, "soc2_profile", None)
        if profile and profile.examination_type == Soc2AssessmentProfile.ExaminationType.TYPE_II:
            if not start:
                self.add_error("period_start", "Type II samples require a population period start.")
            if not end:
                self.add_error("period_end", "Type II samples require a population period end.")
            if start and profile.period_start and start < profile.period_start:
                self.add_error("period_start", "Cannot precede the Type II examination period.")
            if end and profile.period_end and end > profile.period_end:
                self.add_error("period_end", "Cannot extend beyond the Type II examination period.")
        return cleaned


class TestExecutionForm(forms.ModelForm):
    class Meta:
        model = TestExecution
        fields = (
            "objective_result", "procedure", "performed_by", "performed_at",
            "steps_performed", "expected_result", "actual_result", "outcome", "evidence",
        )
        widgets = {
            "performed_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "steps_performed": forms.Textarea(attrs={"rows": 4}),
            "expected_result": forms.Textarea(attrs={"rows": 3}),
            "actual_result": forms.Textarea(attrs={"rows": 4}),
            "evidence": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, organization, assessment, **kwargs):
        super().__init__(*args, **kwargs)
        objectives = ObjectiveAssessment.objects.filter(
            control_result__assessment=assessment
        ).select_related("objective", "control_result__requirement")
        self.fields["objective_result"].queryset = objectives
        self.fields["procedure"].queryset = AssessmentProcedure.objects.filter(
            requirement__assessment_results__assessment=assessment,
            method__in=(AssessmentProcedure.Method.TEST, AssessmentProcedure.Method.REPERFORM),
        ).distinct()
        self.fields["performed_by"].queryset = organization.memberships.filter(active=True)
        self.fields["evidence"].queryset = assessment.evidence_artifacts.all()


class QualityReviewForm(forms.ModelForm):
    class Meta:
        model = Assessment
        fields = ("quality_review_status", "quality_review_notes")
        widgets = {"quality_review_notes": forms.Textarea(attrs={"rows": 5})}


class ReopenAssessmentForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 5}), min_length=10)


class NotificationPreferenceForm(forms.ModelForm):
    class Meta:
        model = NotificationPreference
        fields = (
            "delivery", "assignments", "evidence", "remediation",
            "quality_review", "due_dates",
        )


class NotificationPolicyForm(forms.ModelForm):
    class Meta:
        model = NotificationPolicy
        fields = (
            "notifications_enabled", "email_enabled", "first_reminder_days",
            "second_reminder_days", "notify_on_due_date", "overdue_escalation_days",
            "repeat_overdue_days", "escalation_recipients",
        )

    def clean(self):
        cleaned = super().clean()
        first, second = cleaned.get("first_reminder_days"), cleaned.get("second_reminder_days")
        if first is not None and second is not None and second > first:
            self.add_error("second_reminder_days", "Must be on or after the first reminder window.")
        if cleaned.get("repeat_overdue_days") == 0:
            self.add_error("repeat_overdue_days", "Use at least one day between overdue reminders.")
        return cleaned


class ControlAssessmentForm(forms.ModelForm):
    in_scope = forms.TypedChoiceField(
        choices=((True, "In scope"), (False, "Outside scope")),
        coerce=lambda value: str(value).casefold() == "true",
        widget=forms.Select,
    )

    class Meta:
        model = ControlAssessment
        fields = (
            "status",
            "implementation_state",
            "in_scope",
            "scope_rationale",
            "assessor_notes_findings",
            "primary_owner",
            "supporting_owners",
            "ssp_reference",
        )
        widgets = {
            "assessor_notes_findings": forms.Textarea(attrs={"rows": 6}),
            "scope_rationale": forms.Textarea(attrs={"rows": 3}),
            "supporting_owners": forms.CheckboxSelectMultiple(),
            "ssp_reference": forms.TextInput(
                attrs={"placeholder": "SSP section/reference"}
            ),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        field_name = self.add_prefix("in_scope")
        if self.is_bound and field_name not in self.data:
            data = self.data.copy()
            data[field_name] = str(self.instance.in_scope if self.instance.pk else True)
            self.data = data
        owners = Membership.objects.none()
        if organization is not None:
            owners = Membership.objects.filter(
                organization=organization, active=True
            ).select_related("user").order_by("user__first_name", "user__username")
        self.fields["primary_owner"].queryset = owners
        self.fields["supporting_owners"].queryset = owners

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        notes = (cleaned.get("assessor_notes_findings") or "").strip()
        if not cleaned.get("in_scope") and not (cleaned.get("scope_rationale") or "").strip():
            self.add_error("scope_rationale", "Explain why this criterion is outside scope.")
        if status != ControlAssessment.Status.NOT_ASSESSED and not notes:
            self.add_error(
                "assessor_notes_findings",
                "A conformity statement, finding, or N/A justification is required.",
            )
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.in_scope:
            instance.status = ControlAssessment.Status.NOT_APPLICABLE
            instance.implementation_state = ControlAssessment.Implementation.NA
        if commit:
            instance.save()
            self.save_m2m()
        return instance
