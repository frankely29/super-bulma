import time
import functools
from datetime import datetime

def retry(exceptions: tuple, tries: int = 3, delay: float = 1.0):
    """
    Decorator to retry a function up to `tries` times with `delay` seconds between.
    Usage:
        @retry((ValueError, IOError), tries=5, delay=2)
        def unstable_func(...):
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for _ in range(tries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    time.sleep(delay)
            # final attempt, let exception propagate
            return func(*args, **kwargs)
        return wrapper
    return decorator

def format_timestamp(ts: int) -> str:
    """
    Converts a UNIX timestamp (seconds) to ISO 8601 UTC string.
    """
    return datetime.utcfromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%SZ")
