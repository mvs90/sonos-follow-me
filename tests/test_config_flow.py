from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from test_room import CONFIG

from custom_components.sonos_follow_me.config_flow import schema, validate
from custom_components.sonos_follow_me.const import DEFAULTS, ROOM_VOLUME_FIELDS


def test_schema_and_valid_config():
    assert schema({})({k: v for k, v in CONFIG.items() if k not in ROOM_VOLUME_FIELDS}) == {
        k: v for k, v in {**DEFAULTS, **CONFIG}.items() if k not in ROOM_VOLUME_FIELDS
    }
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
    assert result["step_id"] == "volume"
    result = await flow.async_step_volume(
        {k: CONFIG.get(k, DEFAULTS[k]) for k in ROOM_VOLUME_FIELDS}
    )
    assert result["type"] == "create_entry"
    assert result["title"] == "Bathroom"
    assert result["data"] == {**DEFAULTS, **CONFIG}


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
    assert result["step_id"] == "volume"
    result = await flow.async_step_volume({})
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
    submitted = form["data_schema"](
        {k: v for k, v in config.items() if k not in ROOM_VOLUME_FIELDS}
    )
    assert submitted["secondary"] == []
    result = await flow.async_step_init(submitted)
    assert result["step_id"] == "volume"
    result = await flow.async_step_volume({})
    assert result["type"] == "create_entry"
    assert result["data"]["secondary"] == []


def test_cooldown_settings_and_legacy_defaults():
    legacy = schema({}, True)({})
    assert legacy["volume_reset"] is False
    assert legacy["default_volume"] == 0.3
    assert legacy["volume_cooldown"] == 30
    updated = {**CONFIG, "volume_reset": True, "default_volume": 0.25, "volume_cooldown": 0}
    assert schema(updated, True)({k: v for k, v in updated.items() if k in ROOM_VOLUME_FIELDS}) == {
        k: v for k, v in {**DEFAULTS, **updated}.items() if k in ROOM_VOLUME_FIELDS
    }


@pytest.mark.parametrize("mode", ["group", "master"])
async def test_follow_setup_skips_room_volume_step(mode):
    from custom_components.sonos_follow_me.config_flow import SonosFollowMeConfigFlow

    flow = SonosFollowMeConfigFlow()
    flow.hass = SimpleNamespace(config_entries=Mock())
    flow.hass.config_entries.async_entries.return_value = []
    form = await flow.async_step_user()
    assert not ROOM_VOLUME_FIELDS.intersection(str(k) for k in form["data_schema"].schema)
    result = await flow.async_step_user({**CONFIG, "volume_mode": mode})
    assert result["type"] == "create_entry"
    assert result["data"]["volume_mode"] == mode


async def test_follow_options_preserve_hidden_room_volume_values():
    from custom_components.sonos_follow_me.config_flow import RoomOptionsFlow

    original = {**CONFIG, "volume_reset": True, "default_volume": 0.42, "volume_cooldown": 75}
    entry = SimpleNamespace(entry_id="existing", data=original, options={})
    flow = RoomOptionsFlow()
    flow.handler = "existing"
    flow.hass = SimpleNamespace(config_entries=Mock())
    flow.hass.config_entries.async_get_known_entry.return_value = entry
    flow.hass.config_entries.async_entries.return_value = [entry]
    submitted = {k: v for k, v in CONFIG.items() if k not in ROOM_VOLUME_FIELDS}
    result = await flow.async_step_init({**submitted, "volume_mode": "group"})
    assert result["type"] == "create_entry"
    assert all(result["data"][k] == original[k] for k in ROOM_VOLUME_FIELDS)
    entry.options = result["data"]
    result = await flow.async_step_init({**submitted, "volume_mode": "room"})
    assert result["step_id"] == "volume"
    assert result["data_schema"]({})["default_volume"] == 0.42
