# Tests in a running Home Assistant instance

The development lab supplements the Python unit tests with real Home Assistant
service dispatch, state events, config flows, persistence and frontend loading.
It is **not included in the HACS integration**. The production integration remains
under `custom_components/sonos_follow_me`.

For future runtime changes, run the existing unit tests and the running-HA fault
scenarios below. Hardware checks are separate and briefly affect the selected
speaker. There is no background test schedule.

## Docker Desktop and Sonos

Keep the existing configuration volume and other integrations. On Docker Desktop,
discover speakers from the host LAN interface:

```sh
.venv/bin/python dev/discover_sonos.py --interface HOST_LAN_IP --yaml
```

Merge the output into Home Assistant's `configuration.yaml`. Publish TCP 1400
on that host LAN address (`HOST_LAN_IP:1400:1400`) in addition to the existing
8123 mapping. Mount this project's `custom_components/sonos_follow_me` read-only
at `/config/custom_components/sonos_follow_me` and recreate the HA container.
If `/config/custom_components` is itself a read-only bind mount, create an empty
`sonos_follow_me` directory in its backing directory first for the nested mount.

This uses explicit speaker addresses and Sonos's advertised callback address,
not multicast forwarding through the Docker VM. New speakers or changed IP
addresses require rediscovery and updating `hosts`; a changed host LAN address
also requires updating the callback address and port mapping. Stable DHCP leases
are useful. This is LAN-only; no router WAN forwarding is needed.

Verify Sonos diagnostics: `subscriptions_failed` must be false and event counters
must increase. `subscription_address` may show the internal listener address;
successful incoming events establish that the advertised callback is reachable.

References: [Home Assistant Sonos networking](https://www.home-assistant.io/integrations/sonos/#network-requirements),
[Sonos advanced configuration](https://www.home-assistant.io/integrations/sonos/#advanced-use),
[Docker Desktop host networking limitations](https://docs.docker.com/engine/network/drivers/host/#limitations).

## Authentication and reports

Use a local test account. The login helper prompts without echoing the password:

```sh
.venv/bin/python dev/ha_login.py
```

Subsequent commands use `--auth-file .local/ha-auth.json`. Alternatively provide
`HA_TOKEN` through your secret manager/environment and omit `--auth-file`.
The private file contains refresh credentials, not the password, and has mode
0600. `.local/` is ignored by Git. Do not commit tokens, snapshots, diagnostics,
host configuration or reports containing local entity identifiers. Revoke the
test session in your HA profile when it is no longer needed.

## Deterministic failures without physical audio

Mount `dev/sonos_follow_me_lab` read-only at
`/config/custom_components/sonos_follow_me_lab` and add:

```yaml
sonos_follow_me_lab:
```

Restart HA. The lab exposes only two in-memory media players and two simulated
sensors. It cannot contact physical devices. Run:

```sh
.venv/bin/python dev/check_faults_live.py --auth-file .local/ha-auth.json
```

The runner creates/reuses `Sonos Fehlersimulation`, uses real HA config flows and
media-player services, and reloads the room between independent cases to reset
ownership and failure backoff. Both the simulator and controller are reset after
the run; Follow Me is left off. Existing room state is intentionally not retained
for this dedicated test entry. Do not rename unrelated rooms to these lab names.

Scenarios: muted start, delayed group feedback, first positive volume command
ignored, persistent zero, persistent mute, missing group confirmation, intentional
zero target, negative/positive TV offsets, and cancellation during group wait.
Permanent failures must set `startup_error`; tests assert that unmute/retry calls
remain bounded. Expected warnings/errors in the HA log are part of these cases.
Results and service-call sequences are saved in `.local/fault-live-report.json`.

## Physical Move checks

Create `input_boolean.sonos_lab_pir` and `input_boolean.sonos_lab_radar`, both
initially off, and template binary sensors with the matching IDs that mirror them.
The provided instance already has these helpers and a **Sonos Testlabor** dashboard.

```sh
.venv/bin/python dev/check_move_live.py \
  --auth-file .local/ha-auth.json \
  --player media_player.YOUR_MOVE \
  --source media_player.YOUR_ALREADY_PLAYING_SOURCE
```

The destination must be idle/paused and standalone. A source must already be
playing. The runner creates/reuses `Sonos Move Testlabor`, uses 5% target volume,
and tests mute recovery, PIR/Radar gating, radar hold, departure, repeated joins
and cancelled departure. It never starts or pauses source playback. It snapshots
the destination, restores it in `finally`, and disables Follow Me and both inputs.
The room's test configuration is deliberately retained for reuse. Read
`cleanup_errors` and the before/after states if the run fails.

`.local/move-live-report.json` contains time-stamped state samples. Compare the
actual `volume_level`, `is_volume_muted`, `group_members`, and controller
`startup_error`; a successful HTTP service response alone is insufficient.

Successful simulated failures show that recovery handles those inputs. They do
not prove the root cause of an intermittent fault on a physical speaker.
