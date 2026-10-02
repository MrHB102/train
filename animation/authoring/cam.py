"""Camera authoring: shots with their own keys, anchored to action points, plus shake / lens-punch layers.

All times are video frames at 18 fps. A shot is a hard cut: nothing is interpolated across shot boundaries.
Key offsets are world-space vectors relative to the shot anchor (or absolute when anchor is None).
"""
import math
import random

import rig as rg
import r6


def _ease(tok, a):
    return r6.ease(a, tok)


class Shot:
    def __init__(self, f0, f1, anchor=None, keys=(), follow=1.0, name=''):
        """anchor: callable frame -> (x,y,z) | (x,y,z) | None.  follow<1 adds exponential lag to the anchor (frames)
        keys: [dict(f=, pos=(x,y,z), look=(x,y,z), fov=, roll=, e='io')]  pos/look relative to the anchor."""
        self.f0, self.f1, self.anchor, self.follow, self.name = f0, f1, anchor, follow, name
        self.keys = sorted([dict(k) for k in keys], key=lambda k: k['f'])
        for k in self.keys:
            k.setdefault('fov', 60.0); k.setdefault('roll', 0.0); k.setdefault('e', 'io'); k.setdefault('look', (0, 0, 0))

    def anchor_at(self, f):
        a = self.anchor
        if a is None: return (0.0, 0.0, 0.0)
        return a(f) if callable(a) else a

    def sample(self, f, anchor_pos):
        ks = self.keys
        if f <= ks[0]['f']: k = ks[0]; return k['pos'], k['look'], k['fov'], k['roll']
        if f >= ks[-1]['f']: k = ks[-1]; return k['pos'], k['look'], k['fov'], k['roll']
        for i in range(len(ks) - 1):
            a, b = ks[i], ks[i + 1]
            if a['f'] <= f < b['f']:
                t = _ease(a['e'], (f - a['f']) / (b['f'] - a['f']))
                return (rg.lerp(a['pos'], b['pos'], t), rg.lerp(a['look'], b['look'], t),
                        a['fov'] + (b['fov'] - a['fov']) * t, a['roll'] + (b['roll'] - a['roll']) * t)


class AutoShot:
    """Auto-framed shot: keys give orbit angle (az, relative to the action line P->D: 0 = behind P looking at D, 90/-90 = side,
    180 = behind D), elevation, how much of the frame the subject should fill, lens and roll. Distance is computed so the
    subject points always fit, so the shot stays valid while the characters fly around."""

    def __init__(self, f0, f1, subject, keys, line, follow=1.0, name='', aspect=9 / 16):
        self.f0, self.f1, self.subject, self.line, self.follow, self.name, self.aspect = f0, f1, subject, line, follow, name, aspect
        self.keys = sorted([dict(k) for k in keys], key=lambda k: k['f'])
        for k in self.keys:
            k.setdefault('az', 90.0); k.setdefault('el', 0.0); k.setdefault('fill', 0.8); k.setdefault('fov', 55.0)
            k.setdefault('roll', 0.0); k.setdefault('shift', (0.0, 0.0)); k.setdefault('e', 'io'); k.setdefault('mind', 2.2)
        self._sm = None

    def _params(self, f):
        ks = self.keys
        if f <= ks[0]['f']: return dict(ks[0])
        if f >= ks[-1]['f']: return dict(ks[-1])
        for i in range(len(ks) - 1):
            a, b = ks[i], ks[i + 1]
            if a['f'] <= f < b['f']:
                t = _ease(a['e'], (f - a['f']) / (b['f'] - a['f']))
                o = dict(a)
                for k in ('az', 'el', 'fill', 'fov', 'roll', 'mind'): o[k] = a[k] + (b[k] - a[k]) * t
                o['shift'] = (a['shift'][0] + (b['shift'][0] - a['shift'][0]) * t, a['shift'][1] + (b['shift'][1] - a['shift'][1]) * t)
                return o

    def cam(self, f):
        k = self._params(f)
        pts = self.subject(f)
        L = self.line(f)
        az, el = math.radians(k['az']), math.radians(k['el'])
        c, s_ = math.cos(az), math.sin(az)
        fh = (L[0] * c + L[2] * s_, 0.0, -L[0] * s_ + L[2] * c)   # rotate L about Y by az (az=90 on L=+X looks toward -Z: camera on the +Z side)
        fwd = rg.unit((fh[0] * math.cos(el), -math.sin(el), fh[2] * math.cos(el)))
        right = rg.unit(rg.cross(fwd, (0, 1, 0))); up = rg.cross(right, fwd)
        proj = [(rg.dot(p, right), rg.dot(p, up), rg.dot(p, fwd)) for p in pts]
        r0, r1 = min(q[0] for q in proj), max(q[0] for q in proj)
        u0, u1 = min(q[1] for q in proj), max(q[1] for q in proj)
        d0, d1 = min(q[2] for q in proj), max(q[2] for q in proj)
        cr, cu, cd = (r0 + r1) / 2 + k['shift'][0], (u0 + u1) / 2 + k['shift'][1], (d0 + d1) / 2
        er, eu = max((r1 - r0) / 2, 0.3), max((u1 - u0) / 2, 0.3)
        tn = math.tan(math.radians(k['fov']) / 2)
        dist = max(er / (k['fill'] * self.aspect * tn), eu / (k['fill'] * tn)) + (d1 - d0) / 2
        dist = max(dist, k['mind'])
        center = rg.add(rg.add(rg.mul(right, cr), rg.mul(up, cu)), rg.mul(fwd, cd))
        if self._sm is not None and self.follow < 1.0:
            sc, sd = self._sm
            center = rg.lerp(sc, center, self.follow); dist = sd + (dist - sd) * self.follow
        self._sm = (center, dist)
        return rg.sub(center, rg.mul(fwd, dist)), center, k['fov'], k['roll']


class Camera:
    def __init__(self, frames):
        self.frames = frames
        self.shots = []
        self.shakes = []     # (f, amp_studs, roll_deg, decay_frames, seed)
        self.punches = []    # (f, dfov, decay_frames)
        self.cuts = []

    def shot(self, *a, **kw):
        s = Shot(*a, **kw); self.shots.append(s); return s

    def auto(self, *a, **kw):
        s = AutoShot(*a, **kw); self.shots.append(s); return s

    def shake(self, f, amp=0.25, roll=1.2, decay=7, seed=0):
        self.shakes.append((f, amp, roll, decay, seed))

    def punch(self, f, dfov=-6, decay=4):
        self.punches.append((f, dfov, decay))

    def track(self):
        out = [None] * self.frames
        for s in self.shots:
            sm = None
            if isinstance(s, AutoShot):
                s._sm = None
                for f in range(max(0, s.f0), min(self.frames, s.f1)):
                    P, L, fov, roll = s.cam(f)
                    out[f] = [P, L, fov, roll]
                continue
            for f in range(max(0, s.f0), min(self.frames, s.f1)):
                a = s.anchor_at(f)
                if s.follow < 1.0 and sm is not None:
                    sm = tuple(p + (q - p) * s.follow for p, q in zip(sm, a))
                else:
                    sm = a
                pos, look, fov, roll = s.sample(f, sm)
                P = rg.add(sm, pos) if s.anchor is not None else pos
                L = rg.add(sm, look) if s.anchor is not None else look
                out[f] = [P, L, fov, roll]
        for f in range(self.frames):
            if out[f] is None:
                out[f] = out[f - 1] if f else [(0, 4, 16), (0, 3, 0), 60.0, 0.0]
        res = []
        for f in range(self.frames):
            P, L, fov, roll = out[f]
            fwd = rg.unit(rg.sub(L, P)); right = rg.unit(rg.cross(fwd, (0, 1, 0))); up = rg.cross(right, fwd)
            for (sf, amp, rdeg, dec, seed) in self.shakes:
                age = f - sf
                if 0 <= age < dec * 3:
                    k = math.exp(-age / dec)
                    r = random.Random(seed * 1000 + age)
                    dx, dy = (r.random() * 2 - 1) * amp * k, (r.random() * 2 - 1) * amp * k
                    P = rg.add(P, rg.add(rg.mul(right, dx), rg.mul(up, dy)))
                    L = rg.add(L, rg.add(rg.mul(right, dx), rg.mul(up, dy)))
                    roll += (r.random() * 2 - 1) * rdeg * k
            for (pf, dfov, dec) in self.punches:
                age = f - pf
                if 0 <= age < dec * 3: fov += dfov * math.exp(-age / dec)
            res.append([P[0], P[1], P[2], L[0], L[1], L[2], fov, roll])
        return res


def debug_track(rigs, frames, mode='side', fov=62.0, dist=17.0, h=3.4):
    """neutral reviewing camera that follows the midpoint of the fighters (used for blocking review, not for the final cut)."""
    out = []
    for f in range(frames):
        pts = [r.torso(f) for r in rigs]
        mx = sum(p[0] for p in pts) / len(pts); my = sum(p[1] for p in pts) / len(pts); mz = sum(p[2] for p in pts) / len(pts)
        spread = max(max(abs(p[0] - mx) for p in pts), max(abs(p[1] - my) for p in pts) * 0.6)
        d = max(dist, 9.0 + spread * 2.2)
        if mode == 'side': P = (mx, max(h, my * 0.6 + 2.2), mz + d)
        elif mode == '3q': P = (mx + d * 0.6, my + 3.4, mz + d * 0.8)
        elif mode == 'front': P = (mx + d, my + 3, mz)
        else: P = (mx - d * 0.5, my + 4, mz + d * 0.8)
        out.append([P[0], P[1], P[2], mx, my, mz, fov, 0.0])
    return out
