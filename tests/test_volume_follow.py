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


@pytest.mark.parametrize("mode,base", [("master", 0.4), ("group", 0.6)])
@pytest.mark.parametrize("offset", [-100, -10, 10, 100])
async def test_tv_follow_switch_applies_live_and_after_reference_changes(room, mode, base, offset):
    members = ["media_player.living", "media_player.office"]
    source(room, volume=0.4, members=members, source="TV")
    source(room, "media_player.office", 0.8, members)
    room.config.update(tv_volume_offset=offset, tv_offset_follow=False)
    await enter(room, mode)
    assert room.playback_volume == base
    assert not room.tv_volume_active
    room.apply_settings({**room.config, "tv_offset_follow": True})
    await room.hass.async_block_till_done()
    assert room.playback_volume == round(max(0, min(1, base + offset / 100)), 2)
    assert room.tv_volume_active
    room.apply_settings({**room.config, "tv_offset_follow": False})
    await room.hass.async_block_till_done()
    assert room.playback_volume == base
    assert not room.tv_volume_active
    source(room, volume=0.2, members=members, source="TV")
    await room.hass.async_block_till_done()
    assert room.playback_volume == (0.2 if mode == "master" else 0.5)
    assert room.volume == 0.3
    assert sum(c.args[0] == "join" for c in room.service.call_args_list) == 1
    assert all(
        c.args[0] == "join" or not c.kwargs.get("entity") for c in room.service.call_args_list
    )


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("mode", ["room", "master", "group"])
async def test_tv_follow_switch_leaves_music_and_room_offset_behavior(room, enabled, mode):
    source(room, volume=0.4, source="AirPlay")
    room.config.update(tv_volume_offset=-10, tv_offset_follow=enabled)
    await enter(room, mode)
    assert room.playback_volume == (0.3 if mode == "room" else 0.4)
    assert not room.tv_volume_active
    # A new TV visit must apply the offset in room mode even with the switch off.
    room.config["off_delay"] = 0
    room.hass.states.async_set("binary_sensor.pir", "off")
    await asyncio.sleep(0.02)
    await room.hass.async_block_till_done()
    assert not room.managed
    source(room, volume=0.4, source="TV")
    room.hass.states.async_set("binary_sensor.pir", "on")
    await room.hass.async_block_till_done()
    assert room.playback_volume == (0.2 if mode == "room" else 0.3 if enabled else 0.4)
    assert room.tv_volume_active == (mode == "room" or enabled)


@pytest.mark.parametrize("mode", ["master", "group"])
async def test_tv_follow_switch_during_fade_resynchronizes(room, mode):
    source(room, volume=0.4, source="TV")
    room.config.update(volume_mode=mode, tv_volume_offset=-10, fade_seconds=0.06)
    await room.async_start()
    room.hass.states.async_set("binary_sensor.pir", "on")
    await asyncio.sleep(0.02)
    room.apply_settings({**room.config, "tv_offset_follow": False})
    await room.hass.async_block_till_done()
    assert room.playback_volume == 0.4
    assert room.hass.states.get(room.player).attributes["volume_level"] == 0.4
    assert not room.tv_volume_active


def manual_volume(room, volume):
    state = room.hass.states.get(room.player)
    room.hass.states.async_set(room.player, "playing", {**state.attributes, "volume_level": volume})


@pytest.mark.parametrize("mode", ["master", "group"])
@pytest.mark.parametrize("destination_first", [False, True])
async def test_airplay_group_adjustment_is_not_lowered_to_stale_reference(
    room, mode, destination_first
):
    members = ["media_player.living", "media_player.office"]
    source(room, volume=0.2, members=members, source="AirPlay")
    source(room, "media_player.office", 0.4, members)
    await enter(room, mode)
    before = room.service.call_count
    # iPhone raises all levels; HA gets separate reports, with an old member
    # value briefly lowering the average relative to the new destination level.
    if destination_first:
        manual_volume(room, 0.45)
    source(room, volume=0.3, members=members, source="AirPlay")
    await asyncio.sleep(0.02)
    if not destination_first:
        manual_volume(room, 0.45)
    source(room, "media_player.office", 0.5, members)
    await room.hass.async_block_till_done()
    assert room.hass.states.get(room.player).attributes["volume_level"] == 0.45
    assert room.service.call_count == before
    source(room, volume=0.35, members=members, source="AirPlay")
    manual_volume(room, 0.55)
    await room.hass.async_block_till_done()
    assert room.hass.states.get(room.player).attributes["volume_level"] == 0.55
    assert room.service.call_count == before
    assert room.manual_volume_active
    assert room.playback_volume == 0.55
    assert room.volume == 0.3


@pytest.mark.parametrize("mode", ["room", "master", "group"])
async def test_manual_volume_during_fade_stops_automatic_writes(room, mode):
    source(room, volume=0.4, source="AirPlay")
    room.config.update(volume_mode=mode, fade_seconds=0.12)
    await room.async_start()
    room.hass.states.async_set("binary_sensor.pir", "on")
    await asyncio.sleep(0.03)
    manual_volume(room, 0.73)
    before = room.service.call_count
    await room.hass.async_block_till_done()
    assert room.hass.states.get(room.player).attributes["volume_level"] == 0.73
    assert room.service.call_count == before
    assert room.playback_volume == 0.73
    assert room.startup_error is None


async def test_manual_override_ends_on_next_visit_and_explicit_setting_change(room):
    source(room, volume=0.4, source="TV")
    await enter(room, "master")
    manual_volume(room, 0.65)
    await room.hass.async_block_till_done()
    assert room.manual_volume_active
    room.apply_settings({**room.config, "tv_volume_offset": -10})
    await room.hass.async_block_till_done()
    assert not room.manual_volume_active
    assert room.playback_volume == 0.3
    manual_volume(room, 0.75)
    await room.hass.async_block_till_done()
    room.config["off_delay"] = 0
    room.hass.states.async_set("binary_sensor.pir", "off")
    await asyncio.sleep(0.02)
    await room.hass.async_block_till_done()
    assert not room.managed
    room.hass.states.async_set("binary_sensor.pir", "on")
    await room.hass.async_block_till_done()
    assert not room.manual_volume_active
    assert room.playback_volume == 0.3


async def test_manual_zero_stays_silent_while_source_changes(room):
    source(room, volume=0.4)
    await enter(room, "master")
    manual_volume(room, 0)
    await room.hass.async_block_till_done()
    before = room.service.call_count
    source(room, volume=0.6)
    await room.hass.async_block_till_done()
    assert room.playback_volume == 0
    assert room.service.call_count == before


async def test_tv_follow_switch_persists_on_room_device(room):
    from custom_components.sonos_follow_me.room import Room
    from custom_components.sonos_follow_me.switch import TVOffsetFollowSwitch

    def save(entry, *, options):
        entry.options = options
        room.apply_settings(options)

    room.hass.config_entries.async_update_entry = Mock(side_effect=save)
    switch = TVOffsetFollowSwitch(room)
    assert switch.is_on
    assert switch.device_info["identifiers"] == {("sonos_follow_me", room.entry.entry_id)}
    await switch.async_turn_off()
    restored = Room(room.hass, room.entry)
    assert restored.config["tv_offset_follow"] is False
    assert room.entry.options["player"] == room.player
    await switch.async_turn_on()
    assert room.entry.options["tv_offset_follow"] is True


@pytest.mark.parametrize("mode", ["master", "group"])
async def test_airplay_coordinator_change_suspends_following_before_destination_report(room, mode):
    source(room, volume=0.2, source="AirPlay")
    await enter(room, mode)
    before = room.service.call_count
    source(room, volume=0.3, source="AirPlay")
    await room.hass.async_block_till_done()
    # Even if the destination takes longer than the settle time to report,
    # no competing volume command is sent to AirPlay.
    assert room.service.call_count == before
    assert room.manual_volume_active
    manual_volume(room, 0.35)
    await room.hass.async_block_till_done()
    assert room.playback_volume == 0.35
    assert room.service.call_count == before


async def test_manual_zero_during_fade_stops_remaining_steps(room):
    source(room, volume=0.4)
    room.config.update(volume_mode="master", fade_seconds=0.2)
    await room.async_start()
    room.hass.states.async_set("binary_sensor.pir", "on")
    async with asyncio.timeout(1):
        while room.hass.states.get(room.player).attributes["volume_level"] <= 0:
            await asyncio.sleep(0.001)
        await asyncio.sleep(0)
        manual_volume(room, 0)
    await room.hass.async_block_till_done()
    assert room.manual_volume_active
    assert room.hass.states.get(room.player).attributes["volume_level"] == 0


@pytest.mark.parametrize("endpoint", ["source", "destination"])
@pytest.mark.parametrize("invalid_state", ["unavailable", "playing"])
async def test_recovered_volume_does_not_latch_manual_priority(room, endpoint, invalid_state):
    source(room, volume=0.4, source="AirPlay")
    await enter(room, "master")
    entity = "media_player.living" if endpoint == "source" else room.player
    attrs = dict(room.hass.states.get(entity).attributes)
    attrs.pop("volume_level")
    room.hass.states.async_set(entity, invalid_state, attrs)
    await room.hass.async_block_till_done()
    room.hass.states.async_set(entity, "playing", {**attrs, "volume_level": 0.6})
    await room.hass.async_block_till_done()
    assert not room.manual_volume_active
    if endpoint == "source":
        assert room.playback_volume == 0.6
