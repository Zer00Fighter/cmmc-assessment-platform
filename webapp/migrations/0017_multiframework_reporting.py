from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
class Migration(migrations.Migration):
    dependencies=[("webapp","0016_shared_work"),migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[
        migrations.AlterField(model_name="generateddocument",name="kind",field=models.CharField(choices=[("WORKBOOK","Assessment workbook"),("SSP","Word Security Plan"),("REMEDIATION","Remediation workbook"),("PACKAGE","Complete assessment package"),("FRAMEWORK_REPORT","Framework assessment report"),("CONSOLIDATED","Consolidated multi-framework report"),("TRACEABILITY","Cross-framework traceability matrix")],max_length=25)),
        migrations.AddField(model_name="generateddocument",name="framework",field=models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,related_name="generated_documents",to="webapp.framework")),
        migrations.AddField(model_name="generateddocument",name="status",field=models.CharField(choices=[("DRAFT","Draft"),("FINAL","Final"),("SUPERSEDED","Superseded")],default="DRAFT",max_length=10)),
        migrations.AddField(model_name="generateddocument",name="approved_by",field=models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,related_name="approved_omni_documents",to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name="generateddocument",name="approved_at",field=models.DateTimeField(blank=True,null=True)),
        migrations.AddField(model_name="generateddocument",name="superseded_by",field=models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name="supersedes",to="webapp.generateddocument")),
        migrations.CreateModel(name="ReportingProfile",fields=[("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),("report_title",models.CharField(max_length=250)),("template_version",models.CharField(default="1.0",max_length=50)),("required_sections",models.JSONField(default=list)),("status_labels",models.JSONField(blank=True,default=dict)),("require_objectives",models.BooleanField(default=True)),("require_evidence_applicability",models.BooleanField(default=True)),("active",models.BooleanField(default=True)),("framework",models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,related_name="reporting_profile",to="webapp.framework"))]),
    ]
