"""Public entities, live options and bundled frontend registration."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from custom_components.sonos_follow_me import CARD_URL, LOGO_URL, async_reload, async_setup
from custom_components.sonos_follow_me.binary_sensor import RoomOccupancy
from custom_components.sonos_follow_me.number import SETTINGS, RoomNumber
from custom_components.sonos_follow_me.select import SensorMode
from custom_components.sonos_follow_me.switch import FollowMeSwitch, VolumeResetSwitch


async def test_card_registration():
    hass = SimpleNamespace(http=SimpleNamespace(async_register_static_paths=AsyncMock()))
    with patch("custom_components.sonos_follow_me.add_extra_js_url") as add:
        assert await async_setup(hass, {})
        path = hass.http.async_register_static_paths.call_args.args[0][0]
        assert path.url_path == CARD_URL
        assert Path(path.path).is_file()
        assert not path.cache_headers
        logo = hass.http.async_register_static_paths.call_args.args[0][1]
        assert logo.url_path == LOGO_URL
        assert Path(logo.path).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        assert not logo.cache_headers
        add.assert_called_once_with(hass, f"{CARD_URL}?v=0.4.0")


async def test_entities_expose_stable_room_metadata(room):
    entities = [
        FollowMeSwitch(room),
        VolumeResetSwitch(room),
        RoomOccupancy(room),
        SensorMode(room),
    ]
    entities += [RoomNumber(room, setting) for setting in SETTINGS]
    assert len({entity.unique_id for entity in entities}) == 9
    for entity in entities:
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
