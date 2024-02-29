from django.db import models
from django.utils.functional import cached_property

from . import (
    modes, keys
)

def get_key_from_model(model: "MaintenanceModeMixin") -> keys.Key:
    """
    Returns a key for the given model
    """
    key_parts = model.get_maintenance_key_parts()
    key_parts = [str(part) for part in key_parts]

    return keys.Key(
        value=".".join(key_parts),
        label=model.get_maintenance_label(),
        help_text=model.get_maintenance_help_text(),
        maintenance_template=model.get_maintenance_maintenance_template(),
        timeout=model.get_maintenance_timeout(),
    )

class MaintenanceModeMixin(models.Model):

    maintenance_label: str = None
    maintenance_help_text: str = None
    maintenance_maintenance_template: str = None
    maintenance_timeout: int = keys.DAY

    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    @cached_property
    def maintenance_key(self) -> keys.Key:
        """
        Returns a key for the model
        """
        return get_key_from_model(self)
    
    def get_maintenance_key_parts(self) -> list:
        """
        Return a list of strings to be used as key parts for the maintenance key
        """
        return [self._meta.app_label, self._meta.model_name, self.pk]
    
    def get_maintenance_label(self) -> str:
        """
        Returns a label for the maintenance key
        """
        return self.maintenance_label or str(self)
    
    def get_maintenance_help_text(self) -> str:
        """
        Returns help text for the maintenance key
        """
        return self.maintenance_help_text or ""
    
    def get_maintenance_maintenance_template(self) -> str:
        """
        Returns a template to use for the maintenance key
        """
        return self.maintenance_maintenance_template or None
    
    def get_maintenance_timeout(self) -> int:
        """
        Returns the timeout for the maintenance key
        """
        return self.maintenance_timeout or keys.DAY
    
    def blocking_maintenance_cache(self) -> bool:
        """
        Returns True if the cache should be locked while in maintenance mode
        """
        return False

    @property
    def maintaining(self) -> bool:
        """
        Returns True if the model is in maintenance mode
        """
        return modes.is_in_maintenance(keys=self.maintenance_key)
    
    @maintaining.setter
    def maintaining(self, value: bool):
        """
        Sets the model to maintenance mode
        """
        return modes.maintenance_mode(
            value=value,
            keys=self.maintenance_key,
            timeout=self.get_maintenance_timeout(),
            blocking=self.blocking_maintenance_cache(),
        )

class MaintenanceModePageMixin(MaintenanceModeMixin):
    """
    Mixin for Wagtail pages to enable maintenance mode
    """

    class Meta:
        abstract = True

    def serve_maintenance(self, request, *args, **kwargs):
        """
        Render the maintenance template
        """
        return self.maintenance_key.render(
            request=request,
            page=self,
            parent_context=self.get_context(request=request, *args, **kwargs),
        )

    def serve(self, request, *args, **kwargs):
        if self.maintaining:
            return self.serve_maintenance(request, *args, **kwargs)
        return super().serve(request, *args, **kwargs)
    
