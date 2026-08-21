from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from webapp.soc2_activity_import import import_activities, normalize_workbook


class Command(BaseCommand):
    help = "Normalize and optionally import a multi-tab SOC 2 implementation checklist."

    def add_arguments(self, parser):
        parser.add_argument("workbook", type=Path)
        parser.add_argument("--commit", action="store_true", help="Persist activities and proposed mappings.")

    def handle(self, *args, **options):
        path = options["workbook"]
        if not path.is_file():
            raise CommandError(f"Workbook not found: {path}")
        try:
            if options["commit"]:
                result, report = import_activities(path)
            else:
                _, report = normalize_workbook(path)
                result = {"created": 0, "existing": 0, "mappings_created": 0}
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        if not report.get("valid"):
            raise CommandError("; ".join(report.get("errors", [])))
        mode = "Imported" if options["commit"] else "Validated"
        self.stdout.write(self.style.SUCCESS(
            f"{mode} {report['activity_count']} activities and {report['mapping_count']} "
            f"proposed TSC relationships. Created {result['created']} activities and "
            f"{result['mappings_created']} mappings."
        ))
