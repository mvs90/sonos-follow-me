"""Latched room occupancy including the clear delay."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity

from .entity import RoomEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([RoomOccupancy(entry.runtime_data)])


class RoomOccupancy(RoomEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY

    def __init__(self, room):
        super().__init__(room, "occupancy")

    @property
    def is_on(self):
        return self.room.presence.occupied

    @property
    def extra_state_attributes(self):
        return {"managed_playback": self.room.managed, "sensor_mode": self.room.config["mode"]}
