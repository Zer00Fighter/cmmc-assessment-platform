from django.core.management.base import BaseCommand

from webapp.readiness import deployment_readiness


class Command(BaseCommand):
    help = "Report local and future-production readiness without deploying Omni."

    def handle(self, *args, **options):
        checks = deployment_readiness()
        for item in checks:
            marker = "PASS" if item["ok"] else "NOT READY"
            self.stdout.write(f"[{marker}] {item['name']}: {item['detail']}")
        self.stdout.write(f"{sum(item['ok'] for item in checks)}/{len(checks)} checks ready.")
