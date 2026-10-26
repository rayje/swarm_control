# Crazyflie Indoor Show — JSON Format Reference

This guide documents the **currently implemented** show JSON format in `choreography/engine.py`, with examples, validation behavior, and ideas for extending it. It describes the application's accepted input format, **not** a separate machine-readable JSON Schema file. The examples are intended for the project's offline choreography generator; a valid file does not by itself make a real flight safe.

## 1. Complete example

Save this as `shows/my_first_show.json`:

```json
{
  "room": {
    "width_m": 6.096,
    "depth_m": 4.572,
    "height_m": 2.7432
  },
  "minimum_separation_m": 0.9,
  "wall_margin_m": 0.65,
  "floor_clearance_m": 0.0,
  "ceiling_clearance_m": 0.6,
  "drones": ["CF01", "CF02"],
  "launch_positions_room_m": {
    "CF01": [-1.0, 0.0, 0.0],
    "CF02": [1.0, 0.0, 0.0]
  },
  "phases": [
    {"type": "takeoff", "altitude_m": 1.0, "duration_s": 4.0},
    {"type": "hold", "duration_s": 3.0},
    {
      "type": "formation",
      "name": "line",
      "parameters": {"span": 2.0, "altitude": 1.0},
      "duration_s": 5.0
    },
    {"type": "hold", "duration_s": 3.0},
    {"type": "land", "duration_s": 4.0}
  ]
}
```

All lengths are in **meters** and all times are in **seconds**. The example is illustrative; confirm the real room, obstacles, launch pads, and LPS coordinate alignment before any flight.

## 2. Top-level fields

| Field | JSON type | Required by current implementation | Meaning |
|---|---|---|---|
| `room` | object | Yes, for validation | Room dimensions in meters. |
| `minimum_separation_m` | number | Yes, for validation | Minimum allowed center-to-center separation between drones. |
| `wall_margin_m` | number | Yes, for validation | Required horizontal margin inside the room boundary. |
| `floor_clearance_m` | number | Yes, for validation | Read by validator, but **not currently enforced**. |
| `ceiling_clearance_m` | number | Yes, for validation | Required clearance below the ceiling. |
| `drones` | array of strings | Yes | Unique drone identifiers in formation-assignment order; 1–10 supported. |
| `launch_positions_room_m` | object | Yes | Maps each drone ID to a three-number `[x, y, z]` launch position. |
| `phases` | nonempty array | Yes | Sequential show movements. |

The loader checks that `drones` is nonempty and unique, that there are 1–10 drones, that each named drone has a finite 3D launch position, and that `phases` is nonempty. Other checks occur during generation or validation. The program does **not** perform comprehensive schema validation or reject every unknown field.

## 3. Room dimensions and coordinates

```json
"room": {
  "width_m": 6.096,
  "depth_m": 4.572,
  "height_m": 2.7432
}
```

The trajectory generator uses a **room-centered** reference frame:

- **X:** horizontal, along the room width, with `x = 0` at the center.
- **Y:** horizontal, along the room depth, with `y = 0` at the center.
- **Z:** vertical, measured from the room's floor reference.
- **Yaw:** fourth trajectory axis, in radians; the current formations all target zero yaw.

For a 20 × 15 × 9 ft room, nominal coordinate limits are:

| Axis | Minimum | Maximum |
|---|---:|---:|
| X | −3.048 m | +3.048 m |
| Y | −2.286 m | +2.286 m |
| Z | 0 m | 2.7432 m |

With `wall_margin_m: 0.65` and `ceiling_clearance_m: 0.6`, the nominal allowed bounds become X ±2.398 m, Y ±1.636 m, and Z at most 2.1432 m. The validator applies additional conservative motion slack, so a path exactly at one of these bounds may fail.

**Room coordinates are not automatically LPS coordinates.** Before actual onboard flight, survey the launch pads and verify the room-to-LPS translation and rotation. The room dimensions also do not describe furniture, spectators, anchors, or other obstacles.

## 4. Drones and launch positions

```json
"drones": ["CF01", "CF02", "CF03"],
"launch_positions_room_m": {
  "CF01": [-1.0, 0.0, 0.0],
  "CF02": [0.0, 0.0, 0.0],
  "CF03": [1.0, 0.0, 0.0]
}
```

Each launch position is `[x, y, z]` in room coordinates. Each ID in `drones` must have a corresponding launch position. The **order** of IDs controls which drone receives which slot in a formation; it is not automatically optimized for travel distance or collision avoidance. For live execution, drone IDs must also match the configured radio URIs.

The generator initializes each drone at its launch XYZ and yaw zero. The `land` phase returns each drone to its **original** launch XYZ.

## 5. Phase definitions

Phases are executed in array order, and all drones participate in every phase. Every phase needs a `type` and a positive, finite `duration_s`.

| `type` | Required additional fields | Optional fields | Result |
|---|---|---|---|
| `takeoff` | None | `altitude_m` (default `1.0`) | Moves vertically above each drone's launch XY. |
| `hold` | None | None | Holds the current target position and yaw. |
| `formation` | `name` | `parameters` (default `{}`) | Transitions each drone to its assigned formation slot. |
| `land` | None | None | Returns to original launch XYZ with yaw zero. |

### Takeoff

```json
{"type": "takeoff", "altitude_m": 1.0, "duration_s": 4.0}
```

Targets each drone's launch X and Y with the specified absolute Z coordinate. `altitude_m` is a room-frame Z value, not an added offset above the pad's starting Z.

### Hold

```json
{"type": "hold", "duration_s": 3.0}
```

Creates a stationary polynomial segment at the current position; it does not pause the Python process or halt the overall show clock.

### Formation

```json
{
  "type": "formation",
  "name": "circle",
  "parameters": {"radius": 1.0, "altitude": 1.2},
  "duration_s": 6.0
}
```

Calculates the target slot for every drone and moves all drones simultaneously over the specified duration. Only `line`, `circle`, and `grid` are supported at present.

### Land

```json
{"type": "land", "duration_s": 4.0}
```

Generates a smooth trajectory back to the original launch coordinates. This phase **does not itself guarantee motor shutdown or disarming**; those are separate responsibilities of the real flight controller.

### Total show duration

The duration is the sum of the phase durations. For example, takeoff 4 s + hold 3 s + formation 5 s + hold 3 s + land 4 s = **19 seconds**.

## 6. Supported formations

### Line

```json
{
  "type": "formation",
  "name": "line",
  "parameters": {"span": 2.0, "altitude": 1.0},
  "duration_s": 5.0
}
```

Places `N` drones evenly along X, centered at the room origin, with Y = 0 and Z = `altitude`.

- `span` defaults to `3.2` m.
- `altitude` defaults to `1.0` m.
- For `N > 1`, spacing is `span / (N - 1)`.
- Example for five drones with `span: 2.0`: X positions −1.0, −0.5, 0, +0.5, +1.0 m.

### Circle

```json
{
  "type": "formation",
  "name": "circle",
  "parameters": {"radius": 1.0, "altitude": 1.2},
  "duration_s": 6.0
}
```

Distributes drones around a horizontal circle centered on X = Y = 0:

```text
angle_i = 2π × i / N
x_i = radius × cos(angle_i)
y_i = radius × sin(angle_i)
z_i = altitude
```

- `radius` defaults to `1.15` m.
- `altitude` defaults to `1.0` m.
- Drone order determines the angular assignment.
- This is a **static circular formation**, not continuous orbiting.

### Grid

```json
{
  "type": "formation",
  "name": "grid",
  "parameters": {"spacing": 0.85, "altitude": 1.0},
  "duration_s": 5.0
}
```

The implementation creates up to **two rows**, with `ceil(N/2)` columns. For 10 drones this gives a 2 × 5 grid.

- `spacing` defaults to `0.85` m and controls **both column spacing and row separation**.
- `altitude` defaults to `1.0` m.
- The row Y coordinates are `+0.5 × spacing` and `−0.5 × spacing`.
- Columns are centered on X = 0 and spaced by `spacing`.

For example, `spacing: 0.85` means 0.85 m between adjacent columns **and** 0.85 m between the two rows. The current grid does not accept separate X/Y spacing parameters or a custom row count.

## 7. How the trajectory generator interprets phases

The JSON describes **targets and durations**, not direct motor or radio commands. The engine creates a seventh-order polynomial for each drone and phase, with zero velocity, acceleration, and jerk at each segment endpoint. Consequently, drones stop at each phase boundary before transitioning to the next phase.

The generated trajectory has four polynomial axes (`x`, `y`, `z`, `yaw`). The current built-in formations set yaw to zero. The offline CSV export contains the segment duration followed by eight polynomial coefficients per axis, in **ascending powers of time**.

The current JSON format does **not** support arbitrary per-drone waypoints, continuous orbiting, custom yaw, LED cues, overlapping movement tracks, or independent per-drone durations.

## 8. Safety and validation fields

```json
"minimum_separation_m": 0.9,
"wall_margin_m": 0.65,
"floor_clearance_m": 0.0,
"ceiling_clearance_m": 0.6
```

The offline validator checks sampled positions against:

1. Horizontal room bounds minus `wall_margin_m`.
2. Maximum altitude minus `ceiling_clearance_m`.
3. A lower Z bound of approximately **−0.02 m**.
4. Pairwise center-to-center distances against `minimum_separation_m`.

It applies a conservative speed-based allowance for movement between sample times and reports estimated speed bounds. **`floor_clearance_m` is read but currently not applied** to the lower Z check. Do not rely on it for enforcing ground clearance.

The validator also checks the initial and final ground-level positions. If launch pads are closer together than the configured minimum separation, the show may fail validation even before takeoff.

This is geometric validation, **not** a guarantee of flight safety. It does not account for tracking errors, UWB uncertainty, downwash, radio loss, people, obstacles, or actual motor behavior. It does not enforce user-configurable acceleration or velocity limits.

## 9. Running show files

From the project root, with dependencies installed:

**Preview and validate offline:**

```bash
python choreography_cli.py shows/two_drone_demo.json --preview
```

**Use a finer validation sample interval:**

```bash
python choreography_cli.py shows/ten_drone_grid.json --step 0.01 --preview
```

`--step` is the validator sampling interval in seconds; the default is `0.02`.

**Choose an export directory:**

```bash
python choreography_cli.py shows/my_first_show.json --output output/my_first_show
```

The exporter writes one CSV trajectory per drone and a copy of the JSON show definition.

**Prepare an onboard trajectory without flying:**

```bash
python onboard_execution.py shows/two_drone_demo.json --drones CF01
```

Real flight requires additional explicit flight flags and verified hardware configuration. Use the project's `docs/ONBOARD_EXECUTION.md` for those steps.

### Selecting only some drones

```bash
python onboard_execution.py shows/ten_drone_grid.json --drones CF01 CF02
```

Selecting two drones does **not** necessarily produce a new two-drone version of a ten-drone choreography: formation targets were generated with the complete ordered drone list. For initial tests, create a dedicated one- or two-drone show file with appropriate launch positions and separation checks.

## 10. Common errors and limitations

| Issue | What to check |
|---|---|
| `KeyError` for a drone ID | Every ID in `drones` needs a launch-position entry. |
| Invalid launch positions | Each entry must contain exactly three finite numbers. |
| Unknown formation | Only `line`, `circle`, and `grid` are supported. |
| `TypeError` for formation parameters | Use only the named parameters listed above; unsupported keys are passed to Python functions. |
| Phase duration error | `duration_s` must be positive and finite. |
| Separation violation | Check both launch-pad spacing and movement between formation slots. |
| Wall or ceiling violation | Reduce formation size/altitude or increase room dimensions only if physically accurate. |
| Expected LED behavior missing | Lighting cues are not part of the implemented format. |

Additional unknown JSON keys may be ignored or cause errors depending on where they appear; they do not automatically enable new functionality. There is not yet a formal JSON Schema validator.

## 11. Proposed future schema additions (NOT implemented)

| Proposed field or feature | Purpose |
|---|---|
| `schema_version` | Make future format changes explicit. |
| `name`, `description` | Identify and catalog shows. |
| `waypoints` phase | Support arbitrary flight paths. |
| `positions` per drone | Specify custom formations and shapes. |
| `max_velocity_mps` | Enforce planned speed limits. |
| `max_acceleration_mps2` | Enforce acceleration limits. |
| `yaw_deg` | Control drone orientation. |
| `lighting` | Coordinate LED patterns with motion. |
| `start_time_s` | Support timed, potentially overlapping tracks. |
| `assignment: "min_distance"` | Reduce unnecessary formation crossings. |

**Suggested next enhancement:** add custom per-drone targets and waypoints, then define a formal `show.schema.json` for machine validation. Keep flight-control and safety behavior separate from the show-description schema.

---

**Related project files:** `shows/two_drone_demo.json`, `shows/ten_drone_grid.json`, `choreography/engine.py`, `choreography_cli.py`, and `onboard_execution.py`.
