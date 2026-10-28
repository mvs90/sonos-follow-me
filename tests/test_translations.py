"""Keep custom-integration translations complete and consistent with the UI schema."""

import json
import re
from pathlib import Path

import pytest
from homeassistant.generated.languages import LANGUAGES

from custom_components.sonos_follow_me.config_flow import schema
from custom_components.sonos_follow_me.const import VOLUME_MODES
from custom_components.sonos_follow_me.number import SETTINGS

ROOT = Path(__file__).resolve().parents[1] / "custom_components/sonos_follow_me"
CATALOGS = {p.stem: json.loads(p.read_text()) for p in (ROOT / "translations").glob("*.json")}


def leaves(value, path=""):
    result = {}
    for key, text in value.items():
        name = f"{path}.{key}" if path else key
        if isinstance(text, dict):
            result.update(leaves(text, name))
        else:
            result[name] = text
    return result


@pytest.mark.parametrize("language", sorted(CATALOGS))
def test_complete_supported_languages_and_placeholders(language):
    assert language in LANGUAGES
    baseline = leaves(CATALOGS["en"])
    translated = leaves(CATALOGS[language])
    assert translated.keys() == baseline.keys()
    for key, value in translated.items():
        assert isinstance(value, str) and value.strip(), (language, key)
        assert sorted(re.findall(r"\{\w+\}", value)) == sorted(
            re.findall(r"\{\w+\}", baseline[key])
        ), (language, key)


@pytest.mark.parametrize("language", sorted(CATALOGS))
def test_setup_options_and_selector_labels_match(language):
    texts = CATALOGS[language]
    config, options = texts["config"], texts["options"]
    assert config["step"]["user"] == options["step"]["init"]
    assert config["step"]["volume"] == options["step"]["volume"]
    assert config["error"] == options["error"]
    for step, is_volume in [("user", False), ("volume", True)]:
        fields = {marker.schema for marker in schema({}, is_volume).schema}
        assert fields == set(config["step"][step]["data"])
    for key, choices in [("mode", ["primary", "equal"]), ("volume_mode", VOLUME_MODES)]:
        selector = texts["selector"][key]["options"]
        assert set(selector) == set(choices)
        assert selector == texts["entity"]["select"][key]["state"]
        assert texts["entity"]["select"][key]["name"] == config["step"]["user"]["data"][key]
    assert set(texts["entity"]["number"]) == {setting[0] for setting in SETTINGS}
