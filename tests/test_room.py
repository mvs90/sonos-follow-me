import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.sonos_follow_me.room import Room

CONFIG = dict(
    name="Bathroom",
    player="media_player.bath",
    primary="binary_sensor.pir",
    secondary=["binary_sensor.radar"],
    sources=["media_player.living", "media_player.kitchen"],
    mode="primary",
    off_delay=15,
    fade_seconds=0,
    volume=0.3,
)


@pytest.fixture
async def room(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    entry = SimpleNamespace(data=CONFIG, options={}, entry_id="test")
    room = Room(hass, entry)
    room._store = Mock(async_load=AsyncMock(return_value={}), async_save=AsyncMock())
    for entity, value, attrs in [
        ("binary_sensor.pir", "off", {}),
        ("binary_sensor.radar", "off", {}),
        ("media_player.bath", "paused", {"volume_level": 0.3}),
        ("media_player.living", "playing", {"group_members": ["media_player.living"]}),
        ("media_player.kitchen", "playing", {"group_members": ["media_player.kitchen"]}),
    ]:
        hass.states.async_set(entity, value, attrs)
    room.service = AsyncMock()
    yield room
    await room.async_stop()
    await hass.async_stop()


async def settle(room):
    await asyncio.sleep(0)
    if room._task:
        await room._task


async def test_no_radar_trigger_and_primary_join(room):
    room.hass.states.async_set("binary_sensor.radar", "on")
    room.evaluate()
    await settle(room)
    room.service.assert_not_called()
    room.hass.states.async_set("binary_sensor.pir", "on")
    room.evaluate()
    await settle(room)
    room.service.assert_any_await(
        "join", entity="media_player.living", group_members=["media_player.bath"]
    )
    assert room.managed
    assert sum(c.args[0] == "join" for c in room.service.call_args_list) == 1


async def test_hold_and_clear_timer_cancellation(room):
    room.presence.occupied = True
    room.managed = True
    room.hass.states.async_set("binary_sensor.radar", "on")
    room.evaluate()
    assert room._timer is None
    room.hass.states.async_set("binary_sensor.radar", "off")
    room.evaluate()
    assert room._timer is not None
    timer = room._timer
    room.evaluate()
    assert room._timer is timer
    room.hass.states.async_set("binary_sensor.radar", "on")
    room.evaluate()
    assert room._timer is None
    room._expired(None)
    room.service.assert_not_called()


async def test_departure_unjoins_pauses_restores(room):
    room.managed = True
    room.presence.occupied = True
    room._expired(None)
    await settle(room)
    assert [c.args[0] for c in room.service.call_args_list] == [
        "volume_set",
        "unjoin",
        "media_pause",
        "volume_set",
    ]
    assert not room.managed
    assert not room.presence.occupied
    assert room.service.call_args_list[-1].kwargs["volume_level"] == 0.3


async def test_manual_source_is_not_stopped(room):
    room.hass.states.async_set(room.player, "playing", {"volume_level": 0.4})
    await room._enter()
    await room._leave()
    room.service.assert_not_called()


async def test_no_source_does_not_mute(room):
    room.config["sources"] = ["media_player.missing"]
    await room._enter()
    room.service.assert_not_called()


async def test_coordinator_is_not_unjoined(room):
    room.managed = True
    room.hass.states.async_set(
        room.player, "playing", {"group_members": [room.player, "media_player.other"]}
    )
    await room._leave()
    room.service.assert_not_called()


async def test_join_failure_restores_volume(room):
    async def action(name, **kwargs):
        if name == "join":
            raise HomeAssistantError("offline")

    room.service.side_effect = action
    with pytest.raises(HomeAssistantError):
        await room._enter()
    assert not room.managed
    assert room.service.call_args_list[-1].kwargs["volume_level"] == 0.3


async def test_return_during_fade_aborts_departure(room):
    room.managed = True
    room.config["fade_seconds"] = 1

    async def action(name, **kwargs):
        if name == "volume_set":
            room.hass.states.async_set("binary_sensor.pir", "on")

    room.service.side_effect = action
    await room._leave()
    assert room.managed
    assert all(call.args[0] != "unjoin" for call in room.service.call_args_list)


async def test_disabled_room_never_acts(room):
    await room.async_enable(False)
    room.hass.states.async_set("binary_sensor.pir", "on")
    room.evaluate()
    await settle(room)
    room.service.assert_not_called()


async def test_listener_starts_on_primary_event(room):
    with patch("custom_components.sonos_follow_me.room.async_track_state_change_event") as track:
        await room.async_start()
        event = SimpleNamespace(data={"entity_id": "binary_sensor.pir"})
        room.hass.states.async_set("binary_sensor.pir", "on")
        track.call_args.args[2](event)
        await settle(room)
        assert room.managed


async def test_real_events_and_services_depart_after_delay(room):
    calls = []

    async def record(call):
        calls.append((call.service, call.data))

    for name in ["join", "unjoin", "volume_set", "media_pause"]:
        room.hass.services.async_register("media_player", name, record)
    room.service = Room.service.__get__(room)
    room.config["off_delay"] = 0.02
    await room.async_start()
    room.hass.states.async_set("binary_sensor.pir", "on")
    await room.hass.async_block_till_done()
    assert room.managed
    assert ("join", {"entity_id": "media_player.living", "group_members": [room.player]}) in calls
    room.hass.states.async_set("binary_sensor.radar", "on")
    room.hass.states.async_set("binary_sensor.pir", "off")
    await room.hass.async_block_till_done()
    await asyncio.sleep(0.04)
    assert not any(action == "unjoin" for action, _ in calls)
    room.hass.states.async_set("binary_sensor.radar", "off")
    await room.hass.async_block_till_done()
    await asyncio.sleep(0.04)
    await room.hass.async_block_till_done()
    assert ("unjoin", {"entity_id": room.player}) in calls
    assert not room.managed


async def test_unload_during_fade_restores_volume(room):
    room.managed = True
    room.config["fade_seconds"] = 5
    room._launch(room._leave)
    await asyncio.sleep(0)
    await room.async_stop()
    assert room.service.call_args_list[-1].kwargs["volume_level"] == 0.3
    assert all(c.args[0] != "unjoin" for c in room.service.call_args_list)


async def test_two_rooms_are_independent(room):
    other = Room(
        room.hass,
        SimpleNamespace(
            data={
                **CONFIG,
                "player": "media_player.kitchen",
                "primary": "binary_sensor.other",
                "secondary": ["binary_sensor.other_radar"],
            },
            options={},
            entry_id="other",
        ),
    )
    other.service = AsyncMock()
    other.hass.states.async_set("binary_sensor.other", "off")
    other.hass.states.async_set("binary_sensor.other_radar", "off")
    room.hass.states.async_set("binary_sensor.pir", "on")
    room.evaluate()
    other.evaluate()
    await settle(room)
    assert room.presence.occupied
    assert not other.presence.occupied
    other.service.assert_not_called()


@pytest.mark.parametrize(
    ("enabled", "minutes", "elapsed", "expected"),
    [
        (False, 30, 2000, 0.7),
        (True, 30, 1799, 0.7),
        (True, 30, 1800, 0.2),
        (True, 30, 2500, 0.2),
        (True, 0, 0, 0.2),
    ],
)
async def test_cooldown_selects_next_fade_target(room, enabled, minutes, elapsed, expected):
    room.config.update(volume_reset=enabled, default_volume=0.2, volume_cooldown=minutes)
    room.volume = 0.7
    room.presence.occupied = True
    with patch("custom_components.sonos_follow_me.room.time", return_value=1000):
        room._expired(None)
    await settle(room)
    # Expiry alone must not change the idle speaker's volume or saved target.
    assert room.volume == 0.7
    room.service.assert_not_called()
    room.hass.states.async_set("binary_sensor.pir", "on")
    with patch("custom_components.sonos_follow_me.room.time", return_value=1000 + elapsed):
        room.evaluate()
    await settle(room)
    assert room.volume == expected
    assert room._vacant_since is None
    assert room.service.call_args_list[-1].kwargs["volume_level"] == expected


async def test_return_restarts_full_cooldown_on_next_departure(room):
    room.config.update(volume_reset=True, default_volume=0.2, volume_cooldown=30)
    room.volume = 0.7
    room._vacant_since = 1000
    # No source is necessary for movement to reset the cooldown.
    room.config["sources"] = []
    room.hass.states.async_set("binary_sensor.pir", "on")
    with patch("custom_components.sonos_follow_me.room.time", return_value=2000):
        room.evaluate()
    await settle(room)
    assert room._vacant_since is None
    assert room.volume == 0.7
    room.hass.states.async_set("binary_sensor.pir", "off")
    with patch("custom_components.sonos_follow_me.room.time", return_value=2100):
        room._expired(None)
    await settle(room)
    assert room._vacant_since == 2100
    room.hass.states.async_set("binary_sensor.pir", "on")
    with patch("custom_components.sonos_follow_me.room.time", return_value=3000):
        room.evaluate()
    await settle(room)
    # Original cooldown would have expired at 2800, renewed cooldown ends at 3900.
    assert room.volume == 0.7


@pytest.mark.parametrize("mode,reset", [("primary", False), ("equal", True)])
async def test_radar_only_respects_sensor_mode_for_cooldown(room, mode, reset):
    room.config.update(volume_reset=True, default_volume=0.2, volume_cooldown=30)
    room.presence.mode = mode
    room.volume = 0.7
    room._vacant_since = 1000
    room.hass.states.async_set("binary_sensor.radar", "on")
    with patch("custom_components.sonos_follow_me.room.time", return_value=4000):
        room.evaluate()
    await settle(room)
    assert room._vacant_since == (None if reset else 1000)
    assert room.volume == (0.2 if reset else 0.7)


async def test_cooldown_survives_reload_and_elapsed_time(room):
    room.config.update(volume_reset=True, default_volume=0.2, volume_cooldown=30)
    room._store.async_load.return_value = {"volume": 0.7, "enabled": True, "vacant_since": 1000}
    with patch("custom_components.sonos_follow_me.room.time", return_value=2000):
        await room.async_start()
    assert room._vacant_since == 1000
    assert room.volume == 0.7
    await room.async_stop()
    room._store.async_save.assert_awaited_with(
        {"volume": 0.7, "enabled": True, "vacant_since": 1000}
    )
    room._stopped = False
    room.hass.states.async_set("binary_sensor.pir", "on")
    with patch("custom_components.sonos_follow_me.room.time", return_value=3000):
        await room.async_start()
    await settle(room)
    assert room.volume == 0.2
    assert room._vacant_since is None


async def test_legacy_storage_keeps_volume(room):
    room._store.async_load.return_value = {"volume": 0.6, "enabled": True}
    await room.async_start()
    assert not room.config["volume_reset"]
    assert room.volume == 0.6
    assert room._vacant_since is None


async def test_held_presence_does_not_start_cooldown(room):
    room.config["volume_reset"] = True
    room.presence.occupied = True
    room.hass.states.async_set("binary_sensor.radar", "on")
    room._expired(None)
    assert room._vacant_since is None


async def test_zero_default_volume_is_valid(room):
    room.config.update(volume_reset=True, default_volume=0, volume_cooldown=0)
    room._vacant_since = 1000
    room.volume = 0.7
    room.hass.states.async_set("binary_sensor.pir", "on")
    room.evaluate()
    await settle(room)
    assert room.service.call_args_list[-1].kwargs["volume_level"] == 0
