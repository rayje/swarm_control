# `choreography/engine.py` — trajectory-generation library

## What it does
A reusable Python module, **not a standalone command**. It loads show JSON, generates polynomial segments, evaluates positions at arbitrary times, validates sampled paths and exports CSV files. Both `choreography_cli.py` and `onboard_execution.py` import it.

## Public functions
| Function | Inputs | Result |
|---|---|---|
| `load_show(path)` | JSON path | `(spec, names, pads)` |
| `generate(spec, names, pads)` | Show configuration | Dictionary of `Segment` lists per drone |
| `smooth_segment(start, end, duration)` | `[x,y,z,yaw]` endpoints, seconds | 7th-degree `Segment` |
| `evaluate_path(segments, t)` | Segment list and elapsed seconds | `[x,y,z,yaw]` at time `t` |
| `validate(paths, spec, step=0.02)` | Paths, geometry and sampling interval | Verdict dictionary |
| `export(paths, spec, folder)` | Paths, show and output folder | Per-drone CSV files and show JSON |
| `line`, `circle`, `grid` | Number of drones and geometry parameters | Formation arrays |

## Example usage
```python
from choreography.engine import load_show, generate, validate, export
spec, names, pads = load_show('shows/two_drone_demo.json')
paths = generate(spec, names, pads)
result = validate(paths, spec, step=0.01)
print(result['ok'], result['issues'][:5])
if result['ok']:
    export(paths, spec, 'output/my_show')
```

## Polynomial representation
Each `Segment` stores duration and four arrays of **eight ascending-order coefficients** (X, Y, Z, yaw). `smooth_segment()` creates a septic smoothstep with zero velocity, acceleration and jerk at each endpoint. That means every phase pauses at its endpoints; it does not create continuous nonzero-velocity transitions across phase boundaries.

## Limits and extension points
The validator checks configured XY boundaries, ceiling and minimum pairwise separation with a motion bound; it is not a formal flight safety proof. The JSON's `floor_clearance_m` field is currently parsed but **not used as a flight clearance constraint** by `validate()`; do not assume it is enforced. Add speed/acceleration/jerk limits, obstacle models and robust uncertainty margins before tightly spaced flight.

The generated CSV is a project-specific export format, **not** a ready-to-upload binary Crazyflie memory image. `onboard_execution.py` handles conversion and upload internally.

## Dependencies and order
Requires NumPy and the Python standard library. Imported automatically by the CLI and onboard execution script. There is no reason to execute this file directly.

> **Safety:** The code is experimental and has not been validated on your macOS/Crazyflie hardware. A passing geometric validation is not proof of safe flight. Use a clear controlled area, propeller guards, an operator ready to intervene, and verified LPS coordinates. None of these tools implements onboard collision avoidance or guaranteed multi-radio synchronization.

Run commands from the **project root** after `source .venv/bin/activate`. Use `python <script> --help` to check the flags accepted by your installed copy.
