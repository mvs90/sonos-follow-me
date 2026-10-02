"""Public room settings as ordinary Home Assistant number entities."""

from homeassistant.components.number import NumberEntity, NumberMode

from .entity import RoomEntity

# key, minimum, maximum, step, unit, conversion from internal value
SETTINGS = (
    ("default_volume", 0, 100, 1, "%", 100),
    ("volume_cooldown", 0, 10080, 1, "min", 1),
    ("off_delay", 0, 3600, 1, "s", 1),
    ("fade_seconds", 0, 30, 0.5, "s", 1),
)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([RoomNumber(entry.runtime_data, setting) for setting in SETTINGS])


class RoomNumber(RoomEntity, NumberEntity):
    _attr_mode = NumberMode.BOX

    def __init__(self, room, setting):
        key, minimum, maximum, step, unit, self.factor = setting
        super().__init__(room, key)
        self.key = key
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self):
        return self.room.config[self.key] * self.factor

    async def async_set_native_value(self, value):
        self.room.update_settings({self.key: value / self.factor})
