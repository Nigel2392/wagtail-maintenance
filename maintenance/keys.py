from django.utils.translation import gettext_lazy as _
from django.core.cache import cache
from django.shortcuts import render

from .settings import (
    MAINTENANCE_MODE_TEMPLATE_IGNORE_PATHS,
    MAINTENANCE_MODE_TEMPLATE,
    REFRESH_DELAY,
    BAD_STATUS,
)


MINUTE = 60
HOUR = MINUTE * 60
DAY = HOUR * 24
WEEK = DAY * 7
MONTH = DAY * 30


class Key(str):
    """
        A class that represents a key that is used to determine if maintenance mode is active
        Inherits from string to allow for transparent use in cache.get and cache.set
    """
    status_class = None

    def __new__(cls, value: str, label: str = None, help_text: str = None, timeout: int = MONTH, maintenance_template: str = None, order: int = 0):
        obj = super().__new__(cls, value)
        obj._label = label
        obj._help_text = help_text
        obj._timeout = timeout
        obj._maintenance_template = maintenance_template
        obj._order = order
        return obj
    
    def __repr__(self):
        return f"<{self.__class__.__name__}: {self}>"
    
    def get_status_class(self):
        """
            Return the status class to use for this key
        """
        status_class = getattr(self, "status_class") 
        if not status_class:
            status_class = Status
        return status_class

    def get_context(self, request=None, parent_context=None, **kwargs):
        """
            Return the context to use for the maintenance mode template
        """
        context = {}
        if parent_context:
            context.update(parent_context)

        context.update(kwargs)
        context.update({
            "request": request,
            "refresh": REFRESH_DELAY,
            "self": self,
        })

        return kwargs
    
    def get_template(self, request=None):
        """
            Return the django template to use for this key
        """
        return self._maintenance_template or MAINTENANCE_MODE_TEMPLATE
    
    def render(self, request, parent_context=None, **kwargs):
        """
            Render the maintenance mode template for this key
        """
        return render(
            request, 
            self.get_template(request=request),
            self.get_context(request=request, parent_context=parent_context, **kwargs),
            status=BAD_STATUS,
        )
    
    @property
    def order(self):
        """
            Ordering when checking for currently active keys
            The higher the number, the later it will be checked
        """
        return self._order

    @property
    def is_maintenance(self):
        """
            Returns True if the key is in maintenance mode
            Directly checks the cache
        """
        return cache.get(self, False)
    
    @property
    def label(self):
        """
            Return the user friendly label for this key
        """
        return self._label
    
    @property
    def help_text(self):
        """
            Help text to explain the purpose of this key
        """
        return self._help_text
    
    @property
    def timeout(self):
        """
            When will this key expire from the cache
        """
        return self._timeout
    
    def json(self, value=None):
        """
            Return a dictionary representation of this key
            This will be shown to users with the maintenance.see_info permission in the ping view
        """
        return {
            "value": value if value is not None else self.is_maintenance,
            "order": self.order,
            "label": self.label,
            "help_text": self.help_text,
            "timeout": self.timeout,
        }
    

MAINTENANCE_MODE_KEY = Key(
    "DJANGO_MAINTENANCE_MODE.CACHE",
    label=_("General Maintenance Mode"),
    help_text=_("Enable general maintenance mode"),
    timeout=DAY,
)


class Status:
    def __init__(self, value: bool, key: str = MAINTENANCE_MODE_KEY, cached=None, request=None):
        self.value = value
        self._key = key
        self.cached = cached
        self.request = request

    def __bool__(self):
        return self.maintaining()

    @property
    def key(self):
        if isinstance(self._key, str):
            return Key(self._key)
        return self._key

    def maintaining(self):
        if self.request is None:
            return self.value
        
        path_lower = self.request.path.lower()
        invalid_path = any([
            path_lower.startswith(str(path)) 
            for path in MAINTENANCE_MODE_TEMPLATE_IGNORE_PATHS
        ])

        return self.value and not invalid_path

