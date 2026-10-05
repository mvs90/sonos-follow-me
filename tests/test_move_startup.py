"""Regression scenarios model Sonos timing/mute behavior, not physical Move hardware."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from custom_components.sonos_follow_me import room as room_module


class SimulatedMove:
    """Service completion may precede topology; volume does not clear mute."""

    def __init__(self, room, *, muted=False, join_delay=0, ignore_positive=0):
        self.room = room
        self.volume = 0.3
        self.muted = muted
        self.joined = False
        self.join_delay = join_delay
        self.ignore_positive = ignore_positive
        self.pending = None
        self.commands = []
        self.publish()
        room.service = AsyncMock(side_effect=self.service)

    def publish(self):
        self.room.hass.states.async_set(
            self.room.player,
            "playing" if self.joined else "paused",
            {
                "volume_level": self.volume,
                "is_volume_muted": self.muted,
                "group_members": ["media_player.living", self.room.player]
                if self.joined
                else [self.room.player],
            },
        )

    async def finish_join(self):
        await asyncio.sleep(self.join_delay)
        self.joined = True
        self.publish()

    async def service(self, action, entity=None, **data):
        self.commands.append((action, entity or self.room.player, data))
        if action == "join":
            if self.join_delay:
                self.pending = asyncio.create_task(self.finish_join())
            else:
                self.joined = True
        elif action == "volume_mute":
            self.muted = data["is_volume_muted"]
        elif action == "volume_set":
            value = data["volume_level"]
            if value > 0 and (not self.joined or self.ignore_positive):
                self.ignore_positive = max(0, self.ignore_positive - 1)
            else:
                self.volume = round(value * 100) / 100
        self.publish()


@pytest.fixture(autouse=True)
def short_startup_deadlines(monkeypatch):
    for name, value in {
        "JOIN_TIMEOUT": 0.1,
        "VOLUME_CONFIRM_TIMEOUT": 0.02,
        "STATE_POLL_INTERVAL": 0.005,
    }.items():
        monkeypatch.setattr(room_module, name, value, raising=False)


async def test_previously_muted_move_becomes_audible(room):
    move = SimulatedMove(room, muted=True)
    await room._enter()
    assert move.volume == 0.3
    assert not move.muted
    assert all(
        entity == room.player for action, entity, _ in move.commands if action == "volume_mute"
    )


async def test_delayed_join_does_not_consume_entire_fade(room):
    move = SimulatedMove(room, join_delay=0.03)
    await room._enter()
    if move.pending:
        await move.pending
    assert move.joined
    assert move.volume == 0.3


async def test_ignored_first_target_gets_bounded_recovery(room):
    move = SimulatedMove(room, ignore_positive=1)
    await room._enter()
    assert move.volume == 0.3
    assert sum(action == "join" for action, _, _ in move.commands) == 1


async def test_recovery_stops_after_two_retries_and_reports_failure(room):
    from homeassistant.exceptions import HomeAssistantError

    move = SimulatedMove(room, ignore_positive=100)
    with pytest.raises(HomeAssistantError, match="remained silent"):
        await room._enter()
    assert sum(action == "volume_mute" for action, _, _ in move.commands) == 3
    assert room.volume == 0.3
    assert room.startup_error is not None


async def test_group_timeout_restores_target_without_unmuting(room):
    from homeassistant.exceptions import HomeAssistantError

    move = SimulatedMove(room)

    async def service(action, **data):
        if action != "join":
            await move.service(action, **data)

    room.service = AsyncMock(side_effect=service)
    with pytest.raises(HomeAssistantError, match="join was not confirmed"):
        await room._enter()
    assert not room.managed
    assert room.volume == 0.3
    assert all(action != "volume_mute" for action, _, _ in move.commands)
    assert room.service.call_args_list[-1].kwargs["volume_level"] == 0.3


async def test_explicit_zero_target_stays_zero_and_does_not_unmute(room):
    room.volume = 0
    move = SimulatedMove(room, muted=True)
    await room._enter()
    assert move.volume == 0
    assert move.muted
    assert all(action != "volume_mute" for action, _, _ in move.commands)


async def test_late_fade_zero_does_not_overwrite_remembered_target(room):
    from types import SimpleNamespace
    from unittest.mock import patch

    move = SimulatedMove(room)
    await room._enter()
    old = room.hass.states.get(room.player)
    move.volume = 0
    move.publish()
    room._changed(
        SimpleNamespace(
            data={
                "entity_id": room.player,
                "old_state": old,
                "new_state": room.hass.states.get(room.player),
            }
        )
    )
    assert room.volume == 0.3
    # An intentional later zero is still a valid remembered setting.
    with patch(
        "custom_components.sonos_follow_me.room.monotonic", return_value=room_module.monotonic() + 6
    ):
        room._changed(
            SimpleNamespace(
                data={
                    "entity_id": room.player,
                    "old_state": old,
                    "new_state": room.hass.states.get(room.player),
                }
            )
        )
    assert room.volume == 0


async def test_unrelated_metadata_event_does_not_store_stale_volume(room):
    from types import SimpleNamespace

    move = SimulatedMove(room)
    move.volume = 0
    move.publish()
    old = room.hass.states.get(room.player)
    room.hass.states.async_set(
        room.player, "playing", {**old.attributes, "media_title": "New track"}
    )
    room._changed(
        SimpleNamespace(
            data={
                "entity_id": room.player,
                "old_state": old,
                "new_state": room.hass.states.get(room.player),
            }
        )
    )
    assert room.volume == 0.3


async def test_cancel_during_delayed_join_does_not_continue_fading(room):
    move = SimulatedMove(room, join_delay=0.04)
    task = asyncio.create_task(room._enter())
    await asyncio.sleep(0.01)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    count = len(move.commands)
    await move.pending
    await asyncio.sleep(0.01)
    assert len(move.commands) == count
    assert room.volume == 0.3
    assert room.service.call_args_list[-1].kwargs["volume_level"] == 0.3


async def test_recovery_keeps_tv_offset_and_music_memory(room):
    room.config.update(tv_volume_offset=-10, default_volume=0.3)
    room.volume = 0.6
    room.hass.states.async_set("media_player.living", "playing", {"source": "TV"})
    move = SimulatedMove(room, muted=True, ignore_positive=1)
    await room._enter()
    assert move.volume == 0.5
    assert not move.muted
    assert room.volume == 0.6


async def test_audible_manual_reduction_is_not_raised_again(room):
    move = SimulatedMove(room)
    service = move.service

    async def limited_volume(action, entity=None, **data):
        await service(action, entity=entity, **data)
        if action == "volume_set" and data["volume_level"] > 0:
            move.volume = 0.1
            move.publish()

    room.service = AsyncMock(side_effect=limited_volume)
    await room._enter()
    assert move.volume == 0.1
    assert sum(action == "volume_mute" for action, _, _ in move.commands) == 1


async def test_recovery_does_not_unmute_source_or_other_members(room):
    room.hass.states.async_set(
        "media_player.living",
        "playing",
        {
            "group_members": ["media_player.living", "media_player.kitchen"],
            "is_volume_muted": True,
            "volume_level": 0.2,
        },
    )
    move = SimulatedMove(room, muted=True)
    await room._enter()
    assert room.hass.states.get("media_player.living").attributes["is_volume_muted"] is True
    assert all(entity == room.player for action, entity, _ in move.commands if action != "join")
