import json

from django.core.management.base import BaseCommand, CommandError

from webapp.readiness import deployment_readiness


class Command(BaseCommand):
    help = (
        "Report Omni production security and deployment gates without exposing secrets."
    )

    def add_arguments(self, parser):
        parser.add_argument("--production", action="store_true")
        parser.add_argument("--json", action="store_true")

    def handle(self, *args, **options):
        checks = deployment_readiness()
        if options["json"]:
            self.stdout.write(json.dumps({"checks": checks}, indent=2))
        else:
            for item in checks:
                marker = "PASS" if item["ok"] else "FAIL"
                self.stdout.write(f"[{marker}] {item['name']}: {item['detail']}")
        failures = [item for item in checks if not item["ok"]]
        if options["production"] and failures:
            raise CommandError(
                f"Production security gate failed: {len(failures)} requirement(s) unresolved."
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Security audit completed: {len(checks) - len(failures)}/{len(checks)} gates passed."
            )
        )
