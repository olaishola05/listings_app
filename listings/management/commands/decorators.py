import time
from functools import wraps
from typing import Callable

from django.core.exceptions import ValidationError

from alx_travel_app.listings.management.commands.seed import logger


def timer(func: Callable) -> Callable:
    """Decorator to time function execution."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.info(f"{func.__name__} executed in {end_time - start_time:.2f} seconds")
        return result
    return wrapper


def async_timer(func: Callable) -> Callable:
    """Decorator to time async function execution."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        logger.info(f"{func.__name__} executed in {end_time - start_time:.2f} seconds")
        return result
    return wrapper


def retry(max_attempts: int = 3, delay: float = 1.0):
    """Decorator to retry function execution on failure."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        logger.error(f"{func.__name__} failed after {max_attempts} attempts: {str(e)}")
                        raise
                    logger.warning(f"{func.__name__} attempt {attempt + 1} failed: {str(e)}. Retrying...")
                    time.sleep(delay * (2 ** attempt))
        return wrapper
    return decorator


def validate_data(validation_func: Callable):
    """Decorator to validate data before processing."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not validation_func(*args, **kwargs):
                raise ValidationError(f"Data validation failed for {func.__name__}")
            return func(*args, **kwargs)
        return wrapper
    return decorator
