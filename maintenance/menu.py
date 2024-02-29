from wagtail.admin.menu import (
    Menu, MenuItem,
    SubmenuMenuItem,
    SubMenuItemComponent,
)

class ConditionalMenu(Menu):
    def menu_items_for_request(self, request):
        items = super().menu_items_for_request(request)
        if not items:
            self._is_shown = False
        else:
            self._is_shown = True
        return items
    
class MaintenanceMenu(ConditionalMenu):
    def render_component(self, request, menu_items=None):
        if menu_items is None:
            menu_items = self.menu_items_for_request(request)

        rendered_menu_items = []
        for item in sorted(menu_items, key=lambda i: i.order):
            rendered_menu_items.append(item.render_component(request))

        return rendered_menu_items

class MaintenanceSubmenuMenuItem(SubmenuMenuItem):

    def __init__(self, label, menu, **kwargs):
        if not isinstance(menu, MaintenanceMenu):
            menu.__class__ = MaintenanceMenu
        self.menu = menu
        super().__init__(label, menu, **kwargs)

    def render_component(self, request):
        menu_items = self.menu.menu_items_for_request(request)
        if len(menu_items) == 1:
            return menu_items[0].render_component(request)
        else:
            return SubMenuItemComponent(
                self.name,
                self.label,
                self.menu.render_component(request, menu_items),
                icon_name=self.icon_name,
                classname=self.classname,
                attrs=self.attrs,
            )

class MaintenanceAdminMenuItemMixin:
    def is_shown(self, request):

        if not super().is_shown(request):
            return False

        if request.user.has_perms([
                "maintenance.see_info",
                "maintenance.see_menu_item",
                "maintenance.toggle_maintenance_mode",
            ]):
            return True
        
        return False
    

class MaintenanceAdminSubmenuMenuItem(MaintenanceAdminMenuItemMixin, MaintenanceSubmenuMenuItem):
    pass


class MaintenanceAdminMenuItem(MaintenanceAdminMenuItemMixin, MenuItem):
    pass
