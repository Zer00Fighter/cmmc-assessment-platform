from django.core.management.base import BaseCommand

from webapp.soc2_procedures import ensure_soc2_execution_catalog


class Command(BaseCommand):
    help = "Install Omni-authored SOC 2 objectives and suggested procedures."

    def handle(self, *args, **options):
        result = ensure_soc2_execution_catalog()
        self.stdout.write(self.style.SUCCESS(
            f"SOC 2 execution catalog: {result['requirements']} criteria, "
            f"{result['objectives_created']} objectives, "
            f"{result['procedures_created']} procedures, "
            f"{result['results_created']} assessment results created."
        ))
