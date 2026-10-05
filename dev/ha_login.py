"""Sign into a local HA test instance without putting a password in shell history."""

import argparse
import asyncio
import getpass
import json
import os
from pathlib import Path

import aiohttp


async def login(args):
    url = args.url.rstrip("/")
    username = input("Home Assistant username: ")
    password = getpass.getpass("Home Assistant password: ")
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
        async with session.post(
            url + "/auth/login_flow",
            json={
                "client_id": url + "/",
                "handler": ["homeassistant", None],
                "redirect_uri": url + "/?auth_callback=1",
            },
        ) as response:
            response.raise_for_status()
            flow = await response.json()
        async with session.post(
            url + "/auth/login_flow/" + flow["flow_id"],
            json={"client_id": url + "/", "username": username, "password": password},
        ) as response:
            response.raise_for_status()
            flow = await response.json()
        if flow["type"] != "create_entry":
            raise RuntimeError("Login did not complete (check credentials or MFA requirements)")
        async with session.post(
            url + "/auth/token",
            data={
                "grant_type": "authorization_code",
                "code": flow["result"],
                "client_id": url + "/",
            },
        ) as response:
            response.raise_for_status()
            auth = await response.json()
    path = Path(args.auth_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as handle:
        os.fchmod(handle.fileno(), 0o600)
        json.dump(auth, handle)
    print("Authentication saved to private local file:", path.resolve())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8123")
    parser.add_argument("--auth-file", default=".local/ha-auth.json")
    asyncio.run(login(parser.parse_args()))
