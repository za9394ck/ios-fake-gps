#!/usr/bin/env python3
"""
ios-fake-gps sidecar.

A long-lived helper that owns one no-root iOS developer tunnel and one
LocationSimulation DVT channel. The macOS app speaks to this process over
stdin/stdout using newline-delimited JSON (NDJSON).

The tunnel is created in-process through pymobiledevice3's PreferredRsdTunnel.
On macOS this uses Apple's native remoted transport when available and falls
back to the pure-Python userspace tunnel. Both paths run without root/admin.

Protocol
--------
Commands in (one JSON object per line on stdin):
    {"cmd": "set",   "lat": 40.69, "lon": -74.04, "id": 12}
    {"cmd": "clear",                               "id": 13}
    {"cmd": "ping",                                "id": 14}
    {"cmd": "devices"}
    {"cmd": "quit"}

Events out (one JSON object per line on stdout):
    {"event": "ready",   "device": {...}}
    {"event": "ok",      "id": 12}
    {"event": "pong",    "id": 14}
    {"event": "devices", "devices": [...]}
    {"event": "error",   "message": "...", "fatal": true|false, "id": 12}
    {"event": "bye"}

stderr carries human-readable logs only; stdout is strictly NDJSON.
"""
import argparse
import asyncio
import json
import sys
from contextlib import AsyncExitStack
from typing import Any, Optional

from pymobiledevice3.remote.rsd_tunnel import PreferredRsdTunnel
from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation
from pymobiledevice3.usbmux import list_devices as list_usbmux_devices


def emit(obj: dict[str, Any]) -> None:
    """Write a single NDJSON event to stdout and flush immediately."""
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def log(*args: Any) -> None:
    print("[sidecar]", *args, file=sys.stderr, flush=True)


def describe(rsd: Any) -> dict[str, Any]:
    return {
        "udid": rsd.udid,
        "name": getattr(rsd, "name", None),
        "product_type": getattr(rsd, "product_type", None),
        "product_version": getattr(rsd, "product_version", None),
    }


def describe_usbmux(device: Any) -> dict[str, Any]:
    return {
        "serial": getattr(device, "serial", None),
        "connection": getattr(device, "connection_type", None),
    }


async def list_devices() -> list[dict[str, Any]]:
    devices = await list_usbmux_devices()
    return [describe_usbmux(d) for d in devices]


async def stdin_lines() -> "asyncio.StreamReader":
    """Wrap stdin as an asyncio StreamReader (works on macOS pipes)."""
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    return reader


async def run(udid: Optional[str]) -> int:
    # PreferredRsdTunnel is deliberately used instead of the old privileged
    # tunneld HTTP daemon. It never requires sudo/admin privileges.
    try:
        tunnel = PreferredRsdTunnel(serial=udid, autopair=True, prefer_native=True)
        rsd = await tunnel.aopen()
    except Exception as e:  # noqa: BLE001
        emit({
            "event": "error",
            "fatal": True,
            "code": "tunnel_failed",
            "message": f"Could not establish a no-root developer tunnel: {e}",
        })
        return 2

    async with AsyncExitStack() as stack:
        stack.push_async_callback(tunnel.aclose)
        try:
            dvt = await stack.enter_async_context(DvtProvider(rsd))
            loc = await stack.enter_async_context(LocationSimulation(dvt))
        except Exception as e:  # noqa: BLE001
            emit({
                "event": "error",
                "fatal": True,
                "code": "dvt_failed",
                "message": f"Could not open LocationSimulation: {e}. Is Developer Mode enabled?",
            })
            return 3

        emit({"event": "ready", "device": describe(rsd)})
        log("ready, no-root tunnel established for", rsd.udid)

        reader = await stdin_lines()
        while True:
            raw = await reader.readline()
            if not raw:
                break
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                emit({"event": "error", "fatal": False, "message": f"bad json: {line!r}"})
                continue

            cmd = msg.get("cmd")
            mid = msg.get("id")
            try:
                if cmd == "set":
                    await loc.set(float(msg["lat"]), float(msg["lon"]))
                    emit({"event": "ok", "id": mid})
                elif cmd == "clear":
                    await loc.clear()
                    emit({"event": "ok", "id": mid})
                elif cmd == "ping":
                    emit({"event": "pong", "id": mid})
                elif cmd == "devices":
                    emit({"event": "devices", "devices": await list_devices()})
                elif cmd == "quit":
                    break
                else:
                    emit({
                        "event": "error",
                        "fatal": False,
                        "id": mid,
                        "message": f"unknown cmd: {cmd!r}",
                    })
            except Exception as e:  # noqa: BLE001
                emit({"event": "error", "fatal": False, "id": mid, "message": str(e)})

        try:
            await loc.clear()
        except Exception:
            pass

    emit({"event": "bye"})
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="ios-fake-gps sidecar")
    p.add_argument("--udid", default=None, help="target device UDID (default: first)")
    p.add_argument(
        "--list", action="store_true", help="list USB/network-attached devices and exit"
    )
    return p.parse_args()


async def amain() -> int:
    ns = parse_args()
    if ns.list:
        try:
            emit({"event": "devices", "devices": await list_devices()})
            return 0
        except Exception as e:  # noqa: BLE001
            emit({"event": "error", "fatal": True, "code": "usbmux_failed", "message": str(e)})
            return 2
    return await run(ns.udid)


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(amain()))
    except KeyboardInterrupt:
        sys.exit(130)
