"""Sonos Follow Me integration."""

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import Platform

from .const import DEFAULTS
from .room import Room

PLATFORMS = [Platform.SWITCH, Platform.BINARY_SENSOR, Platform.NUMBER, Platform.SELECT]
CARD_URL = "/sonos_follow_me/sonos-follow-me-card.js"
LOGO_URL = "/sonos_follow_me/follow-me-logo.png"


async def async_setup(hass, config):
    """Serve and load the bundled card once per integration, including YAML dashboards."""
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                CARD_URL, str(Path(__file__).parent / "frontend" / "sonos-follow-me-card.js"), False
            ),
            StaticPathConfig(
                LOGO_URL, str(Path(__file__).parent / "frontend" / "follow-me-logo.png"), False
            ),
        ]
    )
    add_extra_js_url(hass, f"{CARD_URL}?v=0.4.0")
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
