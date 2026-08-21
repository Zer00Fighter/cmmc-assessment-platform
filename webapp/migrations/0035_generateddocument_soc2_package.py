from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("webapp", "0034_remove_soc2_system_boundaries")]

    operations = [migrations.AlterField(
        model_name="generateddocument", name="kind",
        field=models.CharField(max_length=25, choices=[
            ("WORKBOOK", "Assessment workbook"), ("SSP", "Word Security Plan"),
            ("REMEDIATION", "Remediation workbook"),
            ("PACKAGE", "Complete assessment package"),
            ("FRAMEWORK_REPORT", "Framework assessment report"),
            ("CONSOLIDATED", "Consolidated multi-framework report"),
            ("TRACEABILITY", "Cross-framework traceability matrix"),
            ("SOC2_REPORT", "SOC 2 readiness report"),
            ("SOC2_DRL", "SOC 2 document request list"),
            ("SOC2_PACKAGE", "SOC 2 readiness package"),
        ]),
    )]
