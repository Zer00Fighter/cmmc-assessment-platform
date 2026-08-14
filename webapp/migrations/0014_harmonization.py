from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("webapp", "0013_framework_ingestion"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AddField(
            model_name="framework", name="is_omni_control_framework",
            field=models.BooleanField(default=False, help_text="Designates Omni's native mapping hub. Only one catalog version may be designated."),
        ),
        migrations.AddConstraint(
            model_name="framework",
            constraint=models.UniqueConstraint(condition=models.Q(is_omni_control_framework=True), fields=("is_omni_control_framework",), name="one_omni_control_framework_hub"),
        ),
        migrations.CreateModel(
            name="AssessmentReuseDecision",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("basis", models.CharField(choices=[("DIRECT", "Direct mapping"), ("OMNI_DERIVED", "Derived through Omni Control Framework")], max_length=20)),
                ("relationship", models.CharField(choices=[("EQUIVALENT", "Equivalent"), ("PARTIAL", "Partially equivalent"), ("RELATED", "Related"), ("SUPPORTS", "Supports")], max_length=15)),
                ("mapping_path", models.JSONField(default=list)),
                ("reuse_evidence", models.BooleanField(default=True)),
                ("reuse_testing", models.BooleanField(default=True)),
                ("status", models.CharField(choices=[("SUGGESTED", "Suggested"), ("APPROVED", "Approved"), ("REJECTED", "Rejected")], default="SUGGESTED", max_length=12)),
                ("rationale", models.TextField(blank=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("assessment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reuse_decisions", to="webapp.assessment")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="reviewed_assessment_reuse", to=settings.AUTH_USER_MODEL)),
                ("source_result", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reuse_sources", to="webapp.controlassessment")),
                ("target_result", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reuse_targets", to="webapp.controlassessment")),
            ],
            options={"ordering": ("status", "source_result__requirement__framework__code")},
        ),
        migrations.AddConstraint(
            model_name="assessmentreusedecision",
            constraint=models.UniqueConstraint(fields=("assessment", "source_result", "target_result"), name="unique_assessment_reuse_direction"),
        ),
        migrations.AddConstraint(
            model_name="assessmentreusedecision",
            constraint=models.CheckConstraint(condition=~models.Q(source_result=models.F("target_result")), name="assessment_reuse_not_self"),
        ),
    ]
