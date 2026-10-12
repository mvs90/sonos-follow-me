"""Small authenticated client for an explicitly selected Home Assistant test instance."""

import asyncio
import json
import os
from pathlib import Path

import aiohttp


class HA:
    def __init__(self, url, auth_file=None):
        self.url = url.rstrip("/")
        self.auth_file = Path(auth_file) if auth_file else None
        self.session = None
        self.token = os.environ.get("HA_TOKEN")

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=40))
        if self.auth_file:
            auth = json.loads(self.auth_file.read_text())
            if "refresh_token" in auth:
                async with self.session.post(
                    self.url + "/auth/token",
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": auth["refresh_token"],
                        "client_id": self.url + "/",
                    },
                ) as response:
                    response.raise_for_status()
                    auth.update(await response.json())
                self.auth_file.chmod(0o600)
                self.auth_file.write_text(json.dumps(auth))
            self.token = auth["access_token"]
        if not self.token:
            await self.session.close()
            raise RuntimeError("Provide HA_TOKEN or --auth-file; never commit credentials")
        return self

    async def __aexit__(self, *args):
        await self.session.close()

    async def request(self, method, path, data=None):
        async with self.session.request(
            method,
            self.url + path,
            json=data,
            headers={"Authorization": "Bearer " + self.token},
        ) as response:
            if response.status >= 400:
                raise RuntimeError(f"{method} {path}: {response.status}: {await response.text()}")
            return await response.json()

    async def get(self, path):
        return await self.request("GET", path)

    async def post(self, path, data):
        return await self.request("POST", path, data)

    async def finish_room_flow(self, path, data):
        """Submit wiring, then the optional room-volume step with preserved defaults."""
        volume_keys = {"volume", "volume_reset", "default_volume", "volume_cooldown"}
        result = await self.post(path, {k: v for k, v in data.items() if k not in volume_keys})
        if result.get("type") == "form" and result.get("step_id") == "volume":
            values = {
                field["name"]: data.get(field["name"], field.get("default"))
                for field in result["data_schema"]
            }
            result = await self.post(path, values)
        return result

    async def service(self, domain, service, entity_id=None, **data):
        if entity_id:
            data["entity_id"] = entity_id
        return await self.post(f"/api/services/{domain}/{service}", data)

    async def state(self, entity_id):
        return await self.get("/api/states/" + entity_id)

    async def wait(self, entity_id, predicate, timeout=20):
        async with asyncio.timeout(timeout):
            while True:
                state = await self.state(entity_id)
                if predicate(state):
                    return state
                await asyncio.sleep(0.2)

    async def ws(self, message):
        async with self.session.ws_connect(self.url + "/api/websocket") as ws:
            await ws.receive_json()
            await ws.send_json({"type": "auth", "access_token": self.token})
            if (await ws.receive_json())["type"] != "auth_ok":
                raise RuntimeError("WebSocket authentication failed")
            await ws.send_json({"id": 1, **message})
            result = await ws.receive_json()
            if not result.get("success"):
                raise RuntimeError(result)
            return result["result"]
