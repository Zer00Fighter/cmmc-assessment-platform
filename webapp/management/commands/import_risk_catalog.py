from django.core.management.base import BaseCommand, CommandError

from webapp.risk_catalog import import_risk_catalog


class Command(BaseCommand):
    help = "Validate or privately import the CCF Risk Catalog."

    def add_arguments(self, parser):
        parser.add_argument("source")
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        try:
            report = import_risk_catalog(options["source"], options["apply"])
        except (OSError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        if report["issues"]:
            raise CommandError(str(report))
        self.stdout.write(str(report))
