# Command-line reference (verified against script parsers)

| Script | Usage | Actual flight? |
|---|---|---|
| `monitor.py` | `python monitor.py [--simulate] [--csv PATH]` | No |
| `coordinated_flight.py` | `python coordinated_flight.py [--drones CFXX CFYY] [--fly]` | Only with `--fly` and approval |
| `choreography_cli.py` | `python choreography_cli.py SHOW [--output DIR] [--preview] [--step SECONDS]` | No |
| `onboard_execution.py` | `python onboard_execution.py SHOW [--drones CFXX ...] [--fly] [--confirm-flight] [--track-csv PATH]` | Only with both opt-in flags and approval |
| `config.py` | Imported module — no flags | No |
| `flight_tracking.py` | Imported module — no flags | No |
| `choreography/engine.py` | Imported module — no flags | No |

## Flag rules
- **Positional** `SHOW` is required for choreography and onboard execution.
- `--drones` in coordinated flight takes **exactly two** names; in onboard execution it takes **one or more**.
- `--simulate` applies **only** to `monitor.py`.
- `--preview`, `--output`, `--step` apply **only** to `choreography_cli.py`.
- `--track-csv` applies **only** to `onboard_execution.py`.
- `--fly` applies to coordinated flight and onboard execution, **not** monitor or choreography preview.
- Use `python SCRIPT --help` for the installed version's authoritative parser.

## Copy/paste examples
```bash
python monitor.py --simulate --csv logs/sim.csv
python monitor.py --csv logs/live.csv
python coordinated_flight.py --drones CF01 CF02
python choreography_cli.py shows/ten_drone_grid.json --output output/grid --preview --step 0.01
python onboard_execution.py shows/two_drone_demo.json --drones CF01 CF02
```

For real flight and required configuration, see [COORDINATED_FLIGHT.md](COORDINATED_FLIGHT.md) and [ONBOARD_EXECUTION.md](ONBOARD_EXECUTION.md).

> **Safety:** The code is experimental and has not been validated on your macOS/Crazyflie hardware. A passing geometric validation is not proof of safe flight. Use a clear controlled area, propeller guards, an operator ready to intervene, and verified LPS coordinates. None of these tools implements onboard collision avoidance or guaranteed multi-radio synchronization.

Run commands from the **project root** after `source .venv/bin/activate`. Use `python <script> --help` to check the flags accepted by your installed copy.
