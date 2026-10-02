"""Sonos Follow Me integration."""

from homeassistant.const import Platform

from .room import Room

PLATFORMS = [Platform.SWITCH, Platform.BINARY_SENSOR]


async def async_setup_entry(hass, entry):
    """Start one room controller."""
    room = entry.runtime_data = Room(hass, entry)
    await room.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload))
    return True


async def async_reload(hass, entry):
    """Reload after editing options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    """Stop timers and listeners."""
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.async_stop()
        return True
    return False
