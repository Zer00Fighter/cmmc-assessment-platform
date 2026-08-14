from django.core.management.base import BaseCommand, CommandError
from webapp.omni_evidence_catalog import import_catalog

class Command(BaseCommand):
    help = "Validate or privately import the Omni Control Framework evidence request catalog."
    def add_arguments(self, parser):
        parser.add_argument("source")
        parser.add_argument("--apply", action="store_true")
    def handle(self, *args, **options):
        try: report = import_catalog(options["source"], options["apply"])
        except (OSError, ValueError) as exc: raise CommandError(str(exc)) from exc
        self.stdout.write(str(report))
