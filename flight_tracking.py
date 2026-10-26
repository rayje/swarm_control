"""Thread-safe, read-only trajectory tracking for Crazyflie flight sessions."""
import csv
import math
import threading
import time
from pathlib import Path
import numpy as np
from choreography.engine import evaluate_path

FIELDS = ['wall_time_utc','monotonic_s','drone','phase','elapsed_s','cf_timestamp_ms',
          'actual_x','actual_y','actual_z','target_x','target_y','target_z',
          'error_x','error_y','error_z','error_3d_m','battery_v','telemetry_age_s',
          'estimated_min_peer_distance_m','start_offset_s']


class FlightTracker:
    def __init__(self, paths, output, log_period_ms=100, stale_after_s=0.7):
        self.paths = paths  # full LPS-transformed trajectories including takeoff and landing
        self.output = Path(output)
        self.output.parent.mkdir(parents=True, exist_ok=True)
        self.file = self.output.open('w', newline='', buffering=1)
        self.writer = csv.DictWriter(self.file, fieldnames=FIELDS)
        self.writer.writeheader()
        self.period = log_period_ms
        self.stale_after = stale_after_s
        self.lock = threading.RLock()
        self.latest = {}
        self.voltages = {}
        self.configs = {}
        self.rows = []
        self.phase = 'preflight'
        self.phase_start = None
        self.command_starts = {}
        self.start_skew_reference = None
        self.closed = False

    def set_phase(self, phase, start=None):
        with self.lock:
            self.phase = phase
            self.phase_start = time.monotonic() if start is None else start
            if phase == 'trajectory':
                self.command_starts = {}
                self.start_skew_reference = None

    def record_command_start(self, name, instant=None):
        with self.lock:
            instant = time.monotonic() if instant is None else instant
            self.command_starts[name] = instant
            if self.start_skew_reference is None:
                self.start_skew_reference = instant

    def start_logs(self, scf, name):
        from cflib.crazyflie.log import LogConfig
        cf = scf.cf
        position = LogConfig(name='track_xyz', period_in_ms=self.period)
        for axis in 'xyz':
            position.add_variable('stateEstimate.' + axis, 'float')
        position.data_received_cb.add_callback(lambda stamp, data, _: self._position(name, stamp, data))
        battery = LogConfig(name='track_vbat', period_in_ms=500)
        battery.add_variable('pm.vbat', 'float')
        battery.data_received_cb.add_callback(lambda stamp, data, _: self._battery(name, data))
        for config in (position, battery):
            cf.log.add_config(config)
            config.start()
        with self.lock:
            self.configs[name] = (position, battery)

    def stop_logs(self):
        with self.lock:
            configs = list(self.configs.values())
            self.configs.clear()
        for pair in configs:
            for config in pair:
                try:
                    config.stop()
                except Exception as exc:
                    print(f'Warning: telemetry stop failed: {exc}')

    def _battery(self, name, data):
        with self.lock:
            self.voltages[name] = float(data['pm.vbat'])

    def _position(self, name, cf_stamp, data):
        from datetime import datetime, timezone
        now = time.monotonic()
        point = np.array([float(data['stateEstimate.' + a]) for a in 'xyz'])
        if not np.isfinite(point).all():
            return
        with self.lock:
            if self.closed:
                return
            self.latest[name] = (now, point)
            phase = self.phase
            start = self.command_starts.get(name, self.phase_start)
            elapsed = None if start is None else max(0., now-start)
            expected = self._expected(name, phase, elapsed)
            error = point - expected if expected is not None else np.full(3, np.nan)
            distances = [float(np.linalg.norm(point-p)) for peer,(ts,p) in self.latest.items()
                         if peer != name and now-ts <= self.stale_after]
            offset = (self.command_starts[name] - self.start_skew_reference
                      if name in self.command_starts and self.start_skew_reference is not None else None)
            row = dict(zip(FIELDS, [datetime.now(timezone.utc).isoformat(), now, name, phase,
                elapsed, cf_stamp, *point, *(expected if expected is not None else [None]*3),
                *(error if expected is not None else [None]*3),
                float(np.linalg.norm(error)) if expected is not None else None,
                self.voltages.get(name), 0.0, min(distances) if distances else None, offset]))
            self.writer.writerow(row)
            self.rows.append(row)

    def _expected(self, name, phase, elapsed):
        if elapsed is None or name not in self.paths:
            return None
        segs = self.paths[name]
        if phase == 'takeoff':
            return segs[0].evaluate(min(elapsed, segs[0].duration))[:3]
        if phase == 'hover':
            return segs[0].evaluate(segs[0].duration)[:3]
        if phase == 'trajectory':
            return evaluate_path(segs[1:-1], elapsed)[:3]
        if phase == 'landing':
            return segs[-1].evaluate(min(elapsed, segs[-1].duration))[:3]
        return None

    def snapshot(self):
        with self.lock:
            now = time.monotonic()
            return {name: {'position': p.tolist(), 'age_s': now-t,
                           'stale': now-t > self.stale_after,
                           'battery_v': self.voltages.get(name)}
                    for name,(t,p) in self.latest.items()}

    def summary(self):
        with self.lock:
            result = {}
            for name in self.paths:
                rows = [r for r in self.rows if r['drone'] == name and r['phase'] == 'trajectory'
                        and r['error_3d_m'] is not None]
                errors = np.array([r['error_3d_m'] for r in rows])
                result[name] = {'trajectory_samples': len(rows),
                    'rms_error_m': float(np.sqrt(np.mean(errors**2))) if len(errors) else None,
                    'max_error_m': float(np.max(errors)) if len(errors) else None,
                    'p95_error_m': float(np.percentile(errors,95)) if len(errors) else None,
                    'last_battery_v': self.voltages.get(name)}
            if self.command_starts:
                starts = list(self.command_starts.values())
                result['command_dispatch_skew_ms'] = 1000*(max(starts)-min(starts))
            return result

    def close(self):
        with self.lock:
            self.closed = True
            self.file.close()
