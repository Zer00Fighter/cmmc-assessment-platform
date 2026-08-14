from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("webapp", "0022_risk_catalog"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="RiskRegisterEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("risk_id", models.CharField(max_length=30)), ("title", models.CharField(max_length=300)),
                ("description", models.TextField()), ("category", models.CharField(max_length=100)),
                ("source", models.CharField(default="MANUAL", max_length=30)),
                ("status", models.CharField(choices=[("IDENTIFIED","Identified"),("ANALYZING","Analyzing"),("TREATING","Treatment in progress"),("MONITORING","Monitoring"),("ACCEPTED","Accepted"),("CLOSED","Closed")], default="IDENTIFIED", max_length=15)),
                ("likelihood", models.PositiveSmallIntegerField(default=3)), ("impact", models.PositiveSmallIntegerField(default=3)),
                ("inherent_score", models.PositiveSmallIntegerField(default=9)),
                ("treatment", models.CharField(choices=[("UNDECIDED","Undecided"),("MITIGATE","Mitigate"),("ACCEPT","Accept"),("AVOID","Avoid"),("TRANSFER","Transfer")], default="UNDECIDED", max_length=12)),
                ("treatment_plan", models.TextField(blank=True)), ("target_date", models.DateField(blank=True, null=True)),
                ("residual_likelihood", models.PositiveSmallIntegerField(blank=True, null=True)), ("residual_impact", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("residual_score", models.PositiveSmallIntegerField(blank=True, null=True)), ("acceptance_rationale", models.TextField(blank=True)),
                ("accepted_at", models.DateTimeField(blank=True, null=True)), ("acceptance_expires", models.DateField(blank=True, null=True)),
                ("next_review_date", models.DateField(blank=True, null=True)), ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("accepted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="accepted_risks", to=settings.AUTH_USER_MODEL)),
                ("assessment", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="risks", to="webapp.assessment")),
                ("catalog_risk", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="register_entries", to="webapp.riskcatalogentry")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_risks", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="risk_register", to="webapp.organization")),
                ("owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="owned_risks", to="webapp.membership")),
                ("system", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="risks", to="webapp.system")),
                ("controls", models.ManyToManyField(blank=True, related_name="risks", to="webapp.controlassessment")),
                ("remediation_plans", models.ManyToManyField(blank=True, related_name="risks", to="webapp.remediationplan")),
            ], options={"ordering": ("-inherent_score", "risk_id")}),
        migrations.CreateModel(
            name="RiskRegisterHistory",
            fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                    ("action", models.CharField(max_length=30)), ("snapshot", models.JSONField(default=dict)),
                    ("created_at", models.DateTimeField(auto_now_add=True)),
                    ("actor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                    ("risk", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="history", to="webapp.riskregisterentry"))],
            options={"ordering": ("-created_at",)}),
        migrations.AddConstraint(model_name="riskregisterentry", constraint=models.UniqueConstraint(fields=("organization","risk_id"), name="unique_org_risk_id")),
        migrations.AddConstraint(model_name="riskregisterentry", constraint=models.CheckConstraint(condition=models.Q(likelihood__gte=1, likelihood__lte=5), name="risk_likelihood_1_5")),
        migrations.AddConstraint(model_name="riskregisterentry", constraint=models.CheckConstraint(condition=models.Q(impact__gte=1, impact__lte=5), name="risk_impact_1_5")),
        migrations.AddConstraint(model_name="riskregisterentry", constraint=models.CheckConstraint(condition=models.Q(residual_likelihood__isnull=True) | models.Q(residual_likelihood__gte=1, residual_likelihood__lte=5), name="residual_likelihood_1_5")),
        migrations.AddConstraint(model_name="riskregisterentry", constraint=models.CheckConstraint(condition=models.Q(residual_impact__isnull=True) | models.Q(residual_impact__gte=1, residual_impact__lte=5), name="residual_impact_1_5")),
    ]
