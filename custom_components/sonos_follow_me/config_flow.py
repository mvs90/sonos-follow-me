"""UI configuration: one entry per room, any number of rooms."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DEFAULTS, DOMAIN, ROOM_VOLUME_FIELDS, VOLUME_MODES


def schema(values, volume_step=False):
    """Build room settings with persisted defaults."""
    values = {**DEFAULTS, **values}
    fields = {}
    for key, select in {
        "name": selector.TextSelector(),
        "player": selector.EntitySelector(
            selector.EntitySelectorConfig(domain="media_player", integration="sonos")
        ),
        "primary": selector.EntitySelector(selector.EntitySelectorConfig(domain="binary_sensor")),
        "secondary": selector.EntitySelector(
            selector.EntitySelectorConfig(domain="binary_sensor", multiple=True)
        ),
        "sources": selector.EntitySelector(
            selector.EntitySelectorConfig(domain="media_player", integration="sonos", multiple=True)
        ),
        "mode": selector.SelectSelector(
            selector.SelectSelectorConfig(options=["primary", "equal"], translation_key="mode")
        ),
        "volume_mode": selector.SelectSelector(
            selector.SelectSelectorConfig(options=VOLUME_MODES, translation_key="volume_mode")
        ),
        "off_delay": selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=3600, step=1, unit_of_measurement="s", mode="box"
            )
        ),
        "fade_seconds": selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=30, step=0.5, unit_of_measurement="s", mode="box"
            )
        ),
        "volume": selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=1, step=0.01, mode="box")
        ),
        "tv_volume_offset": selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=-100, max=100, step=1, unit_of_measurement="pp", mode="box"
            )
        ),
        "volume_reset": selector.BooleanSelector(),
        "default_volume": selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=1, step=0.01, mode="box")
        ),
        "volume_cooldown": selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=10080, step=1, unit_of_measurement="min", mode="box"
            )
        ),
    }.items():
        if (key in ROOM_VOLUME_FIELDS) != volume_step:
            continue
        if key == "secondary":
            # Suggest existing sensors, but allow clearing them by omitting this field.
            marker = vol.Optional(key, default=list, description={"suggested_value": values[key]})
        else:
            marker = vol.Required(key, default=values[key]) if key in values else vol.Required(key)
        fields[marker] = select
    return vol.Schema(fields)


def validate(hass, data, entry_id=None):
    """Reject ambiguous sensors and duplicate room players."""
    if not data["name"].strip():
        return {"name": "empty_name"}
    if data["primary"] in data.get("secondary", []):
        return {"secondary": "distinct_sensors"}
    if not data["sources"] or data["player"] in data["sources"]:
        return {"sources": "invalid_sources"}
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.entry_id != entry_id and (entry.options or entry.data)["player"] == data["player"]:
            return {"player": "player_used"}
    return {}


class SonosFollowMeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Set up a room."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            user_input = {"secondary": [], **user_input}
        errors = validate(self.hass, user_input) if user_input is not None else {}
        if user_input is not None and not errors:
            self._pending = {**DEFAULTS, **user_input}
            if self._pending["volume_mode"] == "room":
                return await self.async_step_volume()
            return self.async_create_entry(title=user_input["name"], data=self._pending)
        return self.async_show_form(
            step_id="user", data_schema=schema(user_input or {}), errors=errors
        )

    async def async_step_volume(self, user_input=None):
        if user_input is not None:
            self._pending.update(user_input)
            return self.async_create_entry(title=self._pending["name"], data=self._pending)
        return self.async_show_form(step_id="volume", data_schema=schema(self._pending, True))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return RoomOptionsFlow()


class RoomOptionsFlow(config_entries.OptionsFlow):
    """Edit all room settings."""

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            user_input = {"secondary": [], **user_input}
        errors = (
            validate(self.hass, user_input, self.config_entry.entry_id)
            if user_input is not None
            else {}
        )
        if user_input is not None and not errors:
            self._pending = {
                **DEFAULTS,
                **(self.config_entry.options or self.config_entry.data),
                **user_input,
            }
            if self._pending["volume_mode"] == "room":
                return await self.async_step_volume()
            return self._finish()
        return self.async_show_form(
            step_id="init",
            data_schema=schema(user_input or self.config_entry.options or self.config_entry.data),
            errors=errors,
        )

    async def async_step_volume(self, user_input=None):
        if user_input is not None:
            self._pending.update(user_input)
            return self._finish()
        return self.async_show_form(step_id="volume", data_schema=schema(self._pending, True))

    def _finish(self):
        self.hass.config_entries.async_update_entry(self.config_entry, title=self._pending["name"])
        return self.async_create_entry(title="", data=self._pending)
