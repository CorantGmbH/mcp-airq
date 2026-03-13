"""Tests for write tools."""

from unittest.mock import AsyncMock, patch

import pytest

from mcp_airq.tools.write import (
    configure_network,
    set_brightness,
    set_device_name,
    set_led_theme,
    set_night_mode,
)


@pytest.fixture
def mock_airq():
    """Create a mock AirQ instance."""
    airq = AsyncMock()
    return airq


@pytest.mark.asyncio
async def test_set_device_name(mock_ctx, mock_airq):
    """set_device_name calls aioairq and returns confirmation."""
    with patch.object(mock_ctx.request_context.lifespan_context, "resolve", return_value=mock_airq):
        result = await set_device_name(mock_ctx, name="Wohnzimmer")
        assert "Wohnzimmer" in result
        mock_airq.set_device_name.assert_awaited_once_with("Wohnzimmer")


@pytest.mark.asyncio
async def test_set_led_theme_both_sides(mock_ctx, mock_airq):
    """set_led_theme with both sides."""
    with patch.object(mock_ctx.request_context.lifespan_context, "resolve", return_value=mock_airq):
        result = await set_led_theme(mock_ctx, left="CO2", right="Humidity")
        mock_airq.set_led_theme.assert_awaited_once_with({"left": "CO2", "right": "Humidity"})
        assert "CO2" in result


@pytest.mark.asyncio
async def test_set_led_theme_one_side(mock_ctx, mock_airq):
    """set_led_theme with only one side."""
    with patch.object(mock_ctx.request_context.lifespan_context, "resolve", return_value=mock_airq):
        await set_led_theme(mock_ctx, left="VOC")
        mock_airq.set_led_theme.assert_awaited_once_with({"left": "VOC"})


@pytest.mark.asyncio
async def test_set_led_theme_no_side(mock_ctx, mock_airq):
    """set_led_theme with no side returns error."""
    with patch.object(mock_ctx.request_context.lifespan_context, "resolve", return_value=mock_airq):
        result = await set_led_theme(mock_ctx)
        assert "Specify at least one" in result
        mock_airq.set_led_theme.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_night_mode_enable(mock_ctx, mock_airq):
    """set_night_mode enables with correct parameters."""
    with patch.object(mock_ctx.request_context.lifespan_context, "resolve", return_value=mock_airq):
        result = await set_night_mode(
            mock_ctx,
            activated=True,
            start_night="23:00",
            start_day="07:00",
            brightness_night=5.0,
        )
        assert "enabled" in result
        call_args = mock_airq.set_night_mode.call_args[0][0]
        assert call_args["activated"] is True
        assert call_args["start_night"] == "23:00"
        assert call_args["brightness_night"] == 5.0


@pytest.mark.asyncio
async def test_set_night_mode_disable(mock_ctx, mock_airq):
    """set_night_mode disables."""
    with patch.object(mock_ctx.request_context.lifespan_context, "resolve", return_value=mock_airq):
        result = await set_night_mode(mock_ctx, activated=False)
        assert "disabled" in result


@pytest.mark.asyncio
async def test_set_brightness(mock_ctx, mock_airq):
    """set_brightness sets day and night brightness."""
    with patch.object(mock_ctx.request_context.lifespan_context, "resolve", return_value=mock_airq):
        result = await set_brightness(mock_ctx, default=75.0, night=10.0)
        assert "75" in result
        assert "night" in result.lower()
        mock_airq.set_brightness_config.assert_awaited_once_with(default=75.0, night=10.0)


@pytest.mark.asyncio
async def test_configure_network_dhcp(mock_ctx, mock_airq):
    """configure_network with DHCP."""
    with patch.object(mock_ctx.request_context.lifespan_context, "resolve", return_value=mock_airq):
        result = await configure_network(mock_ctx, dhcp=True)
        assert "DHCP" in result
        mock_airq.set_ifconfig_dhcp.assert_awaited_once()


@pytest.mark.asyncio
async def test_configure_network_static(mock_ctx, mock_airq):
    """configure_network with static IP."""
    with patch.object(mock_ctx.request_context.lifespan_context, "resolve", return_value=mock_airq):
        result = await configure_network(
            mock_ctx,
            ip="192.168.1.50",
            subnet="255.255.255.0",
            gateway="192.168.1.1",
            dns="8.8.8.8",
        )
        assert "192.168.1.50" in result
        mock_airq.set_ifconfig_static.assert_awaited_once_with(
            "192.168.1.50", "255.255.255.0", "192.168.1.1", "8.8.8.8"
        )


@pytest.mark.asyncio
async def test_configure_network_static_incomplete(mock_ctx, mock_airq):
    """configure_network with missing static IP params."""
    with patch.object(mock_ctx.request_context.lifespan_context, "resolve", return_value=mock_airq):
        result = await configure_network(mock_ctx, ip="192.168.1.50")
        assert "provide all of" in result
        mock_airq.set_ifconfig_static.assert_not_awaited()
