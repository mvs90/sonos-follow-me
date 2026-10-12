"""Sensor mode selection."""

from homeassistant.components.select import SelectEntity

from .const import VOLUME_MODES
from .entity import RoomEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([SensorMode(entry.runtime_data), VolumeMode(entry.runtime_data)])


class SensorMode(RoomEntity, SelectEntity):
    _attr_options = ["primary", "equal"]

    def __init__(self, room):
        super().__init__(room, "mode")

    @property
    def current_option(self):
        return self.room.config["mode"]

    async def async_select_option(self, option):
        self.room.update_settings({"mode": option})


class VolumeMode(RoomEntity, SelectEntity):
    _attr_options = VOLUME_MODES

    def __init__(self, room):
        super().__init__(room, "volume_mode")

    @property
    def current_option(self):
        return self.room.config["volume_mode"]

    async def async_select_option(self, option):
        self.room.update_settings({"volume_mode": option})
