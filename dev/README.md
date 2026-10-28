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

Restart HA. The lab exposes only three in-memory media players and two simulated
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
zero target, negative/positive TV offsets, offsets with volume reset disabled, offsets before/after cooldown, and cancellation during group wait.
Permanent failures must set `startup_error`; tests assert that unmute/retry calls
remain bounded. Expected warnings/errors in the HA log are part of these cases.
Results and service-call sequences are saved in `.local/fault-live-report.json`.

To check single-sensor configuration and device grouping, leave that simulated
room disabled and run:

```sh
.venv/bin/python dev/check_room_setup_live.py --auth-file .local/ha-auth.json
```

This checks an empty or omitted additional-sensor field, both sensor modes,
cancellation of departure, re-adding the radar, and stable device/entity IDs.
It restores the original room options and leaves Follow Me off. Results are saved
in `.local/room-setup-live-report.json`.

For group/master volume following, use:

```sh
.venv/bin/python dev/check_volume_follow_live.py --auth-file .local/ha-auth.json
```

The optional third simulated player has a different volume so group average and
master following can be distinguished. The runner checks live changes, TV offset,
departure, hidden controls and preserved settings. It restores room options and
leaves Follow Me off; no physical players are used. Configuration runners support
the extra room-volume step introduced in v0.6.0.

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

## Separate preview container and compatibility checks

`dev/compose.preview.yaml` creates a separate HA instance at
`http://127.0.0.1:8124`, with its own named volume and simulated speakers. It uses
the official `dev` image by default. Pin a digest through `HA_PREVIEW_IMAGE` when
recording a reproducible result. For example, use the digest in the
[compatibility report](../docs/compatibility.md). `HA_PREVIEW_PORT` can override
8124. The ordinary stable instance keeps its existing Compose project and data.

```sh
docker compose -f dev/compose.preview.yaml pull
docker compose -f dev/compose.preview.yaml up -d
```

Complete onboarding in that instance and create a local test account. Sign in
with the existing login helper, keeping its authentication separate:

```sh
.venv/bin/python dev/ha_login.py --url http://127.0.0.1:8124 \
  --auth-file .local/ha-preview-auth.json
```

Run the suites in order (each manipulates only the dedicated simulated room):

```sh
.venv/bin/python dev/check_faults_live.py --url http://127.0.0.1:8124 \
  --auth-file .local/ha-preview-auth.json --report .local/preview-faults.json
.venv/bin/python dev/check_room_setup_live.py --url http://127.0.0.1:8124 \
  --auth-file .local/ha-preview-auth.json --report .local/preview-room-setup.json
.venv/bin/python dev/check_volume_follow_live.py --url http://127.0.0.1:8124 \
  --auth-file .local/ha-preview-auth.json --report .local/preview-volume-follow.json
.venv/bin/python dev/check_compatibility_live.py --url http://127.0.0.1:8124 \
  --auth-file .local/ha-preview-auth.json --phase prepare \
  --snapshot .local/preview-snapshot.json
docker compose -f dev/compose.preview.yaml restart
.venv/bin/python dev/check_compatibility_live.py --url http://127.0.0.1:8124 \
  --auth-file .local/ha-preview-auth.json --phase verify \
  --snapshot .local/preview-snapshot.json --report .local/preview-compatibility.json
```

If using a local environment file to pin the image, include its `--env-file`
argument on every Compose command. The `prepare` phase keeps an additional
simulated room, **Sonos Compatibility Second Room**, and creates/updates the
**Sonos Kompatibilität** dashboard at `/sonos-compatibility/test`. Both simulated
rooms stay disabled. Do not reuse those names for non-test configurations. The
`verify` phase waits for room startup, compares IDs and settings, checks all
translation texts and validates the single versioned card resource. To repeat
against stable, use its URL and authentication file and separate snapshot/report
paths; restart that instance using its own Compose project.

In the actual HA browser, inspect the dashboard and logo, adjust and restore both
sliders, switch between room/group/master volume and verify hidden settings, then
open and cancel the graphical card editor. Finish with both Follow Me switches
off and the original test settings restored. The standalone `npm test` suite
adds systematic mobile, language and startup-registry checks.

To run Python tests against an official image's installed dependencies, mount
this repository read-only and invoke the container test helper:

```sh
docker run --rm --entrypoint /bin/sh -v "$PWD:/work:ro" -w /work \
  -e PYTHONDONTWRITEBYTECODE=1 \
  ghcr.io/home-assistant/home-assistant:dev dev/run_container_tests.sh
```

The helper creates a temporary test venv inheriting the image's packages, installs
only test tools, prints the actual HA version and runs lint, formatting and all
Python tests. It does not install a different Home Assistant version. CI runs
this for the latest development image on pushes, pull requests and manual runs.
Local containers stay on their selected image until explicitly updated.
