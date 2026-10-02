"""Enable or disable follow-me per room."""

from homeassistant.components.switch import SwitchEntity

from .entity import RoomEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([FollowMeSwitch(entry.runtime_data), VolumeResetSwitch(entry.runtime_data)])


class FollowMeSwitch(RoomEntity, SwitchEntity):
    def __init__(self, room):
        super().__init__(room, "enabled")

    @property
    def extra_state_attributes(self):
        return {
            **super().extra_state_attributes,
            "room_name": self.room.config["name"],
            "player": self.room.player,
            "primary": self.room.sensors[0],
            "secondary": self.room.sensors[1:],
            "sources": self.room.config["sources"],
            "remembered_volume": self.room.volume,
            "vacant_since": self.room._vacant_since,
        }

    @property
    def is_on(self):
        return self.room.enabled

    async def async_turn_on(self, **kwargs):
        await self.room.async_enable(True)

    async def async_turn_off(self, **kwargs):
        await self.room.async_enable(False)


class VolumeResetSwitch(RoomEntity, SwitchEntity):
    def __init__(self, room):
        super().__init__(room, "volume_reset")

    @property
    def is_on(self):
        return self.room.config["volume_reset"]

    async def async_turn_on(self, **kwargs):
        self.room.update_settings({"volume_reset": True})

    async def async_turn_off(self, **kwargs):
        self.room.update_settings({"volume_reset": False})
