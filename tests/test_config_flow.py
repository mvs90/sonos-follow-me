from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from test_room import CONFIG

from custom_components.sonos_follow_me.config_flow import schema, validate
from custom_components.sonos_follow_me.const import DEFAULTS


def test_schema_and_valid_config():
    assert schema({})(CONFIG) == {**DEFAULTS, **CONFIG}
    hass = SimpleNamespace(config_entries=Mock())
    hass.config_entries.async_entries.return_value = []
    assert validate(hass, CONFIG) == {}


def test_reject_primary_as_additional_sensor():
    assert validate(None, {**CONFIG, "secondary": [CONFIG["primary"]]}) == {
        "secondary": "distinct_sensors"
    }


def test_reject_self_source():
    assert validate(None, {**CONFIG, "sources": [CONFIG["player"]]}) == {
        "sources": "invalid_sources"
    }


def test_duplicate_player_except_own_options():
    hass = SimpleNamespace(config_entries=Mock())
    hass.config_entries.async_entries.return_value = [
        SimpleNamespace(entry_id="existing", data=CONFIG, options={})
    ]
    assert validate(hass, CONFIG) == {"player": "player_used"}
    assert validate(hass, CONFIG, "existing") == {}


async def test_user_flow_creates_room_and_shows_validation():
    from custom_components.sonos_follow_me.config_flow import SonosFollowMeConfigFlow

    flow = SonosFollowMeConfigFlow()
    flow.hass = SimpleNamespace(config_entries=Mock())
    flow.hass.config_entries.async_entries.return_value = []
    result = await flow.async_step_user()
    assert result["type"] == "form"
    result = await flow.async_step_user({**CONFIG, "secondary": [CONFIG["primary"]]})
    assert result["errors"] == {"secondary": "distinct_sensors"}
    result = await flow.async_step_user(CONFIG)
    assert result["type"] == "create_entry"
    assert result["title"] == "Bathroom"
    assert result["data"] == CONFIG


@pytest.mark.parametrize("omit", [False, True])
async def test_user_flow_accepts_one_sensor(omit):
    from custom_components.sonos_follow_me.config_flow import SonosFollowMeConfigFlow

    config = {**CONFIG, "secondary": []}
    if omit:
        config.pop("secondary")
    flow = SonosFollowMeConfigFlow()
    flow.hass = SimpleNamespace(config_entries=Mock())
    flow.hass.config_entries.async_entries.return_value = []
    result = await flow.async_step_user(config)
    assert result["type"] == "create_entry"
    assert result["data"]["primary"] == CONFIG["primary"]
    assert result["data"]["secondary"] == []


@pytest.mark.parametrize("omit", [False, True])
async def test_options_can_remove_all_additional_sensors(omit):
    from custom_components.sonos_follow_me.config_flow import RoomOptionsFlow

    config = {**CONFIG, "secondary": []}
    if omit:
        config.pop("secondary")
    flow = RoomOptionsFlow()
    flow.handler = "existing"
    flow.hass = SimpleNamespace(config_entries=Mock())
    entry = SimpleNamespace(entry_id="existing", data=CONFIG, options={})
    flow.hass.config_entries.async_get_known_entry.return_value = entry
    flow.hass.config_entries.async_entries.return_value = [entry]
    form = await flow.async_step_init()
    # A cleared optional field must not silently restore the old radar sensor.
    submitted = form["data_schema"](config)
    assert submitted["secondary"] == []
    result = await flow.async_step_init(submitted)
    assert result["type"] == "create_entry"
    assert result["data"]["secondary"] == []


def test_cooldown_settings_and_legacy_defaults():
    legacy = schema({})(CONFIG)
    assert legacy["volume_reset"] is False
    assert legacy["default_volume"] == 0.3
    assert legacy["volume_cooldown"] == 30
    updated = {**CONFIG, "volume_reset": True, "default_volume": 0.25, "volume_cooldown": 0}
    assert schema(updated)(updated) == {**DEFAULTS, **updated}
