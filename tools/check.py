#!/usr/bin/env python3
"""Checks for the Axon bottom shell.

Two subcommands, both read binary STL exports of the part:

  health <part.stl>
      Welds the facets and reports volume, open edges and non-manifold
      edges.  A closed, manifold part reports 0 open edges.

  diff <part.stl> <reference.stl> [z ...]
      Compares the two parts' material maps on a 1 mm grid at the given z
      levels and prints how many cells differ, and how many of those lie
      outside a 36 x 36 mm box around the fan seat.  Use it to prove that a
      change touched nothing but the feature you meant to change.

  solid <part.stl> x y z ...
      Prints the material intervals along +Z through each (x, y) column, so
      a wall thickness or a slot opening can be read off directly.

Install:  python3 -m pip install numpy
"""
import struct
import sys

import numpy as np

FAN_CENTRE = (-0.75, -0.50)   # the fan seat, in part coordinates
CELL = 1.0                    # material-map cell, mm


def load(path):
    """Read a binary STL into an (n, 3, 3) float array of triangles."""
    with open(path, "rb") as f:
        f.read(80)
        n = struct.unpack("<I", f.read(4))[0]
        raw = np.frombuffer(f.read(n * 50), dtype=np.uint8).reshape(n, 50)
        return raw[:, 12:48].copy().view("<f4").reshape(n, 3, 3).astype(float)


def weld(tris, quantum=1e-3):
    """Merge vertices that sit within `quantum` mm, and report the faces."""
    points = tris.reshape(-1, 3)
    keys = np.round(points / quantum).astype(np.int64)
    _, index = np.unique(keys, axis=0, return_inverse=True)
    return index.reshape(-1, 3), len(np.unique(index))


def health(path):
    tris = load(path)
    faces, verts = weld(tris)
    edges = {}
    for a, b, c in faces:
        for u, v in ((a, b), (b, c), (c, a)):
            edge = (min(u, v), max(u, v))
            edges[edge] = edges.get(edge, 0) + 1
    uses = np.array(list(edges.values()))
    volume = abs(np.einsum("ij,ij->i", tris[:, 0], np.cross(tris[:, 1], tris[:, 2])).sum() / 6)
    print(f"{path}")
    print(f"  facets {len(tris)}  welded vertices {verts}  volume {volume:.1f} mm^3")
    print(f"  open edges {int((uses == 1).sum())}  non-manifold edges {int((uses > 2).sum())}")
    return 0 if (uses == 1).sum() == 0 else 1


def crossings(tris, cols, batch=250):
    """For each (x, y) column, return the sorted z values where material starts/ends."""
    e1 = tris[:, 1] - tris[:, 0]
    e2 = tris[:, 2] - tris[:, 0]
    down = np.array([0.0, 0.0, 1.0])
    pvec = np.cross(np.broadcast_to(down, (len(tris), 3)), e2)
    det = np.einsum("ij,ij->i", e1, pvec)
    ok = np.abs(det) > 1e-12
    inv = np.zeros_like(det)
    inv[ok] = 1.0 / det[ok]
    out = []
    for i in range(0, len(cols), batch):
        block = cols[i:i + batch]
        origin = np.zeros((len(block), 3))
        origin[:, 0] = block[:, 0]
        origin[:, 1] = block[:, 1]
        origin[:, 2] = -1000.0
        tvec = origin[:, None, :] - tris[None, :, 0]
        u = np.einsum("bnj,nj->bn", tvec, pvec) * inv[None, :]
        qvec = np.cross(tvec, e1[None, :, :])
        v = (qvec @ down) * inv[None, :]
        t = np.einsum("bnj,nj->bn", qvec, e2) * inv[None, :]
        hit = (ok[None, :] & (u >= -1e-9) & (u <= 1 + 1e-9)
               & (v >= -1e-9) & (u + v <= 1 + 1e-9))
        for row in range(len(block)):
            out.append(np.sort(t[row][hit[row]]) - 1000.0)
    return out


def material(tris, xs, ys, z, offset=0.37):
    """Boolean map: is there material at (x + offset, y + offset, z)?"""
    xx, yy = np.meshgrid(xs + offset, ys + offset)
    cols = np.stack([xx.ravel(), yy.ravel()], axis=1)
    inside = np.zeros(len(cols), dtype=bool)
    for i, zc in enumerate(crossings(tris, cols)):
        for k in range(0, len(zc) - 1, 2):
            if zc[k] - 1e-6 <= z <= zc[k + 1] + 1e-6:
                inside[i] = True
                break
    return inside.reshape(len(ys), len(xs))


def diff(part, reference, levels=(-17.4, -16.0, -14.55, -12.0, -10.0, -8.0, -4.0, 0.0, 8.0)):
    a, b = load(part), load(reference)
    xs = np.arange(-53, 54, CELL)
    ys = np.arange(-41, 42, CELL)
    print(f"{part}\nversus {reference}   ({len(xs) * len(ys)} cells per level)")
    worst = 0
    for z in levels:
        ma, mb = material(a, xs, ys, z), material(b, xs, ys, z)
        changed = np.argwhere(ma != mb)
        if len(changed) == 0:
            print(f"  z = {z:7.2f}: no difference")
            continue
        x = xs[changed[:, 1]]
        y = ys[changed[:, 0]]
        outside = np.sum((np.abs(x - FAN_CENTRE[0]) > 18) | (np.abs(y - FAN_CENTRE[1]) > 18))
        worst = max(worst, outside)
        print(f"  z = {z:7.2f}: {len(changed):4d} cells differ, "
              f"{outside} of them outside the fan footprint")
    if worst:
        print(f"FAIL: {worst} differing cells outside the fan footprint")
        return 1
    print("OK: every difference is inside the fan footprint")
    return 0


def solid(path, points):
    tris = load(path)
    for x, y in points:
        zc = crossings(tris, np.array([[x, y]]))[0]
        spans = [(round(zc[i], 2), round(zc[i + 1], 2))
                 for i in range(0, len(zc) - 1, 2) if zc[i + 1] - zc[i] > 1e-3]
        print(f"  ({x:7.2f}, {y:7.2f}) material z-spans: {spans}")
    return 0


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    command, path = argv[1], argv[2]
    if command == "health":
        return health(path)
    if command == "diff":
        return diff(path, argv[3])
    if command == "solid":
        numbers = [float(v) for v in argv[3:]]
        return solid(path, list(zip(numbers[0::2], numbers[1::2])))
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
