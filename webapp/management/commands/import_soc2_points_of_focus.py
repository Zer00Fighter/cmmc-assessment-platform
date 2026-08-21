from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from webapp.soc2_points_of_focus import import_points_of_focus, normalize_points_of_focus


class Command(BaseCommand):
    help = "Validate or privately import user-authorized AICPA Points of Focus."

    def add_arguments(self, parser):
        parser.add_argument("source", type=Path)
        parser.add_argument("--commit", action="store_true")

    def handle(self, *args, **options):
        path = options["source"]
        if not path.is_file():
            raise CommandError(f"Source not found: {path}")
        try:
            if options["commit"]:
                result, report = import_points_of_focus(path)
            else:
                _, report = normalize_points_of_focus(path)
                result = {"created": 0, "existing": 0}
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        if not report["valid"]:
            raise CommandError("; ".join(report["errors"]))
        verb = "Imported" if options["commit"] else "Validated"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {report['point_count']} Points of Focus; "
            f"created {result['created']}, existing {result['existing']}."
        ))
