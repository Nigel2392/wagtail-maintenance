from django.urls import re_path, path
from django.utils.safestring import mark_safe
from . import views

app_name = "maintenance"

urlpatterns_ping = [
    path("ping/", views.ping, name="ping"),
]

urlpatterns = [
    *urlpatterns_ping,
    path("script/", views.maintenance_script, name="script"),
]

try:
    from . import consumers

    websocket_urlpatterns = [
        re_path(r"maintenance/ping/$", consumers.MaintenancePingConsumer.as_asgi()),
    ]
except ImportError:
    pass

def get_maintenance_url(request):
    # Change in settings.py with MAINTENANCE_URL_FUNC = "path.to.get_maintenance_url"
    return mark_safe("/ws/maintenance/ping/")
