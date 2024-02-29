
from typing import Any
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import path, reverse, include
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import Permission
from django.views.generic import View

from wagtail import hooks
from wagtail.admin.views.generic.base import WagtailAdminTemplateMixin

from . import modes, urls, forms, menu
from .settings import MAINTENANCE_MENU_ITEM_HOOK_NAME, IS_ASGI
from .templatetags.maintenance_tags import get_maintenance_url



def maintenance_css_admin(request):
    content = """.sidebar-menu-item--active {
    background-color: hsl(354.94deg 56.76% 47.31%);
}
.sidebar-loading__inner, .sidebar__inner {
    background-color: var(--w-color-critical-200);
}
.w-bg-surface-menus {
    background-color: var(--w-color-critical-200);
}
.hover\:w-bg-surface-menu-item-active:hover {
    background-color: hsl(354.94deg 56.76% 47.31%);
}
.focus\:w-bg-surface-menu-item-active:focus {
    background-color: hsl(354.94deg 56.76% 47.31%);
}
.sidebar-panel--visible {
    box-shadow: unset;
}
.sidebar-sub-menu-panel {
    background-color: var(--w-color-critical-200);
}
.sidebar-footer {
    background-color: var(--w-color-critical-200);
}
"""
    return HttpResponse(content, content_type="text/css")


def maintenance_script_admin(request):
    if IS_ASGI:
        url = get_maintenance_url(request)
        content = """function maintenanceMode() {
    const css = `
    <style type="text/css" id="maintenance-mode">
        .sidebar-menu-item--active {
            background-color: hsl(354.94deg 56.76% 47.31%);
        }
        .sidebar-loading__inner, .sidebar__inner {
            background-color: var(--w-color-critical-200);
        }
        .w-bg-surface-menus {
            background-color: var(--w-color-critical-200);
        }
        .hover\:w-bg-surface-menu-item-active:hover {
            background-color: hsl(354.94deg 56.76% 47.31%);
        }
        .focus\:w-bg-surface-menu-item-active:focus {
            background-color: hsl(354.94deg 56.76% 47.31%);
        }
        .sidebar-panel--visible {
            box-shadow: unset;
        }
        .sidebar-sub-menu-panel {
            background-color: var(--w-color-critical-200);
        }
        .sidebar-footer {
            background-color: var(--w-color-critical-200);
        }
    </style>
    `;
    // Create WebSocket connection.
    const socket = new WebSocket("{url}");
    // Connection opened
    socket.addEventListener("open", (event) => {
      socket.send("Hello Server!", event);
    });
    // Listen for messages
    socket.addEventListener("message", (event) => {
        console.log("Message from server ", event.data);
        try {
            const data = JSON.parse(event.data);
            let maintaining = data.maintenance_mode;
            if (maintaining) {
                if (!window.maintenanceMode.skipInsertStyle) {
                    document.querySelector('body').insertAdjacentHTML('afterbegin', css);
                }
            } else {
                if (!window.maintenanceMode.skipRemoveStyle) {
                    let elem = document.getElementById('maintenance-mode')
                    if (elem) {
                        elem.remove();
                    } else {
                        console.log('No maintenance mode css found');
                    }
                }
            }
        } catch (error) {
            console.error(error);
        }
    });
}
if (!window.maintenanceMode) {
    window.maintenanceMode = {};
    window.maintenanceMode.skipInsertStyle = false;
    window.maintenanceMode.skipRemoveStyle = false;
}
maintenanceMode();""" % {"url": url}
        return HttpResponse(content, content_type="application/javascript")
    return HttpResponse("0;", content_type="application/javascript")


class MaintenanceViewAdmin(WagtailAdminTemplateMixin, View):

    header_icon = 'cog'
    page_title = _("Maintenance Mode")
    page_subtitle = _("Configure maintenance mode")
    template_name = "maintenance/maintenance_mode_admin.html"

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data())

    def dispatch(self, request, *args, **kwargs):
        self.form = forms.MaintenanceModeForm(request.POST or None)

        if not request.user.has_perms([
            "maintenance.toggle_maintenance_mode",
            "maintenance.see_menu_item",
            "maintenance.see_info",
        ]):
            raise PermissionDenied
            

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, form=None, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["form"] = form or self.form
        return context
    
    def post(self, request, *args, **kwargs):
        if self.form.is_valid():
            self.form.save()
        else:
            return self.render_to_response(
                self.get_context_data(form=self.form)
            )
        
        return redirect(reverse("admin_maintenance:modes"))


@hooks.register("insert_global_admin_css")
def global_admin_css():
    if modes.is_in_maintenance():
        return format_html("<link rel='stylesheet' href='{}'>", reverse("admin_maintenance:css"))
    return ""


@hooks.register("insert_global_admin_js")
def global_admin_js():
    return format_html("<script src='{}'></script>", reverse("admin_maintenance:script"))


maintenance_menu = menu.MaintenanceMenu(
    register_hook_name="register_maintenance_menu_item",
    construct_hook_name="construct_maintenance_menu_item",
)


@hooks.register("register_maintenance_menu_item")
def register_maintenance_menu_item():
    return menu.MaintenanceAdminMenuItem(
        _("Maintenance Mode"),
        url=reverse("admin_maintenance:modes"),
        name="maintenance_modes",
        icon_name="cog",
        order=1000,
    )


@hooks.register(MAINTENANCE_MENU_ITEM_HOOK_NAME)
def register_maintenance_menu_item():
    return menu.MaintenanceAdminSubmenuMenuItem(
        _('Maintenance'),
        name="maintenance_settings",
        menu=maintenance_menu,
        icon_name="cog",
        order=1000,
    )


@hooks.register('register_permissions', order=-100)
def register_permissions():
    return Permission.objects.filter(
        content_type__app_label='maintenance',
        codename__in=[
            'toggle_maintenance_mode',
            'see_menu_item',
            'see_info',
        ]
    )


@hooks.register("register_admin_urls")
def register_maintenance_urls():
    return [
        path(
            "maintenance/",
            include(
                ([
                    *urls.urlpatterns_ping,
                    path("mode/", MaintenanceViewAdmin.as_view(), name="modes"),
                    path("script/", maintenance_script_admin, name="script"),
                    path("css/", maintenance_css_admin, name="css"),
                ], "admin_maintenance"),
                namespace="admin_maintenance",
            ),
        ),
    ]

