"""Constants for Sonos Follow Me."""

DOMAIN = "sonos_follow_me"
VOLUME_MODES = ["room", "group", "master"]
ROOM_VOLUME_FIELDS = {"volume", "volume_reset", "default_volume", "volume_cooldown"}
DEFAULTS = {
    "secondary": [],
    "mode": "primary",
    "off_delay": 15,
    "fade_seconds": 3,
    "volume": 0.3,
    "volume_mode": "room",
    "volume_reset": False,
    "default_volume": 0.3,
    "volume_cooldown": 30,
    "tv_volume_offset": 0,
}
