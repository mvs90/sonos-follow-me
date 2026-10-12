"""In-memory players exposing real HA media services with controlled failures."""

import asyncio

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)

from . import DOMAIN


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    async_add_entities(
        [LabPlayer(hass.data[DOMAIN], key) for key in ("source", "destination", "member")]
    )


class LabPlayer(MediaPlayerEntity):
    _attr_should_poll = False
    _attr_supported_features = (
        MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.GROUPING
        | MediaPlayerEntityFeature.PAUSE
    )

    def __init__(self, lab, key):
        self.lab = lab
        self.key = key
        self._attr_name = f"Sonos Fault Lab {key.title()}"
        self._attr_unique_id = f"sonos_follow_me_lab_{key}"
        lab["entities"][key] = self
        self.reset()

    def reset(self):
        self.joined = False
        self._attr_volume_level = 0.2
        self._attr_is_volume_muted = False

    @property
    def state(self):
        if self.lab["source_playing"] and (
            self.key == "source"
            or self.joined
            or (self.key == "member" and self.lab["member_joined"])
        ):
            return MediaPlayerState.PLAYING
        return MediaPlayerState.PAUSED

    @property
    def source(self):
        return "TV" if self.lab["tv"] else "Music"

    @property
    def group_members(self):
        players = self.lab["entities"]
        if self.key == "member" and not self.lab["member_joined"]:
            return [self.entity_id]
        if self.key == "destination" and not self.joined:
            return [self.entity_id]
        keys = ["source"]
        if self.lab["member_joined"]:
            keys.append("member")
        if players["destination"].joined:
            keys.append("destination")
        return [players[k].entity_id for k in keys]

    @property
    def extra_state_attributes(self):
        return {"lab_simulated": True, "lab_calls": self.lab["calls"][-80:]}

    def record(self, action, value=None):
        self.lab["calls"].append({"player": self.key, "action": action, "value": value})

    async def async_set_volume_level(self, volume):
        self.record("volume_set", volume)
        if volume > 0 and self.key == "destination":
            if self.lab["always_zero"]:
                self.async_write_ha_state()
                return
            if self.lab["drop_positive"]:
                self.lab["drop_positive"] -= 1
                self.async_write_ha_state()
                return
        self._attr_volume_level = volume
        self.async_write_ha_state()

    async def async_mute_volume(self, mute):
        self.record("volume_mute", mute)
        if not self.lab["sticky_mute"]:
            self._attr_is_volume_muted = mute
        self.async_write_ha_state()

    async def async_join_players(self, group_members):
        destination = self.lab["entities"]["destination"]
        if self.key != "source" or group_members != [destination.entity_id]:
            raise ValueError("Lab grouping is confined to the two simulated players")
        self.record("join")
        if self.lab["never_join"]:
            return
        generation = self.lab["generation"]

        async def joined():
            await asyncio.sleep(self.lab["join_delay"])
            if self.lab["generation"] == generation:
                destination.joined = True
                destination.async_write_ha_state()
                self.async_write_ha_state()

        task = self.hass.async_create_task(joined())
        self.lab["tasks"].add(task)
        task.add_done_callback(self.lab["tasks"].discard)

    async def async_unjoin_player(self):
        self.record("unjoin")
        self.joined = False
        self.async_write_ha_state()
        self.lab["entities"]["source"].async_write_ha_state()

    async def async_media_pause(self):
        self.record("pause")
        self.joined = False
        self.async_write_ha_state()
