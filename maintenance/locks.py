from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

try:
    from django_redis.cache import RedisCache
except ImportError:
    RedisCache = None

from threading import RLock
import logging

from .keys import (
    MAINTENANCE_MODE_KEY,
    MONTH,
)


logger = logging.getLogger(__name__)


_maintenance_locks = {}


class CacheLock:
    def __init__(self, key: str, timeout: int = MONTH, blocking=False, threading_blocking=True):
        self.key = key
        self.timeout = timeout
        self.blocking = blocking
        self.thread_locked = False
        self.threading_lock = None
        self.threading_blocking = threading_blocking

    def acquire(self, blocking=None):
        if blocking is not None:
            self.blocking = blocking

        if self.threading_lock is None:
            self.threading_lock = RLock()
            self.thread_locked = self.threading_lock.acquire(blocking=self.threading_blocking)
        else:
            raise RuntimeError("Lock is already acquired")
        
        _try_lock(self.key, timeout=self.timeout, blocking=self.blocking)

        return self.thread_locked
    
    def release(self):
        if self.thread_locked:
            _try_unlock(self.key)
            self.threading_lock.release()
            self.thread_locked = False
            self.threading_lock = None
        else:
            raise RuntimeError("Lock is not acquired")
        
    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

def _try_lock(updating: str = MAINTENANCE_MODE_KEY, timeout: int = MONTH, blocking=False):
    if RedisCache is not None:
        if isinstance(cache, RedisCache):
            if updating in _maintenance_locks:
                raise RuntimeError("Maintenance mode key is already locked")
            
            l = cache.lock(updating, timeout=timeout)
            is_locked = l.acquire(blocking=blocking)
            
            if not is_locked:
                raise RuntimeError("Maintenance mode key is already locked")
            
            _maintenance_locks[updating] = l

def _try_unlock(updating: str = MAINTENANCE_MODE_KEY):
    if RedisCache is not None:
        if isinstance(cache, RedisCache):
            if updating in _maintenance_locks:
                try:
                    _maintenance_locks[updating].release()
                    del _maintenance_locks[updating]
                except RuntimeError:
                    logger.exception("Unable to release cache lock")
                except KeyError:
                    pass



