"""Sonos Follow Me integration."""

from homeassistant.const import Platform

from .const import DEFAULTS
from .dashboard import async_setup_dashboard
from .room import Room

PLATFORMS = [Platform.SWITCH, Platform.BINARY_SENSOR, Platform.NUMBER, Platform.SELECT]


async def async_setup(hass, config):
    """Serve and load the bundled card once per integration, including YAML dashboards."""
    await async_setup_dashboard(hass)
    return True


async def async_setup_entry(hass, entry):
    """Start one room controller."""
    room = entry.runtime_data = Room(hass, entry)
    await room.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload))
    return True


async def async_reload(hass, entry):
    """Apply public settings live; reload only changed room wiring."""
    config = {**DEFAULTS, **(entry.options or entry.data)}
    room = entry.runtime_data
    if any(
        config[key] != room.config[key]
        for key in ("name", "player", "primary", "secondary", "sources")
    ):
        await hass.config_entries.async_reload(entry.entry_id)
    else:
        room.apply_settings(config)


async def async_unload_entry(hass, entry):
    """Stop timers and listeners."""
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.async_stop()
        return True
    return False
