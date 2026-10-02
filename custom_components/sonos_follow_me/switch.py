"""Enable or disable follow-me per room."""

from homeassistant.components.switch import SwitchEntity

from .entity import RoomEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([FollowMeSwitch(entry.runtime_data)])


class FollowMeSwitch(RoomEntity, SwitchEntity):
    def __init__(self, room):
        super().__init__(room, "enabled")

    @property
    def is_on(self):
        return self.room.enabled

    async def async_turn_on(self, **kwargs):
        await self.room.async_enable(True)

    async def async_turn_off(self, **kwargs):
        await self.room.async_enable(False)
