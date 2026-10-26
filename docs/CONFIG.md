# `config.py` — radios and dashboard configuration

## What it does / why it matters
This is a Python settings module imported by `monitor.py`, `coordinated_flight.py`, and `onboard_execution.py`. **Do not run it as a command.** It maps friendly names (`CF01` … `CF10`) to radio URIs and sets dashboard room geometry and telemetry thresholds.

## Example radio URI
```python
DRONES = {
    'CF01': 'radio://0/40/2M/E7E7E7E701',
    'CF05': 'radio://1/60/2M/E7E7E7E705',
    'CF08': 'radio://2/80/2M/E7E7E7E708',
}
```
The fields after `radio://` are **USB dongle index / RF channel / bitrate / drone address**. The shipped `config.py` already contains a 4+3+3 distribution, with example addresses; replace these with the real values. Each Crazyflie's channel, bitrate and address must match its URI. USB indices can change after reconnection.

## Settings reference
| Setting | Meaning | Effect |
|---|---|---|
| `DRONES` | Dictionary of drone IDs to URIs | All live connection scripts |
| `ROOM['width']`, `['depth']`, `['height']` | Room dimensions in meters | Dashboard axes only |
| `ROOM['origin_xyz']` | LPS location of room origin | Dashboard coordinate display |
| `ROOM['yaw_deg']` | Room orientation relative to LPS | Dashboard coordinate display |
| `LOG_PERIOD_MS` | Logging period (default 200 ms) | Dashboard telemetry bandwidth |
| `STALE_AFTER_S` | Telemetry stale threshold | Dashboard status indicator |
| `MIN_SEPARATION_WARNING_M` | Display-only separation warning | Dashboard annotation; **not an interlock** |

**Crucial distinction:** `config.py`'s `ROOM` affects the dashboard; choreography uses the `room` field inside each show JSON. Actual flight conversion is separately configured as `LPS_TRANSFORM` in `onboard_execution.py`. Changing one does **not** update the others.

## Verify before flight
Ensure the drone IDs in a show JSON exist in `DRONES`. Confirm actual pad coordinates against LPS telemetry; do not assume room-centered coordinates are LPS coordinates.

> **Safety:** The code is experimental and has not been validated on your macOS/Crazyflie hardware. A passing geometric validation is not proof of safe flight. Use a clear controlled area, propeller guards, an operator ready to intervene, and verified LPS coordinates. None of these tools implements onboard collision avoidance or guaranteed multi-radio synchronization.

Run commands from the **project root** after `source .venv/bin/activate`. Use `python <script> --help` to check the flags accepted by your installed copy.
