from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("webapp", "0032_soc2_points_procedures_conclusions")]

    operations = [
        migrations.AddField(
            model_name="soc2assessmentprofile", name="service_commitments",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="soc2assessmentprofile", name="system_boundaries",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="generateddocument", name="kind",
            field=models.CharField(max_length=25, choices=[
                ("WORKBOOK", "Assessment workbook"), ("SSP", "Word Security Plan"),
                ("REMEDIATION", "Remediation workbook"),
                ("PACKAGE", "Complete assessment package"),
                ("FRAMEWORK_REPORT", "Framework assessment report"),
                ("CONSOLIDATED", "Consolidated multi-framework report"),
                ("TRACEABILITY", "Cross-framework traceability matrix"),
                ("SOC2_REPORT", "SOC 2 assessment report"),
            ]),
        ),
    ]
