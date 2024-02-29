from django import forms
from django.core.cache import cache
from wagtail.admin.widgets import SwitchInput
from wagtail import hooks

from . import modes, keys

class _MaintenanceModeForm(forms.Form):
    DEFAULT_TIMEOUT = modes.DAY

    def save(self, *args, **kwargs):
        d = modes.get_maintenance_dict()
        for key, value in self.cleaned_data.items():
            d[key] = value
            modes._set(value, key, timeout=self.DEFAULT_TIMEOUT, call_hooks=True)
        return d
    

def MaintenanceModeForm(*args, **kwargs):
    """
    Returns a form that can be used to set the maintenance mode
    """
    fields = {}
    help_texts = kwargs.pop("help_texts", {})
    labels = kwargs.pop("labels", {})
    
    _keys = modes.get_keys()
    
    for key in _keys:

        initial     = cache.get(key, False)
        label       = labels.get(key, getattr(key, "label", key))
        help_text   = help_texts.get(key, getattr(key, "help_text", ""))
        should_skip = False

        # Hook logic, can be used for permissions for example
        for fn in hooks.get_hooks("maintenance.form_fields"):
            # If the hook returns True, we should skip this field
            # We do not skip the main maintenance mode key
            should_skip = fn(key=key, is_active=initial, label=label, help_text=help_text) \
                is True and \
                key != keys.MAINTENANCE_MODE_KEY

            if should_skip:
                break

        # Check if we need to skip this field
        if should_skip:
            continue

        fields[key] = forms.BooleanField(
            required=False,
            initial=initial,
            label=label,
            help_text=help_text,\
            widget=SwitchInput,
        )

    return type("MaintenanceModeForm", (_MaintenanceModeForm,), fields)(*args, **kwargs)

