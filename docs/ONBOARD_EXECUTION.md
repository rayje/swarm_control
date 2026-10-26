# `onboard_execution.py` — upload and fly polynomial trajectories

## Purpose and value
Loads and validates show JSON, converts room-centered trajectories into LPS coordinates, uploads the airborne Poly4D segments to selected Crazyflies, uses the onboard High-Level Commander to take off, execute and land, and optionally logs flight tracking. **This is the only trajectory-flight entry point** in this project.

## Command arguments
| Argument | Required? | Default | Meaning |
|---|---|---|---|
| `show` | **Yes** | — | Positional path to show JSON |
| `--drones CF01 [CF02 ...]` | No | `CF01` | One or more drone IDs; all must exist in show and `config.DRONES` |
| `--fly` | No | Off | Enables actual radio connections and motor/flight commands |
| `--confirm-flight` | Required **for real flight** | Off | Second explicit opt-in; alone does not fly |
| `--track-csv PATH` | No | Auto-named file under `logs/` on flight | Where telemetry and tracking records are saved during real flight |
| `--help` | No | — | Print usage |

## Examples
```bash
# Offline: validate/prepare one drone; no radio activity
python onboard_execution.py shows/two_drone_demo.json --drones CF01

# Offline: check two drones
python onboard_execution.py shows/two_drone_demo.json --drones CF01 CF02

# REAL FLIGHT: only after all configuration and safety checks
python onboard_execution.py shows/two_drone_demo.json --drones CF01 --fly --confirm-flight --track-csv logs/cf01.csv
```
`--fly --confirm-flight` permits actual takeoff, and the program then asks you to type `TAKEOFF`. Never copy the live-flight command before surveying pads, checking clearance and testing the hardware path.

## Critical configuration in this file
```python
LPS_TRANSFORM = {'translation_m': None, 'yaw_deg': None}
```
Replace `None` with surveyed `[tx,ty,tz]` in meters and yaw in degrees. Room coordinates are rotated and translated into the LPS frame; the flight path is blocked while this transform is unset. Verify direction/sign of yaw with measured points. The show JSON launch pads must match actual positions after transformation.

Other constants: `TRAJECTORY_ID=1`, `TAKEOFF_DURATION_S=4`, `LAND_DURATION_S=4`, `MAX_PAD_ERROR_M=0.20`, `MAX_HOVER_ERROR_M=0.25`, `MAX_POSITION_SPREAD_M=0.12`, `MIN_BATTERY_V=3.75`, `MAX_TOTAL_SEGMENTS=20`. These are code-level settings, not CLI flags. The script uploads only middle (airborne) phases; the first takeoff and final land phases are performed using firmware commands.

## Execution and dependencies
1. `prepare()` loads and validates **all** drones' trajectories, even if selecting only one.
2. It checks show structure (takeoff first, land last), equal middle durations, continuity, and return to launch XY.
3. On `--fly`, it checks the transform and confirmation flags; connects via `Swarm`.
4. Checks battery, estimator stability and launch-pad alignment; uploads trajectory memory.
5. Starts `FlightTracker`, asks for interactive approval, takes off, verifies hover, starts uploaded trajectories, waits, and requests landing.
6. Writes CSV and a summary.

Imports `config.py`, `choreography/engine.py`, `flight_tracking.py`, `cflib`, and NumPy. **You do not have to run** `choreography_cli.py` or `flight_tracking.py` first. Run offline preview separately as a recommended validation step.

## Known limitations that matter
- Starts are **best-effort concurrent**, not clock-synchronized across the three radios.
- Tracker time alignment is approximate; onboard actual start instants are not measured.
- No real-time tracking-deviation abort, collision avoidance or verified recovery from radio/LPS failure.
- `--drones CF01` selects one path from a multi-drone show; confirm that its path and pad are appropriate for single-aircraft testing.
- Current code should be reviewed on your installed cflib/firmware versions before any propellers-on test.

> **Safety:** The code is experimental and has not been validated on your macOS/Crazyflie hardware. A passing geometric validation is not proof of safe flight. Use a clear controlled area, propeller guards, an operator ready to intervene, and verified LPS coordinates. None of these tools implements onboard collision avoidance or guaranteed multi-radio synchronization.

Run commands from the **project root** after `source .venv/bin/activate`. Use `python <script> --help` to check the flags accepted by your installed copy.
