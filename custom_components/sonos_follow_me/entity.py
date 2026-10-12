"""Shared room entity."""

from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo, Entity

from .const import DOMAIN, ROOM_VOLUME_FIELDS


class RoomEntity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, room, key):
        self.room = room
        self.key = key
        self._attr_unique_id = f"{room.entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, room.entry.entry_id)},
            entry_type=DeviceEntryType.SERVICE,
            name=room.config["name"],
            manufacturer="Sonos Follow Me",
            model="Virtual room",
        )

    @property
    def extra_state_attributes(self):
        return {"sonos_follow_me_room": self.room.entry.entry_id, "setting": self.key}

    async def async_added_to_hass(self):
        self._sync_visibility()
        self.room.listeners.add(self._updated)
        self.async_on_remove(lambda: self.room.listeners.discard(self._updated))

    def _sync_visibility(self):
        """Hide unused settings, preserving the user's own visibility choices."""
        if self.key not in ROOM_VOLUME_FIELDS:
            return
        registry = er.async_get(self.hass)
        entry = registry.async_get(self.entity_id)
        if not entry or entry.hidden_by == er.RegistryEntryHider.USER:
            return
        hidden = er.RegistryEntryHider.INTEGRATION if self.room.following_volume else None
        if entry.hidden_by != hidden:
            registry.async_update_entity(self.entity_id, hidden_by=hidden)

    def _updated(self):
        self._sync_visibility()
        self.async_write_ha_state()
