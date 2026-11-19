"""Provision the Switch Timer test environment through Home Assistant's own APIs.

Idempotent: each step checks first and is skipped if already done.
  1. Onboarding with the test user.
  2. The Switch Timer hub (Add integration -> Switch Timer -> Submit).   [PROVISION_HUB]
  3. A storage dashboard "Switch Timer test" with cards for the test pump and fan.  [PROVISION_HUB]
Timers are NOT created here: the card creates them when an admin opens the dashboard.
"""

from __future__ import annotations

import asyncio
import json as json_module
import os
import sys
from typing import Any

import aiohttp

HA_URL = os.environ.get("HA_URL", "http://ha:8123").rstrip("/")
CLIENT_ID = f"{HA_URL}/"
PROVISION_HUB = os.environ.get("PROVISION_HUB", "true").lower() not in (
    "0",
    "false",
    "no",
)

USERNAME = "test"
PASSWORD = "test-pass-123"  # test environment only
DASHBOARD = "switch-timer-test"
CARDS = [
    {"type": "custom:switch-timer-card", "entity": "switch.test_pump"},
    {"type": "custom:switch-timer-card", "entity": "fan.test_fan"},
]


def log(message: str) -> None:
    print(f"[provision] {message}", flush=True)


async def request(
    session: aiohttp.ClientSession,
    method: str,
    path: str,
    *,
    json: Any = None,
    data: Any = None,
    token: str | None = None,
    ok: tuple[int, ...] = (200,),
) -> tuple[int, Any]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with session.request(
        method, HA_URL + path, json=json, data=data, headers=headers
    ) as resp:
        text = await resp.text()
        try:
            body = json_module.loads(text) if text else None
        except ValueError:
            body = text
        if resp.status not in ok:
            raise RuntimeError(f"{method} {path}: HTTP {resp.status} {body}")
        return resp.status, body


async def wait_for_ha(session: aiohttp.ClientSession) -> None:
    for _ in range(120):
        try:
            async with session.get(f"{HA_URL}/manifest.json") as resp:
                if resp.status == 200:
                    return
        except aiohttp.ClientError:
            pass
        await asyncio.sleep(2)
    raise RuntimeError("Home Assistant did not answer")


async def token_from_code(session: aiohttp.ClientSession, code: str) -> str:
    _, body = await request(
        session,
        "POST",
        "/auth/token",
        data={"grant_type": "authorization_code", "code": code, "client_id": CLIENT_ID},
    )
    return body["access_token"]


async def onboard(session: aiohttp.ClientSession) -> str:
    """Finish onboarding (only the missing steps); return an admin access token."""
    status, steps = await request(session, "GET", "/api/onboarding", ok=(200, 404))
    done = {step["step"] for step in steps if step["done"]} if status == 200 else None

    if done is None or "user" in done:
        log(f"onboarding user exists; logging in as {USERNAME!r}")
        _, flow = await request(
            session,
            "POST",
            "/auth/login_flow",
            json={
                "client_id": CLIENT_ID,
                "handler": ["homeassistant", None],
                "redirect_uri": CLIENT_ID,
            },
        )
        _, result = await request(
            session,
            "POST",
            f"/auth/login_flow/{flow['flow_id']}",
            json={"client_id": CLIENT_ID, "username": USERNAME, "password": PASSWORD},
        )
        token = await token_from_code(session, result["result"])
    else:
        log(f"onboarding: creating user {USERNAME!r}")
        _, body = await request(
            session,
            "POST",
            "/api/onboarding/users",
            json={
                "client_id": CLIENT_ID,
                "name": "Test",
                "username": USERNAME,
                "password": PASSWORD,
                "language": "en",
            },
        )
        token = await token_from_code(session, body["auth_code"])
        done = {"user"}

    if done is not None:
        for step, payload in (
            ("core_config", {}),
            ("analytics", {}),
            ("integration", {"client_id": CLIENT_ID, "redirect_uri": CLIENT_ID}),
        ):
            if step not in done:
                log(f"onboarding: {step}")
                await request(
                    session,
                    "POST",
                    f"/api/onboarding/{step}",
                    json=payload,
                    token=token,
                )
    return token


async def add_hub(session: aiohttp.ClientSession, token: str) -> None:
    _, entries = await request(
        session,
        "GET",
        "/api/config/config_entries/entry?domain=switch_timer",
        token=token,
    )
    if entries:
        log("Switch Timer hub already added")
        return
    _, flow = await request(
        session,
        "POST",
        "/api/config/config_entries/flow",
        json={"handler": "switch_timer"},
        token=token,
    )
    _, result = await request(
        session,
        "POST",
        f"/api/config/config_entries/flow/{flow['flow_id']}",
        json={},
        token=token,
    )
    if result.get("type") != "create_entry":
        raise RuntimeError(f"adding the hub failed: {result}")
    log("Switch Timer hub added")


async def add_dashboard(session: aiohttp.ClientSession, token: str) -> None:
    ws_url = HA_URL.replace("http", "ws", 1) + "/api/websocket"
    async with session.ws_connect(ws_url) as ws:
        await ws.receive_json()  # auth_required
        await ws.send_json({"type": "auth", "access_token": token})
        if (await ws.receive_json()).get("type") != "auth_ok":
            raise RuntimeError("websocket auth failed")
        msg_id = 0

        async def call(message: dict[str, Any]) -> dict[str, Any]:
            nonlocal msg_id
            msg_id += 1
            await ws.send_json({"id": msg_id, **message})
            while True:
                reply = await ws.receive_json()
                if reply.get("id") == msg_id and reply.get("type") == "result":
                    return reply

        dashboards = (await call({"type": "lovelace/dashboards/list"}))["result"]
        if not any(d["url_path"] == DASHBOARD for d in dashboards):
            await call(
                {
                    "type": "lovelace/dashboards/create",
                    "url_path": DASHBOARD,
                    "title": "Switch Timer test",
                    "icon": "mdi:timer-outline",
                    "mode": "storage",
                    "show_in_sidebar": True,
                    "require_admin": False,
                }
            )
            log(f"dashboard /{DASHBOARD} created")
        existing = await call({"type": "lovelace/config", "url_path": DASHBOARD})
        if existing.get("success"):
            log(f"dashboard /{DASHBOARD} already has a configuration")
            return
        saved = await call(
            {
                "type": "lovelace/config/save",
                "url_path": DASHBOARD,
                "config": {
                    "views": [{"title": "Switch Timer", "path": "test", "cards": CARDS}]
                },
            }
        )
        if not saved.get("success"):
            raise RuntimeError(f"saving the dashboard failed: {saved}")
        log(f"dashboard /{DASHBOARD}: cards for switch.test_pump and fan.test_fan")


async def main() -> int:
    async with aiohttp.ClientSession() as session:
        await wait_for_ha(session)
        token = await onboard(session)
        if PROVISION_HUB:
            await add_hub(session, token)
            await add_dashboard(session, token)
        else:
            log("first-install mode: the hub and dashboard are left for you to add")
    log("done")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except Exception as err:  # report any failure and exit non-zero
        log(f"FAILED: {err}")
        sys.exit(1)
