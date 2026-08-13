from django import forms
from django.contrib.auth import get_user_model
from django.utils.text import slugify

from src.evidence.evidence_knowledge import EVIDENCE_KNOWLEDGE

from .models import (
    Assessment, ControlAssessment, EvidenceArtifact, EvidenceRequest,
    Membership, Organization, System,
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
            "due_date", "controls",
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
        return cleaned


class AssessmentForm(forms.ModelForm):
    class Meta:
        model = Assessment
        fields = ("framework", "name")


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
