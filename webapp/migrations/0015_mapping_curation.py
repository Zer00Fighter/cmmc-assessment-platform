from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [("webapp", "0014_harmonization"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="ExternalAuthority", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("code", models.SlugField(max_length=100, unique=True)),
            ("canonical_name", models.CharField(max_length=300)), ("version", models.CharField(blank=True, max_length=100)),
            ("kind", models.CharField(choices=[("STANDARD", "Standard or framework"), ("REGULATION", "Regulation or law"), ("CONTRACT", "Contractual or industry requirement"), ("OTHER", "Other")], default="STANDARD", max_length=15)),
            ("issuer", models.CharField(blank=True, max_length=250)), ("jurisdiction", models.CharField(blank=True, max_length=150)),
            ("aliases", models.JSONField(blank=True, default=list)), ("source_column", models.PositiveIntegerField(blank=True, null=True)), ("active", models.BooleanField(default=True)),
        ], options={"ordering": ("canonical_name", "version")}),
        migrations.CreateModel(name="MappingReference", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("source_requirement_id_text", models.CharField(max_length=100)),
            ("raw_reference", models.TextField()), ("parsed_reference", models.CharField(blank=True, max_length=300)),
            ("status", models.CharField(choices=[("UNRESOLVED", "Unresolved"), ("RESOLVED", "Resolved"), ("IGNORED", "Ignored")], default="UNRESOLVED", max_length=12)),
            ("relationship", models.CharField(choices=[("EQUIVALENT", "Equivalent"), ("PARTIAL", "Partially equivalent"), ("RELATED", "Related"), ("SUPPORTS", "Supports")], default="RELATED", max_length=15)),
            ("review_status", models.CharField(choices=[("PENDING", "Pending review"), ("APPROVED", "Approved"), ("REJECTED", "Rejected")], default="PENDING", max_length=10)),
            ("confidence", models.DecimalField(blank=True, decimal_places=3, max_digits=4, null=True)), ("source_row", models.PositiveIntegerField(blank=True, null=True)),
            ("source_column", models.PositiveIntegerField(blank=True, null=True)), ("rationale", models.TextField(blank=True)), ("reviewed_at", models.DateTimeField(blank=True, null=True)),
            ("authority", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="mapping_references", to="webapp.externalauthority")),
            ("import_job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="mapping_references", to="webapp.frameworkimport")),
            ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="reviewed_mapping_references", to=settings.AUTH_USER_MODEL)),
            ("source_requirement", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="catalog_mapping_references", to="webapp.requirement")),
            ("target_requirement", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="incoming_catalog_references", to="webapp.requirement")),
        ], options={"ordering": ("review_status", "authority__canonical_name", "source_requirement_id_text")}),
        migrations.AddConstraint(model_name="mappingreference", constraint=models.UniqueConstraint(fields=("import_job", "source_requirement_id_text", "authority", "raw_reference"), name="unique_import_mapping_reference")),
    ]
