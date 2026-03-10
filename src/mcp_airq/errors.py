"""Error handling utilities for MCP tool functions."""

import functools
import logging
from collections.abc import Callable

import aiohttp
from aioairq.exceptions import InvalidAirQResponse, InvalidAuth

# APIAccessDenied is not re-exported from aioairq top-level
from aioairq.core import APIAccessDenied

logger = logging.getLogger(__name__)


def handle_airq_errors(fn: Callable) -> Callable:
    """Decorator that catches aioairq and network exceptions,
    returning user-friendly error strings instead of crashing.
    """

    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except ValueError as exc:
            logger.debug("Configuration error in %s: %s", fn.__name__, exc)
            return f"Configuration error: {exc}"
        except InvalidAuth:
            logger.warning("Authentication failed in %s", fn.__name__)
            return "Authentication failed. Check the device password."
        except APIAccessDenied:
            logger.warning("API access denied in %s", fn.__name__)
            return "API access denied. This feature requires an air-Q Science edition."
        except InvalidAirQResponse as exc:
            logger.error("Invalid response in %s: %s", fn.__name__, exc, exc_info=True)
            return f"Unexpected response from device: {exc}"
        except aiohttp.ClientError as exc:
            logger.error("Network error in %s: %s", fn.__name__, exc, exc_info=True)
            return f"Network error: {type(exc).__name__}: {exc}"
        except TimeoutError:
            logger.warning("Timeout in %s", fn.__name__)
            return (
                "Request timed out. Check that the device is on the same "
                "network and powered on."
            )

    return wrapper
