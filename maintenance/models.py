from django.db import models
from django.utils.translation import gettext_lazy as _

# Create your models here.
class PermissionOnlyModel(models.Model):
    class Meta:
        verbose_name = _("Maintenance Permission Model")
        verbose_name_plural = _("Maintenance Permission Models")

        managed = False
        default_permissions = ()
        permissions = (
            ("toggle_maintenance_mode", _("Can toggle maintenance mode")),
            ("see_menu_item", _("Can see menu item")),
            ("see_info", _("Can see maintenance info")),
        )

