"""Authoring layer over r6: an Actor writes whole-body keys (unspecified bones hold their last cell), carries a Rig for
world queries, and offers the project's own motion builders (ballistic flight, contact nudging).

Pose cells use the skill's semantic vector (pitch, yaw, roll, right, up, fwd); bones: hrp t h ra la rl ll.
HRP cell convention in this project: H(x, y, z, yaw) -> world position of the body centre offset (x right, y up, z TOWARD the
camera-side axis) and yaw about Y (0 faces -Z, +90 faces +X, -90 faces -X, 180 faces +Z).
"""
import math

import rig as rg
import r6

BONES = ('hrp', 't', 'h', 'ra', 'la', 'rl', 'll')
HIP = r6.HIP_Y


def H(x=0.0, y=0.0, z=0.0, yaw=0.0, pitch=0.0, roll=0.0):
    """HRP cell from world offsets: x (+X), y (up from rest hip height), z (+Z); fwd channel is -Z."""
    return (pitch, yaw, roll, x, y, -z)


def Hc(x, yc, z, yaw=0.0, pitch=0.0, roll=0.0):
    """HRP cell from the world position of the body centre (torso centre height yc)."""
    return (pitch, yaw, roll, x, yc - HIP, -z)


def hxyz(cell):
    """world (x, y_centre, z) of an HRP cell"""
    return (cell[3], cell[4] + HIP, -cell[5])


class Actor:
    def __init__(self, name, fps=18):
        r6.new(name, fps)
        self.clip = r6.cur()
        self.rig = rg.Rig(self.clip)
        self.last = {b: [0.0] * 6 for b in BONES}
        self.name = name

    # ---- keying
    def k(self, f, ease='out', **cells):
        cur = {b: list(v) for b, v in self.last.items()}
        for n, v in cells.items():
            cur[n] = list(r6._v6(v))
        r6.put(self.clip, f, ease, **cur)
        self.last = cur
        self.rig.invalidate()
        return cur

    def p(self, f, ease='out', **cells):
        """partial key: only the named bones are keyed (others keep interpolating between their own keys); does not touch the carry state"""
        r6.put(self.clip, f, ease, **{n: list(r6._v6(v)) for n, v in cells.items()})
        self.rig.invalidate()

    def aim(self, f, limb, target, yaw=None, tol=0.03, slack=0.0, verbose=False, tip=(0.0, -1.0, 0.0)):
        """re-solve the pitch/yaw/roll of a limb at an existing key frame so its free end touches a WORLD point.
        slack pushes the tip `slack` studs past the point along the limb direction (a fist that drives into the target)."""
        bone = r6.SHORT[limb]
        P, Q = self.rig.fk(f)['Torso']
        d = rg.sub(target, P)
        loc = r6.mv(r6.mt(Q), d)
        key = self.clip['keys'][float(f)]['b'][bone]
        res = rg.solve_limb(bone, loc, yaw=key[1] if yaw is None else yaw, guess=(key[0], key[1], key[2]), tip_local=tip)
        if res[3] > tol and verbose:
            print('aim f%d %s residual %.3f' % (f, limb, res[3]))
        key[0], key[1], key[2] = res[0], res[1], res[2]
        self.rig.invalidate()
        return res[3]

    def from_frame(self, f):
        """continue authoring from the sampled pose at frame f"""
        p = r6.sample(self.clip, f)
        self.last = {b: list(p.get(r6.SHORT[b], [0.0] * 6)) for b in BONES}

    def cell(self, bone, f=None):
        if f is None: return list(self.last[bone])
        return list(r6.sample(self.clip, f).get(r6.SHORT[bone], [0.0] * 6))

    def tweak(self, f, **deltas):
        """add deltas (6-tuples) to the keyed cells at an existing key frame"""
        k = self.clip['keys'][float(f)]['b']
        for n, d in deltas.items():
            b = r6.SHORT[n]
            k[b] = [a + c for a, c in zip(k[b], r6._v6(d))]
        self.rig.invalidate()

    def nudge_root(self, frames, dx=0.0, dy=0.0, dz=0.0):
        """translate the whole body at the given KEY frames (world axes)"""
        for f in frames:
            kk = self.clip['keys'].get(float(f))
            if not kk: continue
            h = kk['b'].setdefault('HumanoidRootPart', [0.0] * 6)
            h[3] += dx; h[4] += dy; h[5] -= dz
        self.rig.invalidate()

    # ---- planting
    def plant(self, frames):
        """feet-to-floor pass on grounded key frames (skill's plant on this clip)"""
        r6._S['clip'] = self.clip
        r6.plant(frames_=[f for f in frames if float(f) in self.clip['keys']])
        self.rig.invalidate()

    # ---- queries
    def pos(self, f): return self.rig.torso(f)


def ballistic(actor, f0, f1, p0, v0, g=62.0, rot0=(0, 0, 0), spin=(0, 0, 0), yaw0=0.0, fps=18, limbs=None, ease='lin', hold_last=True):
    """Key every frame f0..f1 along a ballistic body-centre path.
    p0: world (x, y_centre, z) at f0; v0: studs/s; spin: (pitch, yaw, roll) deg/s added to rot0 (pitch,yaw,roll) at yaw0 offset.
    limbs: callable(age_frames) -> dict of cells for t,h,ra,la,rl,ll (age 0 at f0).  Returns list of centre positions."""
    path = []
    for f in range(f0, f1 + 1):
        t = (f - f0) / fps
        x = p0[0] + v0[0] * t; y = p0[1] + v0[1] * t - 0.5 * g * t * t; z = p0[2] + v0[2] * t
        pitch = rot0[0] + spin[0] * t; yaw = yaw0 + rot0[1] + spin[1] * t; roll = rot0[2] + spin[2] * t
        cells = {'hrp': Hc(x, y, z, yaw, pitch, roll)}
        if limbs: cells.update(limbs(f - f0))
        actor.k(f, ease, **cells)
        path.append((x, y, z))
    return path


def lerp_cell(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(r6._v6(a), r6._v6(b)))


def wobble(age, amp, period, decay, phase=0.0):
    """damped oscillation used for flop / follow-through in limbs (deg)."""
    return amp * math.exp(-age / decay) * math.sin(2 * math.pi * age / period + phase)
