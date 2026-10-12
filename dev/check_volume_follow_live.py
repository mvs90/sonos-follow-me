"""Exercise group/master following and hidden settings with simulated players only."""

import argparse
import asyncio
import json
from pathlib import Path

from ha_client import HA

PLAYER = "media_player.sonos_fault_lab_destination"
SOURCE = "media_player.sonos_fault_lab_source"
MEMBER = "media_player.sonos_fault_lab_member"


async def run(args):
    report = {"checks": []}
    async with HA(args.url, args.auth_file) as ha:
        for entity in (PLAYER, SOURCE, MEMBER):
            assert (await ha.state(entity))["attributes"].get("lab_simulated") is True
        entry = next(
            e
            for e in await ha.get("/api/config/config_entries/entry")
            if e["domain"] == "sonos_follow_me" and e["title"] == "Sonos Fehlersimulation"
        )
        entry_id = entry["entry_id"]
        registry = await ha.ws({"type": "config/entity_registry/list"})
        room_entities = {
            e["unique_id"].removeprefix(entry_id + "_"): e["entity_id"]
            for e in registry
            if e["config_entry_id"] == entry_id
        }
        enabled = room_entities["enabled"]
        assert (await ha.state(enabled))["state"] == "off"
        flow = await ha.post("/api/config/config_entries/options/flow", {"handler": entry_id})
        original = {
            f["name"]: f.get("description", {}).get("suggested_value", f.get("default"))
            for f in flow["data_schema"]
        }
        await ha.request("DELETE", "/api/config/config_entries/options/flow/" + flow["flow_id"])
        assert original["player"] == PLAYER and original["sources"] == [SOURCE]
        stored = {
            k: (await ha.state(room_entities[k]))["state"]
            for k in ("default_volume", "volume_reset", "volume_cooldown")
        }

        async def options(config):
            flow = await ha.post("/api/config/config_entries/options/flow", {"handler": entry_id})
            result = await ha.finish_room_flow(
                "/api/config/config_entries/options/flow/" + flow["flow_id"], config
            )
            assert result["type"] == "create_entry", result

        async def lab(**data):
            await ha.service("sonos_follow_me_lab", "configure", **data)

        async def level(entity, value):
            await ha.service("media_player", "volume_set", entity, volume_level=value)

        async def target(value):
            await ha.wait(
                PLAYER,
                lambda s: (
                    s["state"] == "playing" and abs(s["attributes"]["volume_level"] - value) < 0.001
                ),
            )
            await asyncio.sleep(0.15)

        async def visibility(hidden):
            registry = {
                e["entity_id"]: e for e in await ha.ws({"type": "config/entity_registry/list"})
            }
            for key in stored:
                assert registry[room_entities[key]]["hidden_by"] == (
                    "integration" if hidden else None
                )
                assert (await ha.state(room_entities[key]))["state"] == stored[key]

        def passed(name):
            report["checks"].append(name)
            print("PASS:", name, flush=True)

        try:
            for mode in ("master", "group"):
                await options(
                    {
                        **original,
                        "volume_mode": mode,
                        "fade_seconds": 0.1,
                        "off_delay": 0,
                        "tv_volume_offset": 0,
                    }
                )
                await lab(reset=True, member_joined=True)
                await level(SOURCE, 0.24)
                await level(MEMBER, 0.64)
                await ha.service("switch", "turn_on", enabled)
                await lab(pir=True)
                await target(0.24 if mode == "master" else 0.44)
                await visibility(True)
                await level(MEMBER, 0.84)
                await target(0.24 if mode == "master" else 0.54)
                await level(SOURCE, 0.44)
                await target(0.44 if mode == "master" else 0.64)
                await lab(tv=True)
                await ha.service(
                    "number", "set_value", room_entities["tv_volume_offset"], value=-10
                )
                await target(0.34 if mode == "master" else 0.54)
                source_writes = [
                    c
                    for c in (await ha.state(PLAYER))["attributes"]["lab_calls"]
                    if c["player"] != "destination" and c["action"] == "volume_set"
                ]
                assert len(source_writes) == 4, source_writes
                passed(
                    f"{mode}: entry, live reference changes, TV offset, hidden preserved settings, no source volume writes"
                )
                await lab(pir=False)
                await ha.wait(PLAYER, lambda s: s["state"] == "paused")
                before = (await ha.state(PLAYER))["attributes"]["volume_level"]
                await level(SOURCE, 0.7)
                await asyncio.sleep(0.3)
                assert (await ha.state(PLAYER))["attributes"]["volume_level"] == before
                await ha.service("switch", "turn_off", enabled)
                passed(f"{mode}: following stops after departure")

            await options({**original, "volume_mode": "room"})
            await visibility(False)
            passed("Own-room mode restores visible controls and saved values")
        finally:
            await ha.service("switch", "turn_off", enabled)
            await lab(reset=True)
            await options(original)
            report["restored"] = True
            Path(args.report).write_text(json.dumps(report, indent=2))
            Path(args.report).chmod(0o600)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8123")
    parser.add_argument("--auth-file")
    parser.add_argument("--report", default=".local/volume-follow-live-report.json")
    asyncio.run(run(parser.parse_args()))
