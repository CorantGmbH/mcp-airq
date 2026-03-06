"""Error handling utilities for MCP tool functions."""

import functools
from collections.abc import Callable

import aiohttp
from aioairq.exceptions import InvalidAirQResponse, InvalidAuth

# APIAccessDenied is not re-exported from aioairq top-level
from aioairq.core import APIAccessDenied


def handle_airq_errors(fn: Callable) -> Callable:
    """Decorator that catches aioairq and network exceptions,
    returning user-friendly error strings instead of crashing.
    """

    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except ValueError as exc:
            return f"Configuration error: {exc}"
        except InvalidAuth:
            return "Authentication failed. Check the device password."
        except APIAccessDenied:
            return (
                "API access denied. This feature requires an air-Q Science edition."
            )
        except InvalidAirQResponse as exc:
            return f"Unexpected response from device: {exc}"
        except aiohttp.ClientError as exc:
            return f"Network error: {type(exc).__name__}: {exc}"
        except TimeoutError:
            return (
                "Request timed out. Check that the device is on the same "
                "network and powered on."
            )

    return wrapper
