"""Shared room entity."""

from homeassistant.helpers.entity import DeviceInfo, Entity

from .const import DOMAIN


class RoomEntity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, room, key):
        self.room = room
        self._attr_unique_id = f"{room.entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, room.entry.entry_id)},
            name=room.config["name"],
            manufacturer="Sonos Follow Me",
            model="Virtual room",
        )

    async def async_added_to_hass(self):
        self.room.listeners.add(self.async_write_ha_state)
        self.async_on_remove(lambda: self.room.listeners.discard(self.async_write_ha_state))
