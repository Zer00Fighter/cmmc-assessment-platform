from django.core.management.base import BaseCommand, CommandError

from webapp.soc2_tsc import install_baseline
from webapp.soc2_procedures import ensure_soc2_execution_catalog


class Command(BaseCommand):
    help = "Install the immutable AICPA TSC 2017 / revised-2022 identifier baseline."

    def handle(self, *args, **options):
        try:
            framework, created, report = install_baseline()
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        verb = "Installed" if created else "Verified"
        procedures = ensure_soc2_execution_catalog()
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {framework.code}: {report['criterion_count']} criteria across "
            f"{len(report['domain_counts'])} Trust Services categories; "
            f"{procedures['procedures_created']} suggested procedures added."
        ))
