"""Read-only Crazyflie swarm telemetry dashboard. Python 3.10+."""
import argparse
import csv
import logging
import math
import queue
import signal
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button

from config import DRONES, ROOM, LOG_PERIOD_MS, STALE_AFTER_S, MIN_SEPARATION_WARNING_M

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.syncLogger import SyncLogger

logging.basicConfig(level=logging.WARNING)

@dataclass
class DroneState:
    name: str
    uri: str
    status: str = 'WAITING'
    xyz: tuple | None = None
    vbat: float | None = None
    var_xyz: tuple | None = None
    last_position: float = 0.0
    last_battery: float = 0.0
    last_variance: float = 0.0
    error: str = ''
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)


class Monitor:
    def __init__(self, simulate=False, csv_path='telemetry.csv'):
        self.simulate = simulate
        self.states = {name: DroneState(name, uri) for name, uri in DRONES.items()}
        self.stop = threading.Event()
        self.events = queue.Queue()
        self.csv_path = Path(csv_path)
        self.threads = []
        self.csv_file = None
        self.writer = None

    def emit(self, name, kind, values):
        self.events.put((time.time(), time.monotonic(), name, kind, values))

    def worker(self, name, uri):
        self.emit(name, 'status', 'CONNECTING')
        try:
            with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
                self.emit(name, 'status', 'CONNECTED')
                # Separate blocks keep packets below the 26-byte payload limit.
                specs = [
                    ('position', ['stateEstimate.x', 'stateEstimate.y', 'stateEstimate.z']),
                    ('battery', ['pm.vbat']),
                    ('variance', ['kalman.varPX', 'kalman.varPY', 'kalman.varPZ']),
                ]
                configs = []
                for kind, variables in specs:
                    conf = LogConfig(name=f'{kind}_{name}', period_in_ms=LOG_PERIOD_MS)
                    # Add spec variables to log
                    for variable in variables:
                        conf.add_variable(variable, 'float')

                    try:
                        scf.cf.log.add_config(conf)
                    except (KeyError, AttributeError) as exc:
                        self.emit(name, 'error', f'{kind} log unavailable: {exc}')
                        continue
                    
                    # Setup log callback
                    conf.data_received_cb.add_callback(
                        lambda timestamp, data, logconf, n=name, k=kind, v=tuple(variables):
                            # Emit log event
                            self.emit(n, k, tuple(float(data[x]) for x in v))
                    )
                    # Setup error log callback
                    conf.error_cb.add_callback(
                        lambda logconf, message, n=name:
                            # Emit error log
                            self.emit(n, 'error', f'Logging error: {message}')
                    )
                    configs.append(conf)

                if not any(conf.name.startswith('position_') for conf in configs):
                    raise RuntimeError('Position logging unavailable')

                for conf in configs:
                    conf.start()

                try:
                    while not self.stop.wait(0.2):
                        pass
                finally:
                    for conf in configs:
                        try:
                            conf.stop()
                        except Exception:
                            pass

        except Exception as exc:
            self.emit(name, 'error', f'Connection failed: {exc}')
            self.emit(name, 'status', 'ERROR')
        finally:
            self.emit(name, 'status', 'DISCONNECTED')

    def simulation_worker(self):
        t0 = time.monotonic()
        for name in self.states:
            self.emit(name, 'status', 'CONNECTED')

        while not self.stop.wait(LOG_PERIOD_MS / 1000):
            t = time.monotonic() - t0

            for i, name in enumerate(self.states):
                angle = i * 2 * math.pi / len(self.states)
                xyz = (1.65 * math.cos(angle) + 0.12 * math.cos(t / 4),
                       0.85 * math.sin(angle) + 0.12 * math.sin(t / 4),
                       1.0 + 0.08 * math.sin(t / 3 + angle))

                self.emit(name, 'position', xyz)
                self.emit(name, 'battery', (4.05 - 0.00003 * t,))
                self.emit(name, 'variance', (0.001, 0.001, 0.002))

    def start(self):
        if not self.simulate:
            cflib.crtp.init_drivers()

        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self.csv_file = self.csv_path.open('w', newline='', buffering=1)
        self.writer = csv.writer(self.csv_file)
        self.writer.writerow(['utc_time', 'drone', 'kind', 'x', 'y', 'z', 'battery_v',
                              'variance_x', 'variance_y', 'variance_z'])
        if self.simulate:
            th = threading.Thread(target=self.simulation_worker, daemon=True)
            th.start()
            self.threads.append(th)
        else:
            for name, state in self.states.items():
                th = threading.Thread(target=self.worker, args=(name, state.uri),
                                      daemon=True, name=f'worker-{name}')
                th.start()
                self.threads.append(th)
                time.sleep(0.12)  # stagger initial TOC downloads

    def drain(self):
        while True:
            try:
                wall, mono, name, kind, values = self.events.get_nowait()
            except queue.Empty:
                break

            # Update DroneState with event data
            state = self.states[name]
            with state.lock:
                if kind == 'status':
                    state.status = values
                elif kind == 'error':
                    state.error = values
                    print(f'{name}: {values}')
                elif kind == 'position':
                    state.xyz, state.last_position = values, mono
                elif kind == 'battery':
                    state.vbat, state.last_battery = values[0], mono
                elif kind == 'variance':
                    state.var_xyz, state.last_variance = values, mono

                if kind in ('position', 'battery', 'variance'):
                    self.writer.writerow([
                        datetime.fromtimestamp(wall, timezone.utc).isoformat(), name, kind,
                        *(values if kind == 'position' else ('', '', '')),
                        values[0] if kind == 'battery' else '',
                        *(values if kind == 'variance' else ('', '', ''))
                    ])

    def close(self):
        self.stop.set()
        for th in self.threads:
            th.join(timeout=3)
        self.drain()
        if self.csv_file:
            self.csv_file.close()
            self.csv_file = None


def lps_to_room(xyz):
    ox, oy, oz = ROOM['origin_xyz']
    angle = math.radians(ROOM['yaw_deg'])
    dx, dy = xyz[0] - ox, xyz[1] - oy
    return (math.cos(angle) * dx + math.sin(angle) * dy,
            -math.sin(angle) * dx + math.cos(angle) * dy, xyz[2] - oz)


def run_dashboard(monitor):
    fig = plt.figure(figsize=(14, 8))
    ax = fig.add_axes([0.05, 0.12, 0.60, 0.79], projection='3d')
    panel = fig.add_axes([0.68, 0.12, 0.30, 0.79])
    panel.axis('off')
    fig.suptitle('Crazyflie Swarm Telemetry — READ ONLY', fontsize=15)

    w, d, h = ROOM['width'], ROOM['depth'], ROOM['height']
    ax.set_xlim(-w / 2, w / 2)
    ax.set_ylim(-d / 2, d / 2)
    ax.set_zlim(0, h)
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_zlabel('Z (m)')
    ax.set_box_aspect((w, d, h))
    ax.view_init(elev=25, azim=-65)

    # Room wireframe
    for x in (-w / 2, w / 2):
        for y in (-d / 2, d / 2):
            ax.plot([x, x], [y, y], [0, h], color='gray', alpha=0.25)

    for z in (0, h):
        for y in (-d / 2, d / 2):
            ax.plot([-w / 2, w / 2], [y, y], [z, z], color='gray', alpha=0.25)
        for x in (-w / 2, w / 2):
            ax.plot([x, x], [-d / 2, d / 2], [z, z], color='gray', alpha=0.25)

    cmap = plt.get_cmap('tab10')
    markers = {}
    labels = {}

    for i, name in enumerate(monitor.states):
        color = cmap(i % 10)
        markers[name] = ax.scatter([], [], [], s=75, color=[color])
        labels[name] = ax.text(0, 0, 0, '', fontsize=8, color=color)

    panel_text = panel.text(0, 1, '', va='top', family='monospace', fontsize=10,
                            transform=panel.transAxes)
    stop_ax = fig.add_axes([0.81, 0.035, 0.13, 0.05])
    stop_button = Button(stop_ax, 'Stop monitor')
    stop_button.on_clicked(lambda event: plt.close(fig))

    def update(_):
        monitor.drain()
        now = time.monotonic()
        lines = ['Drone   Status       Battery   Position (m)', '-' * 48]
        valid = []

        for name, state in monitor.states.items():
            with state.lock:
                xyz = state.xyz
                fresh = xyz is not None and now - state.last_position < STALE_AFTER_S
                status = state.status if state.status != 'CONNECTED' else ('LIVE' if fresh else 'STALE')
                battery = f'{state.vbat:.2f}V' if (state.vbat is not None and
                          now - state.last_battery < 3 * STALE_AFTER_S) else '--'

                if fresh and all(math.isfinite(v) for v in xyz):
                    p = lps_to_room(xyz)
                    markers[name]._offsets3d = ([p[0]], [p[1]], [p[2]])
                    labels[name].set_position((p[0], p[1]))
                    labels[name].set_3d_properties(p[2])
                    labels[name].set_text(name)
                    valid.append((name, p))
                    pos = f'{p[0]:+.1f},{p[1]:+.1f},{p[2]:+.1f}'
                else:
                    markers[name]._offsets3d = ([], [], [])
                    labels[name].set_text('')
                    pos = '--'

                lines.append(f'{name:<7} {status:<12} {battery:<8} {pos}')

        closest = None
        for i in range(len(valid)):
            for j in range(i + 1, len(valid)):
                a, b = valid[i], valid[j]
                dist = math.dist(a[1], b[1])
                if closest is None or dist < closest[0]:
                    closest = (dist, a[0], b[0])

        lines.extend(['', f'Fresh positions: {len(valid)}/{len(monitor.states)}'])

        if closest:
            distance, first, second = closest
            lines.append(f'Closest: {first} / {second}: {distance:.2f} m')
            if distance < MIN_SEPARATION_WARNING_M:
                lines.append('WARNING: estimated separation is low')

        lines.extend(['', 'Position estimates only.',
                      'No flight commands or safety enforcement.',
                      f'CSV: {monitor.csv_path}'])

        panel_text.set_text('\n'.join(lines))
        return [panel_text, *markers.values(), *labels.values()]

    animation = FuncAnimation(fig, update, interval=200, blit=False, cache_frame_data=False)
    try:
        plt.show()
    finally:
        monitor.close()
    return animation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--simulate', action='store_true', help='Run without radios')
    parser.add_argument('--csv', default='telemetry.csv', help='Output CSV path')
    args = parser.parse_args()

    monitor = Monitor(simulate=args.simulate, csv_path=args.csv)
    monitor.start()

    run_dashboard(monitor)


if __name__ == '__main__':
    main()
