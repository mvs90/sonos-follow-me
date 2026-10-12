"""Public entities, live options and bundled frontend registration."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.lovelace.resources import (
    ResourceStorageCollection,
    ResourceYAMLCollection,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType

from custom_components.sonos_follow_me import async_reload, async_setup
from custom_components.sonos_follow_me.binary_sensor import RoomOccupancy
from custom_components.sonos_follow_me.dashboard import CARD_URL, LOGO_URL
from custom_components.sonos_follow_me.number import SETTINGS, RoomNumber
from custom_components.sonos_follow_me.select import SensorMode, VolumeMode
from custom_components.sonos_follow_me.switch import FollowMeSwitch, VolumeResetSwitch

VERSION = json.loads(Path("custom_components/sonos_follow_me/manifest.json").read_text())["version"]
MODULE_URL = f"{CARD_URL}?v={VERSION}"


@pytest.fixture
def dashboard():
    hass = SimpleNamespace(
        http=SimpleNamespace(async_register_static_paths=AsyncMock()),
        data={LOVELACE_DATA: SimpleNamespace(resources=ResourceYAMLCollection([]))},
    )
    with (
        patch("custom_components.sonos_follow_me.dashboard.add_extra_js_url") as add,
        patch(
            "custom_components.sonos_follow_me.dashboard.async_get_integration",
            return_value=SimpleNamespace(version=VERSION),
        ),
    ):
        yield hass, add


async def test_card_registration_yaml_fallback(dashboard):
    hass, add = dashboard
    original = [{"url": "/local/user-card.js", "type": "module"}]
    hass.data[LOVELACE_DATA].resources = ResourceYAMLCollection(original)
    assert await async_setup(hass, {})
    path, logo = hass.http.async_register_static_paths.call_args.args[0]
    assert path.url_path == CARD_URL
    assert Path(path.path).is_file()
    assert not path.cache_headers
    assert logo.url_path == LOGO_URL
    assert Path(logo.path).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert not logo.cache_headers
    add.assert_called_once_with(hass, MODULE_URL)
    assert hass.data[LOVELACE_DATA].resources.async_items() == original


@pytest.mark.parametrize("existing", [False, True])
async def test_card_resource_created_or_upgraded_without_touching_other_resources(
    dashboard, existing
):
    hass, add = dashboard
    resources = Mock(spec=ResourceStorageCollection)
    resources.async_items.return_value = [
        {"id": "other", "url": "/local/user-card.js", "type": "module"},
    ]
    if existing:
        resources.async_items.return_value.extend(
            [
                {"id": "card", "url": f"{CARD_URL}?v=0.6.0", "type": "js"},
                {"id": "duplicate", "url": CARD_URL, "type": "module"},
            ]
        )
    hass.data[LOVELACE_DATA].resources = resources
    assert await async_setup(hass, {})
    resources.async_get_info.assert_awaited_once()
    values = {"url": MODULE_URL, "res_type": "module"}
    if existing:
        resources.async_create_item.assert_not_called()
        resources.async_update_item.assert_awaited_once_with("card", values)
        resources.async_delete_item.assert_awaited_once_with("duplicate")
    else:
        resources.async_create_item.assert_awaited_once_with(values)
        resources.async_update_item.assert_not_called()
        resources.async_delete_item.assert_not_called()
    add.assert_not_called()


async def test_current_resource_requires_no_write(dashboard):
    hass, add = dashboard
    resources = Mock(spec=ResourceStorageCollection)
    resources.async_items.return_value = [{"id": "card", "url": MODULE_URL, "type": "module"}]
    hass.data[LOVELACE_DATA].resources = resources
    assert await async_setup(hass, {})
    resources.async_create_item.assert_not_called()
    resources.async_update_item.assert_not_called()
    resources.async_delete_item.assert_not_called()
    add.assert_not_called()


@pytest.mark.parametrize("error", [HomeAssistantError("Storage unavailable"), OSError("Read only")])
async def test_resource_storage_failure_keeps_frontend_fallback(dashboard, error):
    hass, add = dashboard
    resources = Mock(spec=ResourceStorageCollection)
    resources.async_get_info.side_effect = error
    hass.data[LOVELACE_DATA].resources = resources
    assert await async_setup(hass, {})
    add.assert_called_once_with(hass, MODULE_URL)


async def test_entities_expose_stable_room_metadata(room):
    entities = [
        FollowMeSwitch(room),
        VolumeResetSwitch(room),
        RoomOccupancy(room),
        SensorMode(room),
        VolumeMode(room),
    ]
    entities += [RoomNumber(room, setting) for setting in SETTINGS]
    assert len({entity.unique_id for entity in entities}) == 10
    for entity in entities:
        assert entity.device_info["identifiers"] == {("sonos_follow_me", room.entry.entry_id)}
        assert entity.device_info["entry_type"] == DeviceEntryType.SERVICE
        assert entity.extra_state_attributes["sonos_follow_me_room"] == room.entry.entry_id
        assert entity.extra_state_attributes["setting"] == entity.key
    assert entities[0].extra_state_attributes["primary"] == "binary_sensor.pir"


async def test_controls_use_existing_options_and_percent_conversion(room):
    room.update_settings = Mock()
    number = RoomNumber(room, SETTINGS[0])
    assert number.native_value == 30
    await number.async_set_native_value(25)
    room.update_settings.assert_called_with({"default_volume": 0.25})
    reset = VolumeResetSwitch(room)
    await reset.async_turn_on()
    room.update_settings.assert_called_with({"volume_reset": True})
    await reset.async_turn_off()
    room.update_settings.assert_called_with({"volume_reset": False})
    await SensorMode(room).async_select_option("equal")
    room.update_settings.assert_called_with({"mode": "equal"})
    await VolumeMode(room).async_select_option("master")
    room.update_settings.assert_called_with({"volume_mode": "master"})


async def test_unused_volume_controls_hide_and_respect_user_hiding(room):
    entity = RoomNumber(room, SETTINGS[0])
    entity.hass = room.hass
    entity.entity_id = "number.bath_default_volume"
    entry = SimpleNamespace(hidden_by=None)
    registry = Mock()
    registry.async_get.return_value = entry
    with patch("custom_components.sonos_follow_me.entity.er.async_get", return_value=registry):
        room.config["volume_mode"] = "group"
        entity._sync_visibility()
        registry.async_update_entity.assert_called_with(
            entity.entity_id, hidden_by=er.RegistryEntryHider.INTEGRATION
        )
        entry.hidden_by = er.RegistryEntryHider.INTEGRATION
        room.config["volume_mode"] = "room"
        entity._sync_visibility()
        registry.async_update_entity.assert_called_with(entity.entity_id, hidden_by=None)
        registry.async_update_entity.reset_mock()
        entry.hidden_by = er.RegistryEntryHider.USER
        entity._sync_visibility()
        registry.async_update_entity.assert_not_called()


async def test_live_settings_keep_playback_and_cooldown(room):
    room.managed = True
    room._vacant_since = 1234
    room.entry.runtime_data = room
    room.entry.options = {**room.config, "default_volume": 0.25, "volume_reset": True}
    await async_reload(room.hass, room.entry)
    assert room.managed
    assert room._vacant_since == 1234
    assert room.config["default_volume"] == 0.25
    room.service.assert_not_called()


async def test_sensor_rewiring_still_reloads(room):
    room.entry.runtime_data = room
    room.entry.options = {**room.config, "primary": "binary_sensor.new"}
    hass = SimpleNamespace(config_entries=SimpleNamespace(async_reload=AsyncMock()))
    await async_reload(hass, room.entry)
    hass.config_entries.async_reload.assert_awaited_once_with("test")


async def test_update_preserves_other_settings(room):
    room.entry.options = {**room.config, "off_delay": 65}
    manager = Mock()
    room.hass = SimpleNamespace(config_entries=manager)
    room.update_settings({"default_volume": 0.22})
    options = manager.async_update_entry.call_args.kwargs["options"]
    assert options["default_volume"] == 0.22
    assert options["off_delay"] == 65
    assert options["primary"] == "binary_sensor.pir"
