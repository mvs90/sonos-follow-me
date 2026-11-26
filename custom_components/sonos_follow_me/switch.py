"""Enable or disable follow-me per room."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import EntityCategory

from .entity import RoomEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        [
            FollowMeSwitch(entry.runtime_data),
            VolumeResetSwitch(entry.runtime_data),
            TVOffsetFollowSwitch(entry.runtime_data),
        ]
    )


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
            "volume_mode": self.room.config["volume_mode"],
            "volume_reference": self.room._follow_source,
            "manual_volume_active": self.room.manual_volume_active,
            "tv_volume_active": self.room.tv_volume_active,
            "playback_target_volume": self.room.playback_volume,
            "vacant_since": self.room._vacant_since,
            "startup_error": self.room.startup_error,
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


class TVOffsetFollowSwitch(RoomEntity, SwitchEntity):
    """Choose whether followed TV volume includes the room's TV offset."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, room):
        super().__init__(room, "tv_offset_follow")

    @property
    def is_on(self):
        return self.room.config["tv_offset_follow"]

    async def async_turn_on(self, **kwargs):
        self.room.update_settings({"tv_offset_follow": True})

    async def async_turn_off(self, **kwargs):
        self.room.update_settings({"tv_offset_follow": False})
