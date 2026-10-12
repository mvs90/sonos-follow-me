"""Opt-in development simulator. It never contacts or controls physical speakers."""

import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import discovery

DOMAIN = "sonos_follow_me_lab"
CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass, config):
    lab = hass.data[DOMAIN] = {
        "entities": {},
        "generation": 0,
        "tasks": set(),
        "calls": [],
        "pir": False,
        "radar": False,
        "join_delay": 0,
        "never_join": False,
        "drop_positive": 0,
        "always_zero": False,
        "sticky_mute": False,
        "tv": False,
        "source_playing": True,
        "member_joined": False,
    }

    async def configure(call):
        data = dict(call.data)
        if data.pop("reset", False):
            lab["generation"] += 1
            for task in list(lab["tasks"]):
                task.cancel()
            lab.update(
                pir=False,
                radar=False,
                join_delay=0,
                never_join=False,
                drop_positive=0,
                always_zero=False,
                sticky_mute=False,
                tv=False,
                source_playing=True,
                member_joined=False,
                calls=[],
            )
            for entity in lab["entities"].values():
                if hasattr(entity, "reset"):
                    entity.reset()
        muted = data.pop("muted", None)
        lab.update(data)
        if muted is not None:
            lab["entities"]["destination"]._attr_is_volume_muted = muted
        for entity in lab["entities"].values():
            entity.async_write_ha_state()

    hass.services.async_register(
        DOMAIN,
        "configure",
        configure,
        schema=vol.Schema(
            {
                **{
                    vol.Optional(k): cv.boolean
                    for k in (
                        "reset",
                        "pir",
                        "radar",
                        "never_join",
                        "always_zero",
                        "sticky_mute",
                        "muted",
                        "tv",
                        "source_playing",
                        "member_joined",
                    )
                },
                vol.Optional("join_delay"): vol.All(vol.Coerce(float), vol.Range(min=0, max=30)),
                vol.Optional("drop_positive"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
            }
        ),
    )
    for platform in ("media_player", "binary_sensor"):
        await discovery.async_load_platform(hass, platform, DOMAIN, {}, config)
    return True
