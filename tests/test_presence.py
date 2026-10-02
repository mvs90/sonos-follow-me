import pytest

from custom_components.sonos_follow_me.presence import Presence


@pytest.mark.parametrize("mode,expected", [("primary", "idle"), ("equal", "occupied")])
def test_radar_only(mode, expected):
    assert Presence(mode).update("off", ["on"]) == expected


def test_pir_starts_radar_holds_until_all_clear():
    presence = Presence("primary")
    assert presence.update("on", ["off", "off"]) == "occupied"
    assert presence.update("off", ["on", "off"]) == "occupied"
    assert presence.update("off", ["off", "on"]) == "occupied"
    assert presence.update("off", ["off", "off"]) == "clear"
    assert presence.update("off", ["on", "off"]) == "occupied"
    assert presence.update("off", ["off", "off"]) == "clear"
    presence.expire()
    assert presence.update("off", ["on", "off"]) == "idle"


@pytest.mark.parametrize("missing", ["unknown", "unavailable"])
def test_missing_sensor_does_not_clear(missing):
    presence = Presence("primary")
    presence.update("on", ["off"])
    assert presence.update("off", [missing]) == "occupied"
