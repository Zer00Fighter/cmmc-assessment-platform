from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("webapp", "0020_authoritative_sources")]

    operations = [
        migrations.AddField(
            model_name="requirement",
            name="risk_weight",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text="Framework-native relative control weight; Omni CCF uses 1–10, with 0 reserved for deprecated controls.",
                null=True,
            ),
        ),
        migrations.AddConstraint(
            model_name="requirement",
            constraint=models.CheckConstraint(
                condition=models.Q(risk_weight__isnull=True) | models.Q(risk_weight__lte=10),
                name="requirement_risk_weight_lte_10",
            ),
        ),
    ]
