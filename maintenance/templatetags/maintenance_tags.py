from django.template import library
from django.utils.module_loading import import_string
from ..settings import MAINTENANCE_URL_FUNC, IS_ASGI

register = library.Library()

def get_maintenance_url(request):
    return import_string(MAINTENANCE_URL_FUNC)(request)

@register.filter(name="startswith")
def startswith(value, arg):
    if not value:
        return False
    return value.startswith(arg)

@register.simple_tag
def is_asgi():
    return IS_ASGI

@register.simple_tag(takes_context=True, name="get_maintenance_url")
def do_get_maintenance_url(context):
    request = context.get("request")
    return get_maintenance_url(request=request)
