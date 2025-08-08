import functools
import logging
from telegram.error import BadRequest, TimedOut, NetworkError

logger = logging.getLogger(__name__)

def safe_handler(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except (BadRequest, TimedOut, NetworkError) as e:
            logger.warning("Known telegram/network issue in %s: %s", func.__name__, e)
        except Exception:
            logger.exception("Unhandled error in %s", func.__name__)
    return wrapper
