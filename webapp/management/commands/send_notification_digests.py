from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from webapp.models import Notification, NotificationPreference


class Command(BaseCommand):
    help = "Send queued daily and weekly notification digests."

    def add_arguments(self, parser):
        parser.add_argument("--weekly", action="store_true")

    def handle(self, *args, **options):
        delivery = (
            NotificationPreference.Delivery.WEEKLY if options["weekly"]
            else NotificationPreference.Delivery.DAILY
        )
        since = timezone.now() - timedelta(days=7 if options["weekly"] else 1)
        sent = 0
        for preference in NotificationPreference.objects.filter(delivery=delivery).select_related("user"):
            user = preference.user
            items = list(user.omni_notifications.filter(
                email_status=Notification.EmailStatus.QUEUED, created_at__gte=since
            ).order_by("created_at"))
            if not items or not settings.OMNI_EMAIL_ENABLED or not user.email:
                continue
            lines = [f"Omni {'weekly' if options['weekly'] else 'daily'} notification digest", ""]
            lines.extend(f"- {item.title}: {item.message}" for item in items)
            lines.extend(["", f"Open Omni securely: {settings.OMNI_BASE_URL}", "",
                          "Sensitive assessment content is not included in this email."])
            delivered = send_mail(
                f"Omni {'Weekly' if options['weekly'] else 'Daily'} Digest",
                "\n".join(lines), settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True,
            )
            if delivered:
                Notification.objects.filter(pk__in=[item.pk for item in items]).update(
                    email_status=Notification.EmailStatus.SENT
                )
                sent += 1
        self.stdout.write(self.style.SUCCESS(f"Sent {sent} notification digests."))
