"""Verify translations, resources, multiple devices and settings across a real HA restart.

Run prepare after the existing live suites, restart the selected test instance,
then run verify with the same snapshot. Both simulated rooms remain disabled.
"""

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from ha_client import HA

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "sonos_follow_me"
SECOND = "Sonos Compatibility Second Room"
LAB_NAMES = {"Sonos Fehlersimulation", SECOND}
MEMBER = "media_player.sonos_fault_lab_member"
SOURCE = "media_player.sonos_fault_lab_source"


def leaves(value, prefix):
    result = {}
    for key, item in value.items():
        name = f"{prefix}.{key}"
        if isinstance(item, dict):
            result.update(leaves(item, name))
        else:
            result[name] = item
    return result


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
    path.chmod(0o600)


async def inventory(ha):
    # Existing network integrations can delay the dependency setup after restart.
    # Do not confuse the HTTP frontend being ready with the rooms being loaded.
    for _ in range(90):
        entries = [
            e
            for e in await ha.get("/api/config/config_entries/entry")
            if e["domain"] == DOMAIN and e["title"] in LAB_NAMES
        ]
        if len(entries) == 2 and all(e["state"] == "loaded" for e in entries):
            break
        await asyncio.sleep(2)
    assert len(entries) == 2 and all(e["state"] == "loaded" for e in entries), entries
    ids = {e["entry_id"] for e in entries}
    registry = [
        e
        for e in await ha.ws({"type": "config/entity_registry/list"})
        if e["config_entry_id"] in ids
    ]
    assert len(registry) == 20, len(registry)
    assert len({e["device_id"] for e in registry}) == 2
    assert all(e["device_id"] for e in registry)
    settings = {}
    for entity in registry:
        if entity["entity_id"].split(".")[0] in {"number", "select", "switch"}:
            state = await ha.state(entity["entity_id"])
            assert state["state"] not in {"unknown", "unavailable"}
            settings[entity["entity_id"]] = state["state"]
    switches = [e["entity_id"] for e in registry if e["unique_id"].endswith("_enabled")]
    assert all(settings[e] == "off" for e in switches), "Keep both simulated rooms disabled"
    return {
        "entries": sorted(ids),
        "identities": sorted([e["entity_id"], e["unique_id"], e["device_id"]] for e in registry),
        "settings": settings,
        "switches": sorted(switches),
    }


async def run(args):
    async with HA(args.url, args.auth_file) as ha:
        version = (await ha.get("/api/config"))["version"]
        for player in (MEMBER, SOURCE):
            assert (await ha.state(player))["attributes"].get("lab_simulated") is True
        if args.phase == "prepare":
            entries = await ha.get("/api/config/config_entries/entry")
            if not any(e["domain"] == DOMAIN and e["title"] == SECOND for e in entries):
                flow = await ha.post("/api/config/config_entries/flow", {"handler": DOMAIN})
                result = await ha.finish_room_flow(
                    "/api/config/config_entries/flow/" + flow["flow_id"],
                    {
                        "name": SECOND,
                        "player": MEMBER,
                        "primary": "binary_sensor.sonos_fault_lab_radar",
                        "secondary": [],
                        "sources": [SOURCE],
                        "mode": "equal",
                        "volume_mode": "room",
                        "off_delay": 2,
                        "fade_seconds": 0.5,
                        "tv_volume_offset": -6,
                        "volume": 0.17,
                        "volume_reset": True,
                        "default_volume": 0.42,
                        "volume_cooldown": 13,
                    },
                )
                assert result["type"] == "create_entry", result
                entry_id = result["result"]["entry_id"]
                for _ in range(50):
                    registry = await ha.ws({"type": "config/entity_registry/list"})
                    switch = next(
                        (e for e in registry if e["unique_id"] == entry_id + "_enabled"),
                        None,
                    )
                    if switch:
                        break
                    await asyncio.sleep(0.2)
                assert switch
                await ha.service("switch", "turn_off", switch["entity_id"])
            snapshot = await inventory(ha)
            snapshot["version"] = version
            snapshot["prepared"] = datetime.now(UTC).isoformat()
            save(args.snapshot, snapshot)
            dashboards = await ha.ws({"type": "lovelace/dashboards/list"})
            if not any(d["url_path"] == "sonos-compatibility" for d in dashboards):
                await ha.ws(
                    {
                        "type": "lovelace/dashboards/create",
                        "url_path": "sonos-compatibility",
                        "title": "Sonos Kompatibilität",
                        "icon": "mdi:speaker-multiple",
                        "show_in_sidebar": True,
                        "require_admin": True,
                    }
                )
            await ha.ws(
                {
                    "type": "lovelace/config/save",
                    "url_path": "sonos-compatibility",
                    "config": {
                        "views": [
                            {
                                "title": "Testlabor",
                                "path": "test",
                                "cards": [
                                    {
                                        "type": "custom:sonos-follow-me-card",
                                        "entities": snapshot["switches"],
                                    }
                                ],
                            }
                        ]
                    },
                }
            )
            print(f"PASS: two disabled simulated rooms, independent devices/settings ({version})")
            print("Restart this Home Assistant instance, then run --phase verify.")
            return

        saved = json.loads(Path(args.snapshot).read_text())
        current = await inventory(ha)
        for key in ("entries", "identities", "settings"):
            assert current[key] == saved[key], f"Changed after restart: {key}"
        report = {
            "version": version,
            "tested": datetime.now(UTC).isoformat(),
            "checks": ["two rooms/devices", "IDs and settings survive restart", "rooms disabled"],
        }
        translations = {}
        for path in sorted((ROOT / "custom_components" / DOMAIN / "translations").glob("*.json")):
            catalog = json.loads(path.read_text())
            matched = 0
            for category in ("config", "options", "entity", "selector"):
                result = await ha.ws(
                    {
                        "type": "frontend/get_translations",
                        "language": path.stem,
                        "category": category,
                        "integration": [DOMAIN],
                    }
                )
                expected = leaves(catalog[category], f"component.{DOMAIN}.{category}")
                assert all(result["resources"].get(k) == v for k, v in expected.items()), (
                    path.stem,
                    category,
                )
                matched += len(expected)
            translations[path.stem] = matched
        report["translations"] = translations
        manifest = json.loads((ROOT / "custom_components" / DOMAIN / "manifest.json").read_text())
        resources = await ha.ws({"type": "lovelace/resources"})
        matching = [r for r in resources if "/sonos-follow-me-card.js" in r["url"]]
        assert len(matching) == 1, matching
        expected_url = f"/sonos_follow_me/sonos-follow-me-card.js?v={manifest['version']}"
        assert matching[0]["url"] == expected_url and matching[0]["type"] == "module"
        async with ha.session.get(ha.url + expected_url) as response:
            response.raise_for_status()
            source = await response.read()
        assert (
            source
            == (
                ROOT / "custom_components" / DOMAIN / "frontend/sonos-follow-me-card.js"
            ).read_bytes()
        )
        report["checks"].extend(
            ["all translations", "one current card resource", "served card matches source"]
        )
        save(args.report, report)
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8123")
    parser.add_argument("--auth-file", required=True)
    parser.add_argument("--phase", choices=("prepare", "verify"), required=True)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--report", default=".local/compatibility-live-report.json")
    asyncio.run(run(parser.parse_args()))
