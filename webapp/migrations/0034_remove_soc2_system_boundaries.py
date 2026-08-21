from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("webapp", "0033_generateddocument_soc2_report")]

    operations = [
        migrations.RemoveField(
            model_name="soc2assessmentprofile", name="system_boundaries",
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
                ("SOC2_REPORT", "SOC 2 readiness work program"),
            ]),
        ),
    ]
