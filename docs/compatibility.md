# Compatibility verification — 2026-10-28

Sonos Follow Me v0.6.3 was checked against the following official Home Assistant
containers on Docker Desktop, Linux aarch64. This release records compatibility
and adds reproducible test infrastructure; it does not change playback behavior.

| Check | Stable 2026.10.4 | Preview 2026.11.0.dev202610281312 |
| --- | --- | --- |
| Python regression tests using the image's HA dependencies | 125 passed | 125 passed |
| Live startup/failure and TV-offset scenarios | 14 passed | 14 passed |
| Live single-sensor, radar-hold and device grouping checks | 5 passed | 5 passed |
| Live group/master following and settings visibility checks | 5 passed | 5 passed |
| Two independent simulated rooms, 20 entities on two devices | Passed | Passed |
| Settings, entity IDs and device IDs after a container restart | Preserved | Preserved |
| Translations through HA's frontend API | 760 strings / 10 locales | 760 strings / 10 locales |
| One versioned card resource; delivered JS matches repository | Passed | Passed |
| Real HA dashboard: card, sliders, mode changes, graphical editor | Passed | Passed |

The 31 standalone browser regression tests also passed, including the early
custom-element registration case, persistent logo, mobile layouts, all languages,
regional fallbacks, plural forms and service-error handling.

The stable installation was upgraded from 2026.10.2 after an offline backup of its
configuration volume. Its two existing room entries and 18 public setting states
were preserved before running the tests. The preview starts with separate storage,
a separate account and simulated speakers; it does not share the stable database
or production device configuration. Both test rooms are left disabled.

## Reproducible images

- Stable: `ghcr.io/home-assistant/home-assistant@sha256:23f4dfbb69ce76315dbc4de7915504f1c2dcecd7ca2648113a493a385972e133`
- Preview: `ghcr.io/home-assistant/home-assistant@sha256:4f9fc9aaf7667902170d152dd29843559cd66dc358db4a28125994b4b9f513c4`

The preview is the development image resolved on 2026-10-28, not a released
November beta or the final 2026.11 release. The `dev` tag changes over time; the
digest identifies the exact image tested here. See the official
[release channels](https://contributors.home-assistant.io/releases/reference/versions/).

## Scope and limits

Live cases exercise real config flows, entity/service dispatch, event handling,
persistence and frontend loading. They inject mute, missing topology, dropped
volume writes and permanent failures into in-memory players. Expected retry/error
logs from those cases are assertions of recovery behavior, not failed test runs.
No unexpected Sonos Follow Me errors were observed after the final restart.

The physical Move was unavailable during this run, so there is no new hardware
certification for these HA versions. Earlier hardware tests are documented in the
README. Soundbar TV input remains simulated. HACS/Marketplace installation itself
was not exercised; the integration was mounted into each container. Unrelated
integrations in the shared stable instance still report unavailable local devices
and their own warnings; this report assesses Sonos Follow Me.

The passing preview supports this particular build. It cannot establish that an
unreleased final version, later changes or every Sonos device will work. CI now
also tests the latest development image on each push, pull request or manual run.
Its printed HA version identifies the build covered by that run. There is no
scheduled update or unattended upgrade of either local container.

See the [test-lab instructions](../dev/README.md) to reproduce these checks. Private
credentials, configuration backups and raw reports are excluded from Git.
