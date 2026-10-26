# Crazyflie Show Controller — Script-by-Script Run Guide

This guide documents the **actual commands and flags in this project** (flight-tracking release). Platform: macOS; hardware: ten Crazyflie 2.1 with Loco Positioning Decks, eight TDoA3 anchors, and three Crazyradios. Room: 6.096 × 4.572 × 2.7432 m.

> **Flight safety:** All scripts are experimental. The offline preview and monitor do not control motors. The `--fly` flag on flight scripts **does** command motors. There is no real-time collision avoidance or guaranteed failsafe recovery. Never operate the read-only monitor concurrently with a flight script: both need radio connections. Start with one drone, then two, before considering ten. Use guards, a clear flight area, known launch positions, and a practiced independent emergency procedure.

## 1. Installation (once per Mac)

Extract the ZIP. From Terminal:

```bash
cd crazyflie-show-choreography
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

For every new Terminal session, run `cd` into the project and `source .venv/bin/activate` again. To check the available commands:

```bash
python monitor.py --help
python coordinated_flight.py --help
python choreography_cli.py --help
python onboard_execution.py --help
```

**Before connecting to hardware:** close the Crazyflie Client and other scripts using the radios. Verify all drones are powered, uniquely addressed, and use the channel/data rate indicated by their URIs.

## 2. `config.py` — radio and visualization settings (not executable)

Edit `config.py` with a text editor. `DRONES` maps `CF01`…`CF10` to radio URIs. The supplied example distributes drones 4/3/3 across radio indexes 0/1/2 on channels 40/60/80, at 2 Mbps. **These are examples, not automatic discovery**; replace them with your real radio settings. USB indexes can change when you reconnect the dongles.

```python
DRONES = {
    'CF01': 'radio://0/40/2M/E7E7E7E701',
    'CF02': 'radio://0/40/2M/E7E7E7E702',
    # ... add all 10 configured drones ...
}
```

`ROOM` configures the read-only 3D monitor's dimensions and visual coordinate transform. The default `origin_xyz=[0,0,0]` and `yaw_deg=0` are **not** a surveyed LPS calibration. The independent `LPS_TRANSFORM` in `onboard_execution.py` must also be surveyed before flight.

## 3. `monitor.py` — live telemetry dashboard (no motor commands)

**Simulation, no radios needed:**

```bash
python monitor.py --simulate
```

**Live dashboard and CSV:**

```bash
mkdir -p logs
python monitor.py --csv logs/room_test.csv
```

**What it does:** opens a Matplotlib 3D room display with drone labels, positions, batteries, and telemetry freshness; logs position, battery, and estimator-variance measurements. Close the window or use its Stop control to disconnect. Default CSV path, if omitted, is `telemetry.csv`.

**Interpretation:** `LIVE` means recent telemetry, not verified position accuracy. The displayed closest-pair separation is based on asynchronously received estimates, not a safety-critical collision measurement. CSV rows have a `kind` identifying position, battery, or variance data; not every row contains every measurement.

## 4. `coordinated_flight.py` — simple two-drone takeoff / hover / landing

This script does **not** execute horizontal formations or uploaded trajectories. It only takes off, hovers, and lands two selected drones.

**Edit first:** In `coordinated_flight.py`, fill in `TAKEOFF_XY_LPS` with surveyed **absolute LPS** launch-pad XY coordinates for each drone you intend to use. Values of `None` deliberately block flight. Review `ALTITUDE_M`, hover time, and other constants in the file.

**Dry run (no radio or motors):**

```bash
python coordinated_flight.py
python coordinated_flight.py --drones CF03 CF04
```

**Actual two-drone flight (only after preflight checks):**

```bash
python coordinated_flight.py --drones CF01 CF02 --fly
```

The program connects, samples position/battery, checks starting separation, prompts the operator, issues concurrent takeoff commands, waits during hover, and requests landing. It cannot guarantee simultaneous takeoff or recovery after lost radio/positioning.

## 5. `choreography_cli.py` — generate, validate, export, preview (offline only)

**Two-drone example:**

```bash
python choreography_cli.py shows/two_drone_demo.json --preview
```

**Ten-drone example:**

```bash
python choreography_cli.py shows/ten_drone_grid.json --preview
```

**Validate and export without opening a window:**

```bash
python choreography_cli.py shows/ten_drone_grid.json --output output/grid_v1
```

**Change the validation sampling interval (seconds):**

```bash
python choreography_cli.py shows/two_drone_demo.json --step 0.01 --output output/two_drone_dense
```

`--step` must be greater than 0 and at most 0.1 seconds. A successful run exports one polynomial CSV per drone plus show metadata. If validation fails, it exits with status 2 and does not export new trajectories. The CSVs are **room-frame polynomial plans**; they are not commands to send directly to the drones.

### Edit a show JSON

Use `shows/two_drone_demo.json` as a template. It defines room dimensions, minimum separation, wall/floor/ceiling margins, drone IDs, launch positions **in room coordinates**, and a list of phases. Supported phase types in these included examples are `takeoff`, `hold`, `formation`, and `land`. A formation example:

```json
{
  "type": "formation",
  "name": "line",
  "parameters": {"span": 2.0, "altitude": 1.0},
  "duration_s": 5
}
```

The included ten-drone demo is a stationary grid takeoff/hold/landing, not a complex show. Preview all transitions and validate every revised show. Sampled geometric validation cannot guarantee safe real flight.

## 6. `onboard_execution.py` — upload Poly4D and fly (experimental)

This script takes a JSON show file, validates it, converts its **airborne** polynomial phases from room to LPS coordinates, uploads them to trajectory memory, registers them with the High-Level Commander, and—**only with explicit opt-in**—executes flight. Firmware high-level takeoff/landing are commanded separately.

**Mandatory flight configuration:**

In `onboard_execution.py`, replace the deliberately unset transform:

```python
LPS_TRANSFORM = {
    'translation_m': None,  # measured LPS position of room origin, [x, y, z]
    'yaw_deg': None,         # measured yaw rotation from room axes to LPS axes
}
```

Use a surveyed transform, checked at multiple positions, and confirm each drone's physical pad matches the show's `launch_positions_room_m`. **Do not assume the room and LPS origins are the same.** The show must start with `takeoff` and end with `land`, with its airborne trajectory starting and ending above the appropriate pad at the specified takeoff height.

**Offline validation/preparation, no radio:**

```bash
python onboard_execution.py shows/two_drone_demo.json --drones CF01
python onboard_execution.py shows/two_drone_demo.json --drones CF01 CF02
python onboard_execution.py shows/ten_drone_grid.json --drones CF01 CF02 CF03 CF04 CF05 CF06 CF07 CF08 CF09 CF10
```

**Single-drone real flight (after all checks):**

```bash
python onboard_execution.py shows/two_drone_demo.json \
  --drones CF01 --fly --confirm-flight
```

**Two-drone real flight (only after successful single-drone trials):**

```bash
python onboard_execution.py shows/two_drone_demo.json \
  --drones CF01 CF02 --fly --confirm-flight
```

Both `--fly` and `--confirm-flight` are required for real flight, followed by an interactive `TAKEOFF` confirmation. Selecting `--drones CF01` from a two-drone show does **not** automatically make that show a newly collision-validated single-drone plan; validate the full choreography and launch geometry before execution.

**Synchronization warning:** Concurrent host-side command dispatch is not a synchronized onboard clock. Three radios do not automatically synchronize trajectory starts. The system has no deviation-triggered abort or collision avoidance.

## 7. `flight_tracking.py` — tracking library (not a standalone CLI)

**Do not run `python flight_tracking.py` expecting a dashboard.** It defines the `FlightTracker` class, which `onboard_execution.py` uses during `--fly`.

**Track a single-drone hardware flight to a chosen CSV:**

```bash
mkdir -p logs
python onboard_execution.py shows/two_drone_demo.json \
  --drones CF01 --fly --confirm-flight \
  --track-csv logs/cf01_tracking.csv
```

**Track two drones:**

```bash
python onboard_execution.py shows/two_drone_demo.json \
  --drones CF01 CF02 --fly --confirm-flight \
  --track-csv logs/two_drone_tracking.csv
```

When no `--track-csv` path is provided, the flight controller generates a timestamped log under `logs/`. The tracker logs estimated X/Y/Z, planned X/Y/Z, 3D position error, battery voltage, phase, nearest recently observed peer, and command-dispatch timing. It prints a JSON summary with RMS, maximum, and 95th-percentile trajectory errors.

**Important interpretation:** Actual position is the drone's LPS-based *estimate*, not an independent ground-truth measurement. Expected position is aligned to the host's command-dispatch time, not the firmware's verified trajectory-start instant. Reported start offsets and nearest-peer distances therefore do **not** establish precise synchronization or collision clearance. The tracker does not issue aborts.

## 8. `choreography/engine.py` — library module (not a standalone CLI)

Imported by `choreography_cli.py` and `onboard_execution.py`. It implements show loading, seventh-order polynomial generation, trajectory evaluation, geometric validation, and export. To use it, run the CLI rather than executing `engine.py` directly.

## 9. Automated tests

Run from the project root:

```bash
python -m unittest discover -s tests -v
```

The tests exercise offline generation, validation, transformation, and tracking logic. Passing them does **not** prove radio compatibility, timing accuracy, or safe flight behavior.

## 10. Suggested order of operations

1. `python -m unittest discover -s tests -v` — software sanity check.
2. `python monitor.py --simulate` — verify 3D UI without drones.
3. `python monitor.py --csv logs/stationary.csv` — verify telemetry from powered, stationary drones.
4. `python choreography_cli.py shows/two_drone_demo.json --preview` — preview the plan.
5. `python onboard_execution.py shows/two_drone_demo.json --drones CF01` — offline execution preparation.
6. Survey/check the room-to-LPS transform and launch pads; confirm adequate clearance, LPS quality, and emergency procedure.
7. Use `coordinated_flight.py --fly` for a simple **two-drone** hover test only after individual flight confidence, or use the **single-drone** `onboard_execution.py ... --fly --confirm-flight --track-csv ...` command to validate trajectory execution.
8. Inspect the tracking CSV and summary; expand cautiously to two drones, then more only after measured results support it.

## 11. Troubleshooting

| Symptom | What to check |
|---|---|
| `ModuleNotFoundError: cflib` | Activate `.venv`, then `pip install -r requirements.txt`. |
| No drones connect | Crazyradio USB detection; close Crazyflie Client; URI address, channel, rate, and radio index. |
| Only some drones connect | Test one radio group at a time; inspect USB index changes and RF load. |
| Plot does not open | Run from macOS Terminal with a graphical desktop; verify Matplotlib installed. |
| Position is offset/rotated in monitor | Check `ROOM['origin_xyz']` and `ROOM['yaw_deg']`; this affects visualization, not the flight transform. |
| `Set surveyed LPS_TRANSFORM` | Survey and set `translation_m` and `yaw_deg` in `onboard_execution.py`; don't bypass the check. |
| `Set measured TAKEOFF_XY_LPS` | Enter measured launch pad coordinates in `coordinated_flight.py`. |
| Show validation fails | Inspect phase geometry, pad positions, wall/ceiling margins, and minimum separation; do not disable validation. |
| Tracking error unexpectedly high | Check LPS anchor coordinates/coverage, estimator stability, flight speed, and host-command timing bias. |
| Lost telemetry during flight | Treat as a serious operational issue; follow the independent emergency procedure rather than relying on the CSV tracker. |

## 12. Quick command reference

```bash
# No flight commands
python monitor.py --simulate
python monitor.py --csv logs/session.csv
python coordinated_flight.py
python choreography_cli.py shows/two_drone_demo.json --preview
python choreography_cli.py shows/ten_drone_grid.json --output output/grid
python onboard_execution.py shows/two_drone_demo.json --drones CF01
python -m unittest discover -s tests -v

# ACTUAL FLIGHT COMMANDS — only after configuration, validation and physical checks
python coordinated_flight.py --drones CF01 CF02 --fly
python onboard_execution.py shows/two_drone_demo.json --drones CF01 --fly --confirm-flight --track-csv logs/cf01.csv
```

## Project file index

- `config.py`: drone URIs and room display settings.
- `monitor.py`: read-only live/simulated telemetry UI.
- `coordinated_flight.py`: simple two-drone takeoff/hover/land.
- `choreography_cli.py`: offline show generator/validator/3D preview.
- `choreography/engine.py`: choreography library.
- `onboard_execution.py`: onboard upload and execution, optional live tracking.
- `flight_tracking.py`: logging and trajectory-error analysis library.
- `shows/*.json`: editable example shows.
- `tests/*.py`: offline tests.
- `requirements.txt`: dependencies.
