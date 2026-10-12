"""Follow reference volumes without feedback, default resets or source writes."""

import asyncio
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest


@pytest.fixture(autouse=True)
def registry(room):
    room.hass.config_entries = SimpleNamespace(async_entries=Mock(return_value=[]))
    yield
    room.hass.config_entries = None


def source(room, entity="media_player.living", volume=0.2, members=None, **attributes):
    room.hass.states.async_set(
        entity,
        "playing",
        {"volume_level": volume, "group_members": members or [entity], **attributes},
    )


async def enter(room, mode):
    room.config["volume_mode"] = mode
    await room.async_start()
    room.hass.states.async_set("binary_sensor.pir", "on")
    await room.hass.async_block_till_done()


@pytest.mark.parametrize("mode,expected", [("master", 0.2), ("group", 0.4)])
async def test_follow_entry_and_nonconfigured_member_changes(room, mode, expected):
    members = ["media_player.living", "media_player.office"]
    source(room, members=members)
    source(room, "media_player.office", 0.6, members)
    await enter(room, mode)
    assert room.managed
    assert room.playback_volume == expected
    assert room.volume == 0.3
    source(room, "media_player.office", 0.8, members)
    await room.hass.async_block_till_done()
    assert room.playback_volume == (0.2 if mode == "master" else 0.5)
    source(room, volume=0.4, members=members)
    await room.hass.async_block_till_done()
    assert room.playback_volume == (0.4 if mode == "master" else 0.6)
    # Only join is addressed to the source. All volume commands target this room.
    assert all(
        c.args[0] == "join" or not c.kwargs.get("entity") for c in room.service.call_args_list
    )
    assert len(room.service.call_args_list) < 10


async def test_group_excludes_own_volume_and_other_active_followers(room):
    source(room, volume=0.4)
    await enter(room, "group")
    other = SimpleNamespace(player="media_player.other", managed=True, _fading=True)
    source(room, other.player, 0)
    with patch.object(
        room.hass.config_entries,
        "async_entries",
        return_value=[SimpleNamespace(runtime_data=other)],
    ):
        source(room, volume=0.4, members=["media_player.living", room.player, other.player])
        await room.hass.async_block_till_done()
        assert room.playback_volume == 0.4
        before = room.service.call_count
        state = room.hass.states.get(room.player)
        room.hass.states.async_set(
            room.player, "playing", {**state.attributes, "volume_level": 0.1}
        )
        source(room, other.player, 0.9)
        await room.hass.async_block_till_done()
        assert room.service.call_count == before
        assert room.volume == 0.3


@pytest.mark.parametrize("mode", ["master", "group"])
async def test_follow_ignores_cooldown_and_preserves_room_memory(room, mode):
    source(room, volume=0.45)
    room.config.update(volume_mode=mode, volume_reset=True, default_volume=0.9, volume_cooldown=0)
    room._vacant_since = 1
    room.hass.states.async_set("binary_sensor.pir", "on")
    room.evaluate()
    await room.hass.async_block_till_done()
    assert room.playback_volume == 0.45
    assert room.volume == 0.3
    assert room._vacant_since is None


@pytest.mark.parametrize("invalid", [None, float("nan"), 1.2])
async def test_missing_reference_waits_instead_of_using_default(room, invalid):
    source(room, volume=invalid)
    await enter(room, "master")
    assert not room.managed
    room.service.assert_not_called()
    assert "Source volume unavailable" in room.startup_error
    source(room, volume=0.25)
    await room.hass.async_block_till_done()
    assert room.managed
    assert room.playback_volume == 0.25


async def test_zero_reference_is_valid_and_does_not_unmute(room):
    source(room, volume=0)
    await enter(room, "master")
    assert room.playback_volume == 0
    assert not any(c.args[0] == "volume_mute" for c in room.service.call_args_list)


async def test_mode_switches_and_tv_offset_apply_live_without_rejoining(room):
    members = ["media_player.living", "media_player.office"]
    source(room, volume=0.4, members=members, source="TV")
    source(room, "media_player.office", 0.8, members)
    room.config["tv_volume_offset"] = -10
    await enter(room, "master")
    assert room.playback_volume == 0.3
    room.apply_settings({**room.config, "volume_mode": "group"})
    await room.hass.async_block_till_done()
    assert room.playback_volume == 0.5
    room.apply_settings({**room.config, "volume_mode": "room"})
    await room.hass.async_block_till_done()
    assert room.playback_volume == 0.2
    assert room.volume == 0.3
    assert sum(c.args[0] == "join" for c in room.service.call_args_list) == 1


async def test_new_coordinator_and_source_changes_during_fade(room):
    source(room, volume=0.2)
    room.config["fade_seconds"] = 0.06
    room.config["volume_mode"] = "master"
    await room.async_start()
    room.hass.states.async_set("binary_sensor.pir", "on")
    await asyncio.sleep(0.02)
    source(room, volume=0.5)
    await room.hass.async_block_till_done()
    assert room.playback_volume == 0.5
    state = room.hass.states.get(room.player)
    members = ["media_player.new_master", room.player]
    source(room, "media_player.new_master", 0.35, members)
    room.hass.states.async_set(
        room.player, "playing", {**state.attributes, "group_members": members}
    )
    await room.hass.async_block_till_done()
    assert room.playback_volume == 0.35
    await room.async_enable(False)
    before = room.service.call_count
    source(room, "media_player.new_master", 0.9, members)
    await room.hass.async_block_till_done()
    assert room.service.call_count == before


async def test_follow_stops_when_room_leaves(room):
    source(room, volume=0.4)
    room.config["off_delay"] = 0
    await enter(room, "master")
    room.hass.states.async_set("binary_sensor.pir", "off")
    await asyncio.sleep(0.02)
    await room.hass.async_block_till_done()
    assert not room.managed
    assert room.hass.states.get(room.player).attributes["volume_level"] == 0.3
    before = room.service.call_count
    source(room, volume=0.8)
    await room.hass.async_block_till_done()
    assert room.service.call_count == before
