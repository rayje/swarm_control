# End-to-end workflow for a 10-drone indoor show

## Dependency map
```text
config.py ───────────┬──> monitor.py                  [read-only live]
                     ├──> coordinated_flight.py       [two-drone hover]
                     └──> onboard_execution.py        [upload + real flight]
choreography/engine.py ──> choreography_cli.py        [offline preview/export]
          └──────────────> onboard_execution.py
flight_tracking.py ──────> onboard_execution.py        [automatic flight logs]
shows/*.json ────────────> choreography_cli.py AND onboard_execution.py
```
**These are import dependencies, not a chain of processes.** No background monitor needs to remain running for a flight; don't contend for the same radio dongles.

## Suggested staged sequence
1. Edit `config.py` with actual 3-radio/10-drone URIs; verify each address independently.
2. Confirm 8-anchor TDoA3 position estimates are stable; `python monitor.py --simulate` then `python monitor.py --csv logs/lps.csv`.
3. Survey launch pads, actual walls/ceiling and LPS coordinate frame. Edit `shows/*.json` and `onboard_execution.py`'s `LPS_TRANSFORM`.
4. Preview/validate: `python choreography_cli.py shows/two_drone_demo.json --preview --step 0.01`.
5. Check dry run: `python onboard_execution.py shows/two_drone_demo.json --drones CF01`.
6. Perform supervised two-drone hover commissioning with `coordinated_flight.py` **after** its own pad settings are measured.
7. Progress to one-drone uploaded trajectory; inspect `--track-csv` output for errors and telemetry gaps.
8. Increase drone count slowly. Check full-path separation with conservative margins that account for real positioning/tracking errors, and avoid crossing paths or vertical stacking in the 9 ft room.
9. Validate synchronized starts empirically before any close-formation choreography; three radios do not guarantee synchronization.

## Which script should I use?
| Goal | Command |
|---|---|
| Visualize without hardware | `python monitor.py --simulate` |
| Watch live positions | `python monitor.py --csv logs/live.csv` |
| Test two-drone takeoff/land | `python coordinated_flight.py --drones CF01 CF02` (dry run) |
| Design/preview formations | `python choreography_cli.py shows/ten_drone_grid.json --preview` |
| Prepare onboard upload offline | `python onboard_execution.py shows/two_drone_demo.json --drones CF01` |
| Fly uploaded path (only after full commissioning) | `python onboard_execution.py shows/two_drone_demo.json --drones CF01 --fly --confirm-flight --track-csv logs/test.csv` |

## Design modifications
Edit show JSON for duration, drone assignment, room bounds, formations and launch pads; edit `choreography/engine.py` to introduce new formation generators; edit `onboard_execution.py` for flight checks and LPS transform. Do not equate changing `config.ROOM` with changing actual flight geometry.

> **Safety:** The code is experimental and has not been validated on your macOS/Crazyflie hardware. A passing geometric validation is not proof of safe flight. Use a clear controlled area, propeller guards, an operator ready to intervene, and verified LPS coordinates. None of these tools implements onboard collision avoidance or guaranteed multi-radio synchronization.

Run commands from the **project root** after `source .venv/bin/activate`. Use `python <script> --help` to check the flags accepted by your installed copy.
