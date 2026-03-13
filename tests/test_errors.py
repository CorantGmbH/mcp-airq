"""Tests for the @handle_airq_errors decorator."""

import aiohttp
import pytest
from aioairq.core import APIAccessDenied
from aioairq.exceptions import InvalidAirQResponse, InvalidAuth

from mcp_airq.errors import handle_airq_errors


def make_failing_tool(exc):
    """Return a decorated async function that raises exc."""

    @handle_airq_errors
    async def tool():
        raise exc

    return tool


@pytest.mark.asyncio
async def test_handles_invalid_auth():
    result = await make_failing_tool(InvalidAuth())()
    assert "Authentication failed" in result


@pytest.mark.asyncio
async def test_handles_api_access_denied():
    result = await make_failing_tool(APIAccessDenied())()
    assert "API access denied" in result


@pytest.mark.asyncio
async def test_handles_invalid_airq_response():
    result = await make_failing_tool(InvalidAirQResponse("bad"))()
    assert "Unexpected response" in result


@pytest.mark.asyncio
async def test_handles_client_error():
    result = await make_failing_tool(aiohttp.ClientError())()
    assert "Network error" in result


@pytest.mark.asyncio
async def test_handles_timeout_error():
    result = await make_failing_tool(TimeoutError())()
    assert "timed out" in result.lower()


@pytest.mark.asyncio
async def test_handles_value_error():
    result = await make_failing_tool(ValueError("bad config"))()
    assert "Configuration error" in result
    assert "bad config" in result


@pytest.mark.asyncio
async def test_passes_through_return_value():
    @handle_airq_errors
    async def tool():
        return "ok"

    result = await tool()
    assert result == "ok"
