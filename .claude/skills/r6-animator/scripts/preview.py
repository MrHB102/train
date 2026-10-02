#!/usr/bin/env python3
"""preview.py - offline contact sheets of R6 clips (matplotlib+numpy, no Blender needed).
   Use for project-authored JSON only; no database IDs or reference motion.
   python preview.py authored-clip.json [out.png] [--n 12] [--views 3q,side]
   API: sheet(clip, path, n=12, views=('3q','side'), tile=2.4, fr=[frames]|'keys', zoom=1.0, dpi=70) -> path
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r6

COL = {'HumanoidRootPart': '#999999', 'Torso': '#8d97a3', 'Head': '#e7c9a0', 'Right Arm': '#e07a3f', 'Right Leg': '#c9602a',
       'Left Arm': '#3f86d6', 'Left Leg': '#2a64ad'}
VIEW = {'front': 0, '3q': 35, 'side': 90, 'back': 180}          # camera azimuth from the character's front toward its right
CUBE = [((0, 0, 1), [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]), ((0, 0, -1), [(-1, -1, -1), (-1, 1, -1), (1, 1, -1), (1, -1, -1)]),
        ((1, 0, 0), [(1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)]), ((-1, 0, 0), [(-1, -1, -1), (-1, -1, 1), (-1, 1, 1), (-1, 1, -1)]),
        ((0, 1, 0), [(-1, 1, -1), (-1, 1, 1), (1, 1, 1), (1, 1, -1)]), ((0, -1, 0), [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)])]

def _shade(hexc, k):
    r, g, b = [int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return (min(1, r * k), min(1, g * k), min(1, b * k))

def polys(pose, az):
    """list of (depth, 2d polygon, colour) for one pose seen from azimuth az (deg)"""
    a = math.radians(az); out = []; fk = r6.fk(pose)
    for b, (P, Q) in fk.items():
        if b == 'HumanoidRootPart': continue
        sz = r6.J[b][6]; h = (sz[0] / 2, sz[1] / 2, sz[2] / 2)
        if b == 'Head': h = (.625, .5, .5)
        for n, vs in CUBE:
            nw = r6.mv(Q, n)
            # camera sits at azimuth a: front is -z (roblox); camera dir vector from scene to camera
            cam = (math.sin(a), 0.0, -math.cos(a)); vis = nw[0] * cam[0] + nw[1] * cam[1] + nw[2] * cam[2]
            if vis <= 0: continue
            pts = []; dep = 0
            for v in vs:
                w = r6.mv(Q, (v[0] * h[0], v[1] * h[1], v[2] * h[2])); w = (P[0] + w[0], P[1] + w[1], P[2] + w[2])
                sx = w[0] * math.cos(a) + w[2] * math.sin(a)             # screen x: character right when a=0
                dd = -(w[0] * cam[0] + w[2] * cam[2]); pts.append((sx, w[1])); dep += dd
            shade = 0.62 + 0.38 * max(0.0, nw[1] * 0.6 + vis * 0.8)
            out.append((dep / 4, pts, _shade(COL[b], shade)))
    out.sort(key=lambda t: -t[0])
    return out

def sheet(c, path='sheet.png', n=12, views=('3q', 'side'), tile=2.6, cols=6, fr=None, label=True, zoom=1.0, dpi=70):
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon
    fs = r6.frames(c); f0, f1 = fs[0], fs[-1]
    if fr == 'keys': fr = fs
    if fr is None: fr = [f0 + (f1 - f0) * i / max(n - 1, 1) for i in range(n)] if n > 1 else [f0]
    rows = math.ceil(len(fr) / cols); nv = len(views)
    fig, axs = plt.subplots(rows * nv, cols, figsize=(cols * tile, rows * nv * tile * 1.12), squeeze=False)
    for ax in axs.flat: ax.axis('off')
    for i, f in enumerate(fr):
        pose = r6.sample(c, f); r, cc = divmod(i, cols)
        for vi, v in enumerate(views):
            ax = axs[r * nv + vi][cc]
            for dep, pts, col in polys(pose, VIEW[v] if isinstance(v, str) else v): ax.add_patch(Polygon(pts, closed=True, fc=col, ec='#222', lw=.6))
            a_ = math.radians(VIEW[v] if isinstance(v, str) else v); Tp = r6.fk(pose)['Torso'][0]
            cx = Tp[0] * math.cos(a_) + Tp[2] * math.sin(a_)                 # keep the torso centred when the clip travels
            ax.axhline(0, color='#bbb', lw=.8)
            if zoom == 1.0: ax.set_xlim(cx - 3.6, cx + 3.6); ax.set_ylim(-.3, 6.8)
            else: cy = Tp[1] + .55; ax.set_xlim(cx - 3.6 / zoom, cx + 3.6 / zoom); ax.set_ylim(cy - 3.45 / zoom, cy + 3.45 / zoom)      # zoom: closer window centred on the torso
            ax.set_aspect('equal')
            if label and vi == 0: ax.set_title('f%.0f  %.2fs' % (f, (f - f0) / c['fps']), fontsize=8, pad=2)
    fig.subplots_adjust(left=.01, right=.99, top=.97, bottom=.01, wspace=.02, hspace=.08)
    fig.savefig(path, dpi=dpi); plt.close(fig)
    return path

if __name__ == '__main__':
    import argparse, qa
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('clip'); ap.add_argument('out', nargs='?', default='sheet.png')
    ap.add_argument('--n', type=int, default=12); ap.add_argument('--views', default='3q,side')
    a = ap.parse_args()
    try:
        if not 1 <= a.n <= 64: raise ValueError('n must be 1–64')
        print(sheet(qa.read_clip(a.clip), a.out, a.n, tuple(a.views.split(','))))
    except (ValueError, OSError) as e:
        print(str(e), file=sys.stderr); sys.exit(1)
