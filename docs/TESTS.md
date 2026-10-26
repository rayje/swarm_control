# Automated tests and offline verification

## Purpose
Tests help detect regressions in trajectory generation, geometry checks, transformations and tracking logic **without flight**. They cannot certify real hardware, LPS quality, or emergency response.

## Commands
```bash
python -m pip install pytest
python -m pytest -q
python -m compileall -q .
python choreography_cli.py shows/two_drone_demo.json --step 0.01
python onboard_execution.py shows/two_drone_demo.json --drones CF01
```
`-q` is a **pytest flag** for quieter output, not a project-specific flag. `compileall -q` checks syntax; it does not exercise code behavior. Tests do not have to run before each other.

## Before real flight
Verify actual pad survey and transform, radio URI mapping, battery health, firmware/cflib compatibility, full flight-volume clearance, landing behavior, emergency procedures, and logged tracking on one drone. A green test suite does not replace these checks.

> **Safety:** The code is experimental and has not been validated on your macOS/Crazyflie hardware. A passing geometric validation is not proof of safe flight. Use a clear controlled area, propeller guards, an operator ready to intervene, and verified LPS coordinates. None of these tools implements onboard collision avoidance or guaranteed multi-radio synchronization.

Run commands from the **project root** after `source .venv/bin/activate`. Use `python <script> --help` to check the flags accepted by your installed copy.
