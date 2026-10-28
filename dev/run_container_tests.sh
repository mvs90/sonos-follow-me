#!/bin/sh
# Run inside an official HA container with this repository as the working directory.
# The separate venv inherits the exact image's HA dependencies; do not install HA.
set -eu
python3 -c 'from homeassistant.const import __version__; print("Testing Home Assistant", __version__, flush=True)'
test_env=$(mktemp -d /tmp/sonos-follow-me-tests.XXXXXX)
trap 'rm -rf "$test_env"' EXIT
python3 -m venv --system-site-packages "$test_env"
sed '/^homeassistant==/d' requirements-test.txt > "$test_env/requirements.txt"
"$test_env/bin/pip" install --quiet -r "$test_env/requirements.txt"
"$test_env/bin/ruff" check --no-cache custom_components tests dev
"$test_env/bin/ruff" format --check --no-cache custom_components tests dev
PYTHONDONTWRITEBYTECODE=1 "$test_env/bin/pytest" -q -p no:cacheprovider
