maintenance
===========

Wagtail maintenance mode support for easily managing available routes when in maintenance mode.

### Features

* Easily manage maintenance mode from the Wagtail admin.
* Different keys for different types of maintenance.
* Realtime updates for maintenance mode with websockets.
* No database required - purely from cache.
* Customizable maintenance mode page.
* Extra functionality for `django_redis`
   - Persisting the maintenance mode key in the cache.
   - Locking the cache for the maintenance mode key.


Quick start
-----------

1. Add 'maintenance' to your INSTALLED_APPS setting like this:

   ```
   INSTALLED_APPS = [   
      ...,
      'maintenance',
   ]
   ```
2. Add `maintenance.middleware.MaintenanceModeMiddleware` to your middleware settings.
3. Navigate to settings in your wagtail admin menu; enjoy the new maintenance mode settings.

General usage
-----------

### Permissions

* `maintenance.toggle_maintenance_mode`
   Can toggle maintenance mode on/off.

* `maintenance.see_menu_item`
   Can see the maintenance mode menu item.

* `maintenance.see_info`
   Can see extra maintenance mode information, defined by the key in the `maintenance.views.ping` view.

### Modes reference

`maintenance.modes`  
A mode is just a plain string, which is used to identify the type of maintenance mode.
We provide a single default mode which can be used for general maintenance.


#### `def maintain(updating: str = MAINTENANCE_MODE_KEY, timeout: int = MONTH, lock_cache=False) -> Maintenance:`

Return a maintenance mode context manager for the given key.  
This can be used to set/unset maintenance.  
It is possible to use the `with` statement to automatically unset the maintenance mode after the block.  
You are generally able to provide `str` and `maintenance.keys.Key` instances to the `key` parameter.

Example:

```python
from maintenance.modes import maintain

with modes.maintain():
    # Do some long running operations which should not be interrupted by users.
    pass
```

#### `def is_in_maintenance(request=None, keys=None) -> Status:`

Check if the maintenance mode is active for the given request and keys.
If no keys are provided, check all registered keys for maintenance mode.

#### `def maintenance_mode(mode: bool, key: str = MAINTENANCE_MODE_KEY, timeout: int = DAY, blocking=False, call_hooks=False):`

Set or unset the maintenance mode for the given key.
`blocking` is directly passed to `threading.Lock.acquire` and django_redis's cache `Lock.acquire` method.

#### `def unset_maintenance(key: str = MAINTENANCE_MODE_KEY):`

Delete any record of maintenance mode, active or not from the cache for this key.

Maintenance mode "keys"
-----------

We provide different "keys" for maintenance mode.
Keys can be considered as a unique identifier for a specific type of maintenance.

```python
from maintenance import modes, keys

class MyStatusClass(keys.Status):
   """Custom status class to check if the maintenance mode is active for the request."""

    def maintaining(self):
        if self.request is None:
            return self.value
    
        return self.value \
         and not self.request.path.startswith("/maintenance/cannot/happen/here/")

class MyKey(keys.Key):
    status_class = PriorityStatusClass

my_key = MyKey(
    "my_maintenance_key", 
    label=_("My maintenance mode"), 
    help_text=_("This will be automatically triggered when importing/exporting."), 
    timeout=modes.DAY,
)
```

Then register it with wagtail hooks:

```python
from wagtail import hooks

@hooks.register('maintenance.register_key')
def register_maintenance_mode_key():
    return my_key
```

### Key Reference

#### `def get_status_class(self):`

Return the status class for this key.
This is used to check if the maintenance mode is active for the request.

#### `def get_context(self, request=None, parent_context=None, **kwargs):`

Get the context for the maintenance mode template.
This is used to render the maintenance mode page when the key is marked as active.

#### `def get_template(self, request=None):`

Return the template for the maintenance mode page.

#### `def render(self, request, parent_context=None, **kwargs):`

Render the maintenance mode page.
This is only called if this key is the first active key in the ordered list of keys.
If there is another key active before this key, the other key will be used to render the maintenance mode page.

#### `def json(self, value=None):`

Return the json representation of this key.
This will be used to give extra information about the key to people who have permissions for it, on the `maintenance.views.ping` view.

#### `def order(self):`

Return the order of this key as it should be checked for rendering.

#### (property) `def is_maintenance(self):`

Return if the maintenance mode is active for this key.
Directly fetches from cache to refresh the status.

#### (property) `def label(self):`

Label as it should be displayed in the Wagtail admin.

#### (property) `def help_text(self):`

Help text to give more information about this key in the Wagtail admin.

#### (property) `def timeout(self):`

Timeout for this key.
This is used to automatically disable the maintenance mode after a certain time.


Settings
-----------

### IS_ASGI

Are you running an ASGI application with channels and asigref installed?
We provide a websocket consumer to notify the client of the maintenance mode in realtime.

### MAINTENANCE_MODE_BAD_STATUS

This is the status code which is returned when the maintenance mode is active.

### MAINTENANCE_MODE_TEMPLATE

The default template used to render the maintenance mode page.
Keys can individually override this.

### MAINTENANCE_MENU_ITEM_HOOK_NAME

To which menu do you want to register the maintenance mode menu item?
Example:

```python
MAINTENANCE_MENU_ITEM_HOOK_NAME = 'register_settings_menu_item'
```

### MAINTENANCE_URL_FUNC

The import path of the function which returns the maintenance websocket url.

By default hardcoded to return `/ws/maintenance/ping/`.

### MAINTENANCE_MODE_TEMPLATE_IGNORE_PATHS

A list of paths which should not be affected by the maintenance mode.
We will check by converting the request.path to lower case and check if it starts with any path in the list.
Keys can individually override this.
