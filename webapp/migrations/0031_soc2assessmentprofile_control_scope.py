import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("webapp", "0030_implementationactivity_and_mapping"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(model_name="controlassessment", name="in_scope", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="controlassessment", name="scope_rationale", field=models.TextField(blank=True)),
        migrations.CreateModel(
            name="Soc2AssessmentProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("examination_type", models.CharField(choices=[("TYPE_I", "Type I — design as of a specified date"), ("TYPE_II", "Type II — design and operating effectiveness over a period")], max_length=10)),
                ("included_categories", models.JSONField(default=list)),
                ("as_of_date", models.DateField(blank=True, null=True)),
                ("period_start", models.DateField(blank=True, null=True)),
                ("period_end", models.DateField(blank=True, null=True)),
                ("scope_notes", models.TextField(blank=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assessment", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="soc2_profile", to="webapp.assessment")),
                ("updated_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="updated_soc2_profiles", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("assessment__name",)},
        ),
    ]
