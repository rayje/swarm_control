# macOS installation and prerequisites

## Hardware
- 10 Crazyflie 2.1 aircraft with Loco Positioning Decks, configured with unique addresses.
- 8 LPS anchors (4 near 8 ft, 4 near floor), TDoA3; autonomous positioning already tested.
- 3 Crazyradio USB dongles, connected to macOS; test the USB indices after reconnecting.
- 20 × 15 × 9 ft room; measure the *actual* launch pads and usable flight volume.

## Software installation
```bash
cd crazyflie-show-choreography-documented  # or the extracted folder name
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pytest
```
`requirements.txt` lists `cflib>=0.1.28` and `matplotlib>=3.7`. The scripts also import **NumPy**, which should be installed explicitly if it is not installed transitively: `python -m pip install numpy`. Python standard-library modules (argparse, csv, threading, json, etc.) require no extra installation. Matplotlib needs a working graphical backend for interactive previews on macOS.

## Recommended first checks
```bash
python -m compileall -q .
python -m pytest -q
python monitor.py --simulate --csv logs/simulation.csv
python choreography_cli.py shows/two_drone_demo.json --preview
python onboard_execution.py shows/two_drone_demo.json --drones CF01
```
The last three commands do not fly. `monitor.py --simulate` needs no radios. Avoid opening the Crazyflie client and this project against the same dongle at once.

## Dependency order
There is **no required sequence of separately running processes**. The scripts import shared modules and run independently. For practical commissioning, configure `config.py`, then simulate, validate a show, inspect the dry run, and only then attempt a supervised hardware flight. See [WORKFLOW.md](WORKFLOW.md).

> **Safety:** The code is experimental and has not been validated on your macOS/Crazyflie hardware. A passing geometric validation is not proof of safe flight. Use a clear controlled area, propeller guards, an operator ready to intervene, and verified LPS coordinates. None of these tools implements onboard collision avoidance or guaranteed multi-radio synchronization.

Run commands from the **project root** after `source .venv/bin/activate`. Use `python <script> --help` to check the flags accepted by your installed copy.
