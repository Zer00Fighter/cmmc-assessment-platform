from django import forms

from .models import Assessment, ControlAssessment


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
            "control_owner",
            "ssp_reference",
        )
        widgets = {
            "assessor_notes_findings": forms.Textarea(attrs={"rows": 6}),
            "control_owner": forms.TextInput(
                attrs={"placeholder": "Accountable owner"}
            ),
            "ssp_reference": forms.TextInput(
                attrs={"placeholder": "SSP section/reference"}
            ),
        }

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
