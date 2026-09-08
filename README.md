<p align="center">
  <img src="assets/icon_1024.png" alt="iOS Fake GPS icon" width="160" height="160">
</p>

<h1 align="center">iOS Fake GPS</h1>

<p align="center">A Lockito-style location simulator for iPhone — a clean macOS app.</p>

<p align="center">
  <a href="https://github.com/orestislef/ios-fake-gps/releases/latest"><img src="https://img.shields.io/badge/download-macOS%20app-blue" alt="Download"></a>
  <a href="https://github.com/orestislef/ios-fake-gps/actions/workflows/ci.yml"><img src="https://github.com/orestislef/ios-fake-gps/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/platform-macOS%20·%20Apple%20silicon-lightgrey" alt="Platform">
  <img src="https://img.shields.io/badge/iOS-17%2B-black" alt="iOS 17+">
</p>

<p align="center">
  <a href="https://github.com/orestislef/ios-fake-gps/releases/latest"><b>⬇️ Download for macOS</b></a>
  &nbsp;·&nbsp;
  <a href="#get-started">Get started</a>
  &nbsp;·&nbsp;
  <a href="https://github.com/orestislef/ios-fake-gps/discussions">Discussions</a>
  &nbsp;·&nbsp;
  ⭐ Star the repo if it helps you!
</p>

Set a fixed location **or** play a moving route (with adjustable speed, looping
and GPS jitter) on a **non-jailbroken** iPhone. Everything is driven from a
native macOS app — the iPhone just needs to be connected.

This is the iOS counterpart to Android's **Lockito**. Unlike Android, iOS has no
public "mock location" API, so an app installed *on the phone* can't fake GPS for
other apps. Instead the location is driven from a tethered Mac over Apple's
**developer tunnel** — the same mechanism used by Apple's developer tooling to
simulate location. Whatever you set is seen **system-wide** by apps on the device.

![The macOS app: route mode over the Bay Area, tunnel connected](docs/app.png)

> **Use responsibly.** This is meant for testing location-aware apps you own and
> for personal use. Using it to defeat anti-cheat, commit fraud, or bypass
> location-based access controls breaks those services' terms — and possibly the
> law.

## Get started

1. Download the latest **FakeGPS-macos-arm64.zip** from the
   [**Releases**](https://github.com/orestislef/ios-fake-gps/releases) page and
   unzip it.
2. Drag **FakeGPS.app** into your **Applications** folder.
3. First launch only: macOS may warn that the app is from an unidentified
   developer (the app isn't notarized). **Right-click the app → Open** and
   confirm. If it still refuses, run once:
   ```bash
   xattr -dr com.apple.quarantine /Applications/FakeGPS.app
   ```
4. Open the app, connect your iPhone with USB, tap **Trust** on the iPhone if
   prompted, and make sure **Developer Mode** is enabled.
5. Follow the in-app checklist and connect to the device.

**No admin password is required. No `sudo` is required.** The app establishes
the iOS developer tunnel in-process using `pymobiledevice3`'s no-root RSD
transport. On supported macOS versions it prefers Apple's native remoted
transport and can fall back to the pure-Python userspace tunnel.

The released app bundles its Python runtime and dependencies, so normal users
do **not** need to install Python or use the Terminal.

### What the checklist asks for

- **Connect your iPhone** — plug it in with USB, tap **Trust** if prompted, and
  turn on Developer Mode (Settings ▸ Privacy & Security ▸ Developer Mode).
- **Connect** — the app establishes the developer tunnel and opens the DVT
  LocationSimulation service automatically.

There is **no privileged tunnel daemon** and no administrator-password prompt.

## Features

- **Teleport** — click the map or search an address to jump the device there.
- **Route playback** — drop waypoints and move along them continuously.
- **Speed control** — 1–300 km/h, with smooth per-second interpolation.
- **Loop** a route indefinitely.
- **GPS jitter** — add a few metres of noise so the track looks natural.
- **Address / place search** powered by MapKit.
- **Live position marker**, plus distance and ETA readouts.
- **Auto-reset on exit** — disconnecting or quitting restores the phone's real
  location automatically.

## How it works

```
macOS app (SwiftUI + MapKit)            bundled engine              iPhone
  search / drop pins / route ─────────▶  pymobiledevice3  ──RSD/DVT──▶ every app
  speed · loop · jitter      ◀─────────  LocationSimulation             sees fake GPS
  interpolates the movement              (frozen, inside .app)
```

- The **app** owns the map, route editing and movement interpolation, so speed,
  pause, loop and jitter are controlled on the Mac side.
- The **engine** is a small Python program built on
  [pymobiledevice3](https://github.com/doronz88/pymobiledevice3) and frozen into
  a standalone binary inside `FakeGPS.app` — no Python is needed for normal use.
- The engine opens a **no-root RSD developer tunnel** and then a DVT
  `LocationSimulation` channel. On macOS, `PreferredRsdTunnel` tries the native
  remoted transport first and falls back to its userspace implementation.
- The old privileged `tunneld` daemon and its local HTTP control API are no
  longer used.

## Requirements

### End users

- A Mac on **Apple silicon** (the prebuilt app is `arm64`).
- An iPhone on **iOS 17 or newer**.
- USB connection for initial pairing/tunnel setup.
- **Developer Mode** enabled on the iPhone.

### Developers

- Xcode / Swift toolchain capable of building the macOS package.
- Python 3 with `venv` support.

## For developers — build from source

The project is a Swift Package (`macapp/`) plus a Python engine (`sidecar/`).

Set up the Python environment once:

```bash
./setup.sh
```

This creates the development environment under `~/.ios-fake-gps/venv` and
installs the pinned `pymobiledevice3` dependency.

Build the Swift package:

```bash
cd macapp
swift build
```

Run the macOS app from source:

```bash
cd macapp
swift run
```

Or open `macapp/Package.swift` in Xcode and run the package/app target.

Build the bundled, double-clickable application and release zip:

```bash
./scripts/build_app.sh
```

The build produces the app under `dist/` and bundles the Python runtime inside
it, so the resulting app does not require the developer's virtual environment.

Regenerate the icon:

```bash
~/.ios-fake-gps/venv/bin/python scripts/make_icon.py
iconutil -c icns assets/AppIcon.iconset -o assets/AppIcon.icns
```

### Project layout

```
ios-fake-gps/
├── macapp/Sources/FakeGPS/   the macOS app (SwiftUI + MapKit)
├── sidecar/                  Python location engine + runtime entry point
├── scripts/                  build_runtime.sh, build_app.sh, make_icon.py
├── assets/                   app icon
└── docs/                     screenshots
```

## Command-line testing (developers)

The sidecar can be run directly during development. This is useful for testing
the no-root tunnel and DVT location service without launching the SwiftUI app.

### 1. Check that the iPhone is visible over USB

From the repository root:

```bash
.venv/bin/python sidecar/fakegps_runtime.py usbmux --list
```

Expected output is JSON containing the connected device, for example:

```json
{"devices":[{"serial":"00008140-000211213484801C","connection":"USB"}]}
```

The serial/UDID will be different on every device.

### 2. Start the no-root sidecar

Start it as a long-running process and **do not pipe stdin** if you want to
observe the simulated location on the phone:

```bash
.venv/bin/python sidecar/fakegps_runtime.py sidecar \
  --udid YOUR_DEVICE_UDID
```

When the tunnel and DVT LocationSimulation service are ready, the sidecar
prints an event similar to:

```json
{"event":"ready","device":{"udid":"YOUR_DEVICE_UDID",...}}
```

No `sudo` or administrator password is required.

### 3. Set a location

While the sidecar is still running, type one JSON command and press Enter:

```json
{"cmd":"set","lat":47.6062,"lon":-122.3321}
```

For example, the coordinates above are Seattle downtown. A successful command
returns:

```json
{"event":"ok","id":null}
```

Leave the sidecar running while checking Apple Maps or another location-aware
app on the iPhone. If the process exits, its cleanup handler clears the
simulated location.

You can also use an explicit request ID:

```json
{"cmd":"set","lat":47.6062,"lon":-122.3321,"id":1}
```

### 4. Clear the simulated location

To restore the phone's real GPS location:

```json
{"cmd":"clear"}
```

Expected response:

```json
{"event":"ok","id":null}
```

### 5. Quit cleanly

```json
{"cmd":"quit"}
```

The sidecar clears the simulated location before closing the DVT/tunnel
connection and emits:

```json
{"event":"bye"}
```

### Supported sidecar commands

| Command | Description |
|---|---|
| `set` | Set simulated latitude/longitude |
| `clear` | Restore real device location |
| `ping` | Health check; returns `pong` |
| `devices` | List USB/network-visible devices |
| `quit` | Clear location and shut down |

For example:

```text
{"cmd":"ping","id":2}
{"cmd":"devices"}
{"cmd":"clear","id":3}
{"cmd":"quit"}
```

The sidecar uses newline-delimited JSON (NDJSON): one JSON object per input
line and one event per output line. Human-readable diagnostics are written to
stderr; stdout is reserved for protocol events.

## Troubleshooting

- **App won't open ("unidentified developer")** — right-click → Open, or run
  `xattr -dr com.apple.quarantine /Applications/FakeGPS.app`.
- **iPhone never detected** — check the USB cable, tap **Trust** on the phone,
  and confirm Developer Mode is enabled. If necessary, reconnect the phone or
  reboot it.
- **Could not establish a no-root developer tunnel** — make sure the iPhone is
  unlocked, trusted, connected over USB, and Developer Mode is enabled. Close
  other developer/tunneling tools that may be holding the device connection.
- **Could not open LocationSimulation** — verify Developer Mode and allow a few
  seconds for the developer services to become available after connecting.
- **The location changes and immediately returns to the real location** — make
  sure the sidecar process is still running. The sidecar automatically clears
  the simulated location when it receives EOF or exits.
- **`urllib3` reports `NotOpenSSLWarning` on an older local Python** — this is a
  warning from the local Python/OpenSSL combination. It does not by itself mean
  that the RSD/DVT tunnel failed; check whether the sidecar reaches the
  `ready` event.

## Limitations

- The Mac must stay connected to the iPhone while the developer tunnel is in
  use. Wi-Fi may be available after the device has been paired, depending on
  the developer transport and device state.
- This changes the location reported through Apple's developer location
  simulation path. It does **not** fake Wi-Fi, cell-tower, Bluetooth, or other
  independent signals, so apps that cross-check multiple signals may detect a
  mismatch.
- The prebuilt release is currently targeted at Apple silicon Macs.

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) and the
[Code of Conduct](CODE_OF_CONDUCT.md). For security reports, see
[SECURITY.md](SECURITY.md).

## License & use

Released under the [MIT License](LICENSE). Please read the
[Disclaimer](DISCLAIMER.md): this tool is for lawful testing and personal use
only — not for fraud, evading anti-cheat/anti-fraud systems, or deceiving third
parties.
