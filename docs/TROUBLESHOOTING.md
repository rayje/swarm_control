# Troubleshooting and known limitations

| Symptom | Likely issue | Check |
|---|---|---|
| `ModuleNotFoundError: cflib` | Wrong interpreter/venv | `source .venv/bin/activate`; `python -m pip install -r requirements.txt` |
| `ModuleNotFoundError: numpy` | NumPy not explicitly pinned | `python -m pip install numpy` |
| Radio connection fails | Wrong URI, USB index, RF channel, address or bitrate | Compare actual client URI; test one drone; ensure client closed |
| Wrong drone appears | USB index changed | Re-enumerate dongles and check URI mapping |
| Monitor shows wrong room position | `config.ROOM` transform mismatched | Survey room origin and yaw; confirm LPS frame |
| `LPS_TRANSFORM` error | Real-flight conversion not configured | Set surveyed translation and yaw in `onboard_execution.py` |
| Pad mismatch | Launch position or frame incorrect | Compare drone's reported LPS XYZ with transformed pad XYZ |
| Validation rejects show | Paths too close or outside room | Change formation geometry/durations; inspect report; do not disable validation |
| `--confirm-flight` alone doesn't fly | Needs `--fly` too | This is intentional two-step opt-in |
| Flight command waits for input | Operator approval | Type `TAKEOFF` only after clearance checks; otherwise cancel |
| Unexpected telemetry error | LPS estimator drift, delay or bad transform | Compare static measured locations and tracking timestamps |
| Preview window missing | Matplotlib backend issue | Run on macOS desktop with a GUI backend |

## Important implementation caveats
- `onboard_execution.py` uploads only airborne segments, not takeoff/landing segments.
- `flight_tracking.py` tracks approximate host dispatch offsets, not synchronized onboard clocks.
- `monitor.py` proximity warnings do not stop drones.
- `floor_clearance_m` in show JSON is not currently enforced as a positive clearance by the trajectory validator.
- A `--step` validation setting controls offline geometry sampling, not onboard control rate.
- No script guarantees recovery from lost positioning or radio links.

Consult [WORKFLOW.md](WORKFLOW.md) for safe staging and [COMMAND_REFERENCE.md](COMMAND_REFERENCE.md) for exact invocation examples.

> **Safety:** The code is experimental and has not been validated on your macOS/Crazyflie hardware. A passing geometric validation is not proof of safe flight. Use a clear controlled area, propeller guards, an operator ready to intervene, and verified LPS coordinates. None of these tools implements onboard collision avoidance or guaranteed multi-radio synchronization.

Run commands from the **project root** after `source .venv/bin/activate`. Use `python <script> --help` to check the flags accepted by your installed copy.
