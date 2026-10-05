"""Independent simulated presence inputs, unrelated to physical room helpers."""

from homeassistant.components.binary_sensor import BinarySensorEntity

from . import DOMAIN


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    async_add_entities([LabSensor(hass.data[DOMAIN], key) for key in ("pir", "radar")])


class LabSensor(BinarySensorEntity):
    _attr_should_poll = False

    def __init__(self, lab, key):
        self.lab = lab
        self.key = key
        self._attr_name = f"Sonos Fault Lab {key.upper()}"
        self._attr_unique_id = f"sonos_follow_me_lab_{key}"
        self._attr_extra_state_attributes = {"lab_simulated": True}
        lab["entities"][key] = self

    @property
    def is_on(self):
        return self.lab[self.key]
