"""v2 review: render chosen OUTPUT frames (120 fps timeline) of the current curve state with neutral cameras, as a contact sheet.

    review2.sheet(B, [n0, n1, ...], 'name', view='3q')       B = qa2.Bake(warp)
"""
import json
import math
import os

import numpy as np

import review
import rig as rg

OUT = review.OUT


def _cam(B, i, view, dist, fov=50.0):
    P = B.parts['P'][i, 0, :3]; D = B.parts['D'][i, 0, :3]
    m = (P + D) / 2
    d = D - P; d[1] = 0; L = np.linalg.norm(d); u = d / L if L > 0.2 else np.array([1.0, 0, 0])
    side = np.array([-u[2], 0, u[0]])
    spread = max(L, abs(P[1] - D[1]))
    dd = max(dist, 6 + spread * 1.6)
    if view == 'side': c = m + side * dd + np.array([0, 1.2, 0])
    elif view == '3q': c = m + side * dd * 0.75 - u * dd * 0.55 + np.array([0, 2.5, 0])
    elif view == 'top': c = m + np.array([0, dd, 0]) + side * 0.5
    else: c = m - side * dd * 0.75 + u * dd * 0.55 + np.array([0, 2.5, 0])
    return [float(x) for x in c] + [float(x) for x in m] + [fov, 0.0]


def sheet(B, frames, name, view='3q', dist=9.0, scale=0.26, cols=6, labels=None):
    k = len(frames)
    shot = {'fps': 18, 'frames': k, 'width': 1080, 'height': 1920, 'chars': {}, 'cam': [], 'fx': []}
    for cid, kind in (('P', 'player'), ('D', 'dummy')):
        parts = {b: [] for b in rg.PARTS}
        for i in frames:
            for j, b in enumerate(rg.PARTS):
                parts[b].append([round(float(x), 4) for x in B.parts[cid][i, j]])
        shot['chars'][cid] = {'kind': kind, 'parts': parts}
    shot['cam'] = [_cam(B, i, view, dist) for i in frames]
    shot['focus'] = [[float(x) for x in (B.parts['P'][i, 0, :3] + B.parts['D'][i, 0, :3]) / 2] for i in frames]
    os.makedirs(os.path.join(OUT, 'test'), exist_ok=True)
    pth = os.path.join(OUT, 'test', 'review2_%s.json' % name)
    with open(pth, 'w') as fh: json.dump(shot, fh)
    od = os.path.join(OUT, 'review', name + '_frames')
    review.render_frames(pth, list(range(k)), od, scale)
    labs = labels or ['n%d af%.1f' % (i, B.af[i]) for i in frames]
    # contact_sheet labels frame numbers itself; pass our own labels
    png = os.path.join(OUT, 'review', name + '.png')
    review.contact_sheet(od, list(range(k)), png, cols, labels=labs, fps=120)
    return png
