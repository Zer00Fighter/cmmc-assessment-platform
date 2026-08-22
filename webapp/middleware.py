import uuid

from django.conf import settings


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.omni_request_id = uuid.uuid4().hex
        response = self.get_response(request)
        policy = (
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; font-src 'self'; connect-src 'self'; media-src 'none'; "
            "object-src 'none'; frame-src 'none'; frame-ancestors 'none'; base-uri 'self'; "
            "form-action 'self'"
        )
        if not settings.DEBUG:
            policy += "; upgrade-insecure-requests"
        response.setdefault(
            "Content-Security-Policy",
            policy,
        )
        response.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()",
        )
        response.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        response.setdefault("X-Permitted-Cross-Domain-Policies", "none")
        response.setdefault("X-Robots-Tag", "noindex, nofollow, noarchive")
        response.setdefault("X-Request-ID", request.omni_request_id)
        sensitive_path = request.path.startswith(
            ("/accounts/", "/admin/", "/organizations/", "/notifications/", "/profile/")
        )
        if (
            getattr(request, "user", None)
            and request.user.is_authenticated
            or sensitive_path
        ):
            response["Cache-Control"] = "no-store, no-cache, private, max-age=0"
            response["Pragma"] = "no-cache"
        return response
