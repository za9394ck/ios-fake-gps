#!/usr/bin/env python3
"""
Combined runtime entry point, frozen by PyInstaller into a single standalone
binary that ships inside FakeGPS.app — so end users need no Python install.

Usage:
    fakegps-runtime sidecar [args...]   # runs the no-root location sidecar
    fakegps-runtime usbmux [args...]    # lists attached devices without a tunnel
"""
import sys


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    rest = sys.argv[2:]

    if mode == "sidecar":
        import asyncio
        import gpsd_helper
        sys.argv = ["gpsd_helper"] + rest
        return asyncio.run(gpsd_helper.amain())

    if mode == "usbmux":
        import asyncio
        import json

        async def _list():
            from pymobiledevice3.usbmux import list_devices
            out = []
            for d in await list_devices():
                out.append({
                    "serial": getattr(d, "serial", None),
                    "connection": getattr(d, "connection_type", None),
                })
            return out

        try:
            devices = asyncio.run(_list())
            print(json.dumps({"devices": devices}))
        except Exception as e:  # noqa: BLE001
            print(json.dumps({"devices": [], "error": str(e)}))
        return 0

    sys.stderr.write("usage: fakegps-runtime {sidecar|usbmux} [args...]\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
