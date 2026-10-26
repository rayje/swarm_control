# `flight_tracking.py` — flight telemetry/tracking library

## Purpose and value
Records reported XYZ position, battery voltage, expected trajectory XYZ, 3D error and approximate nearest-peer distance. Helps evaluate LPS tracking performance and estimate timing differences after a flight.

**This is an imported library, not a command-line script. It has no CLI flags.** Use `onboard_execution.py --track-csv PATH` to activate it during a flight.

## Usage
```bash
# Offline preview; no tracking CSV from actual flight
python choreography_cli.py shows/two_drone_demo.json --preview

# Actual flight with tracking (only after safe hardware commissioning)
python onboard_execution.py shows/two_drone_demo.json --drones CF01 --fly --confirm-flight --track-csv logs/cf01.csv
```

## API overview
`FlightTracker(paths, output, log_period_ms=100, stale_after_s=0.7)` accepts **LPS-transformed complete** trajectory paths and an output CSV filename. The execution controller calls `start_logs(scf,name)`, `set_phase(phase)`, `record_command_start(name)`, `snapshot()`, `summary()`, `stop_logs()` and `close()`.

## CSV columns and interpretation
| Column | Meaning / caveat |
|---|---|
| `wall_time_utc`, `monotonic_s`, `cf_timestamp_ms` | Host UTC, host monotonic, drone log timestamps; clocks are not necessarily synchronized |
| `drone`, `phase`, `elapsed_s` | Drone and current controller phase, estimated elapsed time |
| `actual_x/y/z` | LPS-estimated position |
| `target_x/y/z` | Expected position from polynomial and host timing |
| `error_x/y/z`, `error_3d_m` | Estimated tracking error; includes timing alignment uncertainty |
| `battery_v` | Most recently received battery reading |
| `telemetry_age_s` | Current code writes `0.0` when receiving a position callback; **not** a measured end-to-end packet latency |
| `estimated_min_peer_distance_m` | Distance to recently received peer positions, **not guaranteed simultaneous samples** |
| `start_offset_s` | Relative host command-dispatch timing; **not** actual motor/trajectory start skew |

Position logs default to 100 ms (10 Hz), battery logs to 500 ms (2 Hz). Increasing rates increases traffic over the Crazyradios.

## Customization
Adjust `log_period_ms` and `stale_after_s` in the `FlightTracker` constructor. Add fields to `FIELDS` and populate them in `_position()` for additional measurements. For accurate timing research, log onboard state or use a synchronized measurement method; do not interpret command offsets as synchronized execution.

## Dependencies and order
Requires NumPy, `cflib` for live logs, and `choreography.engine` for trajectory evaluation. Automatically invoked by `onboard_execution.py` during live flight. It does not require or drive `monitor.py`.

> **Safety:** The code is experimental and has not been validated on your macOS/Crazyflie hardware. A passing geometric validation is not proof of safe flight. Use a clear controlled area, propeller guards, an operator ready to intervene, and verified LPS coordinates. None of these tools implements onboard collision avoidance or guaranteed multi-radio synchronization.

Run commands from the **project root** after `source .venv/bin/activate`. Use `python <script> --help` to check the flags accepted by your installed copy.
