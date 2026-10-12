"""Serve the bundled card and register it with the dashboard resource loader."""

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.exceptions import HomeAssistantError
from homeassistant.loader import async_get_integration

from .const import DOMAIN

CARD_URL = "/sonos_follow_me/sonos-follow-me-card.js"
LOGO_URL = "/sonos_follow_me/follow-me-logo.png"
_LOGGER = logging.getLogger(__name__)


async def async_setup_dashboard(hass):
    """Use Lovelace's module loader, with a bootstrap-safe fallback for YAML resources."""
    frontend = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(CARD_URL, str(frontend / "sonos-follow-me-card.js"), False),
            StaticPathConfig(LOGO_URL, str(frontend / "follow-me-logo.png"), False),
        ]
    )
    integration = await async_get_integration(hass, DOMAIN)
    url = f"{CARD_URL}?v={integration.version}"
    resources = hass.data[LOVELACE_DATA].resources
    if isinstance(resources, ResourceStorageCollection):
        try:
            # Public API ensures persisted resources are loaded before checking for duplicates.
            await resources.async_get_info()
            existing = [
                item
                for item in resources.async_items()
                if item["url"].split("?", 1)[0].split("#", 1)[0] == CARD_URL
            ]
            values = {"url": url, "res_type": "module"}
            if existing:
                first, *duplicates = existing
                if first["url"] != url or first["type"] != "module":
                    await resources.async_update_item(first["id"], values)
                for duplicate in duplicates:
                    await resources.async_delete_item(duplicate["id"])
            else:
                await resources.async_create_item(values)
            return
        except (HomeAssistantError, OSError):
            _LOGGER.exception("Could not register dashboard resource; using frontend module loader")

    # YAML resource collections are read-only. The JS waits for HA's current element
    # registry before defining its classes, avoiding the early-extra-module race.
    add_extra_js_url(hass, url)
