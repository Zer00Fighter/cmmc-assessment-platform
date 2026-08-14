from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run daily Omni invitation, reminder, digest, and local backup maintenance."

    def add_arguments(self, parser):
        parser.add_argument("--skip-backup", action="store_true")

    def handle(self, *args, **options):
        call_command("expire_invitations")
        call_command("send_workflow_reminders")
        call_command("send_notification_digests")
        if not options["skip_backup"]:
            call_command("backup_omni")
        self.stdout.write(self.style.SUCCESS("Omni daily maintenance completed."))
