"""Check single-sensor rooms and device grouping using only the isolated lab players."""

import argparse
import asyncio
import json
from pathlib import Path

from ha_client import HA

DOMAIN = "sonos_follow_me"
PLAYER = "media_player.sonos_fault_lab_destination"
SOURCE = "media_player.sonos_fault_lab_source"


async def run(args):
    report = {"checks": []}
    async with HA(args.url, args.auth_file) as ha:
        for entity in (PLAYER, SOURCE):
            assert (await ha.state(entity))["attributes"].get("lab_simulated") is True
        entries = await ha.get("/api/config/config_entries/entry")
        entry = next(
            e for e in entries if e["domain"] == DOMAIN and e["title"] == "Sonos Fehlersimulation"
        )
        entry_id = entry["entry_id"]

        async def registry():
            return [
                e
                for e in await ha.ws({"type": "config/entity_registry/list"})
                if e["platform"] == DOMAIN
            ]

        before = await registry()
        enabled = next(e["entity_id"] for e in before if e["unique_id"] == entry_id + "_enabled")
        assert (await ha.state(enabled))["state"] == "off", "Disable the lab room before running"
        flow = await ha.post("/api/config/config_entries/options/flow", {"handler": entry_id})
        original = {
            field["name"]: field.get("description", {}).get("suggested_value", field.get("default"))
            for field in flow["data_schema"]
        }
        await ha.request("DELETE", "/api/config/config_entries/options/flow/" + flow["flow_id"])
        assert original["player"] == PLAYER and original["sources"] == [SOURCE]

        async def options(config):
            flow = await ha.post("/api/config/config_entries/options/flow", {"handler": entry_id})
            result = await ha.post(
                "/api/config/config_entries/options/flow/" + flow["flow_id"], config
            )
            assert result["type"] == "create_entry", result
            await ha.post(f"/api/config/config_entries/entry/{entry_id}/reload", {})
            await ha.wait(enabled, lambda s: s["state"] == "off")

        async def lab(**data):
            await ha.service("sonos_follow_me_lab", "configure", **data)

        def passed(name):
            report["checks"].append(name)
            print("PASS:", name, flush=True)

        try:
            for mode, omit in [("primary", False), ("equal", False), ("primary", True)]:
                await ha.service("switch", "turn_off", enabled)
                await lab(reset=True)
                config = {**original, "secondary": [], "mode": mode, "off_delay": 1}
                if omit:
                    config.pop("secondary")
                await options(config)
                assert (await ha.state(enabled))["attributes"]["secondary"] == []
                await ha.service("switch", "turn_on", enabled)
                await lab(radar=True)
                await asyncio.sleep(0.2)
                assert not (await ha.state(PLAYER))["attributes"]["lab_calls"]
                await lab(pir=True)
                await ha.wait(PLAYER, lambda s: s["state"] == "playing")
                await lab(pir=False)
                await asyncio.sleep(0.2)
                await lab(pir=True)
                await asyncio.sleep(1.1)
                assert (await ha.state(PLAYER))["state"] == "playing"
                assert not any(
                    c["action"] == "unjoin"
                    for c in (await ha.state(PLAYER))["attributes"]["lab_calls"]
                )
                await lab(pir=False)
                await ha.wait(PLAYER, lambda s: s["state"] == "paused")
                assert (await ha.state(PLAYER))["attributes"]["group_members"] == [PLAYER]
                passed(f"Single sensor ({mode}, omitted={omit}): enter, cancel departure, leave")

            await ha.service("switch", "turn_off", enabled)
            await lab(reset=True)
            await options({**original, "mode": "primary", "off_delay": 1})
            await ha.service("switch", "turn_on", enabled)
            await lab(pir=True, radar=True)
            await ha.wait(PLAYER, lambda s: s["state"] == "playing")
            await lab(pir=False)
            await asyncio.sleep(1.2)
            assert (await ha.state(PLAYER))["state"] == "playing"
            await lab(radar=False)
            await ha.wait(PLAYER, lambda s: s["state"] == "paused")
            passed("Restored additional sensor holds occupancy until both are clear")

            after = await registry()

            def identity(items):
                return {(e["entity_id"], e["unique_id"], e["device_id"]) for e in items}

            assert identity(before) == identity(after)
            devices = {
                d["id"]: d
                for d in await ha.ws({"type": "config/device_registry/list"})
                if any(identifier[0] == DOMAIN for identifier in d["identifiers"])
            }
            assert len(devices) == sum(e["domain"] == DOMAIN for e in entries)
            assert all(d["entry_type"] == "service" for d in devices.values())
            assert all(e["device_id"] in devices for e in after)
            passed(
                "One service device per room; every entity assigned; no duplicate or changed IDs"
            )
            report["devices"] = [{"id": d["id"], "name": d["name"]} for d in devices.values()]
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
    parser.add_argument("--report", default=".local/room-setup-live-report.json")
    asyncio.run(run(parser.parse_args()))
