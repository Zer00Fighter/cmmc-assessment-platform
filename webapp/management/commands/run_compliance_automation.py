from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from webapp.models import (
    AuditEvent, ComplianceAutomationPolicy, ComplianceAutomationRun,
)


class Command(BaseCommand):
    help = "Run due organization-scoped Omni compliance workflow automation."

    def add_arguments(self, parser):
        parser.add_argument("--organization", dest="organization_slug")
        parser.add_argument(
            "--force", action="store_true",
            help="Run the selected organization now even if disabled or not yet due.",
        )

    def handle(self, *args, **options):
        today = timezone.localdate()
        policies = ComplianceAutomationPolicy.objects.select_related(
            "organization", "updated_by"
        )
        slug = options.get("organization_slug")
        if options.get("force") and not slug:
            raise CommandError("--force requires --organization to prevent a global manual run.")
        if slug:
            policies = policies.filter(organization__slug=slug)
            if not policies.exists():
                raise CommandError(f"No compliance automation policy exists for {slug}.")
        if not options.get("force"):
            policies = policies.filter(enabled=True, next_run_on__lte=today)
        completed = failed = 0
        for candidate in policies:
            with transaction.atomic():
                policy = ComplianceAutomationPolicy.objects.select_for_update().get(
                    pk=candidate.pk
                )
                if policy.runs.filter(
                    status=ComplianceAutomationRun.Status.RUNNING,
                    finished_at__isnull=True,
                ).exists():
                    self.stderr.write(f"Skipped {policy.organization.slug}: a run is active.")
                    continue
                run = ComplianceAutomationRun.objects.create(
                    policy=policy, status=ComplianceAutomationRun.Status.RUNNING
                )
            output = StringIO()
            try:
                call_command(
                    "send_workflow_reminders",
                    organization_slug=policy.organization.slug,
                    stdout=output,
                )
            except Exception as exc:
                run.status = ComplianceAutomationRun.Status.FAILED
                run.error = str(exc)
                failed += 1
                policy.last_status = ComplianceAutomationPolicy.LastStatus.FAILED
                policy.last_error = str(exc)
            else:
                run.status = ComplianceAutomationRun.Status.SUCCESS
                run.summary = output.getvalue().strip()
                completed += 1
                policy.last_status = ComplianceAutomationPolicy.LastStatus.SUCCESS
                policy.last_error = ""
            finally:
                now = timezone.now()
                run.finished_at = now
                run.save(update_fields=("status", "summary", "error", "finished_at"))
                policy.last_run_at = now
                interval = 1 if policy.frequency == policy.Frequency.DAILY else 7
                policy.next_run_on = today + timedelta(days=interval)
                policy.save(update_fields=(
                    "last_run_at", "last_status", "last_error", "next_run_on", "updated_at",
                ))
                AuditEvent.objects.create(
                    organization=policy.organization, actor=policy.updated_by,
                    action="compliance_automation.completed",
                    object_type="ComplianceAutomationRun", object_id=str(run.id),
                    detail={"status": run.status, "summary": run.summary},
                )
        self.stdout.write(self.style.SUCCESS(
            f"Compliance automation finished: {completed} successful, {failed} failed."
        ))
        if failed:
            raise CommandError(f"{failed} organization automation run(s) failed.")
