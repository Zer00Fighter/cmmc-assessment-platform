import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("webapp", "0029_complianceautomationpolicy_complianceautomationrun"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ImplementationActivity",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_identifier", models.CharField(max_length=50)),
                ("source_area", models.CharField(max_length=150)),
                ("category", models.CharField(blank=True, max_length=150)),
                ("activity", models.TextField()),
                ("control_type", models.CharField(blank=True, max_length=30)),
                ("source_filename", models.CharField(max_length=255)),
                ("source_sha256", models.CharField(max_length=64)),
                ("source_sheet", models.CharField(max_length=100)),
                ("source_row", models.PositiveIntegerField()),
                ("source_metadata", models.JSONField(blank=True, default=dict)),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ("source_area", "source_identifier")},
        ),
        migrations.CreateModel(
            name="ImplementationActivityMapping",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("target_framework_code", models.CharField(max_length=50)),
                ("target_requirement_id_text", models.CharField(max_length=50)),
                ("relationship", models.CharField(choices=[("EQUIVALENT", "Equivalent"), ("PARTIAL", "Partially equivalent"), ("RELATED", "Related"), ("SUPPORTS", "Supports")], default="SUPPORTS", max_length=15)),
                ("review_status", models.CharField(choices=[("PROPOSED", "Proposed"), ("APPROVED", "Approved"), ("REJECTED", "Rejected")], default="PROPOSED", max_length=10)),
                ("confidence", models.DecimalField(blank=True, decimal_places=3, max_digits=4, null=True)),
                ("rationale", models.TextField(blank=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("activity", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="criterion_mappings", to="webapp.implementationactivity")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="reviewed_implementation_activity_mappings", to=settings.AUTH_USER_MODEL)),
                ("target_requirement", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="implementation_activity_mappings", to="webapp.requirement")),
            ],
            options={"ordering": ("activity__source_identifier", "target_requirement_id_text")},
        ),
        migrations.AddConstraint(model_name="implementationactivity", constraint=models.UniqueConstraint(fields=("source_sha256", "source_sheet", "source_row"), name="unique_implementation_activity_source_row")),
        migrations.AddConstraint(model_name="implementationactivitymapping", constraint=models.UniqueConstraint(fields=("activity", "target_framework_code", "target_requirement_id_text"), name="unique_implementation_activity_target")),
    ]
