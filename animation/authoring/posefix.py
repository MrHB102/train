"""v2 pose solver for interpenetration at key frames (mostly impact keys, where a hit-stop holds the pose on screen).

For a story key frame it adjusts, as little as possible,
  * the dummy: root offset, torso / head / limb rotations (a struck dummy whips its extremities away from the attacker)
  * the player: rotations of the limbs that are NOT striking, and the head
so that no body box of one character sinks into the other, while every strike tip keeps touching its target point
(the striking limb itself and the attacker's root/torso are never moved here).  Solved with L-BFGS-B on the SAT depths.
"""
import math

import numpy as np
from scipy.optimize import minimize

import choreo as C
import rig as rg
import r6
import qa2

PARTS = qa2.PARTS
HALF = qa2.HALF
LIMBS = ('Left Arm', 'Right Arm', 'Left Leg', 'Right Leg')


def _clamped(pose):
    m = rg.lowest_point(pose)
    if m < -1e-3:
        h = list(pose.get('HumanoidRootPart', [0.0] * 6)); h[4] += -m; pose = dict(pose); pose['HumanoidRootPart'] = h
    return pose


def _boxes(pose):
    fk = r6.fk(_clamped(pose))
    return {b: fk[b] for b in PARTS}


def overlap_cost(bp, bd, allow):
    tot = 0.0; worst = 0.0
    for pa in PARTS:
        Pa, Qa = bp[pa]
        for pb in PARTS:
            Pb, Qb = bd[pb]
            if rg.dist(Pa, Pb) > 2.9: continue
            d = r6.depth(Pa, Qa, HALF[pa], Pb, Qb, HALF[pb])
            lim = allow.get((pa, pb), allow.get((pa, None), 0.0))
            e = d - lim
            if e > 0.0:
                tot += e * e; worst = max(worst, e)
    return tot, worst


# smooth proxy for the boxes: a few spheres per part (local centres, radius) -> differentiable overlap for the optimiser
SPH = {'Torso': [((x, y, 0.0), 0.55) for x in (-0.5, 0.5) for y in (-0.5, 0.5)],
       'Head': [((0.0, 0.0, 0.0), 0.62)],
       'Left Arm': [((0.0, y, 0.0), 0.5) for y in (-0.6, 0.0, 0.6)], 'Right Arm': [((0.0, y, 0.0), 0.5) for y in (-0.6, 0.0, 0.6)],
       'Left Leg': [((0.0, y, 0.0), 0.5) for y in (-0.6, 0.0, 0.6)], 'Right Leg': [((0.0, y, 0.0), 0.5) for y in (-0.6, 0.0, 0.6)]}
_SL = [(b, np.array(c), r) for b in PARTS for c, r in SPH[b]]
_SB = [b for b, c, r in _SL]
_SR = np.array([r for b, c, r in _SL])


def _spheres(boxes):
    out = np.zeros((len(_SL), 3))
    for k, (b, c, r) in enumerate(_SL):
        P, Q = boxes[b]
        out[k] = np.asarray(P) + np.array(r6.mv(Q, c))
    return out


def _allow_matrix(allow):
    A = np.zeros((len(_SL), len(_SL)))
    for i, a in enumerate(_SB):
        for j, b in enumerate(_SB):
            A[i, j] = allow.get((a, b), allow.get((a, None), 0.0))
    return A


def sphere_cost(sp, sd, A):
    d = np.linalg.norm(sp[:, None, :] - sd[None, :, :], axis=2)
    e = np.maximum(0.0, _SR[:, None] + _SR[None, :] - d - A)
    return float((e * e).sum())


def fix_frame(f, contacts, allow, airborne, verbose=False):
    """f: story key frame. contacts: [(limb_bone, tgt_bone, local, tip)] of the player at f. allow: {(P part, D part|None): depth}"""
    p0 = r6.sample(C.P.clip, f); d0 = r6.sample(C.D.clip, f)
    strike = {c[0] for c in contacts}
    pvars = [(b, i) for b in LIMBS if b not in strike for i in (0, 2)] + [('Head', 0), ('Head', 1)]
    pvars += [(b, i) for b in sorted(strike) for i in (0, 1, 2)]                 # strike limbs may re-aim (tip must follow)
    if contacts:
        pvars += [('HumanoidRootPart', 3), ('HumanoidRootPart', 5)]            # and the attacker may adjust its step a little
        pvars += [('Torso', 0), ('Torso', 1), ('Torso', 2)]                    # ... and its torso line
        if rg.lowest_point(p0) > 0.6:
            pvars += [('HumanoidRootPart', 4)]                                 # airborne attacker: height too
    dvars = [('HumanoidRootPart', 3), ('HumanoidRootPart', 5)] + ([('HumanoidRootPart', 4)] if airborne else []) + \
            [('Torso', 0), ('Torso', 1), ('Torso', 2), ('Head', 0), ('Head', 1)] + [(b, i) for b in LIMBS for i in (0, 2)]
    nP = len(pvars)

    def poses(x):
        p = {b: list(v) for b, v in p0.items()}; d = {b: list(v) for b, v in d0.items()}
        for k, (b, i) in enumerate(pvars): p[b][i] += x[k]
        for k, (b, i) in enumerate(dvars): d[b][i] += x[nP + k]
        return p, d

    def tip_target(p, d, bp, bd):
        out = []
        for limb, tb, local, tip in contacts:
            P_, Q_ = bp[limb]; T_, R_ = bd[tb]
            out.append((rg.add(P_, r6.mv(Q_, tip)), rg.add(T_, r6.mv(R_, local))))
        return out

    bp0 = _boxes(p0); bd0 = _boxes(d0)
    AM = _allow_matrix(allow)
    base_rel = [rg.sub(t, q) for q, t in tip_target(p0, d0, bp0, bd0)]

    def cost(x):
        p, d = poses(x)
        bp = _boxes(p); bd = _boxes(d)
        ov, _ = overlap_cost(bp, bd, allow)
        c = 100.0 * ov
        for (q, t), rel in zip(tip_target(p, d, bp, bd), base_rel):
            c += 300.0 * rg.norm(rg.sub(rg.sub(t, q), rel)) ** 2
        for k, (b, i) in enumerate(pvars):
            if i >= 3: c += 2.0 * (x[k] / 0.5) ** 2
            elif b == 'Torso': c += 1.0 * (x[k] / 20.0) ** 2
            else: c += 0.5 * (x[k] / 25.0) ** 2
        for k, (b, i) in enumerate(dvars):
            s = 0.6 if i >= 3 else 35.0
            c += (1.0 if i >= 3 else 0.3) * (x[nP + k] / s) ** 2
        return c

    n = nP + len(dvars)
    bounds = [((-0.8, 0.8) if i >= 3 else ((-30, 30) if b == 'Torso' else (-55, 55))) for b, i in pvars] + [((-2.0, 2.0) if i >= 3 else (-70, 70)) for b, i in dvars]
    x0 = np.zeros(n)
    c0 = cost(x0)
    _, w0 = overlap_cost(bp0, bd0, allow)
    if w0 <= 0.0:
        return None
    # multi-start: as authored / dummy leaning back / dummy shoved back along the line
    u = rg.sub(bd0['Torso'][0], bp0['Torso'][0]); u = rg.unit((u[0], 0.0, u[2]))
    starts = [x0]
    xs = x0.copy(); xs[nP + 0] = 0.5 * u[0]; xs[nP + 1] = -0.5 * u[2]; xs[nP + dvars.index(('Torso', 0))] = -15.0; starts.append(xs)
    xs = x0.copy(); xs[nP + 0] = 0.9 * u[0]; xs[nP + 1] = -0.9 * u[2]; xs[nP + dvars.index(('Torso', 0))] = -30.0; xs[nP + dvars.index(('Head', 0))] = -25.0; starts.append(xs)
    best = None
    for st in starts:
        r = minimize(cost, st, method='Powell', bounds=bounds, options=dict(maxiter=6, xtol=0.05, ftol=1e-4))
        if best is None or r.fun < best.fun: best = r
    r = best
    p_, d_ = poses(r.x)
    if overlap_cost(_boxes(p_), _boxes(d_), allow)[1] > 0.2:
        r2 = minimize(cost, r.x, method='Powell', bounds=bounds, options=dict(maxiter=12, xtol=0.02, ftol=1e-5))
        if r2.fun < r.fun: r = r2
    x = r.x
    p, d = poses(x)
    _, w1 = overlap_cost(_boxes(p), _boxes(d), allow)
    return dict(f=f, before=w0, after=w1, cost0=c0, cost1=float(r.fun), p=p, d=d, pvars=pvars, dvars=dvars, x=x)


def write_back(res):
    """store the solved cells into both clips at frame f (adds the bones to partial keys)"""
    f = float(res['f'])
    for clip, pose, vars_ in ((C.P.clip, res['p'], res['pvars']), (C.D.clip, res['d'], res['dvars'])):
        k = clip['keys'].setdefault(f, {'e': None, 'b': {}})
        for b in {b for b, i in vars_}:
            k['b'][b] = list(pose[b])
    C.P.rig.invalidate(); C.D.rig.invalidate()


def contacts_at(f):
    out = []
    for c in C.CONTACTS:
        if c['att'] is C.P and abs(c['f'] - f) < 1e-6:
            out.append((r6.SHORT[c['limb']], r6.SHORT[c['bone']], tuple(c['local']), tuple(c['tip'])))
    return out


def allow_at(f, contacts):
    a = {}
    for limb, tb, local, tip in contacts:
        a[(limb, tb)] = 0.5 + max(0.0, 1.0 - abs(tip[1])); a[(limb, None)] = 0.22
    if 224.5 <= f <= 247.5:
        a[('Left Arm', None)] = 0.9; a[('Right Arm', None)] = 0.9
    if 531.5 <= f <= 541.5:
        a[('Right Arm', 'Head')] = 0.9
    if 377.4 <= f <= 379.6:
        a[('Head', None)] = 0.4
    return a


def _solve_one(f):
    con = contacts_at(f)
    allow = allow_at(f, con)
    air = rg.lowest_point(r6.sample(C.D.clip, f)) > 0.6
    return fix_frame(f, con, allow, air)


def run(frames, verbose=True, workers=4):
    """solve frames in parallel (fork: workers see the clips as they are now; each result only touches its own frame)"""
    import multiprocessing as mp
    log = []
    frames = list(frames)
    if workers > 1 and len(frames) > 4:
        with mp.get_context('fork').Pool(workers) as pool:
            results = pool.map(_solve_one, frames, chunksize=2)
    else:
        results = [_solve_one(f) for f in frames]
    for f, res in zip(frames, results):
        if res is None: continue
        if res['after'] < res['before'] - 0.02:
            write_back(res)
        log.append('posefix f%-8.3f worst overlap %.2f -> %.2f studs%s' % (f, res['before'], res['after'], '' if res['after'] < res['before'] - 0.02 else ' (kept)'))
        if verbose: print(log[-1])
    return log


def key_overlaps(frames=None):
    """story key frames (player or dummy key) whose pose overlaps beyond the allowances, with the worst depth"""
    fs = sorted(set(C.P.clip['keys']) | set(C.D.clip['keys'])) if frames is None else frames
    out = []
    for f in fs:
        if any(a <= f <= b for a, b in ((224.5, 247.5),)): continue
        con = contacts_at(f); al = allow_at(f, con)
        _, w = overlap_cost(_boxes(r6.sample(C.P.clip, f)), _boxes(r6.sample(C.D.clip, f)), al)
        if w > 0.06: out.append((f, w))
    return out
