"""Event-driven room controller with cancellable departure and serialized playback."""

import asyncio
import logging

from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .presence import Presence

_LOGGER = logging.getLogger(__name__)


class Room:
    """Own only playback joined by this controller, never an existing music source."""

    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        self.config = dict(entry.options or entry.data)
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

    async def async_start(self):
        saved = await self._store.async_load() or {}
        self.volume = saved.get("volume", self.volume)
        self.enabled = saved.get("enabled", True)
        # Playback ownership deliberately does not survive restart.
        self._unsub = async_track_state_change_event(
            self.hass,
            list(dict.fromkeys([*self.sensors, self.player, *self.config["sources"]])),
            self._changed,
        )
        self.evaluate()

    def _save(self):
        self._store.async_delay_save(lambda: {"volume": self.volume, "enabled": self.enabled}, 1)

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
        if event.data["entity_id"] == self.player and not self._fading:
            state = event.data["new_state"]
            if (
                state
                and state.state == "playing"
                and isinstance(volume := state.attributes.get("volume_level"), (float, int))
            ):
                self.volume = max(0, min(1, volume))
                self._save()
        self.evaluate()

    @callback
    def evaluate(self):
        if self._stopped or not self.enabled:
            return
        status = self.status()
        if status == "clear":
            if self._timer is None:
                self._timer = async_call_later(self.hass, self.config["off_delay"], self._expired)
        else:
            self._cancel_timer()
            if (
                status == "occupied"
                and not self.managed
                and (self._task is None or self._task.done())
            ):
                self._launch(self._enter)
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

        self._task = self.hass.async_create_task(run())

    async def service(self, action, entity=None, **data):
        await self.hass.services.async_call(
            "media_player", action, {"entity_id": entity or self.player, **data}, blocking=True
        )

    def source(self):
        for entity in self.config["sources"]:
            state = self.hass.states.get(entity)
            if state and state.state == "playing":
                members = state.attributes.get("group_members") or [entity]
                if self.player not in members:
                    return members[0]
        return None

    async def _fade(self, start, end, leaving=False):
        self._fading = True
        try:
            steps = 12 if self.config["fade_seconds"] else 1
            for step in range(1, steps + 1):
                if leaving and (not self.enabled or self.status() != "idle"):
                    await self.service("volume_set", volume_level=self.volume)
                    return False
                x = step / steps
                await self.service(
                    "volume_set", volume_level=round(start + (end - start) * x * x * (3 - 2 * x), 4)
                )
                if steps > 1:
                    await asyncio.sleep(self.config["fade_seconds"] / steps)
            return True
        finally:
            self._fading = False

    async def _enter(self):
        source = self.source()
        if not source or self.state(self.player) in ("playing", "unavailable", "unknown"):
            return
        self._fading = True
        try:
            await self.service("volume_set", volume_level=0)
            await self.service("join", entity=source, group_members=[self.player])
            self.managed = True
            await self._fade(0, self.volume)
        except (HomeAssistantError, asyncio.CancelledError):
            # Do not leave a player muted after a failed/cancelled join.
            await self.service("volume_set", volume_level=self.volume)
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
            return
        try:
            if not await self._fade(
                state.attributes.get("volume_level", self.volume), 0, leaving=True
            ):
                return
            # Recheck after the final fade sleep, before changing group membership.
            if not self.enabled or self.status() != "idle":
                return
            await self.service("unjoin")
            await self.service("media_pause")
            self.managed = False
        finally:
            await self.service("volume_set", volume_level=self.volume)

    async def async_enable(self, enabled):
        self.enabled = enabled
        self._cancel_timer()
        if self._task and not self._task.done():
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            if self.managed:
                await self.service("volume_set", volume_level=self.volume)
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
        await self._store.async_save({"volume": self.volume, "enabled": self.enabled})
