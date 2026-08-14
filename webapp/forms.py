from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.text import slugify

from src.evidence.evidence_knowledge import EVIDENCE_KNOWLEDGE

from .models import (
    Assessment, AssessmentFramework, AssessmentProcedure, AssessmentSample, AssessmentTeamMember,
    ControlAssessment, EvidenceArtifact, EvidenceRequest, Framework,
    InterviewSession, Membership, ObjectiveAssessment, Organization,
    NotificationPreference,
    NotificationPolicy,
    RemediationMilestone, RemediationPlan, System, TestExecution,
)


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
            "due_date", "notify_owner", "controls",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "controls": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, organization, assessment, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["title"].required = False
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
            "period_end", "review_status", "assessor_notes", "requests", "controls",
        )
        widgets = {
            "period_start": forms.DateInput(attrs={"type": "date"}),
            "period_end": forms.DateInput(attrs={"type": "date"}),
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
        if (cleaned.get("review_status") == EvidenceArtifact.ReviewStatus.REJECTED
                and not (cleaned.get("assessor_notes") or "").strip()):
            self.add_error("assessor_notes", "Explain why the evidence was rejected.")
        return cleaned


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


class AssessmentPlanForm(forms.ModelForm):
    class Meta:
        model = Assessment
        fields = (
            "engagement_start", "engagement_end", "scope_boundaries",
            "assessment_locations", "sampling_methodology",
            "notifications_enabled", "email_notifications_enabled",
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
        fields = ("status", "assessor_notes", "evidence")
        widgets = {
            "assessor_notes": forms.Textarea(attrs={"rows": 5}),
            "evidence": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, assessment, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["evidence"].queryset = assessment.evidence_artifacts.all()

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("status") != ObjectiveAssessment.Status.NOT_ASSESSED and not (
            cleaned.get("assessor_notes") or ""
        ).strip():
            self.add_error("assessor_notes", "Document the objective-level conclusion.")
        return cleaned


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
            "selection_method", "rationale", "selected_items", "objectives",
        )
        widgets = {
            "population_description": forms.Textarea(attrs={"rows": 3}),
            "selection_method": forms.Textarea(attrs={"rows": 3}),
            "rationale": forms.Textarea(attrs={"rows": 3}),
            "selected_items": forms.Textarea(attrs={"rows": 4}),
            "objectives": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, assessment, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["objectives"].queryset = ObjectiveAssessment.objects.filter(
            control_result__assessment=assessment
        ).select_related("objective")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("sample_size", 0) > cleaned.get("population_size", 0):
            self.add_error("sample_size", "Cannot exceed the population size.")
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
            method=AssessmentProcedure.Method.TEST,
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
    class Meta:
        model = ControlAssessment
        fields = (
            "status",
            "implementation_state",
            "assessor_notes_findings",
            "primary_owner",
            "supporting_owners",
            "ssp_reference",
        )
        widgets = {
            "assessor_notes_findings": forms.Textarea(attrs={"rows": 6}),
            "supporting_owners": forms.CheckboxSelectMultiple(),
            "ssp_reference": forms.TextInput(
                attrs={"placeholder": "SSP section/reference"}
            ),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
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
        if status != ControlAssessment.Status.NOT_ASSESSED and not notes:
            self.add_error(
                "assessor_notes_findings",
                "A conformity statement, finding, or N/A justification is required.",
            )
        return cleaned
