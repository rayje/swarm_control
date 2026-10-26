"""Opt-in Crazyflie Poly4D upload and execution. Run without --fly for offline checks.

Safety: experimental; no onboard collision avoidance or guaranteed multi-radio sync.
"""
import argparse
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from choreography.engine import load_show, generate, validate, Segment
from config import DRONES

# Fill these with measured LPS coordinates. No flight permitted until configured.
# x_lps = tx + cos(yaw)*x_room - sin(yaw)*y_room
# y_lps = ty + sin(yaw)*x_room + cos(yaw)*y_room
# z_lps = tz + z_room
LPS_TRANSFORM = {'translation_m': None, 'yaw_deg': None}

TRAJECTORY_ID = 1
TAKEOFF_DURATION_S = 4.0
LAND_DURATION_S = 4.0
MAX_PAD_ERROR_M = 0.20
MAX_HOVER_ERROR_M = 0.25
MAX_POSITION_SPREAD_M = 0.12
MIN_BATTERY_V = 3.75  # illustrative, adjust to actual battery condition
MAX_TOTAL_SEGMENTS = 20


def transform_paths(paths, translation, yaw_deg):
    """Rigidly transform polynomial coefficients, including constant offsets."""
    angle = math.radians(yaw_deg)
    c, s = math.cos(angle), math.sin(angle)
    result = {}
    for name, segments in paths.items():
        transformed = []
        for seg in segments:
            x, y, z, heading = (np.array(a, dtype=float) for a in seg.axes)
            X = c*x - s*y
            Y = s*x + c*y
            Z = z.copy()
            X[0] += translation[0]
            Y[0] += translation[1]
            Z[0] += translation[2]
            H = heading.copy()
            H[0] += angle
            transformed.append(Segment(seg.duration, [a.tolist() for a in (X,Y,Z,H)]))
        result[name] = transformed
    return result


def prepare(show_path, selected):
    spec, names, pads = load_show(show_path)
    if not selected or any(n not in names for n in selected):
        raise ValueError('Selected drones must appear in the show')
    if not all(n in DRONES for n in selected):
        raise ValueError('Missing drone URI in config.py')
    # Validate ALL trajectories, even if flying only one drone.
    full = generate(spec, names, pads)
    verdict = validate(full, spec, step=0.01)
    if not verdict['ok']:
        raise RuntimeError('Unsafe choreography: ' + '; '.join(verdict['issues'][:5]))
    phases = spec['phases']
    if phases[0]['type'] != 'takeoff' or phases[-1]['type'] != 'land':
        raise ValueError('Show must start with takeoff and end with land')
    # Use firmware takeoff/land. Upload ONLY airborne middle phases.
    middle = {n: full[n][1:-1] for n in selected}
    if any(not pieces or len(pieces) > MAX_TOTAL_SEGMENTS for pieces in middle.values()):
        raise ValueError('Require 1..20 airborne polynomial segments per drone')
    duration = sum(p.duration for p in next(iter(middle.values())))
    for n in selected:
        if not math.isclose(sum(p.duration for p in middle[n]), duration):
            raise ValueError('Trajectory durations differ')
        start = full[n][0].evaluate(full[n][0].duration)
        first = middle[n][0].evaluate(0)
        if not np.allclose(start, first, atol=1e-5):
            raise ValueError(f'{n} airborne trajectory start does not match takeoff end')
        end = middle[n][-1].evaluate(middle[n][-1].duration)
        landing_start = full[n][-1].evaluate(0)
        if not np.allclose(end, landing_start, atol=1e-5):
            raise ValueError(f'{n} airborne trajectory end does not match landing start')
        # Require launch/landing at same XY so firmware vertical landing is safe.
        if np.linalg.norm(end[:2] - pads[names.index(n), :2]) > 1e-5:
            raise ValueError(f'{n} does not return above its launch pad before landing')
    return spec, names, pads, middle, duration, verdict


def read_position_battery(scf):
    from cflib.crazyflie.log import LogConfig
    from cflib.crazyflie.syncLogger import SyncLogger
    config = LogConfig(name='show_position', period_in_ms=100)
    for k in ('stateEstimate.x', 'stateEstimate.y', 'stateEstimate.z'):
        config.add_variable(k, 'float')
    points = []
    with SyncLogger(scf, config) as logger:
        for _, data, _ in logger:
            points.append(np.array([data['stateEstimate.' + axis] for axis in 'xyz'], dtype=float))
            if len(points) >= 8:
                break
    bat = LogConfig(name='show_battery', period_in_ms=100)
    bat.add_variable('pm.vbat', 'float')
    with SyncLogger(scf, bat) as logger:
        _, data, _ = next(iter(logger))
        voltage = float(data['pm.vbat'])
    avg = np.mean(points, axis=0)
    spread = max(np.linalg.norm(p-avg) for p in points)
    if not np.isfinite(avg).all() or not math.isfinite(voltage):
        raise RuntimeError('Invalid telemetry')
    if spread > MAX_POSITION_SPREAD_M:
        raise RuntimeError(f'Unstable LPS position (spread {spread:.2f} m)')
    if voltage < MIN_BATTERY_V:
        raise RuntimeError(f'Battery below threshold: {voltage:.2f} V')
    return avg, voltage


def upload(scf, segments):
    from cflib.crazyflie.mem import MemoryElement
    from cflib.crazyflie.mem.trajectory_memory import Poly4D
    mems = scf.cf.mem.get_mems(MemoryElement.TYPE_TRAJ)
    if len(mems) != 1:
        raise RuntimeError('Expected one trajectory memory element')
    memory = mems[0]
    memory.poly4Ds = [Poly4D(p.duration, *(Poly4D.Poly(axis) for axis in p.axes)) for p in segments]
    if len(segments) * 132 > memory.size:
        raise RuntimeError('Trajectory exceeds Crazyflie trajectory memory')
    result = memory.write_data_sync()
    if result is False:
        raise RuntimeError('Trajectory upload failed')
    scf.cf.high_level_commander.define_trajectory(TRAJECTORY_ID, 0, len(segments))
    return len(segments)


def run(show, selected, fly, confirm, track_csv=None):
    spec, names, pads, middle, duration, verdict = prepare(show, selected)
    print(json.dumps({'selected': selected, 'airborne_duration_s': duration,
                      'validation': verdict}, indent=2))
    if not fly:
        print('OFFLINE ONLY: No radio connections or flight commands issued.')
        return
    if LPS_TRANSFORM['translation_m'] is None or LPS_TRANSFORM['yaw_deg'] is None:
        raise RuntimeError('Set surveyed LPS_TRANSFORM before --fly')
    translation = LPS_TRANSFORM['translation_m']
    yaw = LPS_TRANSFORM['yaw_deg']
    if len(translation) != 3 or not all(math.isfinite(float(x)) for x in [*translation, yaw]):
        raise ValueError('Invalid LPS transform')
    if not confirm:
        raise RuntimeError('Supply --confirm-flight after reviewing the flight plan')
    # Room-frame validation must already have passed; rigid transforms preserve distances.
    converted = transform_paths(middle, translation, yaw)
    all_paths = transform_paths(generate(spec, names, pads), translation, yaw)
    import cflib.crtp
    from cflib.crazyflie.swarm import Swarm, CachedCfFactory
    cflib.crtp.init_drivers()
    uris = [DRONES[n] for n in selected]
    by_uri = {DRONES[n]: n for n in selected}
    from flight_tracking import FlightTracker
    from datetime import datetime
    tracker = FlightTracker({n: all_paths[n] for n in selected},
        track_csv or f'logs/flight_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
    try:
      with Swarm(uris, factory=CachedCfFactory(rw_cache='./cache')) as swarm:
          def preflight(scf):
              name = by_uri[scf.cf.link_uri]
              xyz, v = read_position_battery(scf)
              expected = all_paths[name][0].evaluate(0)[:3]
              if np.linalg.norm(xyz[:2] - expected[:2]) > MAX_PAD_ERROR_M:
                  raise RuntimeError(f'{name} pad XY mismatch: {xyz} vs {expected}')
              if abs(xyz[2] - expected[2]) > MAX_PAD_ERROR_M:
                  raise RuntimeError(f'{name} pad Z mismatch: {xyz} vs {expected}')
              print(f'{name}: pad OK; battery {v:.2f} V')
              return xyz
          positions = swarm.parallel_safe(preflight)
          coords = list(positions.values())
          for i in range(len(coords)):
              for j in range(i+1, len(coords)):
                  if np.linalg.norm(coords[i]-coords[j]) < spec['minimum_separation_m']:
                      raise RuntimeError('Launch positions too close')
          swarm.parallel_safe(lambda scf: upload(scf, converted[by_uri[scf.cf.link_uri]]))
          swarm.parallel_safe(lambda scf: tracker.start_logs(scf, by_uri[scf.cf.link_uri]))
          print('Trajectories uploaded and registered. Ready for takeoff.')
          answer = input('Type TAKEOFF to arm and execute this show: ')
          if answer != 'TAKEOFF':
              print('Cancelled without flight')
              return
          airborne = False
          try:
              def takeoff(scf):
                  name = by_uri[scf.cf.link_uri]
                  target_z = all_paths[name][0].evaluate(all_paths[name][0].duration)[2]
                  scf.cf.high_level_commander.takeoff(float(target_z), TAKEOFF_DURATION_S)
              tracker.set_phase('takeoff')
              airborne = True
              swarm.parallel_safe(takeoff)
              time.sleep(TAKEOFF_DURATION_S + 1.0)
              tracker.set_phase('hover')
              def hover_check(scf):
                  name = by_uri[scf.cf.link_uri]
                  actual, _ = read_position_battery(scf)
                  expected = converted[name][0].evaluate(0)[:3]
                  if np.linalg.norm(actual - expected) > MAX_HOVER_ERROR_M:
                      raise RuntimeError(f'{name} hover position mismatch: {actual} vs {expected}')
              swarm.parallel_safe(hover_check)
              print('Starting uploaded trajectories (best-effort concurrent, NOT synchronized).')
              tracker.set_phase('trajectory')
              def start_trajectory(scf):
                  name = by_uri[scf.cf.link_uri]
                  tracker.record_command_start(name)
                  scf.cf.high_level_commander.start_trajectory(
                      TRAJECTORY_ID, time_scale=1.0, relative_position=False, relative_yaw=False)
              swarm.parallel_safe(start_trajectory)
              time.sleep(duration + 1.0)
          finally:
              if airborne:
                  tracker.set_phase('landing')
                  print('Requesting landing; monitor all drones visually.')
                  try:
                      swarm.parallel_safe(lambda scf: scf.cf.high_level_commander.land(
                          float(all_paths[by_uri[scf.cf.link_uri]][0].evaluate(0)[2]), LAND_DURATION_S))
                      time.sleep(LAND_DURATION_S + 1.0)
                  except Exception as exc:
                      print(f'LANDING COMMAND ERROR: {exc}. Operator intervention required.')
                      raise
    finally:
        tracker.stop_logs()
        summary = tracker.summary()
        tracker.close()
        print('Flight tracking CSV:', tracker.output)
        print('Flight tracking summary:', json.dumps(summary, indent=2))
    print('Flight sequence complete; inspect logs and actual flight behavior.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('show', help='Show JSON file')
    parser.add_argument('--drones', nargs='+', default=['CF01'], help='Drone IDs (default: CF01)')
    parser.add_argument('--fly', action='store_true', help='Enable real radio flight')
    parser.add_argument('--confirm-flight', action='store_true', help='Second explicit flight opt-in')
    parser.add_argument('--track-csv', help='Flight tracking CSV output path')
    args = parser.parse_args()
    run(args.show, args.drones, args.fly, args.confirm_flight, args.track_csv)

if __name__ == '__main__':
    main()
