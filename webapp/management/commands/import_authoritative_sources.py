from django.core.management.base import BaseCommand, CommandError
from webapp.authoritative_sources import import_authoritative_sources
class Command(BaseCommand):
    help = "Validate or privately import the Omni authoritative-source registry."
    def add_arguments(self, parser):
        parser.add_argument("source"); parser.add_argument("--apply", action="store_true")
    def handle(self, *args, **options):
        try: report = import_authoritative_sources(options["source"], options["apply"])
        except (OSError, ValueError) as exc: raise CommandError(str(exc)) from exc
        self.stdout.write(str(report))
