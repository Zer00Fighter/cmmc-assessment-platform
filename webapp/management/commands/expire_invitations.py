from django.core.management.base import BaseCommand
from django.utils import timezone

from webapp.models import OrganizationInvitation


class Command(BaseCommand):
    help = "Mark expired pending invitations as expired."

    def handle(self, *args, **options):
        count = OrganizationInvitation.objects.filter(
            status=OrganizationInvitation.Status.PENDING, expires_at__lte=timezone.now()
        ).update(status=OrganizationInvitation.Status.EXPIRED)
        self.stdout.write(self.style.SUCCESS(f"Expired {count} invitations."))
