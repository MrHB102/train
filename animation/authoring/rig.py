"""Project-side helpers on top of the r6-animator skill (r6.py): world-space queries, limb IK, shot export.

Nothing here is a preset animation. The R6 math (FK, pose semantics, easing, lint) comes from the skill's r6.py;
this module only answers geometric questions about poses the project authors and serialises them for the renderer.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, '..', '..', '.claude', 'skills', 'r6-animator', 'scripts'))
sys.path.insert(0, SKILL)
import r6  # noqa: E402

PARTS = ('Torso', 'Head', 'Left Arm', 'Right Arm', 'Left Leg', 'Right Leg')
D2R = math.pi / 180.0


# ------------------------------------------------------------------ vector helpers
def add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def mul(a, k): return (a[0] * k, a[1] * k, a[2] * k)
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def norm(a): return math.sqrt(dot(a, a))
def unit(a):
    n = norm(a)
    return (a[0] / n, a[1] / n, a[2] / n) if n > 1e-9 else (0.0, 0.0, 0.0)
def dist(a, b): return norm(sub(a, b))
def lerp(a, b, t): return tuple(x + (y - x) * t for x, y in zip(a, b))


HALF = {'Torso': (1.0, 1.0, .5), 'Head': (.625, .625, .625), 'Right Arm': (.5, 1.0, .5), 'Left Arm': (.5, 1.0, .5),
        'Right Leg': (.5, 1.0, .5), 'Left Leg': (.5, 1.0, .5)}


def lowest_point(pose):
    f = r6.fk(pose); m = 1e9
    for b, h in HALF.items():
        P, Q = f[b]
        ext = abs(Q[3]) * h[0] + abs(Q[4]) * h[1] + abs(Q[5]) * h[2]
        m = min(m, P[1] - ext)
    return m


# ------------------------------------------------------------------ world queries (Roblox axes: X right, Y up, Z back)
class Rig:
    """Wraps one r6 clip and caches FK per frame."""

    def __init__(self, clip, floor=True):
        self.clip = clip
        self.floor = floor
        self.evalfn = None          # v2: callable(story_frame) -> pose evaluated from the Blender F-curves
        self._cache = {}
        self._pcache = {}

    def pose(self, f):
        """sampled pose with the floor constraint applied: no part may go under y=0 (HRP is lifted by the penetration)."""
        if f in self._pcache:
            return self._pcache[f]
        p = self.evalfn(f) if self.evalfn else r6.sample(self.clip, f)
        if self.floor:
            m = lowest_point(p)
            if m < -1e-3:
                h = list(p.get('HumanoidRootPart', [0.0] * 6)); h[4] += -m; p = dict(p); p['HumanoidRootPart'] = h
        self._pcache[f] = p
        return p

    def fk(self, f):
        if f not in self._cache:
            self._cache[f] = r6.fk(self.pose(f))
        return self._cache[f]

    def invalidate(self):
        self._cache.clear(); self._pcache.clear()

    def point(self, f, bone, local=(0, 0, 0)):
        """world position of a point given in a part's local frame (studs)."""
        b = r6.SHORT.get(bone, bone)
        P, Q = self.fk(f)[b]
        return add(P, r6.mv(Q, local))

    def axis(self, f, bone, local_dir):
        b = r6.SHORT.get(bone, bone)
        return r6.mv(self.fk(f)[b][1], local_dir)

    # convenient anchor points
    def fist(self, f, side='r'):      # centre of the arm's free end
        return self.point(f, side + 'a', (0, -1.0, 0))
    def fist_front(self, f, side='r'):  # knuckle point a little past the end (strike tip)
        return self.point(f, side + 'a', (0, -1.15, 0))
    def sole(self, f, side='r'):
        return self.point(f, side + 'l', (0, -1.0, 0))
    def shin(self, f, side='r'):
        return self.point(f, side + 'l', (0, -0.55, 0))
    def head(self, f): return self.point(f, 'h')
    def chest(self, f): return self.point(f, 't', (0, 0.3, -0.5))
    def torso(self, f): return self.point(f, 't')
    def root(self, f): return self.fk(f)['HumanoidRootPart'][0]
    def facing(self, f):
        """horizontal facing direction (unit) of the torso."""
        v = self.axis(f, 't', (0, 0, -1))
        return unit((v[0], 0.0, v[2]))


# ------------------------------------------------------------------ limb IK (aim a limb tip at a torso-local point)
def _limb_tip_local(bone):
    """tip point of a limb in the limb's local frame, and its joint pivot (joint frame)."""
    return (0.0, -1.0, 0.0)


def solve_limb(bone, target, yaw=0.0, guess=None, tip_local=(0.0, -1.0, 0.0)):
    """semantic (pitch, yaw, roll) for a limb so that its free end (local (0,-1,0)) reaches `target`,
    a point given in the PARENT (torso) frame. Returns (pitch, yaw, roll, residual).
    Arms/legs rotate about the pivot encoded by the canonical R6 Motor6D; solved numerically on r6.fk's own math."""
    b = r6.SHORT.get(bone, bone)
    c0 = r6.J[b][1]
    tgt = tuple(target)

    def tip(p, y, r):
        Rw = r6.sem2rw(b, (p, y, r))
        c1 = r6.J[b][3]
        # part centre in torso frame: c0 - Rw*c1 ; tip = centre + Rw*(0,-1,0)
        rc1 = r6.mv(Rw, c1)
        ctr = (c0[0] - rc1[0], c0[1] - rc1[1], c0[2] - rc1[2])
        t = r6.mv(Rw, tip_local)
        return (ctr[0] + t[0], ctr[1] + t[1], ctr[2] + t[2])

    best = None
    starts = [guess] if guess else []
    starts += [(p, yaw, r) for p in (-60, 0, 45, 90, 135, 180) for r in (-30, 0, 30, 70)]
    for s in starts:
        p, y, r = s
        # damped Gauss-Newton with numerical jacobian, yaw held fixed
        for _ in range(60):
            cur = tip(p, y, r)
            e = sub(tgt, cur)
            if norm(e) < 1e-4:
                break
            h = 0.5
            jp = [(a - b_) / h for a, b_ in zip(tip(p + h, y, r), cur)]
            jr = [(a - b_) / h for a, b_ in zip(tip(p, y, r + h), cur)]
            # solve 2 unknowns (p, r) in least squares
            a11 = dot(jp, jp) + 1e-3; a12 = dot(jp, jr); a22 = dot(jr, jr) + 1e-3
            b1 = dot(jp, e); b2 = dot(jr, e)
            det = a11 * a22 - a12 * a12
            if abs(det) < 1e-12:
                break
            dp = (a22 * b1 - a12 * b2) / det
            dr = (a11 * b2 - a12 * b1) / det
            dp = max(-25, min(25, dp)); dr = max(-25, min(25, dr))
            p += dp; r += dr
        res = norm(sub(tgt, tip(p, y, r)))
        if best is None or res < best[3] - 1e-9:
            best = (p, y, r, res)
        if res < 1e-3:
            break
    return best


# ------------------------------------------------------------------ shot export
def export_shot(path, rigs, frames, cam, w=1080, h=1920, fps=18, fx=(), tags=None, extras=None, focus=None):
    """rigs: {id: {'rig': Rig, 'kind': 'player'|'dummy', 'hair': [...]|None, 'hurt': [...]|None, 'vis': [...]|None}}"""
    out = {'fps': fps, 'frames': frames, 'width': w, 'height': h, 'chars': {}, 'cam': [], 'fx': list(fx)}
    for cid, spec in rigs.items():
        rg = spec['rig']
        parts = {b: [] for b in PARTS}
        for f in range(frames):
            fk = rg.fk(f)
            for b in PARTS:
                P, Q = fk[b]
                parts[b].append([round(P[0], 4), round(P[1], 4), round(P[2], 4)] + [round(q, 5) for q in Q])
        d = {'kind': spec['kind'], 'parts': parts}
        for k in ('hair', 'hurt', 'vis'):
            if spec.get(k) is not None:
                d[k] = spec[k]
        out['chars'][cid] = d
    out['cam'] = [[round(x, 4) for x in c] for c in cam]
    if tags: out['tags'] = tags
    if focus: out['focus'] = [[round(x, 3) for x in c] for c in focus]
    if extras: out.update(extras)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w') as fh:
        json.dump(out, fh, separators=(',', ':'))
    return path
