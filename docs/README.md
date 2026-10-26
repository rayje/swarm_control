# Crazyflie Show Controller — detailed documentation

These guides are based on the actual CLI arguments and Python imports in this project. Each explains purpose, value, dependencies, arguments, example commands, modification points and safe operational order.

## Getting started
- [macOS installation and prerequisites](SETUP.md)
- [Drone/radio configuration](CONFIG.md)
- [End-to-end workflow and dependency map](WORKFLOW.md)
- [Command/flag cheat sheet](COMMAND_REFERENCE.md)

## Individual scripts
- [Live telemetry dashboard (`monitor.py`)](MONITOR.md)
- [Two-drone coordinated flight (`coordinated_flight.py`)](COORDINATED_FLIGHT.md)
- [Offline show preview (`choreography_cli.py`)](CHOREOGRAPHY_CLI.md)
- [Trajectory engine (`choreography/engine.py`)](CHOREOGRAPHY_ENGINE.md)
- [Onboard execution (`onboard_execution.py`)](ONBOARD_EXECUTION.md)
- [Tracking library (`flight_tracking.py`)](FLIGHT_TRACKING.md)

## Additional reference
- [Tests](TESTS.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Original combined run guide](Crazyflie_Run_Guide.md)

**Note:** `config.py`, `flight_tracking.py`, and `choreography/engine.py` are imported modules, not standalone command-line tools. The monitor and choreography preview are non-flight commands; `--fly` enables hardware flight in the two flight controllers.
