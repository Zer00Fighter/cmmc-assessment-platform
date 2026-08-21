import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("webapp", "0031_soc2assessmentprofile_control_scope"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(model_name="assessmentprocedure", name="method", field=models.CharField(choices=[("EXAMINE", "Examine"), ("INTERVIEW", "Interview"), ("TEST", "Test"), ("OBSERVE", "Observe"), ("REPERFORM", "Reperform")], max_length=12)),
        migrations.AddField(model_name="objectiveassessment", name="design_conclusion", field=models.CharField(choices=[("NOT_ASSESSED", "Not assessed"), ("EFFECTIVE", "Effective"), ("DEFICIENT", "Deficient"), ("NOT_APPLICABLE", "Not applicable")], default="NOT_ASSESSED", max_length=20)),
        migrations.AddField(model_name="objectiveassessment", name="implementation_conclusion", field=models.CharField(choices=[("NOT_ASSESSED", "Not assessed"), ("EFFECTIVE", "Effective"), ("DEFICIENT", "Deficient"), ("NOT_APPLICABLE", "Not applicable")], default="NOT_ASSESSED", max_length=20)),
        migrations.AddField(model_name="objectiveassessment", name="operating_effectiveness_conclusion", field=models.CharField(choices=[("NOT_TESTED", "Not tested"), ("EFFECTIVE", "Effective"), ("EXCEPTION", "Exception identified"), ("DEFICIENT", "Deficient"), ("NOT_APPLICABLE", "Not applicable")], default="NOT_TESTED", max_length=20)),
        migrations.AddField(model_name="assessmentsample", name="period_start", field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name="assessmentsample", name="period_end", field=models.DateField(blank=True, null=True)),
        migrations.CreateModel(
            name="Soc2PointOfFocus",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("point_id", models.CharField(max_length=50)),
                ("licensed_text", models.TextField()),
                ("source_filename", models.CharField(max_length=255)),
                ("source_sha256", models.CharField(max_length=64)),
                ("source_reference", models.CharField(blank=True, max_length=500)),
                ("source_row", models.PositiveIntegerField(blank=True, null=True)),
                ("source_page", models.PositiveIntegerField(blank=True, null=True)),
                ("active", models.BooleanField(default=True)),
                ("requirement", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="soc2_points_of_focus", to="webapp.requirement")),
            ],
            options={"ordering": ("requirement__requirement_id", "point_id")},
        ),
        migrations.CreateModel(
            name="AssessmentProcedureCustomization",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("method", models.CharField(choices=[("EXAMINE", "Examine"), ("INTERVIEW", "Interview"), ("TEST", "Test"), ("OBSERVE", "Observe"), ("REPERFORM", "Reperform")], max_length=12)),
                ("procedure_text", models.TextField()),
                ("enabled", models.BooleanField(default=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("base_procedure", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="customizations", to="webapp.assessmentprocedure")),
                ("objective_result", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="procedure_customizations", to="webapp.objectiveassessment")),
                ("updated_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="updated_procedure_customizations", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("method", "id")},
        ),
        migrations.AddConstraint(model_name="soc2pointoffocus", constraint=models.UniqueConstraint(fields=("requirement", "point_id", "source_sha256"), name="unique_soc2_point_source_version")),
    ]
