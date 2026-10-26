"""Offline choreography generation, validation, and 3D preview. No radio commands."""
import argparse
import json
from pathlib import Path

import numpy as np
from choreography.engine import load_show, generate, validate, export, evaluate_path


def preview(paths, spec, fps=15):
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation
    names = list(paths)
    total = sum(s.duration for s in paths[names[0]])
    room = spec['room']
    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(111, projection='3d')
    ax.set_xlim(-room['width_m']/2, room['width_m']/2)
    ax.set_ylim(-room['depth_m']/2, room['depth_m']/2)
    ax.set_zlim(0, room['height_m'])
    ax.set_xlabel('Room X (m)')
    ax.set_ylabel('Room Y (m)')
    ax.set_zlabel('Z (m)')
    dots = ax.scatter([], [], [], s=70)
    labels = [ax.text(0, 0, 0, name) for name in names]
    title = ax.set_title('')

    def update(frame):
        t = min(frame/fps, total)
        pts = np.array([evaluate_path(paths[n], t)[:3] for n in names])
        dots._offsets3d = (pts[:, 0], pts[:, 1], pts[:, 2])
        for label, p in zip(labels, pts):
            label.set_position((p[0], p[1]))
            label.set_3d_properties(p[2], zdir='z')
        title.set_text(f'Offline preview — t={t:.1f}/{total:.1f}s')
        return [dots, title, *labels]

    animation = FuncAnimation(fig, update, frames=int(total*fps)+1,
                              interval=1000/fps, blit=False, repeat=True)
    plt.show()
    return animation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('show', help='JSON show specification')
    parser.add_argument('--output', default='output/show', help='CSV output directory')
    parser.add_argument('--preview', action='store_true', help='Open animated 3D preview')
    parser.add_argument('--step', type=float, default=0.02)
    args = parser.parse_args()
    if not 0 < args.step <= 0.1:
        parser.error('--step must be in (0, 0.1]')
    spec, names, pads = load_show(args.show)
    paths = generate(spec, names, pads)
    result = validate(paths, spec, args.step)
    print(json.dumps(result, indent=2))
    if not result['ok']:
        print('FAILED validation: no trajectories exported.')
        raise SystemExit(2)
    export(paths, spec, args.output)
    print(f'Validated trajectory CSVs saved to {args.output}')
    print('These are room-frame plans, NOT uploaded or executed on Crazyflies.')
    if args.preview:
        preview(paths, spec)


if __name__ == '__main__':
    main()
