from typing import Union
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _
from wagtail import hooks

try:
    from django_redis.cache import RedisCache
except ImportError:
    RedisCache = None

from .keys import (
    MAINTENANCE_MODE_KEY,
    MONTH,
    DAY,
    Status,
    Key,
)

from . import locks

import logging


logger = logging.getLogger("maintenance")


def get_maintenance_key_data(cached=None) -> dict:
    keys = get_keys()
    m = dict()

    if cached is None:
        cached = cache.get_many(keys)

    for k in keys:
        if hasattr(k, "json"):
            m[k] = k.json(
                value=cached.get(k, False)
            )
        else:
            m[k] = {
                "value": cached.get(k, False),
                "label": getattr(k, "label", k),
                "help_text": getattr(k, "help_text", ""),
                "order": getattr(k, "order", 0),
                "timeout": getattr(k, "timeout", 0),
            }
    return m


class Maintenance:
    def __init__(self, updating: str = MAINTENANCE_MODE_KEY, timeout: int = MONTH, lock_cache=False):
        self.updating = updating
        self.timeout = timeout
        self.initial = {}
        self.lock_cache = lock_cache
        self._entered = False

    def set(self, mode: bool, call_hooks=True):
        """
        Set the maintenance mode

        :param mode: True or False
        :return: None
        """
        if self._entered:
            _set(mode, self.updating, timeout=self.timeout, call_hooks=call_hooks)
        else:
            # Must lock cache
            maintenance_mode(mode, key=self.updating, timeout=self.timeout, blocking=self.lock_cache, call_hooks=call_hooks)

    def __enter__(self):
        if not self.updating:
            raise ValueError("Maintenance mode key must be specified")
        
        locks._try_lock(self.updating, timeout=self.timeout, blocking=self.lock_cache)
        self._entered = True
        
        self.initial = get_maintenance_dict()
        # _set(True, self.updating, timeout=self.timeout, call_hooks=True)

        self.set(True, call_hooks=False)

        for hook in hooks.get_hooks("maintenance.entering_maintenance"):
            hook(True)

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()
        locks._try_unlock(self.updating)
        self._entered = False

    def release(self):
        changed = get_maintenance_dict()
        keys_to_skip = []
        initial = self.initial.copy()
        for key, value in changed.items():
            if key == self.updating:
                continue

            if value and value != initial.get(key, False):
                # The value was changed while we were in maintenance mode
                # so we should not change it back
                keys_to_skip.append(key)

        for key in keys_to_skip:
            try:
                del initial[key]
            except KeyError:
                pass

        for key, value in initial.items():
            _set(value, key, timeout=self.timeout, call_hooks=False)

        self.set(False, call_hooks=False)
        
        for hook in hooks.get_hooks("maintenance.exiting_maintenance"):
            hook(False)


@hooks.register("maintenance.register_key")
def register_maintenance_mode_key():
    return MAINTENANCE_MODE_KEY

def get_keys() -> Union[list[str], list[Key]]:
    """
    Returns a list of keys that are used to determine if maintenance mode is active

    :return: list
    """
    keys = []

    for fn in hooks.get_hooks("maintenance.register_key"):
        res = fn()
        if res:
            if isinstance(res, str):
                keys.append(res)
            elif isinstance(res, (list, tuple)):
                keys.extend(list(res))
            else:
                raise ValueError("maintenance.register_key hook must return a string, list, or tuple")

    return keys


def get_maintenance_dict(keys=None) -> dict:
    if keys is None:
        keys = get_keys()
    return cache.get_many(keys) or {}


def maintain(updating: str = MAINTENANCE_MODE_KEY, timeout: int = MONTH, lock_cache=False) -> Maintenance:
    """
    Returns a context manager for (un)setting maintenance mode
    """
    return Maintenance(
        updating=updating,
        timeout=timeout,
        lock_cache=lock_cache,
    )


def is_in_maintenance(request=None, keys=None) -> Status:
    """
    Reports whether the maintenance mode is currently active
    Returns the first key with the lowest order that is in maintenance mode

    :return: True or False
    """

    if keys is None:
        keys = get_keys()

    if isinstance(keys, (str, Key)):
        keys = [keys]
    
    # Retrieve and sort the keys
    cached = cache.get_many(keys)
    max_order = max([getattr(key, "order", 0) for key in keys])
    keys = sorted(keys, key=lambda key: getattr(key, "order", max_order))

    # Check each key in order
    for key in keys:
        get_status_class = getattr(key, "get_status_class", lambda: Status)
        status_class = get_status_class()

        if cached.get(key, False):
            # This key is marked as in maintenance mode
            return status_class(True, key=key, cached=cached, request=request)
    
    # No keys are in maintenance mode
    return Status(False, key=None, cached=cached, request=request)

def maintenance_mode(mode: bool, key: str = MAINTENANCE_MODE_KEY, timeout: int = DAY, blocking=False, call_hooks=False):
    """
    Set the maintenance mode

    :param mode: True or False
    :return: None
    """

    try:
        # If cache allows for transactions we should lock.
        # this includes a threading lock to prevent multiple threads from
        # trying to mutate the global dict at the same time.
        if hasattr(cache, "lock"):
            l = locks.CacheLock(key, timeout=timeout, blocking=blocking)
            l.acquire()

        logger.info("Setting maintenance mode to %s", mode)

        _set(mode, key, timeout=timeout, call_hooks=call_hooks)

        # unlock if we locked
        if hasattr(cache, "lock"):
            l.release()
    except Exception as e:
        logger.exception("Failed to set maintenance mode to %s", mode)
        raise e

def unset_maintenance(key: str = MAINTENANCE_MODE_KEY):
    """
    Delete the maintenance mode

    :return: None
    """

    logger.info("Unsetting maintenance mode for %s", key)

    cache.delete(key)


def _set(mode: bool, key: str = MAINTENANCE_MODE_KEY, timeout: int = DAY, call_hooks=False):
    if call_hooks:
        in_maintenance = is_in_maintenance(keys=key)

        for hook in hooks.get_hooks("maintenance.changing_maintenance"):
            hook(in_maintenance, mode)


    cache.set(key, mode, timeout=timeout)
    if hasattr(cache, "persist") or (
        RedisCache is not None and isinstance(cache, RedisCache)
    ): 
        cache.persist(key)

    if call_hooks:

        if in_maintenance:
            logger.info("Exiting maintenance mode")
            if not mode:
                for hook in hooks.get_hooks("maintenance.exiting_maintenance"):
                    hook(in_maintenance)
            else:
                logger.info("Maintenance mode unchanged (already in maintenance mode)")
        else:
            if mode:
                logger.info("Entering maintenance mode")
                for hook in hooks.get_hooks("maintenance.entering_maintenance"):
                    hook(in_maintenance)

            else:
                logger.info("Maintenance mode unchanged (already not in maintenance mode)")

