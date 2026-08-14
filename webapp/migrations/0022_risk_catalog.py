from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("webapp", "0021_requirement_risk_weight"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="RiskCatalogEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("risk_id", models.CharField(max_length=30, unique=True)),
                ("grouping", models.CharField(max_length=100)),
                ("title", models.CharField(max_length=300)),
                ("description", models.TextField()),
                ("active", models.BooleanField(default=True)),
                ("source_row", models.PositiveIntegerField()),
                ("source_filename", models.CharField(max_length=255)),
                ("source_sha256", models.CharField(max_length=64)),
            ],
            options={"ordering": ("grouping", "risk_id")},
        ),
        migrations.CreateModel(
            name="RequirementRiskMapping",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("review_status", models.CharField(choices=[("PROPOSED", "Proposed"), ("APPROVED", "Approved"), ("REJECTED", "Rejected")], default="PROPOSED", max_length=10)),
                ("rationale", models.TextField()),
                ("source", models.CharField(default="MANUAL", max_length=30)),
                ("confidence", models.DecimalField(blank=True, decimal_places=3, max_digits=4, null=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("proposed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="proposed_control_risks", to=settings.AUTH_USER_MODEL)),
                ("requirement", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="risk_mappings", to="webapp.requirement")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="reviewed_control_risks", to=settings.AUTH_USER_MODEL)),
                ("risk", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="control_mappings", to="webapp.riskcatalogentry")),
            ],
            options={"ordering": ("review_status", "requirement__framework__code", "requirement__requirement_id", "risk__risk_id")},
        ),
        migrations.AddConstraint(model_name="requirementriskmapping", constraint=models.UniqueConstraint(fields=("requirement", "risk"), name="unique_requirement_risk_mapping")),
    ]
