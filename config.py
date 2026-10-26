"""Edit these example URIs to match your Crazyflies and Crazyradios."""
DRONES = {
    **{f'CF{i:02d}': f'radio://0/40/2M/E7E7E7E7{i:02X}' for i in range(1, 5)},
    **{f'CF{i:02d}': f'radio://1/60/2M/E7E7E7E7{i:02X}' for i in range(5, 8)},
    **{f'CF{i:02d}': f'radio://2/80/2M/E7E7E7E7{i:02X}' for i in range(8, 11)},
}
# All dimensions are in meters. Origin is the CENTER of the room.
# Adjust origin_xyz and yaw_deg if your LPS frame differs.
ROOM = {'width': 6.096, 'depth': 4.572, 'height': 2.7432,
        'origin_xyz': [0.0, 0.0, 0.0], 'yaw_deg': 0.0}
LOG_PERIOD_MS = 200  # 5 Hz per drone, per log block
STALE_AFTER_S = 1.5
MIN_SEPARATION_WARNING_M = 0.75  # display-only, not a safety guarantee
