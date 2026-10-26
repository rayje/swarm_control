"""Conservative, opt-in coordinated flight demo for 2 Crazyflies.

No commands are transmitted unless --fly is supplied. Review README before use.
Requires current cflib and high-level commander support in Crazyflie firmware.
"""
import argparse
import math
import time
from dataclasses import dataclass

from config import DRONES

# These are absolute LPS coordinates, NOT room-centered display coordinates.
# Replace with measured hover positions directly above the two takeoff pads.
# None intentionally prevents real flight until explicitly configured.
TAKEOFF_XY_LPS = {
    'CF01': None,  # e.g. (1.2, 1.5)
    'CF02': None,  # e.g. (3.2, 1.5)
}

ALTITUDE_M = 0.8
MIN_START_SEPARATION_M = 1.5
MAX_START_POSITION_ERROR_M = 0.20
MAX_STATIONARY_SPREAD_M = 0.15
BATTERY_MIN_V = 3.75  # conservative illustrative threshold, not a complete battery check
HOVER_S = 5.0
TAKEOFF_S = 3.0
LAND_S = 3.0
POSITION_SAMPLES = 8


@dataclass
class Sample:
    xyz: tuple
    vbat: float


def read_samples(scf):
    from cflib.crazyflie.log import LogConfig
    from cflib.crazyflie.syncLogger import SyncLogger
    # Separate logging blocks avoid exceeding the Crazyflie log packet size.
    samples = []
    pos = LogConfig(name='flight_pos', period_in_ms=100)
    for variable in ('stateEstimate.x', 'stateEstimate.y', 'stateEstimate.z'):
        pos.add_variable(variable, 'float')
    with SyncLogger(scf, pos) as logger:
        for _, data, _ in logger:
            samples.append(tuple(float(data[k]) for k in (
                'stateEstimate.x', 'stateEstimate.y', 'stateEstimate.z')))
            if len(samples) >= POSITION_SAMPLES:
                break
    battery = LogConfig(name='flight_bat', period_in_ms=100)
    battery.add_variable('pm.vbat', 'float')
    with SyncLogger(scf, battery) as logger:
        _, data, _ = next(iter(logger))
        vbat = float(data['pm.vbat'])
    if not all(math.isfinite(x) for xyz in samples for x in xyz) or not math.isfinite(vbat):
        raise RuntimeError('Nonfinite position or battery telemetry')
    avg = tuple(sum(p[i] for p in samples) / len(samples) for i in range(3))
    spread = max(math.dist(p, avg) for p in samples)
    if spread > MAX_STATIONARY_SPREAD_M:
        raise RuntimeError(f'Position estimate unstable: max spread {spread:.2f} m')
    if vbat < BATTERY_MIN_V:
        raise RuntimeError(f'Battery {vbat:.2f} V below configured threshold')
    return Sample(avg, vbat)


def preflight(scf):
    sample = read_samples(scf)
    print(f'{scf.cf.link_uri}: position={sample.xyz}, battery={sample.vbat:.2f}V')
    return sample


def takeoff(scf):
    scf.cf.high_level_commander.takeoff(ALTITUDE_M, TAKEOFF_S)


def land(scf):
    scf.cf.high_level_commander.land(0.0, LAND_S)


def validate_start_positions(names, samples):
    for name in names:
        expected = TAKEOFF_XY_LPS[name]
        actual = samples[DRONES[name]].xyz
        error = math.dist(actual[:2], expected)
        if error > MAX_START_POSITION_ERROR_M:
            raise RuntimeError(f'{name} is {error:.2f} m from its configured launch pad')
    a, b = (samples[DRONES[name]].xyz for name in names)
    distance = math.dist(a[:2], b[:2])
    if distance < MIN_START_SEPARATION_M:
        raise RuntimeError(f'Launch separation {distance:.2f} m is too small')
    print(f'Preflight passed; launch separation {distance:.2f} m')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--drones', nargs=2, default=['CF01', 'CF02'],
                        metavar='CFXX', help='Exactly two configured drone names')
    parser.add_argument('--fly', action='store_true', help='Enable actual motor/flight commands')
    args = parser.parse_args()
    names = args.drones
    if names[0] == names[1] or any(name not in DRONES for name in names):
        parser.error('Select two distinct drones from config.py')
    if args.fly and any(TAKEOFF_XY_LPS.get(name) is None for name in names):
        parser.error('Set measured TAKEOFF_XY_LPS for both drones before --fly')
    print('Plan:', ', '.join(names), f'takeoff to {ALTITUDE_M} m, hover {HOVER_S} s, land')
    print('This demo DOES NOT move drones horizontally and DOES NOT guarantee exact synchronization.')
    if not args.fly:
        print('DRY RUN: no radio connection and no motor commands. Use --fly only after reviewing safety checks.')
        return
    import cflib.crtp
    from cflib.crazyflie.swarm import Swarm, CachedCfFactory
    cflib.crtp.init_drivers()
    uris = [DRONES[name] for name in names]
    with Swarm(uris, factory=CachedCfFactory(rw_cache='./cache')) as swarm:
        print('Connected. Collecting stationary position and battery measurements...')
        samples = swarm.parallel_safe(preflight)
        validate_start_positions(names, samples)
        input('Clear flight area and confirm both drones ready; press Enter to TAKE OFF (Ctrl-C cancels): ')
        airborne = False
        try:
            # Mark as potentially airborne BEFORE dispatching any takeoff commands.
            airborne = True
            swarm.parallel_safe(takeoff)
            time.sleep(TAKEOFF_S + HOVER_S)
        finally:
            if airborne:
                print('Requesting coordinated landing...')
                try:
                    swarm.parallel_safe(land)
                    time.sleep(LAND_S + 1.0)
                except Exception as exc:
                    print(f'LANDING COMMAND ERROR: {exc}; follow your established emergency procedure')
                    raise
    print('Flight sequence finished; verify both drones are on the ground.')


if __name__ == '__main__':
    main()
