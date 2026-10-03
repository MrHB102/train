"""v2 cinematic camera, evaluated per 120 fps output frame.

Shot design (which angle, lens, cut points) still comes from the direction modules; this layer turns it into an operated
camera:
  * framing        a little tighter and lower than v1, every shot creeps (slow orbit drift + push-in) so no frame is static
  * operator lag   critically-damped springs on the camera position and look-at point, simulated in REAL time (they keep
                   working through slow motion), pre-rolled before each cut so a shot starts already moving
  * frame guard    if the lag would push the subject out of frame, the look-at is pulled back toward the exact framing
  * handheld       smooth multi-sine drift on yaw / pitch / roll and position (stronger on action shots)
  * impact shake   damped sinusoidal shake (translation + roll + pitch kick) instead of per-frame random jumps
  * lens punch     FOV kick that springs back, on the strongest hits
  * focus          focus distance follows the subject; aperture from the lens (long lens / close-up = shallow depth of field)
  * safety         the camera never gets closer than 1.6 studs to any body part
"""
import math
import random

import numpy as np

import choreo as C
import cam as camlib
import rig as rg

FPS = 120.0
DEBUG = {}


def _spring(x, v, target, w, dt):
    """critically damped spring step (semi-implicit), vectors as numpy arrays"""
    a = w * w * (target - x) - 2.0 * w * v
    v = v + a * dt
    x = x + v * dt
    return x, v


def _basis(P, L, roll_deg):
    fwd = rg.unit(rg.sub(L, P)); right = rg.unit(rg.cross(fwd, (0, 1, 0))); up = rg.cross(right, fwd)
    r = math.radians(roll_deg)
    x = rg.add(rg.mul(right, math.cos(r)), rg.mul(up, math.sin(r)))
    y = rg.add(rg.mul(right, -math.sin(r)), rg.mul(up, math.cos(r)))
    return fwd, x, y


def project(P, L, fov, roll, p, aspect=9 / 16):
    fwd, x, y = _basis(P, L, roll)
    d = rg.sub(p, P)
    z = rg.dot(d, fwd)
    if z < 0.05: return None
    t = math.tan(math.radians(fov) / 2)
    return (rg.dot(d, x) / (z * t * aspect), rg.dot(d, y) / (z * t), z)


class Handheld:
    def __init__(self, seed):
        r = random.Random(seed)
        self.comp = [(r.uniform(0.17, 0.33), r.uniform(0, 6.28)), (r.uniform(0.45, 0.8), r.uniform(0, 6.28)), (r.uniform(1.1, 1.9), r.uniform(0, 6.28))]

    def __call__(self, t, k=0):
        s = 0.0
        for i, (fr, ph) in enumerate(self.comp):
            s += math.sin(2 * math.pi * fr * t * (1 + 0.13 * k) + ph + k * 1.7) / (1.0 + i * 0.9)
        return s / 1.8


def shot_at(af):
    """the shot that owns story frame af (later shots override earlier ones, like v1)"""
    owner = None
    for s in C.CAM.shots:
        if s.f0 <= af < s.f1: owner = s
    return owner


def _subject_pts(s, af):
    if isinstance(s, camlib.AutoShot):
        try: return s.subject(af)
        except Exception: pass
    return [C.P.rig.head(af), C.D.rig.head(af), C.P.rig.torso(af), C.D.rig.torso(af)]


def _exact(s, af, k_imm):
    """exact framing of shot s at story frame af with the v2 framing tweaks (no lag). k_imm: seconds since the cut"""
    if isinstance(s, camlib.AutoShot):
        s.follow = 1.0; s._sm = None
        keys = s.keys
        saved = [(k['az'], k['el'], k['fill'], k['fov']) for k in keys]
        sign = 1 if (sum(map(ord, s.name)) + int(s.f0)) % 2 else -1
        for k in keys:
            k['el'] = k['el'] - 3.0
            k['az'] = k['az'] + sign * 7.0 * k_imm            # slow orbit creep
            k['fill'] = min(0.95, k['fill'] * (1.0 + 0.03 * min(k_imm, 3.0)))   # slow push-in
        P, L, fov, roll = s.cam(af)
        for k, (az, el, fill, fv) in zip(keys, saved):
            k['az'], k['el'], k['fill'], k['fov'] = az, el, fill, fv
        return P, L, fov, roll
    a = s.anchor_at(af)
    pos, look, fov, roll = s.sample(af, a)
    P = rg.add(a, pos) if s.anchor is not None else pos
    L = rg.add(a, look) if s.anchor is not None else look
    return P, L, fov, roll


def build(warp, bake, verbose=True):
    """returns per output frame [px,py,pz, lx,ly,lz, fov, roll, focus_dist, aperture] and the cut list (output frames)"""
    n_out = warp.n_total
    afs = [warp.af(n) for n in range(n_out)]
    owners = [shot_at(a) for a in afs]
    camlib.AutoShot.FILL_SCALE = 0.86
    camlib.AutoShot.MIN_DIST = 5.0
    out = [None] * n_out
    cuts = [0] + [n for n in range(1, n_out) if owners[n] is not owners[n - 1]]
    dt = 1.0 / FPS
    seg_bounds = list(zip(cuts, cuts[1:] + [n_out]))
    for si, (n0, n1) in enumerate(seg_bounds):
        s = owners[n0]
        if s is None: continue
        hh = Handheld(si * 31 + 7)
        action = (n1 - n0) / FPS < 1.6
        # pre-roll the springs 0.25 s before the cut (the shot evaluated slightly before its start)
        pre = 30
        x = l = lv = o = ov = None
        gs = 0.0
        t_imm = 0.0
        # 1) exact framing for every frame of the shot (+ pre-roll), then a non-causal gaussian (sigma ~0.07 s) so that
        #    discontinuities of the framing itself (the director switching the subject set) become quick reframes
        ks = list(range(-pre, n1 - n0))
        EX = []
        for k in ks:
            n = n0 + k
            af = warp.af(n) if n >= 0 else afs[0] + n / (FPS / 18.0)
            if k > 0:
                # creep clock: real time, running up to 2.5x faster while the story is in slow motion (bullet-time orbit)
                t_imm += (1.0 + 1.5 * max(0.0, 1.0 - warp.speed(af))) / FPS
            P, L, fov, roll = _exact(s, af, t_imm)
            EX.append((np.array(P, float), np.array(L, float), fov, roll, af, t_imm))
        Pa = np.array([e[0] for e in EX]); La = np.array([e[1] for e in EX])
        sig = 8.0; r = int(3 * sig); gk = np.exp(-np.arange(-r, r + 1) ** 2 / (2 * sig * sig)); gk /= gk.sum()
        def smooth(A):
            Ap = np.concatenate([np.repeat(A[:1], r, 0), A, np.repeat(A[-1:], r, 0)])
            return np.stack([np.convolve(Ap[:, i], gk, mode='valid') for i in range(3)], axis=1)
        Ps, Ls = smooth(Pa), smooth(La)
        for j, k in enumerate(ks):
            n = n0 + k
            P, L = Ps[j], Ls[j]
            fov, roll, af, t_imm = EX[j][2], EX[j][3], EX[j][4], EX[j][5]
            O = P - L                                            # camera offset from its aim point
            dE = float(np.linalg.norm(O))
            if x is None:
                l, lv, o, ov = L.copy(), np.zeros(3), O.copy(), np.zeros(3)
                dd, dv = np.array([dE]), np.array([0.0])
                x = True
            # 2) operator lag: the aim point trails the action; the offset (orbit direction) follows a stiffer spring and
            #    the framing distance eases too, so fast orbits do not cut the corner toward the subject
            l, lv = _spring(l, lv, L, 13.0 if action else 9.0, dt)
            o, ov = _spring(o, ov, O, 16.0 if action else 11.0, dt)
            dd, dv = _spring(dd, dv, np.array([dE]), 15.0 if action else 11.0, dt)
            if k < 0: continue
            o_dir = o / max(np.linalg.norm(o), 1e-6)
            # 3) frame guard: keep the subject inside ~85% of the frame
            pts = _subject_pts(s, af)
            worst = 0.0
            for p in pts:
                pr = project(tuple(l + o_dir * float(dd[0])), tuple(l), fov, roll, p)
                if pr: worst = max(worst, abs(pr[0]), abs(pr[1]))
            g_t = min(1.0, max(0.0, (worst - 0.74) / 0.14))
            g = gs = gs + max(-0.05, min(0.15, g_t - gs))          # rate-limited: the guard eases in/out, never snaps
            Lf = l * (1 - g) + L * g
            Of = o_dir * (1 - g) + (O / max(np.linalg.norm(O), 1e-6)) * g
            dist_f = float(dd[0]) * (1 - g) + dE * g
            Pf = Lf + Of / max(np.linalg.norm(Of), 1e-6) * dist_f
            DEBUG[n] = (g, float(dd[0]), dE, worst)
            out[n] = [Pf, Lf, fov, roll, af, s, t_imm, action]
    # ---- layers in real time: handheld, shakes, punches; then focus and safety
    shakes = [(warp.out(f), amp, rdeg, dec / 18.0, seed) for (f, amp, rdeg, dec, seed) in C.CAM.shakes]
    punches = [(warp.out(f), dfov, dec / 18.0) for (f, dfov, dec) in C.CAM.punches]
    res = []
    hh_by_seg = {}
    for n in range(n_out):
        if out[n] is None:
            out[n] = out[n - 1]
        P, L, fov, roll, af, s, t_imm, action = out[n]
        t = n / FPS
        fwd, xr, yr = _basis(tuple(P), tuple(L), roll)
        dist = float(np.linalg.norm(np.asarray(L) - np.asarray(P)))
        hh = hh_by_seg.setdefault(id(s), Handheld(len(hh_by_seg) * 13 + 3))
        amp = (0.0065 if action else 0.0042) * dist          # ~0.35 / 0.24 deg of drift
        off = np.asarray(xr) * hh(t, 0) * amp + np.asarray(yr) * hh(t, 1) * amp * 0.8
        Lh = np.asarray(L) + off
        Ph = np.asarray(P) + np.asarray(xr) * hh(t, 2) * 0.02 + np.asarray(yr) * hh(t, 3) * 0.015
        rl = roll + hh(t, 4) * (0.35 if action else 0.22)
        for (n0, a, rdeg, dec, seed) in shakes:
            age = (n - n0) / FPS
            if 0 <= age < dec * 5 + 0.05:
                env_ = math.exp(-age / max(dec, 0.02))
                r = random.Random(seed)
                f1, f2, ph1, ph2 = r.uniform(13, 17), r.uniform(9, 12), r.uniform(0, 6.3), r.uniform(0, 6.3)
                sx = math.sin(2 * math.pi * f1 * age + ph1) * a * env_
                sy = math.sin(2 * math.pi * f2 * age + ph2) * a * env_ * 0.8
                d = np.asarray(xr) * sx + np.asarray(yr) * sy
                Ph = Ph + d; Lh = Lh + d * 0.55
                rl += math.sin(2 * math.pi * f2 * age + ph1) * rdeg * env_
        for (n0, dfov, dec) in punches:
            age = (n - n0) / FPS
            if 0 <= age < dec * 6 + 0.05:
                atk = 1 - math.exp(-age / 0.012)
                fov = fov + 0.6 * dfov * atk * math.exp(-age / max(dec, 0.02))
        # focus: harmonic middle of the subject's depth range (both fighters as sharp as possible), aperture from the lens,
        # capped so the subject range stays within ~2.5 px of blur: the background / foreground carry the depth of field
        zs = []
        for p in list(_subject_pts(s, af)) + [C.P.rig.head(af), C.D.rig.head(af)]:
            pr = project(tuple(Ph), tuple(Lh), fov, rl, p)
            if pr and abs(pr[0]) < 1.15 and abs(pr[1]) < 1.15: zs.append(pr[2])
        if zs:
            zn, zf = max(0.5, min(zs)), max(zs)
            focus = 2 * zn * zf / (zn + zf)
            spread = max(abs(1 - focus / zn), abs(1 - focus / zf), 1e-3)
        else:
            focus, spread = dist, 0.05
        aperture = max(0.0, min(1.0, (62.0 - fov) / 34.0))
        aperture = min(aperture, 2.5 / (15.0 * spread))
        res.append([*map(float, Ph), *map(float, Lh), float(fov), float(rl), float(focus), float(aperture)])
    # smooth the focus distance (rack focus, not a jump) except at cuts
    cutset = set(cuts)
    fz = res[0][8]; fv = 0.0
    for n in range(n_out):
        if n in cutset: fz, fv = res[n][8], 0.0
        else:
            fz_, fv = _spring(np.array([fz]), np.array([fv]), np.array([res[n][8]]), 16.0, 1 / FPS); fz = float(fz_[0]); fv = float(fv[0])
        res[n][8] = fz
    # safety: keep the lens out of the bodies and above the floor
    pushed = 0
    for n in range(n_out):
        P = np.array(res[n][0:3]); L = np.array(res[n][3:6])
        if P[1] < 0.9: P[1] = 0.9; res[n][1] = 0.9
        fwd = (L - P) / max(np.linalg.norm(L - P), 1e-6)
        mind = 1e9
        for cid in ('P', 'D'):
            for j in range(6):
                mind = min(mind, np.linalg.norm(bake.parts[cid][n, j, :3] - P) - 1.0)
        if mind < 1.6:
            P = P - fwd * (1.6 - mind); res[n][0:3] = list(map(float, P)); pushed += 1
    if verbose:
        print('camera v2: %d output frames, %d cuts, %d frames pushed out of bodies' % (n_out, len(cuts), pushed))
    return res, cuts
