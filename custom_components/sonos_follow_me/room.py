"""Event-driven room controller with cancellable departure and serialized playback."""

import asyncio
import logging
from collections import deque
from math import isfinite
from time import monotonic, time

from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import (
    TrackStates,
    async_call_later,
    async_track_state_change_filtered,
)
from homeassistant.helpers.storage import Store

from .const import DEFAULTS, DOMAIN
from .presence import Presence

_LOGGER = logging.getLogger(__name__)
JOIN_TIMEOUT = 10
VOLUME_CONFIRM_TIMEOUT = 2
STATE_POLL_INTERVAL = 0.1
STARTUP_RECOVERY_ATTEMPTS = 2
VOLUME_ECHO_WINDOW = 5


class Room:
    """Own only playback joined by this controller, never an existing music source."""

    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        self.config = {**DEFAULTS, **(entry.options or entry.data)}
        self.player = self.config["player"]
        self.sensors = [self.config["primary"], *self.config["secondary"]]
        self.presence = Presence(self.config["mode"])
        self.enabled = True
        self.managed = False
        self.volume = self.config["volume"]
        self.listeners = set()
        self._store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}")
        self._unsub = None
        self._timer = None
        self._task = None
        self._fading = False
        self._stopped = False
        self._volume_echoes = deque(maxlen=48)
        self._retry_after = 0
        self.startup_error = None
        self._tv_volume = None
        self._vacant_since = None
        self._follow_source = None
        self._follow_volume = None
        self._last_volume_target = None
        self._volume_sync_needed = False

    async def async_start(self):
        saved = await self._store.async_load() or {}
        self.volume = saved.get("volume", self.volume)
        self.enabled = saved.get("enabled", True)
        self._vacant_since = saved.get("vacant_since")
        # Playback ownership deliberately does not survive restart.
        self._unsub = async_track_state_change_filtered(
            self.hass,
            TrackStates(False, set(self.sensors), {"media_player"}),
            self._changed,
        ).async_remove
        self.evaluate()

    @callback
    def update_settings(self, updates):
        """Persist public settings through the same options used by the config flow."""
        options = {**DEFAULTS, **(self.entry.options or self.entry.data), **updates}
        self.hass.config_entries.async_update_entry(self.entry, options=options)

    @callback
    def apply_settings(self, config):
        """Apply non-structural changes without losing playback ownership."""
        previous = self.config
        self.config = config
        self.presence.mode = config["mode"]
        if previous["volume_mode"] != config["volume_mode"]:
            self._follow_volume = None
            self._tv_volume = None
            self._volume_sync_needed = True
        if previous["tv_volume_offset"] != config["tv_volume_offset"]:
            self._volume_sync_needed = True
        if previous["off_delay"] != config["off_delay"]:
            self._cancel_timer()
        self.evaluate()
        self.notify()

    def _stored_state(self):
        return {"volume": self.volume, "enabled": self.enabled, "vacant_since": self._vacant_since}

    def _save(self):
        self._store.async_delay_save(self._stored_state, 1)

    def _resume_volume(self):
        """Choose the next visit's target without touching an idle speaker.

        A timestamp rather than a timer preserves elapsed cooldown across restarts.
        Valid occupancy cancels it even when no source is currently playing.
        """
        if self._vacant_since is None:
            return
        if (
            not self.following_volume
            and self.config["volume_reset"]
            and time() - self._vacant_since >= self.config["volume_cooldown"] * 60
        ):
            self.volume = self.config["default_volume"]
        self._vacant_since = None
        self._save()

    def notify(self):
        for listener in list(self.listeners):
            listener()

    def state(self, entity):
        state = self.hass.states.get(entity)
        return state.state if state else "unavailable"

    def status(self):
        return self.presence.update(
            self.state(self.sensors[0]), [self.state(s) for s in self.sensors[1:]]
        )

    @callback
    def _changed(self, event):
        entity = event.data["entity_id"]
        watched = [*self.sensors, self.player, *self.config["sources"]]
        if self.following_volume:
            source = self._current_coordinator() if self.managed else self.source()
            watched.extend(self._group_members(source))
        if entity not in watched:
            return
        if entity == self.player and not self._fading and not self.following_volume:
            state = event.data["new_state"]
            if (
                state
                and state.state == "playing"
                and state.attributes.get("is_volume_muted") is not True
                and isinstance(volume := state.attributes.get("volume_level"), (float, int))
                and not self._is_volume_echo(volume)
                and (
                    (old := event.data.get("old_state")) is None
                    or old.attributes.get("volume_level") != volume
                )
            ):
                if self._tv_volume is not None:
                    self._tv_volume = max(0, min(1, volume))
                else:
                    self.volume = max(0, min(1, volume))
                    self._save()
        self.evaluate()

    @callback
    def evaluate(self):
        if self._stopped or not self.enabled:
            return
        status = self.status()
        if status == "occupied":
            self._resume_volume()
        if status == "clear":
            if self._timer is None:
                self._timer = async_call_later(self.hass, self.config["off_delay"], self._expired)
        else:
            self._cancel_timer()
            if (
                status == "occupied"
                and not self.managed
                and monotonic() >= self._retry_after
                and (self._task is None or self._task.done())
            ):
                self._launch(self._enter)
        self._schedule_volume_sync()
        self.notify()

    def _cancel_timer(self):
        if self._timer:
            self._timer()
            self._timer = None

    @callback
    def _expired(self, _now):
        self._timer = None
        if not self.enabled or self.status() != "clear":
            return
        self.presence.expire()
        self._vacant_since = time()
        self._save()
        self.notify()
        self._launch(self._leave)

    def _launch(self, operation):
        previous = self._task
        if previous and not previous.done():
            previous.cancel()

        async def run():
            if previous:
                await asyncio.gather(previous, return_exceptions=True)
            try:
                await operation()
            except HomeAssistantError:
                _LOGGER.exception("Sonos action failed in room %s", self.config["name"])
            finally:
                self.notify()
                # Process source changes received during a fade, without overlapping services.
                self.hass.loop.call_soon(self._schedule_volume_sync)

        self._task = self.hass.async_create_task(run())

    async def service(self, action, entity=None, **data):
        await self.hass.services.async_call(
            "media_player", action, {"entity_id": entity or self.player, **data}, blocking=True
        )

    def _is_volume_echo(self, volume):
        """Do not store delayed reports of our own fade steps as manual volume."""
        now = monotonic()
        return any(
            now - sent < VOLUME_ECHO_WINDOW and round(volume * 100) == value
            for sent, value in self._volume_echoes
        )

    async def _set_volume(self, value):
        self._volume_echoes.append((monotonic(), round(value * 100)))
        await self.service("volume_set", volume_level=value)

    async def _wait_until(self, predicate, timeout):
        try:
            async with asyncio.timeout(timeout):
                while not predicate():
                    await asyncio.sleep(STATE_POLL_INTERVAL)
        except TimeoutError:
            return False
        return True

    def _group_ready(self, source):
        player = self.hass.states.get(self.player)
        coordinator = self.hass.states.get(source)
        if (
            not player
            or player.state != "playing"
            or not coordinator
            or coordinator.state != "playing"
        ):
            return False
        for state in (player, coordinator):
            members = state.attributes.get("group_members") or []
            if members and members[0] == source and self.player in members:
                return True
        return False

    def _volume_confirmed(self, target):
        state = self.hass.states.get(self.player)
        if not state or state.state != "playing":
            return False
        volume = state.attributes.get("volume_level")
        return (
            isinstance(volume, (int, float))
            and abs(volume - target) <= 0.0051
            and (target == 0 or state.attributes.get("is_volume_muted") is not True)
        )

    async def _confirm_startup(self, source, target):
        """Recover only a silent start, with a bounded number of attempts."""
        for attempt in range(STARTUP_RECOVERY_ATTEMPTS + 1):
            if await self._wait_until(
                lambda: self._volume_confirmed(target), VOLUME_CONFIRM_TIMEOUT
            ):
                return
            if not self._group_ready(source):
                raise HomeAssistantError("Sonos group changed during fade-in")
            state = self.hass.states.get(self.player)
            volume = state.attributes.get("volume_level")
            muted = state.attributes.get("is_volume_muted")
            # A nonzero, audible adjustment may be a user setting or device volume limit.
            if target > 0 and isinstance(volume, (int, float)) and volume > 0 and muted is not True:
                return
            if (
                attempt == STARTUP_RECOVERY_ATTEMPTS
                or target == 0
                or not isinstance(volume, (int, float))
            ):
                raise HomeAssistantError(
                    f"Sonos startup remained silent/unconfirmed: volume={volume}, muted={muted}, target={target}"
                )
            _LOGGER.warning(
                "Retrying silent Sonos start for %s (%s/%s): volume=%s, muted=%s, target=%s",
                self.player,
                attempt + 1,
                STARTUP_RECOVERY_ATTEMPTS,
                volume,
                muted,
                target,
            )
            await self._set_volume(0)
            await self.service("volume_mute", is_volume_muted=False)
            await self._fade(0, target)

    def source(self):
        for entity in self.config["sources"]:
            state = self.hass.states.get(entity)
            if state and state.state == "playing":
                members = state.attributes.get("group_members") or [entity]
                if self.player not in members:
                    return members[0]
        return None

    def source_is_tv(self, entity):
        """Inspect the selected group coordinator, not soundbar model or media type."""
        state = self.hass.states.get(entity)
        if state is None or state.state != "playing":
            return False
        return str(state.attributes.get("source", "")).casefold() == "tv" or str(
            state.attributes.get("media_content_id", "")
        ).startswith("x-sonos-htastream:")

    @property
    def following_volume(self):
        return self.config["volume_mode"] != "room"

    def _group_members(self, source):
        state = self.hass.states.get(source) if source else None
        return list(state.attributes.get("group_members") or [source]) if state else []

    def _current_coordinator(self):
        members = self._group_members(self.player)
        return members[0] if members and members[0] != self.player else None

    def _reference_volume(self, source):
        """Read source levels without letting our own follower fades feed back."""
        if not source or source == self.player or self.state(source) != "playing":
            return None
        excluded = {self.player}
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            room = getattr(entry, "runtime_data", None)
            if room and (room.managed or room._fading):
                excluded.add(room.player)
        members = (
            [source] if self.config["volume_mode"] == "master" else self._group_members(source)
        )
        values = []
        for entity in dict.fromkeys(members):
            if entity == self.player or (
                self.config["volume_mode"] == "group" and entity in excluded
            ):
                continue
            state = self.hass.states.get(entity)
            if not state or state.state in ("unknown", "unavailable"):
                continue
            value = state.attributes.get("volume_level")
            if isinstance(value, (int, float)) and isfinite(value) and 0 <= value <= 1:
                values.append(value)
        return sum(values) / len(values) if values else None

    def _volume_target(self, source):
        base = self._reference_volume(source) if self.following_volume else self.volume
        if base is None:
            return None
        offset = self.config["tv_volume_offset"] if self.source_is_tv(source) else 0
        return round(max(0, min(1, base + offset / 100)), 2)

    @callback
    def _schedule_volume_sync(self):
        if (
            self._stopped
            or not self.enabled
            or not self.managed
            or not self.presence.occupied
            or (self._task is not None and not self._task.done())
            or (not self.following_volume and not self._volume_sync_needed)
        ):
            return
        source = self._current_coordinator()
        if not source or not self._group_ready(source):
            return
        target = self._volume_target(source)
        if target is None:
            return
        start = self.hass.states.get(self.player).attributes.get("volume_level")
        if not isinstance(start, (int, float)) or not isfinite(start):
            return
        self._follow_source = source
        if not self._volume_sync_needed and target == self._last_volume_target:
            return
        self._launch(self._sync_volume)

    async def _sync_volume(self):
        source = self._current_coordinator()
        target = self._volume_target(source)
        if target is None or not source or not self._group_ready(source):
            return
        state = self.hass.states.get(self.player)
        start = state.attributes.get("volume_level")
        if not isinstance(start, (int, float)) or not isfinite(start):
            return
        self._remember_target(source, target)
        await self._fade(start, target)

    def _remember_target(self, source, target):
        self._follow_source = source
        self._last_volume_target = target
        self._volume_sync_needed = False
        self._follow_volume = target if self.following_volume else None
        self._tv_volume = (
            target if self.config["tv_volume_offset"] and self.source_is_tv(source) else None
        )

    @property
    def tv_volume_active(self):
        return self._tv_volume is not None

    @property
    def playback_volume(self):
        """TV volume is visit-local; music memory never includes the TV correction."""
        if self.following_volume and self._follow_volume is not None:
            return self._follow_volume
        return self.volume if self._tv_volume is None else self._tv_volume

    async def _fade(self, start, end, leaving=False):
        previous_fading = self._fading
        self._fading = True
        try:
            steps = 12 if self.config["fade_seconds"] else 1
            for step in range(1, steps + 1):
                if leaving and (not self.enabled or self.status() != "idle"):
                    await self._set_volume(self.playback_volume)
                    return False
                x = step / steps
                await self._set_volume(round(start + (end - start) * x * x * (3 - 2 * x), 4))
                if steps > 1:
                    await asyncio.sleep(self.config["fade_seconds"] / steps)
            return True
        finally:
            self._fading = previous_fading

    async def _enter(self):
        source = self.source()
        if not source or self.state(self.player) in ("playing", "unavailable", "unknown"):
            return
        target = self._volume_target(source)
        if target is None:
            self.startup_error = "Source volume unavailable; waiting for a valid volume"
            return
        self._remember_target(source, target)
        self.startup_error = None
        self._fading = True
        try:
            await self._set_volume(0)
            await self.service("join", entity=source, group_members=[self.player])
            self.managed = True
            if not await self._wait_until(lambda: self._group_ready(source), JOIN_TIMEOUT):
                raise HomeAssistantError("Sonos group join was not confirmed within 10 seconds")
            if target > 0:
                await self.service("volume_mute", is_volume_muted=False)
            await self._fade(0, target)
            await self._confirm_startup(source, target)
        except (HomeAssistantError, asyncio.CancelledError) as error:
            if isinstance(error, HomeAssistantError):
                self.startup_error = str(error)
                self._retry_after = monotonic() + 30
                if not self._group_ready(source):
                    self.managed = False
            # Restore the correct target on failure or interrupted entry.
            if not self.managed:
                self._tv_volume = None
                self._follow_volume = None
            await self._set_volume(self.playback_volume)
            raise
        finally:
            self._fading = False

    async def _leave(self):
        if not self.managed:
            return
        state = self.hass.states.get(self.player)
        if state is None or state.state in ("unknown", "unavailable"):
            return
        members = state.attributes.get("group_members") or []
        if members and members[0] == self.player and len(members) > 1:
            # Never dismantle a group if this speaker became its coordinator.
            self.managed = False
            self._tv_volume = None
            self._follow_volume = None
            return
        try:
            if not await self._fade(
                state.attributes.get("volume_level", self.playback_volume), 0, leaving=True
            ):
                return
            # Recheck after the final fade sleep, before changing group membership.
            if not self.enabled or self.status() != "idle":
                return
            await self.service("unjoin")
            await self.service("media_pause")
            self.managed = False
            self._tv_volume = None
            self._follow_volume = None
        finally:
            await self._set_volume(self.playback_volume)

    async def async_enable(self, enabled):
        self.enabled = enabled
        self._cancel_timer()
        if self._task and not self._task.done():
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            if self.managed:
                await self._set_volume(self.playback_volume)
        self.presence.expire()
        self._save()
        self.evaluate()
        self.notify()

    async def async_stop(self):
        self._stopped = True
        self._cancel_timer()
        if self._unsub:
            self._unsub()
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
        await self._store.async_save(self._stored_state())
