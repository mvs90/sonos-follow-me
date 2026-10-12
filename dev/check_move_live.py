"""Opt-in hardware checks; use only a dedicated room and an idle, standalone Sonos.

The selected destination briefly joins an already playing source at 5% volume.
Source playback is never started, stopped, or changed. A destination snapshot is
restored and the test room is disabled in finally. Reports stay in .local/.
"""

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from ha_client import HA


def brief(state):
    return {
        "entity_id": state["entity_id"],
        "state": state["state"],
        "attributes": {
            k: v
            for k, v in state["attributes"].items()
            if k
            in (
                "volume_level",
                "is_volume_muted",
                "group_members",
                "source",
                "remembered_volume",
                "playback_target_volume",
                "startup_error",
            )
        },
    }


async def run(args):
    report = {"started": datetime.now(UTC).isoformat(), "checks": [], "samples": []}
    output = Path(args.report)
    output.parent.mkdir(parents=True, exist_ok=True)
    async with HA(args.url, args.auth_file) as ha:
        original = await ha.state(args.player)
        source = await ha.state(args.source)
        if original["state"] not in ("idle", "paused"):
            raise RuntimeError("Destination must be idle or paused")
        if original["attributes"].get("group_members") != [args.player]:
            raise RuntimeError("Destination must be standalone")
        if source["state"] != "playing":
            raise RuntimeError("An already playing source is required")
        report["before"] = [brief(original), brief(source)]
        report["ha_version"] = (await ha.get("/api/config"))["version"]
        room_name = "Sonos Move Testlabor"
        entries = await ha.get("/api/config/config_entries/entry")
        matches = [
            e for e in entries if e["domain"] == "sonos_follow_me" and e["title"] == room_name
        ]
        config = {
            "name": room_name,
            "player": args.player,
            "primary": "binary_sensor.sonos_lab_pir",
            "secondary": ["binary_sensor.sonos_lab_radar"],
            "sources": [args.source],
            "mode": "primary",
            "off_delay": 2,
            "fade_seconds": 1.5,
            "volume": 0.05,
            "volume_reset": True,
            "default_volume": 0.05,
            "volume_cooldown": 0,
            "tv_volume_offset": 0,
        }
        if matches:
            entry_id = matches[0]["entry_id"]
            flow = await ha.post("/api/config/config_entries/options/flow", {"handler": entry_id})
            result = await ha.finish_room_flow(
                "/api/config/config_entries/options/flow/" + flow["flow_id"], config
            )
        else:
            flow = await ha.post(
                "/api/config/config_entries/flow",
                {"handler": "sonos_follow_me", "show_advanced_options": False},
            )
            result = await ha.finish_room_flow(
                "/api/config/config_entries/flow/" + flow["flow_id"], config
            )
            entry_id = result.get("result", {}).get("entry_id")
        if result["type"] != "create_entry":
            raise RuntimeError(result)
        await asyncio.sleep(1)
        registry = await ha.ws({"type": "config/entity_registry/list"})
        entities = {
            e["unique_id"].removeprefix(entry_id + "_"): e["entity_id"]
            for e in registry
            if e["config_entry_id"] == entry_id
        }
        enabled = entities["enabled"]
        report["room_entry_id"] = entry_id
        report["room_switch"] = enabled
        helpers = ["input_boolean.sonos_lab_pir", "input_boolean.sonos_lab_radar"]
        pir, radar = helpers
        recording = True

        async def record():
            while recording:
                report["samples"].append(
                    {
                        "at": datetime.now(UTC).isoformat(),
                        "states": [brief(await ha.state(e)) for e in (args.player, enabled)],
                    }
                )
                await asyncio.sleep(0.25)

        async def passed(name):
            report["checks"].append(
                {"name": name, "result": "pass", "at": datetime.now(UTC).isoformat()}
            )
            print("PASS:", name, flush=True)

        def playing_at(volume):
            return lambda s: (
                s["state"] == "playing"
                and abs(s["attributes"].get("volume_level", -1) - volume) < 0.006
                and not s["attributes"].get("is_volume_muted")
            )

        async def leave():
            await ha.service("input_boolean", "turn_off", helpers)
            await ha.wait(
                args.player,
                lambda s: (
                    s["state"] != "playing"
                    and s["attributes"].get("group_members") == [args.player]
                ),
            )
            await asyncio.sleep(0.5)

        await ha.service("sonos", "snapshot", args.player, with_group=False)
        task = asyncio.create_task(record())
        try:
            await ha.service("switch", "turn_off", enabled)
            await ha.service("input_boolean", "turn_off", helpers)
            remembered = (await ha.state(enabled))["attributes"]["remembered_volume"]
            if abs(remembered - 0.05) > 0.001:
                raise RuntimeError(
                    "Existing test room remembers a different volume. Recreate the dedicated "
                    "Sonos Move Testlabor room before running this bounded-volume test."
                )
            await ha.service("switch", "turn_on", enabled)
            await ha.service("media_player", "volume_mute", args.player, is_volume_muted=True)
            await ha.wait(args.player, lambda s: s["attributes"].get("is_volume_muted") is True)
            await passed("Move mute change arrives through Sonos push feedback")
            await ha.service("input_boolean", "turn_on", radar)
            await asyncio.sleep(3)
            assert (await ha.state(args.player))["state"] != "playing"
            await passed("Radar alone does not start primary-mode room")
            await ha.service("input_boolean", "turn_on", pir)
            await ha.wait(args.player, playing_at(0.05))
            await asyncio.sleep(1)
            assert (await ha.state(enabled))["attributes"]["startup_error"] is None
            await passed("Muted Move joins and fades to 5% without pressing Volume+")
            await ha.service("input_boolean", "turn_off", pir)
            await asyncio.sleep(4)
            assert playing_at(0.05)(await ha.state(args.player))
            await passed("Radar holds playback after PIR clears")
            await leave()
            await passed("Both sensors clear: fade-out, unjoin and pause")
            # Check multiple independent starts against actual group/volume feedback.
            for cycle in range(1, 4):
                await ha.service("input_boolean", "turn_on", pir)
                await ha.wait(args.player, playing_at(0.05))
                await asyncio.sleep(1)
                assert (await ha.state(enabled))["attributes"]["startup_error"] is None
                await leave()
                await passed(f"Repeated real Move join/fade/leave cycle {cycle}")
            # A return during off-delay must cancel departure.
            await ha.service("input_boolean", "turn_on", pir)
            await ha.wait(args.player, playing_at(0.05))
            await ha.service("input_boolean", "turn_off", pir)
            await asyncio.sleep(0.5)
            await ha.service("input_boolean", "turn_on", pir)
            await asyncio.sleep(3)
            assert playing_at(0.05)(await ha.state(args.player))
            await passed("New movement cancels pending departure")
            await leave()
        except BaseException as error:
            report["failure"] = repr(error)
            raise
        finally:
            recording = False
            cleanup_errors = []
            try:
                await task
            except Exception as error:
                report["recording_error"] = repr(error)
            for domain, service, entity, data in [
                ("switch", "turn_off", enabled, {}),
                ("input_boolean", "turn_off", helpers, {}),
                ("media_player", "unjoin", args.player, {}),
                ("sonos", "restore", args.player, {"with_group": False}),
            ]:
                try:
                    await ha.service(domain, service, entity, **data)
                except Exception as error:
                    cleanup_errors.append(str(error))
            await asyncio.sleep(2)
            report["after"] = [
                brief(await ha.state(e)) for e in (args.player, args.source, enabled)
            ]
            report["cleanup_errors"] = cleanup_errors
            report["finished"] = datetime.now(UTC).isoformat()
            output.write_text(json.dumps(report, indent=2))
            output.chmod(0o600)
            print("Report:", output.resolve(), flush=True)
            if cleanup_errors:
                raise RuntimeError(cleanup_errors)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8123")
    parser.add_argument("--auth-file")
    parser.add_argument("--player", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--report", default=".local/move-live-report.json")
    asyncio.run(run(parser.parse_args()))
