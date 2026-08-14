from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("webapp", "0012_loginattempt"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AlterField(model_name="requirement", name="domain", field=models.CharField(max_length=100)),
        migrations.AddField(model_name="framework", name="source_filename", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="framework", name="source_sha256", field=models.CharField(blank=True, max_length=64)),
        migrations.AddField(model_name="requirement", name="source_page", field=models.PositiveIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="requirement", name="source_reference", field=models.CharField(blank=True, max_length=300)),
        migrations.AddField(model_name="requirement", name="source_row", field=models.PositiveIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="requirementmapping", name="approved_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="requirementmapping", name="approved_by", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="approved_requirement_mappings", to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name="requirementmapping", name="confidence", field=models.DecimalField(blank=True, decimal_places=3, max_digits=4, null=True)),
        migrations.AddField(model_name="requirementmapping", name="source_reference", field=models.CharField(blank=True, max_length=300)),
        migrations.AlterField(model_name="requirementmapping", name="relationship", field=models.CharField(choices=[("EQUIVALENT", "Equivalent"), ("PARTIAL", "Partially equivalent"), ("RELATED", "Related"), ("SUPPORTS", "Supports")], default="RELATED", max_length=15)),
        migrations.CreateModel(
            name="FrameworkImport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_file", models.FileField(upload_to="private/framework-imports/%Y/%m/")),
                ("source_filename", models.CharField(max_length=255)),
                ("source_format", models.CharField(choices=[("CSV", "CSV"), ("XLSX", "Excel"), ("PDF", "PDF")], max_length=8)),
                ("source_sha256", models.CharField(max_length=64)),
                ("status", models.CharField(choices=[("PREVIEW", "Awaiting approval"), ("IMPORTED", "Imported"), ("REJECTED", "Rejected"), ("FAILED", "Failed validation")], default="PREVIEW", max_length=12)),
                ("normalized_data", models.JSONField(default=dict)),
                ("validation_report", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="approved_framework_imports", to=settings.AUTH_USER_MODEL)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="framework_imports", to=settings.AUTH_USER_MODEL)),
                ("imported_framework", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="imports", to="webapp.framework")),
            ],
            options={"ordering": ("-created_at",)},
        ),
    ]
