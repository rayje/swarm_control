# `coordinated_flight.py` — two-drone takeoff / hover / land

## Purpose and value
A deliberately limited two-drone flight test to verify radio connections, LPS start positions, estimator stability and basic High-Level Commander operation. **It does not execute choreography or move horizontally.** Useful before attempting uploaded trajectories.

## Flags
| Argument | Required? | Default | Behavior |
|---|---|---|---|
| `--drones CFXX CFYY` | No | `CF01 CF02` | **Exactly two** distinct keys from `config.DRONES` |
| `--fly` | No | Off | Enables real connections, preflight and takeoff/landing |
| `--help` | No | — | Print help |

## Examples
```bash
python coordinated_flight.py
python coordinated_flight.py --drones CF03 CF04
python coordinated_flight.py --drones CF01 CF02 --fly
```
The first two examples are **dry runs**: they print the plan without connecting. The last one can spin motors and fly after an interactive Enter confirmation.

## Mandatory configuration before `--fly`
In `coordinated_flight.py`, set `TAKEOFF_XY_LPS` for the selected drone IDs to surveyed **absolute LPS** XY positions. `None` intentionally blocks real flight. Other editable constants include `ALTITUDE_M` (0.8), `HOVER_S` (5), `TAKEOFF_S` (3), `LAND_S` (3), `MIN_START_SEPARATION_M` (1.5), `MAX_START_POSITION_ERROR_M` (0.20), `MAX_STATIONARY_SPREAD_M` (0.15), and `BATTERY_MIN_V` (3.75). These are illustrative thresholds, not a safety certification.

## Runtime sequence
1. Connect to both URIs using `Swarm`.
2. Collect 8 position samples and one battery sample per drone.
3. Reject unstable position, low voltage, pad mismatch or insufficient starting separation.
4. Wait for operator confirmation; issue concurrent takeoff commands.
5. Hover, then request landing in a `finally` block.

`Swarm.parallel_safe()` dispatches commands concurrently, **not at exactly the same time**. Landing on errors is best-effort, not guaranteed recovery.

## Dependencies and workflow
Imports `config.py` and `cflib`. It does **not** depend on `monitor.py`, the choreography engine or `flight_tracking.py`. Run after your read-only LPS tests, and before multi-drone choreography flights.

> **Safety:** The code is experimental and has not been validated on your macOS/Crazyflie hardware. A passing geometric validation is not proof of safe flight. Use a clear controlled area, propeller guards, an operator ready to intervene, and verified LPS coordinates. None of these tools implements onboard collision avoidance or guaranteed multi-radio synchronization.

Run commands from the **project root** after `source .venv/bin/activate`. Use `python <script> --help` to check the flags accepted by your installed copy.
