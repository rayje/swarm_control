# `choreography_cli.py` — generate, validate, preview and export

## Purpose and value
Reads a show JSON, creates per-drone seventh-order polynomial paths, checks room boundaries and separation, exports trajectory CSVs, and optionally opens a 3D animated preview. **This script never commands motors or connects to Crazyradio.** Use it to iterate on choreography safely offline.

## Arguments
| Argument | Required? | Default | Meaning |
|---|---|---|---|
| `show` | **Yes** | — | Positional path to show JSON (not a flag) |
| `--output DIR` | No | `output/show` | Folder for generated trajectory CSV and show JSON |
| `--preview` | No | Off | Show animated 3D preview |
| `--step SECONDS` | No | `0.02` | Time sampling interval for geometric validation; smaller is slower |
| `--help` | No | — | Show built-in usage |

## Examples
```bash
python choreography_cli.py shows/two_drone_demo.json
python choreography_cli.py shows/ten_drone_grid.json --preview
python choreography_cli.py shows/two_drone_demo.json --output output/test_a --step 0.01 --preview
```
`--step 0.01` means a 10 ms validation sample interval, **not** a flight control frequency. The validator includes a conservative between-sample motion allowance but does not model LPS error, tracking error, or obstacles. A passing result does not guarantee safety.

## Show JSON structure
```json
{
  "room": {"width_m": 6.096, "depth_m": 4.572, "height_m": 2.7432},
  "minimum_separation_m": 0.9,
  "wall_margin_m": 0.65,
  "floor_clearance_m": 0.0,
  "ceiling_clearance_m": 0.6,
  "drones": ["CF01", "CF02"],
  "launch_positions_room_m": {"CF01": [-1,0,0], "CF02": [1,0,0]},
  "phases": [
    {"type": "takeoff", "altitude_m": 1.0, "duration_s": 4},
    {"type": "hold", "duration_s": 3},
    {"type": "formation", "name": "line", "parameters": {"span": 2.0, "altitude": 1.0}, "duration_s": 5},
    {"type": "land", "duration_s": 4}
  ]
}
```
The supported phase types are `takeoff`, `hold`, `formation`, and `land`; formation names are `line`, `circle`, `grid`. Durations are seconds; positions and sizes are meters. Drones are assigned positions in the order of the `drones` array. Avoid intersecting transition paths and check all intermediate motion, not just formation endpoints.

## How to modify
Edit `shows/*.json` for a new performance. To implement a new formation, add a generator to `FORMATIONS` in `choreography/engine.py` that returns one `[x,y,z,yaw]` row per drone. Rerun validation and preview after every change.

## Dependencies and order
Imports `choreography.engine`, NumPy and (for preview) Matplotlib. No other script must run first. `onboard_execution.py` can load the **same show JSON directly**; it does not require you to run this CLI or import the exported CSVs beforehand.

> **Safety:** The code is experimental and has not been validated on your macOS/Crazyflie hardware. A passing geometric validation is not proof of safe flight. Use a clear controlled area, propeller guards, an operator ready to intervene, and verified LPS coordinates. None of these tools implements onboard collision avoidance or guaranteed multi-radio synchronization.

Run commands from the **project root** after `source .venv/bin/activate`. Use `python <script> --help` to check the flags accepted by your installed copy.
