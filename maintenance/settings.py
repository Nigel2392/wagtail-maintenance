from django.conf import settings
from django.urls import reverse_lazy

IS_ASGI = getattr(settings, "IS_ASGI", False)
BAD_STATUS = getattr(settings, "MAINTENANCE_MODE_BAD_STATUS", 503)
MAINTENANCE_MODE_TEMPLATE = getattr(settings, "MAINTENANCE_MODE_TEMPLATE", "maintenance/maintenance_mode.html")
MAINTENANCE_MENU_ITEM_HOOK_NAME = getattr(settings, "MAINTENANCE_MENU_ITEM_HOOK_NAME", "register_settings_menu_item")
MAINTENANCE_URL_FUNC = getattr(settings, "MAINTENANCE_URL_FUNC", "maintenance.urls.get_maintenance_url")
MAINTENANCE_MODE_TEMPLATE_IGNORE_PATHS = getattr(settings, "MAINTENANCE_MODE_TEMPLATE_IGNORE_PATHS", [
    reverse_lazy("admin:index"),
    reverse_lazy("wagtailadmin_home"),
    reverse_lazy("maintenance:ping"),
    reverse_lazy("maintenance:script"),

    reverse_lazy("admin_maintenance:ping"),
    reverse_lazy("admin_maintenance:modes"),
    reverse_lazy("admin_maintenance:script"),
    reverse_lazy("admin_maintenance:css"),
])

REFRESH_DELAY = 60
