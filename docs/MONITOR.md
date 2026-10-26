# `monitor.py` — live 3D telemetry dashboard

## Purpose and value
Connects to the drones in `config.DRONES`, receives LPS-estimated XYZ positions, battery and estimator information, renders a 3D room and writes telemetry CSV. Useful for checking anchor coverage, detecting stale links and comparing relative positions **before** choreography flight. This is read-only: it sends no takeoff or motion commands.

## Arguments
| Argument | Required? | Default | Meaning |
|---|---|---|---|
| `--simulate` | No | Off | Synthetic moving drones; **no radio connection** |
| `--csv PATH` | No | `telemetry.csv` | Output CSV file; create parent folder if needed |
| `--help` | No | — | Show built-in help |

## Examples
```bash
python monitor.py --help
python monitor.py --simulate --csv logs/sim.csv
python monitor.py --csv logs/room_test.csv
```
In the last command, all configured Crazyflies should be powered on and accessible through the three dongles. Close the GUI window to stop the session. Do not run this concurrently with a flight script using the same radios unless you've explicitly engineered and tested shared access.

## What to expect
A 3D plot with labels, battery/status text, estimated nearest-neighbor distance and CSV records. `STALE_AFTER_S` controls when missing data is flagged. Position is an *estimate*; proximity warnings are not collision prevention.

## Modify for your show
- Edit `DRONES` to monitor a subset during initial tests.
- Edit `ROOM` to align the visualization with surveyed LPS coordinates.
- Adjust `LOG_PERIOD_MS` (200 ms = 5 Hz) to balance update frequency and bandwidth.
- Extend `Monitor` in `monitor.py` to log additional Crazyflie variables, observing radio and logging packet limits.

## Dependencies and order
Imports `config.py`, `cflib`, and Matplotlib. No other script must be run first. For real data, the LPS and radios must already be configured and operating. It does **not** automatically pass telemetry to `onboard_execution.py`.

> **Safety:** The code is experimental and has not been validated on your macOS/Crazyflie hardware. A passing geometric validation is not proof of safe flight. Use a clear controlled area, propeller guards, an operator ready to intervene, and verified LPS coordinates. None of these tools implements onboard collision avoidance or guaranteed multi-radio synchronization.

Run commands from the **project root** after `source .venv/bin/activate`. Use `python <script> --help` to check the flags accepted by your installed copy.
