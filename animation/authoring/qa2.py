"""v2 QA on the final 120 fps motion (evaluated from the Blender curves, floor constraint included).

  bake()        -> per output frame, world boxes of every part of both characters (cached; also used by the exporter)
  pops()        -> frames where a part's velocity changes abruptly outside impacts / teleports (motion pops)
  collisions()  -> player x dummy box interpenetration (SAT depth) outside the allowed contacts (strikes, grabs)
  self_hits()   -> limbs sunk into their own torso/head beyond what the R6 joint geometry explains
"""
import math

import numpy as np

import choreo as C
import rig as rg
import r6

PARTS = rg.PARTS
HALF = {'Torso': (1.0, 1.0, .5), 'Head': (.625, .625, .625), 'Left Arm': (.5, 1.0, .5), 'Right Arm': (.5, 1.0, .5),
        'Left Leg': (.5, 1.0, .5), 'Right Leg': (.5, 1.0, .5)}
SELF_LIM = {('Right Arm', 'Torso'): .62, ('Left Arm', 'Torso'): .62, ('Right Leg', 'Torso'): .62, ('Left Leg', 'Torso'): .62,
            ('Right Arm', 'Head'): .5, ('Left Arm', 'Head'): .5, ('Right Leg', 'Left Leg'): .6}


class Bake:
    def __init__(self, warp):
        self.warp = warp
        self.n = warp.n_total
        self.af = np.array([warp.af(i) for i in range(self.n)])
        self.parts = {}
        for cid, A in (('P', C.P), ('D', C.D)):
            arr = np.zeros((self.n, len(PARTS), 12))
            for i in range(self.n):
                fk = A.rig.fk(float(self.af[i]))
                for j, b in enumerate(PARTS):
                    P, Q = fk[b]
                    arr[i, j, :3] = P; arr[i, j, 3:] = Q
            self.parts[cid] = arr


def depth(pa, qa, ha, pb, qb, hb):
    return r6.depth(pa, qa, ha, pb, qb, hb)


def pops(B, thresh=2.2, skip=()):
    """velocity jump between consecutive output frames, relative to the local speed scale. Returns [(n, af, who, part, dv)]"""
    out = []
    for cid in ('P', 'D'):
        X = B.parts[cid][:, :, :3]
        V = np.diff(X, axis=0) * 120.0                      # studs/s, frame i -> i+1
        dV = np.linalg.norm(np.diff(V, axis=0), axis=2)    # change of velocity at frame i+1
        sp = np.linalg.norm(V, axis=2)
        for i in range(dV.shape[0]):
            for j in range(len(PARTS)):
                scale = max(sp[i, j], sp[i + 1, j], 6.0)
                if dV[i, j] > 25.0 and dV[i, j] / scale > thresh:
                    af = B.af[i + 1]
                    if any(a - 0.05 <= af <= b + 0.05 for a, b in skip): continue
                    out.append((i + 1, round(float(af), 2), cid, PARTS[j], round(float(dV[i, j]), 1)))
    return out


def collisions(B, allow, min_depth=0.08):
    """allow: list of (af0, af1, P_part or None, D_part or None, max_depth). Returns runs of offending frames."""
    P, D = B.parts['P'], B.parts['D']
    hits = []
    for i in range(B.n):
        af = B.af[i]
        cp = P[i, :, :3]; cd = D[i, :, :3]
        for a, pa in enumerate(PARTS):
            for b, pb in enumerate(PARTS):
                if np.linalg.norm(cp[a] - cd[b]) > 2.9: continue
                d = depth(tuple(cp[a]), tuple(P[i, a, 3:]), HALF[pa], tuple(cd[b]), tuple(D[i, b, 3:]), HALF[pb])
                if d <= min_depth: continue
                ok = False
                for (f0, f1, ap, bp, md) in allow:
                    if f0 <= af <= f1 and (ap is None or ap == pa) and (bp is None or bp == pb) and d <= md:
                        ok = True; break
                if not ok:
                    hits.append((i, float(af), pa, pb, d))
    # group into runs
    runs = []
    for h in sorted(hits):
        if runs and h[0] - runs[-1]['n1'] <= 3:
            r = runs[-1]; r['n1'] = h[0]; r['af1'] = h[1]; r['max'] = max(r['max'], h[4]); r['pairs'].add((h[2], h[3]))
        else:
            runs.append(dict(n0=h[0], n1=h[0], af0=h[1], af1=h[1], max=h[4], pairs={(h[2], h[3])}))
    return runs


def self_hits(B, cid, margin=0.12):
    X = B.parts[cid]
    out = []
    for i in range(B.n):
        for (a, b), lim in SELF_LIM.items():
            ia, ib = PARTS.index(a), PARTS.index(b)
            d = depth(tuple(X[i, ia, :3]), tuple(X[i, ia, 3:]), HALF[a], tuple(X[i, ib, :3]), tuple(X[i, ib, 3:]), HALF[b])
            if d > lim + margin:
                out.append((i, float(B.af[i]), a, b, d - lim))
    runs = []
    for h in out:
        if runs and h[0] - runs[-1]['n1'] <= 3:
            r = runs[-1]; r['n1'] = h[0]; r['af1'] = h[1]; r['max'] = max(r['max'], h[4]); r['pairs'].add((h[2], h[3]))
        else:
            runs.append(dict(n0=h[0], n1=h[0], af0=h[1], af1=h[1], max=h[4], pairs={(h[2], h[3])}))
    return runs
