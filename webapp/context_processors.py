def notification_summary(request):
    if not request.user.is_authenticated:
        return {}
    return {
        "unread_notification_count": request.user.omni_notifications.filter(
            read_at=None
        ).count()
    }
