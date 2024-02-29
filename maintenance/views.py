from django.http import HttpResponse, JsonResponse
from django.utils.translation import gettext_lazy as _

from . import modes, middleware, settings as app_settings
from .templatetags.maintenance_tags import get_maintenance_url


def maintenance_script(request):
    if app_settings.IS_ASGI:
        url = get_maintenance_url(request)
        content = """function maintenanceMode() {{
            // Create WebSocket connection.
            const socket = new WebSocket(\"{url}\");
            // Connection opened
            socket.addEventListener(\"open\", (event) => {{
                socket.send(\"Connected to maintenance ping socket\");
            }});
            // Listen for messages
            socket.addEventListener(\"message\", (event) => {{
                try {{
                    const data = JSON.parse(event.data);
                    let maintaining = data.maintenance_mode;
                    if (maintaining) {{
                        window.location.reload();
                    }}
                }} catch (error) {{
                    console.error(error);
                }}
            }});
        }}
        maintenanceMode();""" % {"url": url}
        return HttpResponse(content, content_type="application/javascript")
    return HttpResponse("0;", content_type="application/javascript")


def ping(request):
    in_maintenance_mode = modes.is_in_maintenance()
    status = 200
    maintenance_values = {}

    if in_maintenance_mode:
        status = middleware.BAD_STATUS
        maintenance_values["error"] = _("The site is currently in maintenance mode. Please try again later."),

    if request.user and request.user.is_authenticated and request.user.has_perm("maintenance.see_info"):
        maintenance_values["maintenance"] = modes.get_maintenance_key_data()

    response = JsonResponse(
        data={
            "maintenance_mode": bool(in_maintenance_mode),
            "refresh_delay": app_settings.REFRESH_DELAY,
            **maintenance_values,
        },
        json_dumps_params={
            "indent": 4,
        },
        status=status,
    )

    if in_maintenance_mode:
        response["Retry-After"] = app_settings.REFRESH_DELAY
        response["Cache-Control"] = "no-cache"
        response["X-Maintenance-Mode"] = "1"

    return response

