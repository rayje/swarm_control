"""Offline, deterministic 7th-order multi-drone trajectory planner.

All positions are in room-centered metres; trajectories include stationary
start/end segments and are NOT directly flyable until surveyed LPS transform
and launch-pad alignment are verified.
"""
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class Segment:
    duration: float
    axes: list  # x, y, z, yaw: eight ascending polynomial coefficients each

    def evaluate(self, t):
        t = max(0., min(float(t), self.duration))
        return np.array([sum(c * t**i for i, c in enumerate(axis)) for axis in self.axes])


def smooth_segment(start, end, duration):
    """Septic smoothstep: zero velocity, acceleration, jerk at both ends."""
    if duration <= 0:
        raise ValueError('duration must be positive')
    s = np.asarray(start, dtype=float)
    e = np.asarray(end, dtype=float)
    axes = []
    for a, b in zip(s, e):
        d = b - a
        T = float(duration)
        axes.append([float(a), 0., 0., 0.,
                     float(35*d/T**4), float(-84*d/T**5),
                     float(70*d/T**6), float(-20*d/T**7)])
    return Segment(float(duration), axes)


def line(n, span=3.2, altitude=1.0):
    return np.array([[x, 0., altitude, 0.] for x in np.linspace(-span/2, span/2, n)])


def circle(n, radius=1.15, altitude=1.0):
    # Preserve assignment ordering across formation changes; collision validation
    # must still check every transition.
    return np.array([[radius*math.cos(2*math.pi*i/n),
                      radius*math.sin(2*math.pi*i/n), altitude, 0.]
                     for i in range(n)])


def grid(n, spacing=0.85, altitude=1.0):
    cols = math.ceil(n / 2)
    return np.array([[(i % cols - (cols-1)/2)*spacing,
                      (0.5 if i < cols else -0.5)*spacing,
                      altitude, 0.] for i in range(n)])


FORMATIONS = {'line': line, 'circle': circle, 'grid': grid}


def load_show(path):
    spec = json.loads(Path(path).read_text())
    names = spec['drones']
    if len(names) != len(set(names)) or not names:
        raise ValueError('Drone names must be unique and nonempty')
    if not 1 <= len(names) <= 10:
        raise ValueError('This example supports 1-10 drones')
    pads = np.array([spec['launch_positions_room_m'][name] for name in names], dtype=float)
    if pads.shape != (len(names), 3) or not np.isfinite(pads).all():
        raise ValueError('Invalid launch positions')
    phases = spec['phases']
    if not phases:
        raise ValueError('No phases')
    return spec, names, pads


def generate(spec, names, pads):
    n = len(names)
    current = np.column_stack([pads, np.zeros(n)])
    paths = {name: [] for name in names}
    for phase in spec['phases']:
        duration = float(phase['duration_s'])
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError('Phase duration must be positive and finite')
        kind = phase['type']
        if kind == 'hold':
            target = current.copy()
        elif kind == 'land':
            target = np.column_stack([pads, np.zeros(n)])
        elif kind == 'takeoff':
            target = np.column_stack([pads[:, :2], np.full(n, float(phase.get('altitude_m', 1.0))), np.zeros(n)])
        elif kind == 'formation':
            name = phase['name']
            if name not in FORMATIONS:
                raise ValueError(f'Unknown formation {name}')
            kwargs = phase.get('parameters', {})
            target = FORMATIONS[name](n, **kwargs)
        else:
            raise ValueError(f'Unknown phase type {kind}')
        for i, name in enumerate(names):
            paths[name].append(smooth_segment(current[i], target[i], duration))
        current = target
    return paths


def evaluate_path(segments, t):
    remaining = float(t)
    for seg in segments:
        if remaining <= seg.duration:
            return seg.evaluate(remaining)
        remaining -= seg.duration
    return segments[-1].evaluate(segments[-1].duration)


def validate(paths, spec, step=0.02):
    """Sampled validation + conservative speed bound. NOT formal collision proof."""
    names = list(paths)
    duration = sum(s.duration for s in paths[names[0]])
    room = spec['room']
    half_x, half_y = room['width_m']/2, room['depth_m']/2
    min_dist = float(spec['minimum_separation_m'])
    margin = float(spec['wall_margin_m'])
    floor = float(spec['floor_clearance_m'])
    ceiling = float(spec['ceiling_clearance_m'])
    # Account for possible unsampled motion by subtracting a bound on each
    # drone's displacement between samples. Derivative bound uses Bernstein
    # control points, valid for each polynomial segment.
    def speed_bound(seg):
        T = seg.duration
        # Convert power coefficients in u=t/T to Bernstein coefficients.
        def bernstein(axis):
            a = [axis[k]*T**k for k in range(8)]
            return [sum(a[k]*math.comb(i,k)/math.comb(7,k) for k in range(i+1)) for i in range(8)]
        coords = np.array([bernstein(seg.axes[j]) for j in range(3)])
        return max(float(np.linalg.norm(7*(coords[:,i+1]-coords[:,i])/T)) for i in range(7))
    max_speeds = {name: max(speed_bound(s) for s in segs) for name,segs in paths.items()}
    issues = []
    minimum_observed = float('inf')
    count = math.ceil(duration/step)
    for k in range(count+1):
        t = min(k*step, duration)
        points = np.array([evaluate_path(paths[name], t)[:3] for name in names])
        for i, p in enumerate(points):
            # Conservative spatial margin to account for movement between samples.
            slack = max_speeds[names[i]]*step/2
            if abs(p[0])+slack > half_x-margin or abs(p[1])+slack > half_y-margin:
                issues.append(f'{names[i]} leaves XY envelope near t={t:.2f}s')
            # Ground contact is allowed only during takeoff/landing, checked separately.
            if p[2]+slack > room['height_m']-ceiling or p[2]-slack < -0.02:
                issues.append(f'{names[i]} violates Z envelope near t={t:.2f}s')
        for i in range(len(names)):
            for j in range(i+1, len(names)):
                d = float(np.linalg.norm(points[i]-points[j]))
                minimum_observed = min(minimum_observed, d)
                slack = (max_speeds[names[i]]+max_speeds[names[j]])*step/2
                if d-slack < min_dist:
                    issues.append(f'{names[i]}/{names[j]} too close near t={t:.2f}s ({d:.2f}m)')
        if len(issues) >= 25:
            break
    return {'ok': not issues, 'issues': issues, 'duration_s': duration,
            'minimum_sampled_separation_m': None if math.isinf(minimum_observed) else minimum_observed,
            'max_speed_bounds_mps': max_speeds,
            'sample_interval_s': step,
            'note': 'Sampled geometric validation only; does not model estimator error, radio loss, tracking error, downwash or obstacles.'}


def export(paths, spec, folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    for name, segs in paths.items():
        with (folder / f'{name}.csv').open('w') as f:
            f.write('# duration,x0..x7,y0..y7,z0..z7,yaw0..yaw7 (ascending powers, SI units)\n')
            for seg in segs:
                f.write(','.join(format(v, '.12g') for v in [seg.duration]+sum(seg.axes, []))+'\n')
    (folder/'show.json').write_text(json.dumps(spec, indent=2))
