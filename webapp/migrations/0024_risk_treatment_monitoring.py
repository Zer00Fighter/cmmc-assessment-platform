from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("webapp", "0023_risk_register"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AddField(model_name="assessment", name="risk_management_enabled", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="assessment", name="include_risk_in_reports", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="riskregisterentry", name="supporting_evidence", field=models.ManyToManyField(blank=True, related_name="risks", to="webapp.evidenceartifact")),
        migrations.AddField(model_name="riskregisterentry", name="review_frequency_days", field=models.PositiveSmallIntegerField(default=90)),
        migrations.AddField(model_name="riskregisterentry", name="last_reviewed_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="riskregisterentry", name="trend", field=models.CharField(choices=[("UNKNOWN","Unknown"),("INCREASING","Increasing"),("STABLE","Stable"),("DECREASING","Decreasing")], default="UNKNOWN", max_length=12)),
        migrations.AddField(model_name="riskregisterentry", name="monitoring_notes", field=models.TextField(blank=True)),
        migrations.AddField(model_name="riskregisterentry", name="trigger_events", field=models.TextField(blank=True)),
        migrations.AddField(model_name="riskregisterentry", name="closure_rationale", field=models.TextField(blank=True)),
        migrations.AddField(model_name="riskregisterentry", name="closed_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="riskregisterentry", name="closed_by", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="closed_risks", to=settings.AUTH_USER_MODEL)),
        migrations.CreateModel(name="RiskTolerancePolicy", fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
            ("maximum_residual_score",models.PositiveSmallIntegerField(default=11)),
            ("critical_acceptance_allowed",models.BooleanField(default=False)),
            ("maximum_acceptance_days",models.PositiveSmallIntegerField(default=365)),
            ("review_reminder_days",models.PositiveSmallIntegerField(default=14)),
            ("acceptance_expiry_reminder_days",models.PositiveSmallIntegerField(default=30)),
            ("updated_at",models.DateTimeField(auto_now=True)),
            ("organization",models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,related_name="risk_tolerance_policy",to="webapp.organization")),
            ("updated_by",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="updated_risk_tolerance_policies",to=settings.AUTH_USER_MODEL))]),
        migrations.CreateModel(name="RiskTreatmentAction", fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
            ("title",models.CharField(max_length=300)),("description",models.TextField(blank=True)),
            ("status",models.CharField(choices=[("NOT_STARTED","Not started"),("IN_PROGRESS","In progress"),("BLOCKED","Blocked"),("COMPLETE","Complete")],default="NOT_STARTED",max_length=15)),
            ("priority",models.CharField(choices=[("LOW","Low"),("MEDIUM","Medium"),("HIGH","High"),("CRITICAL","Critical")],default="MEDIUM",max_length=10)),
            ("planned_start",models.DateField(blank=True,null=True)),("due_date",models.DateField(blank=True,null=True)),
            ("completed_date",models.DateField(blank=True,null=True)),("completion_notes",models.TextField(blank=True)),
            ("created_at",models.DateTimeField(auto_now_add=True)),("updated_at",models.DateTimeField(auto_now=True)),
            ("created_by",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="created_risk_treatment_actions",to=settings.AUTH_USER_MODEL)),
            ("owner",models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name="risk_treatment_actions",to="webapp.membership")),
            ("remediation_plan",models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name="risk_treatment_actions",to="webapp.remediationplan")),
            ("risk",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="treatment_actions",to="webapp.riskregisterentry")),
            ("dependencies",models.ManyToManyField(blank=True,related_name="dependent_actions",to="webapp.risktreatmentaction")),
            ("evidence",models.ManyToManyField(blank=True,related_name="risk_treatment_actions",to="webapp.evidenceartifact"))],options={"ordering": ("status","due_date","id")}),
        migrations.CreateModel(name="RiskReassessment", fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
            ("previous_likelihood",models.PositiveSmallIntegerField()),("previous_impact",models.PositiveSmallIntegerField()),
            ("new_likelihood",models.PositiveSmallIntegerField()),("new_impact",models.PositiveSmallIntegerField()),
            ("rationale",models.TextField()),("assessed_at",models.DateTimeField(auto_now_add=True)),
            ("assessed_by",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="risk_reassessments",to=settings.AUTH_USER_MODEL)),
            ("risk",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="reassessments",to="webapp.riskregisterentry")),
            ("evidence",models.ManyToManyField(blank=True,related_name="risk_reassessments",to="webapp.evidenceartifact"))],options={"ordering": ("-assessed_at",)}),
        migrations.CreateModel(name="RiskAcceptanceRequest", fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
            ("rationale",models.TextField()),("requested_expiration",models.DateField()),
            ("status",models.CharField(choices=[("PENDING","Pending"),("APPROVED","Approved"),("REJECTED","Rejected"),("CANCELLED","Cancelled")],default="PENDING",max_length=10)),
            ("requested_at",models.DateTimeField(auto_now_add=True)),("reviewed_at",models.DateTimeField(blank=True,null=True)),
            ("review_comment",models.TextField(blank=True)),
            ("requested_by",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="risk_acceptance_requests",to=settings.AUTH_USER_MODEL)),
            ("reviewed_by",models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,related_name="reviewed_risk_acceptance_requests",to=settings.AUTH_USER_MODEL)),
            ("risk",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="acceptance_requests",to="webapp.riskregisterentry"))],options={"ordering": ("status","requested_at")}),
    ]
