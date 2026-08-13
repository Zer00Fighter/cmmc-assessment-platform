from django import forms
from django.contrib.auth import get_user_model
from django.utils.text import slugify

from .models import Assessment, ControlAssessment, Membership, Organization, System


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
