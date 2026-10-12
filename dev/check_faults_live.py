"""Reproducible failure scenarios through a running HA instance's actual services.

Requires dev/sonos_follow_me_lab mounted as a separate custom integration.
The simulator has no device or network access; only its two players are targeted.
"""

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from ha_client import HA

DOMAIN = "sonos_follow_me_lab"
PLAYER = "media_player.sonos_fault_lab_destination"
SOURCE = "media_player.sonos_fault_lab_source"


async def run(args):
    report = {"started": datetime.now(UTC).isoformat(), "scenarios": []}
    async with HA(args.url, args.auth_file) as ha:
        for entity in (PLAYER, SOURCE):
            assert (await ha.state(entity))["attributes"].get("lab_simulated") is True
        entries = await ha.get("/api/config/config_entries/entry")
        name = "Sonos Fehlersimulation"
        existing = next(
            (e for e in entries if e["domain"] == "sonos_follow_me" and e["title"] == name), None
        )
        config = {
            "name": name,
            "player": PLAYER,
            "primary": "binary_sensor.sonos_fault_lab_pir",
            "secondary": ["binary_sensor.sonos_fault_lab_radar"],
            "sources": [SOURCE],
            "mode": "primary",
            "off_delay": 0,
            "fade_seconds": 0,
            "volume": 0.2,
            "volume_reset": True,
            "default_volume": 0.2,
            "volume_cooldown": 0,
            "tv_volume_offset": 0,
        }
        if existing:
            entry_id = existing["entry_id"]
        else:
            flow = await ha.post(
                "/api/config/config_entries/flow",
                {"handler": "sonos_follow_me", "show_advanced_options": False},
            )
            result = await ha.finish_room_flow(
                "/api/config/config_entries/flow/" + flow["flow_id"], config
            )
            assert result["type"] == "create_entry", result
            entry_id = result["result"]["entry_id"]
        await asyncio.sleep(0.5)
        registry = await ha.ws({"type": "config/entity_registry/list"})
        enabled = next(e["entity_id"] for e in registry if e["unique_id"] == entry_id + "_enabled")
        report["room_switch"] = enabled
        report["ha_version"] = (await ha.get("/api/config"))["version"]

        async def lab(**data):
            return await ha.service(DOMAIN, "configure", **data)

        async def setup(settings, faults):
            await ha.service("switch", "turn_off", enabled)
            await lab(reset=True, source_playing=False)
            flow = await ha.post("/api/config/config_entries/options/flow", {"handler": entry_id})
            result = await ha.finish_room_flow(
                "/api/config/config_entries/options/flow/" + flow["flow_id"], {**config, **settings}
            )
            assert result["type"] == "create_entry", result
            # Reset ownership, startup error and the 30-second failure backoff
            # between scenarios, just as unloading/reloading an actual room does.
            await ha.post(f"/api/config/config_entries/entry/{entry_id}/reload", {})
            # Establish vacancy through actual presence events; next entry then
            # picks the configured default, including an intentional zero.
            await ha.service("switch", "turn_on", enabled)
            await lab(pir=True)
            await asyncio.sleep(0.2)
            await lab(pir=False)
            await ha.wait(enabled, lambda s: s["attributes"].get("vacant_since") is not None)
            await ha.service("switch", "turn_off", enabled)
            await lab(reset=True, **faults)
            await ha.service("switch", "turn_on", enabled)

        cases = [
            ("muted_start", {}, {"muted": True}, 0.2, None),
            ("delayed_join", {}, {"join_delay": 1.5}, 0.2, None),
            ("lost_first_volume_command", {}, {"drop_positive": 1}, 0.2, None),
            (
                "permanent_zero_bounded_retries",
                {},
                {"always_zero": True},
                None,
                "silent/unconfirmed",
            ),
            (
                "persistent_mute_bounded_retries",
                {},
                {"muted": True, "sticky_mute": True},
                None,
                "silent/unconfirmed",
            ),
            ("missing_group_feedback", {}, {"never_join": True}, None, "not confirmed"),
            ("intentional_zero_remains_muted", {"default_volume": 0}, {"muted": True}, 0, None),
            (
                "tv_negative_offset",
                {"tv_volume_offset": -10},
                {"tv": True, "drop_positive": 1},
                0.1,
                None,
            ),
            ("tv_positive_offset", {"tv_volume_offset": 10}, {"tv": True}, 0.3, None),
            (
                "tv_negative_offset_without_reset",
                {"volume_reset": False, "default_volume": 0.8, "tv_volume_offset": -5},
                {"tv": True, "drop_positive": 1},
                0.15,
                None,
            ),
            (
                "tv_positive_offset_without_reset",
                {"volume_reset": False, "default_volume": 0.8, "tv_volume_offset": 5},
                {"tv": True},
                0.25,
                None,
            ),
            (
                "tv_offset_before_cooldown",
                {"volume_cooldown": 30, "default_volume": 0.8, "tv_volume_offset": -5},
                {"tv": True},
                0.15,
                None,
            ),
            (
                "tv_offset_after_immediate_cooldown",
                {"volume_cooldown": 0, "default_volume": 0.4, "tv_volume_offset": -5},
                {"tv": True},
                0.35,
                None,
            ),
            ("cancel_pending_join", {}, {"never_join": True}, None, None),
        ]
        try:
            for name, settings, faults, expected, error in cases:
                item = {
                    "name": name,
                    "settings": settings,
                    "faults": faults,
                    "started": datetime.now(UTC).isoformat(),
                }
                report["scenarios"].append(item)
                await setup(settings, faults)
                await lab(pir=True)
                if name == "cancel_pending_join":
                    await asyncio.sleep(0.4)
                    await ha.service("switch", "turn_off", enabled)
                    before = len((await ha.state(PLAYER))["attributes"]["lab_calls"])
                    await asyncio.sleep(1)
                    assert len((await ha.state(PLAYER))["attributes"]["lab_calls"]) == before
                elif error:
                    await ha.wait(
                        enabled,
                        lambda s: error in (s["attributes"].get("startup_error") or ""),
                        timeout=18,
                    )
                    await asyncio.sleep(0.5)
                else:
                    await ha.wait(
                        PLAYER,
                        lambda s: (
                            s["state"] == "playing"
                            and abs(s["attributes"]["volume_level"] - expected) < 0.001
                            and (expected == 0 or not s["attributes"]["is_volume_muted"])
                        ),
                    )
                    await asyncio.sleep(0.3)
                    assert (await ha.state(enabled))["attributes"].get("startup_error") is None
                player = await ha.state(PLAYER)
                switch = await ha.state(enabled)
                calls = player["attributes"]["lab_calls"]
                unmutes = [c for c in calls if c["action"] == "volume_mute"]
                if name in ("permanent_zero_bounded_retries", "persistent_mute_bounded_retries"):
                    assert len(unmutes) == 3, calls
                if name == "lost_first_volume_command":
                    assert len(unmutes) == 2, calls
                if name == "missing_group_feedback":
                    assert not unmutes, calls
                if name == "intentional_zero_remains_muted":
                    assert not unmutes and player["attributes"]["is_volume_muted"], calls
                if name.startswith("tv_"):
                    assert switch["attributes"]["remembered_volume"] == (
                        0.4 if name == "tv_offset_after_immediate_cooldown" else 0.2
                    )
                assert not any(
                    c["player"] == "source"
                    and c["action"] in ("volume_set", "volume_mute", "pause")
                    for c in calls
                )
                item.update(
                    result="pass",
                    player=player,
                    controller=switch,
                    finished=datetime.now(UTC).isoformat(),
                )
                print("PASS:", name, flush=True)
        except BaseException as error:
            report["failure"] = repr(error)
            raise
        finally:
            await ha.service("switch", "turn_off", enabled)
            await lab(reset=True)
            report["finished"] = datetime.now(UTC).isoformat()
            path = Path(args.report)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(report, indent=2))
            path.chmod(0o600)
            print("Report:", path.resolve(), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8123")
    parser.add_argument("--auth-file")
    parser.add_argument("--report", default=".local/fault-live-report.json")
    asyncio.run(run(parser.parse_args()))
