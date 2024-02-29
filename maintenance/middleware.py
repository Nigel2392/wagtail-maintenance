from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse
from django.conf import settings

from wagtail import hooks
from . import modes
from .settings import (
    REFRESH_DELAY,
    BAD_STATUS,
)

class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # Checks for allowed maintenance mode views.
        # Skip maintenance mode checks for ANY of these conditions
        path_lower = request.path.lower()
        not_allowed_checks = [
            hasattr(request, "is_dummy") and request.is_dummy,
            hasattr(request, "is_preview") and request.is_preview,

            # Wagtailadmin
            path_lower.startswith(f"{reverse('wagtailadmin_home')}/js"),
            path_lower.startswith(f"{reverse('wagtailadmin_home')}/sprite"),

            # Admin facing (required for maintenance mode to work)
            path_lower.startswith(reverse("admin_maintenance:ping").lower()),
            path_lower.startswith(reverse("admin_maintenance:modes").lower()),
            path_lower.startswith(reverse("admin_maintenance:script").lower()),
            path_lower.startswith(reverse("admin_maintenance:css").lower()),

            # User facing (required for maintenance mode to work)
            path_lower.startswith(reverse("maintenance:ping").lower()),
            path_lower.startswith(reverse("maintenance:script").lower()),
        ]

        # Unsure about nescessity of this (keys can individually check for this.)
        # for hook in hooks.get_hooks("maintenance_mode_not_allowed"):
        #     checks = hook(request)
        #     if isinstance(checks, (list, tuple)):
        #         not_allowed_checks.extend(checks)
        #     else:
        #         not_allowed_checks.append(checks)

        # Check if debug - staticfiles are then likely to be served by Django.
        # if so, skip checks for static and media files.
        if settings.DEBUG:
            if settings.STATIC_URL:
                not_allowed_checks.append(
                    path_lower.startswith(settings.STATIC_URL.lower())
                )

            if settings.MEDIA_URL:
                not_allowed_checks.append(
                    path_lower.startswith(settings.MEDIA_URL.lower())
                )

        # Check if we need to skip the maintenance checks.
        if any(not_allowed_checks):
            # We don't care about maintenance.
            return self.get_response(request)

        # Check if in maintenance mode
        status = modes.is_in_maintenance(request=request)
        if bool(status):
            accepts_json = request.accepts("application/json")
            accepts_html = any([
                request.accepts("text/html"),
                request.accepts("application/xhtml+xml"),
                not accepts_json,
            ])

            if accepts_html: # Respond with whatever template the key provided
                response = status.key.render(request=request)
                response.status_code = BAD_STATUS

            elif accepts_json:
                # Respond with a JSON message to indicate maintenance is active.
                response = JsonResponse(
                    data={
                        "maintenance_mode": True,
                        "error": _("The site is currently in maintenance mode. Please try again later."),
                    },
                    json_dumps_params={"indent": 4},
                    status=BAD_STATUS
                )

            # Let the client refresh automatically - maybe the maintenance is done.
            response["Retry-After"] = REFRESH_DELAY
            response["Cache-Control"] = "no-cache"
            response["X-Maintenance-Mode"] = "1"
            return response
            
        return self.get_response(request)
