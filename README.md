# Sonos Follow Me

<p><img src="docs/follow-me-logo.png" alt="Follow Me logo" width="160"></p>

Follow music between rooms using PIR and radar presence sensors. A Home Assistant custom integration, installable through HACS or the Home Assistant Marketplace as a custom repository. MIT licensed; independent community project, not affiliated with Sonos.

**[Deutsche Anleitung](README.de.md)**

## Features

- Any number of rooms, each with its own Sonos speaker, one primary sensor and optional additional sensors, source priorities and timing.
- **Primary mode:** PIR starts occupancy. Radar and any additional sensors only hold occupancy after the PIR has detected someone. Radar alone cannot start music.
- **Equal mode:** any configured sensor can start or maintain occupancy.
- Departure only after **all** sensors remain `off` throughout the configured delay. Renewed presence cancels departure, including during fading.
- Optional default volume after an absence cooldown (including immediate reset for the next visit).
- Room enable switch and occupancy entity. Smooth configurable fades; remembered volume and enable state, without external helpers.
- Setup, options, entity labels and dashboard card in ten language variants. Uses the official Sonos integration locally.

## Installation

[![Open Sonos Follow Me in your Home Assistant](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=mvs90&repository=sonos-follow-me&category=integration)

Requires Home Assistant **2026.9.0+**, the official **Sonos** integration, and at least one binary sensor per room. Tested against HA 2026.9.4, including a Sonos Move and isolated simulated failure scenarios.

1. Open the install link above, or add `https://github.com/mvs90/sonos-follow-me` as a custom repository, category **Integration**. On Home Assistant 2026.10 and older, use HACS. Starting with 2026.11, use **Settings → Marketplace**.
2. Install **Sonos Follow Me**. In HACS, restart Home Assistant after downloading. The Marketplace can start first-time setup immediately; updates still require a restart.
3. Go to **Settings → Devices & services → Add integration → Sonos Follow Me**, unless setup has opened automatically.
4. Add one entry per room. Repeat to manage additional speakers/rooms.

Since v0.5.0, each room appears as a device under **Settings → Devices & services → Sonos Follow Me**, with its switches, occupancy sensor and settings grouped together. The integration is no longer classified as a helper. Existing room devices, entity IDs and settings are retained after updating and restarting; do not delete and recreate rooms. Manually created helpers from earlier YAML automations are not changed.

A primary sensor alone can start and maintain occupancy in either sensor mode. When it stays off for the clear delay, the speaker fades out. In **Configure**, leave **Additional sensors** empty or remove previously selected sensors.

This repository is **not yet listed in the default catalog**. Until its catalog submission is accepted, use the custom repository link above. HACS and the Marketplace use the [same catalog](https://contributors.home-assistant.io/marketplace/guides/catalog/). Sonos Follow Me remains independently maintained community software.

Manual installation: copy `custom_components/sonos_follow_me` to your HA `config/custom_components` directory and restart.

## Bundled dashboard card (v0.3.0+)

![Dashboard card with sample rooms](docs/dashboard-card.png)

*Preview with simulated room data.*

The integration ships and automatically loads **Sonos Follow Me**, a custom dashboard card. Since v0.3.1, its header includes the project logo, served locally with the integration. Update in HACS, restart Home Assistant, then fully reload the browser/app. Choose **Edit dashboard → Add card → Sonos Follow Me**. No separate frontend repository or manual resource registration is required. Since v0.6.1, the integration creates/updates a dashboard module resource; installations with read-only YAML resources use a fallback that waits for the Home Assistant frontend to finish registering its elements.

```yaml
type: custom:sonos-follow-me-card
title: Sonos Follow Me
```

All rooms are discovered automatically. The graphical editor supports a custom title and selection of specific rooms. Optional YAML `entities` accepts a list of your room's **Follow Me switch entity IDs**; an omitted or empty list shows all rooms.

The card shows occupancy, speakers, remembered volume, cooldown status (updated approximately every 30 seconds), sensor states and source priority. Control Follow Me, volume reset, default volume **in percent**, cooldown, clear delay, fade duration and sensor mode directly. Additional settings/sensor details expand per room. It supports the languages below, mobile layouts, theme colors and visible service errors.

Controls use standard Home Assistant `switch`, `number` and `select` entities and normal entity permissions, so they also work in other cards and automations. Public settings persist through config-entry options and apply live without losing playback ownership. Device/sensor/source assignments and room names remain in the integration's Configure dialog; changing those still reloads the room.

From v0.4.2, default volume and TV offset use sliders with live value labels. The card displays the offset as a signed percentage; calculation remains additive (30% − 10% = 20%). Cooldown help explains that the next movement after expiry fades to the default volume when volume reset is enabled.

Since v0.6.1, the header and logo stay mounted during state changes, control actions and timed updates, preventing image flicker. Early module loading waits for Home Assistant's final custom-element registry before defining the card and editor.

If **Custom element doesn't exist: sonos-follow-me-card** persists:

1. Install **v0.6.1 or later** in HACS, **restart Home Assistant**, and wait for integration startup to finish.
2. Fully reload the dashboard. In the Companion App, reset the frontend cache if necessary.
3. **Settings → Dashboards → Resources** should contain `/sonos_follow_me/sonos-follow-me-card.js?v=0.6.2` with type **JavaScript module**. Read-only YAML resources are left intact and use the automatic frontend fallback. The same URL can also be added manually.
4. If that URL returns **404** in the browser, check integration setup and Home Assistant logs, and re-download the HACS package if its files are missing.

The integration must be configured and loaded. Disabled entities need enabling if their controls are desired.

Frontend development: `npm ci`, `npx playwright install chromium`, `npm test`. Browser tests use simulated Home Assistant states and services; they do not connect to real speakers.

## Languages (v0.6.2+)

Setup, options, entity labels, the dashboard card and its editor support **English, German, French, Spanish, Italian, Dutch, Polish, Swedish, Portuguese and Brazilian Portuguese**. The card uses your Home Assistant profile language, resolves regional variants such as `fr-CA` to French, and falls back to English for unsupported languages. Room and speaker names remain as you named them.

Editable JSON catalogs are checked for missing keys and mismatched placeholders. Shared card labels are generated from the integration's translations, so changes stay consistent. To correct a translation or add a language, follow the [translation maintenance guide](dev/TRANSLATIONS.md).

## Integration branding and HACS listing (v0.3.2+)

Local `brand/icon.png`, `icon@2x.png`, `logo.png` and `logo@2x.png` assets ship inside the integration. Home Assistant can use these for its integration UI; update through HACS, restart Home Assistant and reload the frontend. The transparent images support the built-in dark-image fallbacks.

The current HACS validator accepts these local brand assets; no separate submission to the central Brands repository is needed. Once an integration is in the catalog, the Marketplace also obtains its brand images from its latest release. Older HACS versions may not show local icons in the repository list. See the [custom integration branding documentation](https://contributors.home-assistant.io/marketplace/guides/integrations/#brand-images).

## Volume source (v0.6.0+)

Each room has a **Volume source** selector in its card, device and configuration:

- **Own room volume:** the existing remembered-volume and optional default/cooldown behavior. Existing rooms keep this mode after updating.
- **Follow group:** average of valid volume levels in the source group, excluding this destination and other active Follow Me destinations to avoid fade feedback.
- **Follow master:** the current group coordinator's volume, even if a different group member was selected as a source.

Following applies on entry and tracks changes throughout occupancy and the clear delay. Only the destination is adjusted; source volume levels are never set. Group membership and coordinator changes are tracked. Following ends on departure or disable; mute state is not mirrored.

Default volume, reset and cooldown controls are hidden in the card and device view while following and have no effect. The configuration's separate initial/default-volume step appears only for own room volume. Saved settings and remembered room volume survive mode changes. The TV offset remains available and is added once to the followed level; fade duration and clear delay still apply.

With no valid reference volume on entry, the room waits before joining instead of using a hidden default. If reference levels become unavailable during playback, it holds the last followed target until a valid reference returns.

## Room settings

| Setting | Meaning |
| --- | --- |
| Name | Name of the virtual room device |
| Sonos speaker | One destination speaker per room; cannot be assigned twice |
| Primary sensor | Reliable PIR / movement sensor |
| Additional sensors | Optional distinct presence sensors, e.g. radar; leave empty for a single-sensor room |
| Sources | Other Sonos players; the first playing source in the selected order wins |
| Sensor mode | `primary` (PIR starts, others hold) or `equal` |
| Clear delay | 0–3600 seconds; default 15 |
| Fade duration | 0–30 seconds per fade; default 3; 0 disables fading |
| Initial volume | 0–1; default 0.3; afterwards the remembered volume is used |
| Reset volume after absence | Optional, disabled by default (including existing rooms) |
| Default volume | Next visit’s target after cooldown, 0–1; default 0.3 |
| Volume cooldown | 0–10080 minutes; default 30; 0 means the next visit uses the default immediately |

Edit a room through its integration **Configure** button. Switch entities allow a dashboard toggle or a separate automation to enable/disable several rooms together.

### Optional volume cooldown

Enable **Reset volume after absence**, choose a **Default volume**, and set **Volume cooldown** (for example 30 minutes). The cooldown starts when the room becomes vacant **after the clear delay**. It does not change the speaker volume while the room is empty or interrupt ongoing playback.

Example: last volume 60%, default 25%, cooldown 30 minutes. Return after 10 minutes and music fades to 60%. That return cancels the old cooldown; the next departure starts a fresh 30 minutes. Return after 30 minutes or longer and music fades to 25%. With 0 minutes, each new visit after the room has cleared uses 25%.

Only valid occupancy counts: radar alone in primary mode cannot cancel the cooldown. A valid return resets it even if no music source is playing. An already-started cooldown survives a restart/reload, including time offline. Changing the cooldown setting applies the new duration to the saved vacancy time. Disabling Follow Me does not itself start a cooldown; existing cooldown timestamps remain saved. The existing restart/playback ownership behavior below still applies.

### Bathroom example

1. Radar falsely reports presence while PIR is off → nothing happens in primary mode.
2. Someone enters and PIR turns on → the speaker joins the first playing source.
3. The person sits still; PIR turns off, radar stays on → music continues.
4. Both sensors turn off → the clear delay starts.
5. A sensor turns on during that delay → the delay is cancelled.
6. All sensors stay off → fade out, unjoin, pause the detached speaker, restore its remembered volume.
7. A later radar-only detection cannot reactivate the room until PIR detects presence again.

An `unknown`, `unavailable` or missing sensor does **not** count as clear; it holds an already occupied room. Fix an unavailable sensor or disable the room if necessary.

## TV audio volume offset (v0.4.0+)

Each room has a **TV volume offset** in its options and dashboard card, from -100 to +100 **percentage points**. Zero disables the adjustment. Since v0.4.3, the offset applies to the volume selected for this visit. For example, a selected target of 30% with -10 points fades to 20%; +10 points fades to 40%. The card displays a signed percentage.

On joining, the integration checks the selected group's **coordinator** for `source: TV` or a Sonos TV stream ID beginning `x-sonos-htastream:`. A soundbar model, media title or `media_content_type: music` alone does not identify TV input. Selecting another member of the TV group as source still resolves its coordinator.

When TV is detected and the offset is nonzero, the target is **selected visit volume + offset**, clamped to 0–100%. With volume reset disabled, or when returning before cooldown expiry, the remembered volume is the base. Only after an enabled cooldown expires does the default volume become the base. Example: remembered 40%, default 25%, offset -10% gives 30% before expiry or with reset disabled, and 15% after expiry. AirPlay, music and unrecognized sources receive no TV offset. Manual volume changes during an adjusted TV visit affect that visit but do not overwrite music volume memory. Subsequent TV joins apply the offset once to the newly selected base; it does not accumulate across visits. The card indicates when TV volume is active.

Detection and offset changes apply on the next join. Switching from TV to music or back within an already-joined group does not automatically change its volume. Restart/playback-ownership limitations below still apply. TV behavior was tested using simulated Sonos states/services, not a connected soundbar.

## Silent startup / Sonos Move (v0.4.1+)

Entry now waits up to 10 seconds for Home Assistant to report both the expected group and playing destination before unmuting that destination (positive targets only) and fading in. Source/coordinator mute and other members are not changed.

After fading, volume/mute feedback gets up to 2 seconds to arrive. A still-zero or muted destination receives at most two additional unmute/fade attempts. An audible lower volume is respected. This is bounded startup recovery, not a continuous unmute watchdog; an intentional zero target is preserved. Disable, unload and occupancy expiry cancel the running start.

Reports matching our own volume commands from the previous 5 seconds are excluded from volume memory, preventing late fade-to-zero feedback from becoming the next target. A manual change to exactly one of those values within the window may also be excluded from memory, but the device volume is not undone. Metadata-only state events no longer rewrite volume memory.

Recovery attempts are logged under `custom_components.sonos_follow_me`; a failed start is also exposed as `startup_error` on the room's Follow Me switch and cleared at the next start. After a failure, new join attempts are held off for at least 30 seconds. For recurring problems, capture that error and the destination's `volume_level`, `is_volume_muted` and `group_members`.

Regression tests reproduce pre-fix failures with simulated persistent mute, delayed topology, ignored volume writes and stale volume reports. On 2026-10-05, v0.4.1 also passed nine checks against a physical Move through Home Assistant 2026.9.4, including muted startup, repeated joins and PIR/Radar behavior, plus ten isolated failure scenarios in that running HA instance. These results do not prove the original intermittent fault's root cause. A previously persisted zero volume is deliberately not replaced with a louder value.

## Playback behavior and limitations

- Start music on a source yourself. The integration copies an existing playing group; it does not select playlists or start a silent source. If a source starts while the room is occupied, its state change triggers joining.
- Each entry controls one Sonos media-player entity. Configure more entries for more rooms/speakers. A Sonos stereo pair exposed as one entity also works through the Sonos integration.
- Only speakers joined by this controller are automatically detached/paused. Already playing destinations, existing group members, and manually started source playback are not taken over. If a managed destination becomes coordinator for other speakers, automatic departure relinquishes control to avoid dismantling that group.
- Disabling a room stops its automation and leaves playback in place. It does not pause the group. Sensor evaluation restarts on enable; radar alone cannot re-arm primary mode.
- Volume changes during ordinary playback are remembered. Changes **during a fade** are not treated as a new target and may be overwritten; set fade duration to zero if immediate manual volume control is preferred.
- Volume and enable state persist across restarts. Occupancy and playback ownership deliberately reset on restart/reload. Previously joined playback is left untouched; detach/pause that destination manually once if you want automatic ownership on the next visit.
- Failed Sonos actions are logged. After the error cooldown, a later state event can retry joining; there is no continuous retry loop. Network outages can prevent cleanup or volume restoration.
- Disable your old Follow Me blueprint automations for these same speakers to prevent conflicting actions. No changes to your Home Assistant instance are made by publishing/installing the repository alone.

## Development

Python 3.14 and Home Assistant 2026.9.4:

```sh
python -m venv .venv
.venv/bin/pip install -r requirements-test.txt
.venv/bin/pytest -q
.venv/bin/ruff check custom_components tests dev
.venv/bin/ruff format --check custom_components tests dev
```

Tests cover the presence latch, UI validation, timer cancellation, source selection, playback ownership, service failures and interrupted departure. GitHub Actions runs the Python tests against the minimum supported Home Assistant release (2026.9.0) and the current stable release (2026.10.4), plus browser tests, Hassfest and full HACS validation including brand images. No HACS checks are excluded.

The [running-HA test lab](dev/README.md) provides Docker Desktop Sonos networking instructions, reproducible failure injection through real HA services, and an opt-in physical Move test runner. Local credentials, backups and detailed reports stay outside Git in `.local/`.

Based on the user-provided `Multiroom Sonos Follow Me (Universal)` automation, reimplemented as an event-driven integration. Bug reports and pull requests are welcome; include HA version, mode and a sanitized sequence of sensor states.

See [Home Assistant Sonos documentation](https://www.home-assistant.io/integrations/sonos/) and [HACS integration requirements](https://contributors.home-assistant.io/marketplace/guides/integrations/).
