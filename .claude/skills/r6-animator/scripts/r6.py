"""r6 - R6 animation math/authoring utilities. Read and extend when the brief needs it; no motion presets.

BOOT   : import sys; sys.path.insert(0, r"<SKILL>/scripts"); import r6          (works inside Blender and outside)
FLOW   : r6.use() -> r6.new("Walk", fps=30, loop=True) -> r6.table(...)/r6.track(bone, 'f:v f:v')/r6.key(...) -> r6.build() -> r6.sheet() -> r6.check()
POSE   : bones  t=Torso h=Head la/ra=Left/Right Arm ll/rl=Left/Right Leg hrp=HumanoidRootPart
         value  (pitch,yaw,roll,right,up,fwd)  degrees / studs, relative to rest; trailing zeros optional; bare number = pitch.
         pitch+ = limb tip swings to the FRONT (head/torso: top leans FRONT)   roll+ = limb tip swings OUTWARD (torso/head: tilt to the character's RIGHT)
         yaw+   = front turns OUTWARD (torso/head: turn to the character's RIGHT).  Same numbers on L and R = mirror-symmetric pose.
GROUND : r6.plant() puts the lowest foot of every key on the floor (torso up-offset); skip airborne keys with plant(skip=[...]).
EASE   : lin step in out io | bo bi bio (bounce) | eo ei eio (elastic).  Easing on a key shapes the segment key -> next key (Roblox Pose semantics).
"""
import math, json, os, sys

D2R = math.pi / 180.0
BONES = ('HumanoidRootPart', 'Torso', 'Head', 'Left Arm', 'Right Arm', 'Left Leg', 'Right Leg')
SHORT = {'hrp': 'HumanoidRootPart', 't': 'Torso', 'h': 'Head', 'la': 'Left Arm', 'ra': 'Right Arm', 'll': 'Left Leg', 'rl': 'Right Leg'}
KEY = {v: k for k, v in SHORT.items()}

# ------------------------------------------------------------------ 3x3 math (row-major 9-tuples) ---
def mm(a, b):
    return (a[0]*b[0]+a[1]*b[3]+a[2]*b[6], a[0]*b[1]+a[1]*b[4]+a[2]*b[7], a[0]*b[2]+a[1]*b[5]+a[2]*b[8],
            a[3]*b[0]+a[4]*b[3]+a[5]*b[6], a[3]*b[1]+a[4]*b[4]+a[5]*b[7], a[3]*b[2]+a[4]*b[5]+a[5]*b[8],
            a[6]*b[0]+a[7]*b[3]+a[8]*b[6], a[6]*b[1]+a[7]*b[4]+a[8]*b[7], a[6]*b[2]+a[7]*b[5]+a[8]*b[8])
def mt(a): return (a[0], a[3], a[6], a[1], a[4], a[7], a[2], a[5], a[8])
def mv(a, v): return (a[0]*v[0]+a[1]*v[1]+a[2]*v[2], a[3]*v[0]+a[4]*v[1]+a[5]*v[2], a[6]*v[0]+a[7]*v[1]+a[8]*v[2])
def rx(t): c, s = math.cos(t), math.sin(t); return (1, 0, 0, 0, c, -s, 0, s, c)
def ry(t): c, s = math.cos(t), math.sin(t); return (c, 0, s, 0, 1, 0, -s, 0, c)
def rz(t): c, s = math.cos(t), math.sin(t); return (c, -s, 0, s, c, 0, 0, 0, 1)
I3 = (1, 0, 0, 0, 1, 0, 0, 0, 1)
def _cl(x): return max(-1.0, min(1.0, x))
def xyz(a, b, c): return mm(mm(rx(a), ry(b)), rz(c))          # Roblox CFrame.Angles order
def yxz(a, b, c): return mm(mm(ry(b), rx(a)), rz(c))          # args (x, y, z) -> Ry*Rx*Rz
def to_xyz(R):
    b = math.asin(_cl(R[2]))
    if abs(R[2]) < 0.999999: return math.atan2(-R[5], R[8]), b, math.atan2(-R[1], R[0])
    return math.atan2(R[7], R[4]), b, 0.0
def to_yxz(R):
    a = math.asin(_cl(-R[5]))
    if abs(R[5]) < 0.999999: return a, math.atan2(R[2], R[8]), math.atan2(R[3], R[4])
    return a, math.atan2(-R[6], R[0]), 0.0

# ------------------------------------------------------------------ canonical R6 rig ---------------
_RJ = (-1, 0, 0, 0, 0, 1, 0, 1, 0)                 # RootJoint / Neck C0=C1 rotation
_RS = (0, 0, 1, 0, 1, 0, -1, 0, 0)                 # Right Shoulder / Right Hip
_LS = (0, 0, -1, 0, 1, 0, 1, 0, 0)                 # Left  Shoulder / Left  Hip
# bone: (parent, C0.pos, C0=C1 rot (Jr), C1.pos, side, tip_down, part_size)
J = {
    'HumanoidRootPart': (None, (0, 0, 0), I3, (0, 0, 0), 'C', 0, (2, 2, 1)),
    'Torso': ('HumanoidRootPart', (0, 0, 0), _RJ, (0, 0, 0), 'C', 0, (2, 2, 1)),
    'Head': ('Torso', (0, 1, 0), _RJ, (0, -.5, 0), 'C', 0, (2, 1, 1)),
    'Right Arm': ('Torso', (1, .5, 0), _RS, (-.5, .5, 0), 'R', 1, (1, 2, 1)),
    'Left Arm': ('Torso', (-1, .5, 0), _LS, (.5, .5, 0), 'L', 1, (1, 2, 1)),
    'Right Leg': ('Torso', (1, -1, 0), _RS, (.5, 1, 0), 'R', 1, (1, 2, 1)),
    'Left Leg': ('Torso', (-1, -1, 0), _LS, (-.5, 1, 0), 'L', 1, (1, 2, 1)),
}
HIP_Y = 3.0                                        # torso/HRP centre height above ground at rest (studs)
def _sg(b):
    side, down = J[b][4], J[b][5]
    sp = 1 if down else -1
    return sp, (1 if side == 'L' else -1), sp * (-1 if side == 'L' else 1)
SG = {b: _sg(b) for b in BONES}
LIMB = {b for b in BONES if J[b][5]}               # limbs use XYZ euler, centre bones YXZ

def sem2rw(b, v):
    """semantic (pitch,yaw,roll) -> character-frame rotation matrix"""
    sp, sy, sr = SG[b]; p, y, r = (v[0] * sp * D2R, v[1] * sy * D2R, v[2] * sr * D2R)
    return xyz(p, y, r) if b in LIMB else yxz(p, y, r)
def rw2sem(b, R):
    sp, sy, sr = SG[b]
    a, c, d = to_xyz(R) if b in LIMB else to_yxz(R)
    return [sp * a / D2R, sy * c / D2R, sr * d / D2R]

def sem2cf(b, v):
    """semantic vector (<=6) -> Roblox Pose.CFrame (joint space, 12 floats x,y,z,r00..r22)"""
    v = list(v) + [0.0] * (6 - len(v)); Jr = J[b][2]
    Rw = sem2rw(b, v); Rt = mm(mm(mt(Jr), Rw), Jr)
    T = mv(mt(Jr), (v[3], v[4], -v[5]))
    return [T[0], T[1], T[2]] + list(Rt)
def cf2sem(b, cf):
    Jr = J[b][2]; Rw = mm(mm(Jr, tuple(cf[3:12])), mt(Jr)); t = mv(Jr, cf[:3])
    return rw2sem(b, Rw) + [t[0], t[1], -t[2]]

# ------------------------------------------------------------------ easing -------------------------
# token -> (Roblox EasingStyle, EasingDirection) ; Roblox style 0 Linear 1 Constant 2 Elastic 4 Bounce 5 CubicV2 ; dir 0 In 1 Out 2 InOut
TOK = {'lin': (0, 1), 'step': (1, 1), 'in': (5, 0), 'out': (5, 1), 'io': (5, 2), 'bi': (4, 0), 'bo': (4, 1), 'bio': (4, 2),
       'ei': (2, 0), 'eo': (2, 1), 'eio': (2, 2)}
ALIAS = {'linear': 'lin', 'constant': 'step', 'cubic': 'out', 'inout': 'io', 'smooth': 'io', 'bounce': 'bo', 'elastic': 'eo', '': 'lin', None: 'lin'}
BL = {'lin': ('LINEAR', 'AUTO'), 'step': ('CONSTANT', 'AUTO'), 'in': ('CUBIC', 'EASE_IN'), 'out': ('CUBIC', 'EASE_OUT'), 'io': ('CUBIC', 'EASE_IN_OUT'),
      'bi': ('BOUNCE', 'EASE_IN'), 'bo': ('BOUNCE', 'EASE_OUT'), 'bio': ('BOUNCE', 'EASE_IN_OUT'),
      'ei': ('ELASTIC', 'EASE_IN'), 'eo': ('ELASTIC', 'EASE_OUT'), 'eio': ('ELASTIC', 'EASE_IN_OUT')}
def tok(es, ed=1):
    """Roblox (EasingStyle, EasingDirection) -> token.  Cubic(3) is treated as CubicV2(5)."""
    if es == 0: return 'lin'
    if es == 1: return 'step'
    d = {0: 'i', 1: 'o', 2: 'io'}.get(ed, 'o')
    if es in (3, 5): return {'i': 'in', 'o': 'out', 'io': 'io'}[d]
    return ('b' if es == 4 else 'e') + d
def _tok(e):
    e = ALIAS.get(e, e)
    if e not in TOK: raise ValueError("ease '%s' unknown; use %s" % (e, ' '.join(TOK)))
    return e

def _bounce_out(x):
    n, d = 7.5625, 2.75
    if x < 1 / d: return n * x * x
    if x < 2 / d: x -= 1.5 / d; return n * x * x + .75
    if x < 2.5 / d: x -= 2.25 / d; return n * x * x + .9375
    x -= 2.625 / d; return n * x * x + .984375
def _elastic_out(x):
    if x <= 0 or x >= 1: return x
    return 2 ** (-10 * x) * math.sin((x * 10 - .75) * (2 * math.pi / 3)) + 1
def ease(a, t):
    """eased progress for raw progress a in [0,1] with token t"""
    if a <= 0: return 0.0
    if a >= 1: return 1.0
    if t == 'lin': return a
    if t == 'step': return 0.0
    if t in ('in', 'out', 'io'): k = 'c'; d = {'in': 'i', 'out': 'o', 'io': 'io'}[t]
    else: k = t[0]; d = t[1:]
    def f_out(x):
        return 1 - (1 - x) ** 3 if k == 'c' else (_bounce_out(x) if k == 'b' else _elastic_out(x))
    if d == 'o': return f_out(a)
    if d == 'i': return 1 - f_out(1 - a)
    return (1 - f_out(1 - 2 * a)) / 2 if a < .5 else (1 + f_out(2 * a - 1)) / 2

# ------------------------------------------------------------------ clip model ----------------------
# clip = {'name','fps','loop','ease','keys':{frame:{'e':token or None,'b':{bone:[6 floats]}}}}
def _v6(v):
    if isinstance(v, (int, float)): v = (v,)
    v = [float(x) for x in v][:6]; return v + [0.0] * (6 - len(v))
def _bone(k):
    k = SHORT.get(str(k).lower(), k)
    if k not in J: raise KeyError("bone '%s'; use %s" % (k, ' '.join(SHORT)))
    return k
def clip(name='clip', fps=30, loop=False, ease_='out'):
    if not math.isfinite(float(fps)) or fps <= 0: raise ValueError('fps must be positive and finite')
    return {'name': name, 'fps': fps, 'loop': loop, 'ease': _tok(ease_), 'keys': {}}
def put(c, f, e=None, reset=False, **pose):
    k = c['keys'].setdefault(float(f), {'e': None, 'b': {}})
    if e is not None: k['e'] = _tok(e)
    if reset:
        for b in BONES[1:]: k['b'][b] = [0.0] * 6
    for n, v in pose.items(): k['b'][_bone(n)] = _v6(v)
    return k
def frames(c): return sorted(c['keys'])
def length(c): fs = frames(c); return (fs[-1] - fs[0]) / c['fps'] if fs else 0.0

def sample(c, f):
    """pose dict {bone: [6]} at frame f (value-space interpolation with per-key easing)"""
    out = {}
    for b in BONES:
        ks = [(g, c['keys'][g]) for g in frames(c) if b in c['keys'][g]['b']]
        if not ks: continue
        if f <= ks[0][0]: out[b] = list(ks[0][1]['b'][b]); continue
        if f >= ks[-1][0]: out[b] = list(ks[-1][1]['b'][b]); continue
        for i in range(len(ks) - 1):
            g0, k0 = ks[i]; g1, k1 = ks[i + 1]
            if g0 <= f < g1:
                a = ease((f - g0) / (g1 - g0), k0['e'] or c['ease'])
                v0, v1 = k0['b'][b], k1['b'][b]; out[b] = [x + (y - x) * a for x, y in zip(v0, v1)]; break
    return out

def mirror_pose(p):
    """mirror a pose dict across the sagittal plane"""
    sw = {'Left Arm': 'Right Arm', 'Right Arm': 'Left Arm', 'Left Leg': 'Right Leg', 'Right Leg': 'Left Leg'}
    o = {}
    for b, v in p.items():
        if b in sw: o[sw[b]] = list(v)                              # outward/front semantics are already symmetric
        else: o[b] = [v[0], -v[1], -v[2], -v[3], v[4], v[5]]       # centre bones: yaw/roll/right flip
    return o

def retime(c, speed=1.0, amp=1.0, bones=None):
    """returns a copy: time / speed, angles * amp (offsets untouched)"""
    n = clip(c['name'], c['fps'], c['loop'], c['ease']); f0 = frames(c)[0] if c['keys'] else 0
    for f, k in c['keys'].items():
        nk = n['keys'].setdefault(f0 + (f - f0) / speed, {'e': k['e'], 'b': {}})
        for b, v in k['b'].items():
            nk['b'][b] = [x * amp for x in v[:3]] + list(v[3:]) if (bones is None or KEY[b] in bones) else list(v)
    return n

# ------------------------------------------------------------------ forward kinematics + lint -------
def fk(pose):
    """pose {bone:[6]} -> {bone: (centre(x,y,z roblox axes), R(character frame))}; Y up, -Z front, ground y=0 at rest"""
    out = {}
    def go(b, P0, Q0):
        _, c0, _, c1, _, _, _ = J[b]
        v = _v6(pose.get(b, ())); Rw = sem2rw(b, v); t = (v[3], v[4], -v[5])
        loc = mv(Q0, (c0[0] + t[0] - mv(Rw, c1)[0], c0[1] + t[1] - mv(Rw, c1)[1], c0[2] + t[2] - mv(Rw, c1)[2]))
        P = (P0[0] + loc[0], P0[1] + loc[1], P0[2] + loc[2]); Q = mm(Q0, Rw); out[b] = (P, Q)
        for k, jv in J.items():
            if jv[0] == b: go(k, P, Q)
    go('HumanoidRootPart', (0, HIP_Y, 0), I3)
    return out
def foot_y(pose):
    """lowest point of each leg (studs above rest ground)"""
    f = fk(pose); r = {}
    for b in ('Left Leg', 'Right Leg'):
        P, Q = f[b]; pts = []
        for sx in (-.5, .5):
            for sz in (-.5, .5): v = mv(Q, (sx, -1, sz)); pts.append(P[1] + v[1])
        r[b] = min(pts)
    return r

HALF = {'Torso': (1.0, 1.0, .5), 'Head': (.625, .5, .5), 'Right Arm': (.5, 1.0, .5), 'Left Arm': (.5, 1.0, .5), 'Right Leg': (.5, 1.0, .5), 'Left Leg': (.5, 1.0, .5)}
_PAIRS = (('Right Arm', 'Torso', .62), ('Left Arm', 'Torso', .62), ('Right Leg', 'Torso', .62), ('Left Leg', 'Torso', .62), ('Right Arm', 'Head', .5), ('Left Arm', 'Head', .5),
          ('Head', 'Torso', .6), ('Right Arm', 'Left Arm', .5), ('Right Leg', 'Left Leg', .6), ('Right Arm', 'Right Leg', .6), ('Left Arm', 'Left Leg', .6), ('Right Arm', 'Left Leg', .6), ('Left Arm', 'Right Leg', .6))
def _cr(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def _dt(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def depth(pa, qa, ha, pb, qb, hb):
    """penetration depth (studs) of two oriented boxes (SAT, minimum translation); 0 = apart"""
    A = [(qa[i], qa[3 + i], qa[6 + i]) for i in range(3)]; B = [(qb[i], qb[3 + i], qb[6 + i]) for i in range(3)]      # columns = box axes in the character frame
    d = (pb[0] - pa[0], pb[1] - pa[1], pb[2] - pa[2]); best = 1e9
    for ax in A + B + [_cr(a, b) for a in A for b in B]:
        n = math.sqrt(_dt(ax, ax))
        if n < 1e-6: continue
        ax = (ax[0] / n, ax[1] / n, ax[2] / n)
        ov = sum(ha[i] * abs(_dt(A[i], ax)) for i in range(3)) + sum(hb[i] * abs(_dt(B[i], ax)) for i in range(3)) - abs(_dt(d, ax))
        if ov <= 0: return 0.0
        best = min(best, ov)
    return best
def hits(pose):
    """[(boneA, boneB, depth, limit)] pairs of body parts that interpenetrate more than the joint geometry explains"""
    f = fk(pose); out = []
    for a, b, lim in _PAIRS:
        dp = depth(f[a][0], f[a][1], HALF[a], f[b][0], f[b][1], HALF[b])
        if dp > lim: out.append((a, b, dp, lim))
    return out

LIM = {'Head': ((-60, 70), (-85, 85), (-45, 45)), 'Torso': ((-45, 60), (-75, 75), (-45, 45)),
       'Right Arm': ((-60, 190), (-95, 95), (-75, 190)), 'Left Arm': ((-60, 190), (-95, 95), (-75, 190)),
       'Right Leg': ((-70, 120), (-60, 60), (-35, 60)), 'Left Leg': ((-70, 120), (-60, 60), (-35, 60))}
def lint(c, max_lines=14, strict=False):
    """text report of likely problems; empty list = clean.  Limbs through the body are INFO (stylised poses may break the shoulder on purpose); strict=True makes them W"""
    out = []; fs = frames(c)
    if len(fs) < 2: return ['W only %d key' % len(fs)]
    fps = c['fps']; names = ('pitch', 'yaw', 'roll')
    for f in fs:
        for b, v in c['keys'][f]['b'].items():
            for i in range(3):
                lo, hi = LIM.get(b, ((-360, 360),) * 3)[i]
                if v[i] < lo - 1e-6 or v[i] > hi + 1e-6: out.append('W f%g %s %s %.0f° outside [%d,%d]' % (f, KEY[b], names[i], v[i], lo, hi))
    for i in range(len(fs) - 1):                                      # pops / long gaps
        f0, f1 = fs[i], fs[i + 1]
        for b in BONES:
            if b in c['keys'][f0]['b'] and b in c['keys'][f1]['b']:
                d = max(abs(x - y) for x, y in zip(c['keys'][f0]['b'][b][:3], c['keys'][f1]['b'][b][:3]))
                if d > 120: out.append('W f%g-%g %s turns %.0f° in one segment: add an in-between (quaternion shortcut)' % (f0, f1, KEY[b], d))
                sp = d / max(f1 - f0, 1e-6) * fps
                if sp > 2400 and f1 - f0 > 1e-6: out.append('I f%g-%g %s %.0f°/s (snap; ok only for impacts)' % (f0, f1, KEY[b], sp))
        if (f1 - f0) / fps > 0.6 and (c['keys'][f0]['e'] or c['ease']) not in ('step',): out.append('I f%g-%g %.2fs between keys: dead stretch unless it is a deliberate hold' % (f0, f1, (f1 - f0) / fps))
    if c['loop']:
        a, z = c['keys'][fs[0]]['b'], c['keys'][fs[-1]]['b']
        for b in set(a) | set(z):
            va, vz = a.get(b, [0] * 6), z.get(b, [0] * 6)
            if max(abs(x - y) for x, y in zip(va, vz)) > 1.0: out.append('W loop: %s differs first/last key (%.1f): copy first key to the end' % (KEY[b], max(abs(x - y) for x, y in zip(va, vz))))
    lo = 1e9; hi = -1e9; seen_hit = set(); step = max(1, int((fs[-1] - fs[0]) / 60))
    f = fs[0]
    while f <= fs[-1] + 1e-9:
        p = sample(c, f); fy = foot_y(p); m = min(fy.values()); lo = min(lo, m)
        if p.get('Torso'): hi = max(hi, p['Torso'][4])
        if m < -0.15: out.append('W f%g feet %.2f studs under the ground (torso too low / legs too straight-down)' % (f, -m))
        for a, b, dp, lm in hits(p):
            k = (a, b)
            if k not in seen_hit: seen_hit.add(k); out.append('%s f%g %s intersects %s by %.2f studs%s' % ('W' if strict else 'I', f, KEY[a], KEY[b], dp, ': re-pose so the limb stays attached' if strict else ' (ok when the pose is stylised on purpose; check(strict=True) to flag)'))
        f += step
    if not any(k['b'].get('Torso') and any(abs(x) > 0.01 for x in k['b']['Torso'][:5]) for k in c['keys'].values()): out.append('I torso never moves: add weight shift / bob / lean')
    return out[:max_lines]

# ------------------------------------------------------------------ Roblox raw <-> clip -------------
def to_raw(c, bake=False):
    """clip -> raw KeyframeSequence dict for rbx.write_rbxmx"""
    fs = frames(c); f0 = fs[0]; kfs = []
    times = fs if not bake else [f0 + i for i in range(int(fs[-1] - f0) + 1)]
    for f in times:
        poses = sample(c, f) if bake else c['keys'][f]['b']
        e = 'lin' if bake else (c['keys'][f]['e'] or c['ease'])
        kfs.append({'t': (f - f0) / c['fps'], 'name': 'Keyframe', 'markers': [],
                    'poses': {b: {'cf': sem2cf(b, v), 'es': TOK[e][0], 'ed': TOK[e][1], 'w': 1.0} for b, v in poses.items()}})
    return {'name': c['name'], 'loop': c['loop'], 'priority': 2, 'hip': 0.0, 'path': '', 'kfs': kfs}
def _fr(t, fps):
    f = float(t) * fps; r = round(f)
    return float(r) if abs(f - r) < 1e-2 else round(f, 4)         # snap float noise so keys stay on whole frames
def from_raw(seq, fps=30):
    """raw sequence (rbx.sequences) -> clip (time kept exactly: frames = seconds*fps)"""
    c = clip(seq['name'], fps, seq.get('loop', False), 'lin')
    for kf in seq['kfs']:
        k = c['keys'].setdefault(_fr(kf['t'], fps), {'e': None, 'b': {}})
        for n, p in kf['poses'].items():
            if n not in J or p.get('w', 1.0) <= 0: continue
            k['b'][n] = cf2sem(n, p['cf']); k['e'] = tok(p['es'], p['ed'])
    return c
def clip_json(c, nd=1, translation_nd=3):
    """compact JSON-able form: [[time_s, {short:[trimmed values]}, ease], ...]"""
    fs = frames(c); f0 = fs[0] if fs else 0; out = []
    for f in fs:
        k = c['keys'][f]; d = {}
        for b, v in k['b'].items():
            v = [round(x, nd if i < 3 else translation_nd) + 0.0 for i, x in enumerate(v)]
            while len(v) > 1 and v[-1] == 0: v.pop()
            d[KEY[b]] = v
        out.append([round((f - f0) / c['fps'], 4), d, k['e'] or c['ease']])
    return out
def clip_from_json(keys, name='clip', fps=30, loop=False):
    c = clip(name, fps, loop, 'out')
    for t, d, e in keys:
        k = c['keys'].setdefault(_fr(t, fps), {'e': e, 'b': {}}); k['e'] = e
        for s, v in d.items(): k['b'][_bone(s)] = _v6(v)
    return c

# ------------------------------------------------------------------ authoring helpers ---------------
_S = {'clip': None, 'arm': None}
def new(name, fps=30, loop=False, ease='out'):
    _S['clip'] = clip(name, fps, loop, ease); return 'clip %s fps=%s loop=%s ease=%s' % (name, fps, loop, ease)
def cur():
    if _S['clip'] is None: raise RuntimeError('r6.new(name) first')
    return _S['clip']
def key(f, ease=None, reset=False, **pose):
    put(cur(), f, ease, reset, **pose); return 'k%g' % f
def table(txt):
    """whitespace table. header: f [ease] <bones...>; cells: n | n,n,n,... | -  (not keyed).  '#' comments.
       f    ra       la      rl     ll      t            ease
       0    40       -40     -30    30      0,0,0,0,.1   out"""
    rows = [l.split('#')[0].split() for l in txt.strip().splitlines()]; rows = [r for r in rows if r]
    hdr = [h.lower() for h in rows[0]]; c = cur(); n = 0
    for r in rows[1:]:
        f = float(r[0]); pose = {}; e = None
        for h, cell in zip(hdr[1:], r[1:]):
            if cell == '-': continue
            if h == 'ease': e = cell; continue
            pose[h] = [float(x) for x in cell.split(',') if x != '']
        put(c, f, e, **pose); n += 1
    return '%d keys, %gs' % (len(c['keys']), length(c))
def track(bone, txt, ease=None):
    """key ONE bone on its own frames (stagger bones = fluid): 'f:pitch,yaw,roll,right,up,fwd[@ease] f:...'  e.g.
       r6.track('ra', '0:38,0,22 56:-8,0,28 72:-50,0,28@io 79:90,-4,8')"""
    c = cur(); n = 0
    for tk in txt.split():
        f, _, v = tk.partition(':'); v, _, e = v.partition('@')
        put(c, float(f), e or ease, **{_bone(bone): [float(x) for x in v.split(',') if x != '']}); n += 1
    return '%s: %d keys' % (_bone(bone), n)
def alive(f0, f1, step=10, amp=3.0, bones=('t', 'h', 'ra', 'la', 'rl', 'll')):
    """living hold: adds a key every `step` frames in (f0, f1) that nudges each bone's pitch/yaw/roll by a slow +-`amp` deg drift (house style:
       holds creep 3-6 deg, never freeze).  Use ONLY inside holds, after the beats are authored; bones already keyed on a frame are left alone."""
    c = cur(); n = 0; f = float(f0) + step
    while f < f1 - 1e-6:
        p = sample(c, f)
        for i, b in enumerate(bones):
            B = _bone(b)
            if B not in p or (f in c['keys'] and B in c['keys'][f]['b']): continue
            v = list(p[B]); ph = f / (step * 2.7)
            for j in range(3): v[j] += amp * math.sin(ph * 2.0 + i * 1.7 + j * 2.1) * (0.6 if j else 1.0)
            put(c, f, **{B: v}); n += 1
        f += step
    return 'alive %d keys in f%g-%g' % (n, f0, f1)
def copy(f0, f1, mirror=False, ease=None):
    c = cur(); k = c['keys'][float(f0)]; p = mirror_pose(k['b']) if mirror else {b: list(v) for b, v in k['b'].items()}
    c['keys'][float(f1)] = {'e': ease or k['e'], 'b': p}; return 'k%g<-k%g' % (f1, f0)
def cycle():
    """loop clip: last key = first key (keeps first key's easing)"""
    c = cur(); c['loop'] = True; fs = frames(c); k = c['keys'][fs[0]]
    c['keys'][fs[-1]]['b'] = {b: list(v) for b, v in k['b'].items()}; return 'loop closed at f%g' % fs[-1]
def plant(frames_=None, skip=(), air=0.05):
    """feet-to-ground pass: sets the torso 'up' offset of each key frame (default all; not `skip`, not frames where hrp is raised > air studs)
       so the lowest foot rests exactly on the ground.  Works on the SAMPLED pose, so bones keyed on different frames (tracks) stay intact.
       Call after posing the legs, before check().  Do NOT plant airborne keys (jump/run flight)."""
    c = cur(); n = 0; sk = [float(x) for x in skip]
    for f in (frames_ if frames_ is not None else frames(c)):
        f = float(f)
        if f in sk: continue
        p = sample(c, f); h = p.get('HumanoidRootPart')
        if h and h[4] > air: continue
        t = list(p.get('Torso', [0.0] * 6)); t[4] = 0.0; q = dict(p); q['Torso'] = t
        t[4] = round(-min(foot_y(q).values()), 3); c['keys'][f]['b']['Torso'] = t; n += 1
    return 'planted %d keys' % n
def speed(k=1.0, amp=1.0, bones=None): _S['clip'] = retime(cur(), k, amp, bones); return 'speed x%g amp x%g' % (k, amp)
def check(strict=False): r = lint(cur(), strict=strict); return '\n'.join(r) if r else 'clean'
def info():
    c = cur(); return '%s %gs %d keys fps=%s loop=%s' % (c['name'], length(c), len(c['keys']), c['fps'], c['loop'])
def export(path=None, bake=False):
    """-> .rbxmx (Roblox Studio: drag into the Animation Editor / Insert). Needs rbx.py next to this file."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import rbx
    c = cur(); path = path or os.path.join(os.path.expanduser('~'), c['name'] + '.rbxmx')
    return rbx.write_rbxmx(to_raw(c, bake), path)
_LIB = {}
def stash(name):
    """store a copy of the current clip as a reusable segment (cycle, hit, pose...).  Then r6.new(...) a master and r6.add(name, ...) it."""
    import copy; _LIB[name] = copy.deepcopy(cur()); c = _LIB[name]
    return 'stashed "%s": %d keys, %.2fs @%sfps' % (name, len(c['keys']), length(c), c['fps'])
def add(name, at=0.0, times=1, mirror=False, speed=1.0, amp=1.0, travel=0.0, root='auto'):
    """paste a stashed segment into the current clip, `at` seconds.  times>1 repeats it (a loop's last key == first key is shared);
       travel = studs the root advances per repetition (adds to hrp fwd: run/walk stride).  The first/last key of the segment get all
       six R6 bones filled in, so segments join cleanly.  A later segment wins on a shared frame.
       root='auto': the segment's root offset (hrp right/fwd) continues from where the clip's root is at `at` (no teleport between
       run -> jump -> punch); root=0 restarts at the origin; root=(right, fwd) starts there."""
    c = cur(); s = retime(_LIB[name], speed, amp)
    if mirror:
        for k in s['keys'].values(): k['b'] = mirror_pose(k['b'])
    fs = frames(s); f0, span = fs[0], max(fs[-1] - fs[0], 1e-9); n = max(1, int(times)); fill = {}
    for f in (fs[0], fs[-1]):
        p = sample(s, f); fill[f] = {b: p.get(b, [0.0] * 6) for b in BONES[1:]}
    if root == 'auto':
        h0 = sample(c, _fr(at, c['fps'])).get('HumanoidRootPart') if c['keys'] else None; base = (h0[3], h0[5]) if h0 else (0.0, 0.0)
    elif root in (0, None, False): base = (0.0, 0.0)
    else: base = (float(root[0]), float(root[1]))
    for i in range(n):
        for j, f in enumerate(fs):
            if i > 0 and j == 0: continue
            k = s['keys'][f]; b = {x: list(v) for x, v in k['b'].items()}
            if f in fill:
                for x, v in fill[f].items(): b.setdefault(x, list(v))
            if travel or 'HumanoidRootPart' in b or base != (0.0, 0.0):
                prog = (f - f0 + i * span) / span; h = b.get('HumanoidRootPart', [0.0] * 6); h[3] += base[0]; h[5] += base[1] + travel * prog; b['HumanoidRootPart'] = h
            c['keys'][_fr((at + (f - f0 + i * span) / s['fps']), c['fps'])] = {'e': k['e'], 'b': b}
    return 'added "%s" x%d at %gs (%gs long)' % (name, n, at, n * span / s['fps'])
def dump(path=None, precision=6, translation_precision=7):
    """current clip -> compact JSON (feed it to  db.py add FILE  to learn from your own animation)"""
    c = cur(); d = {'name': c['name'], 'fps': c['fps'], 'loop': c['loop'], 'keys': clip_json(c, precision, translation_precision)}
    if path:
        with open(path, 'w', encoding='utf-8') as f: json.dump(d, f)
        return path
    return json.dumps(d, separators=(',', ':'))

# ================================================================== Blender layer (bpy 5.1+, lazy) ===========================
import re
_B = {'name': None, 'S': None, 'B': {}, 'k': 1.0, 'img': None}

def _bpy():
    import bpy; return bpy
def _fcs(act, slot=None):
    """all fcurves of an action, legacy or layered (Blender 4.4+/5.x)"""
    if act is None: return []
    if hasattr(act, 'fcurves') and not getattr(act, 'is_action_layered', False): return list(act.fcurves)
    out = []
    for l in act.layers:
        for s in l.strips:
            for cb in getattr(s, 'channelbags', []):
                if slot is None or cb.slot_handle == slot.handle: out += list(cb.fcurves)
    return out
def _m3(R):
    from mathutils import Matrix
    return Matrix(((R[0], R[1], R[2]), (R[3], R[4], R[5]), (R[6], R[7], R[8])))
def _t9(M): return (M[0][0], M[0][1], M[0][2], M[1][0], M[1][1], M[1][2], M[2][0], M[2][1], M[2][2])

_NEED = ('Torso', 'Head', 'Right Arm', 'Left Arm', 'Right Leg', 'Left Leg')
def use(name=None, build_if_missing=False):
    """bind the intended R6 rig; require explicit permission to create a proxy via rig()/build_if_missing=True"""
    bpy = _bpy(); from mathutils import Vector, Matrix
    cand = [o for o in bpy.data.objects if o.type == 'ARMATURE' and all(b in o.data.bones for b in _NEED)]
    o = bpy.data.objects.get(name) if name else None
    if name and o not in cand: raise RuntimeError('named R6 armature not found or incompatible: ' + name)
    if o is None:
        a = bpy.context.view_layer.objects.active
        if a not in cand and len(cand) > 1: raise RuntimeError('multiple R6 rigs: select or name the intended armature')
        o = a if a in cand else (cand[0] if cand else None)
    if o is None:
        if not build_if_missing: raise RuntimeError('no armature with bones: ' + ', '.join(_NEED))
        return rig()
    bn = o.data.bones; hd = lambda n: Vector(bn[n].head_local)
    up = (hd('Head') - hd('Torso')).normalized(); r = hd('Right Arm') - hd('Left Arm'); dist = r.length / 2.0; r = (r - up * r.dot(up)).normalized()   # shoulders are +-1 stud from the torso centre
    back = r.cross(up).normalized()
    S = Matrix(((r.x, up.x, back.x), (r.y, up.y, back.y), (r.z, up.z, back.z)))
    _B.update(name=o.name, S=S, k=dist, B={b.name: b.matrix_local.to_3x3() for b in bn})
    return 'rig "%s" scale=%.3f front=%s right=%s up=%s' % (o.name, _B['k'], tuple(round(-x, 2) for x in back), tuple(round(x, 2) for x in r), tuple(round(x, 2) for x in up))
def _arm():
    bpy = _bpy(); o = bpy.data.objects.get(_B['name']) if _B['name'] else None
    if o is None or o.type != 'ARMATURE': use(_B['name'], build_if_missing=False); o = bpy.data.objects[_B['name']]
    return o

def rig(name='R6_Rig', loc=(0, 0, 0)):
    """build a canonical R6 rig + box parts (character faces -Y like Blender's front view; 1 stud = 1 unit)"""
    bpy = _bpy(); import bmesh; from mathutils import Vector, Matrix
    S = Matrix(((-1, 0, 0), (0, 0, 1), (0, 1, 0)))
    arm = bpy.data.armatures.new(name); ob = bpy.data.objects.new(name, arm); ob.location = loc
    bpy.context.collection.objects.link(ob); vl = bpy.context.view_layer
    for x in vl.objects: x.select_set(False)
    vl.objects.active = ob; ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    cen = {b: p[0] for b, p in fk({}).items()}; jp = {}
    for b in BONES:
        par = J[b][0]; jp[b] = cen[b] if par is None else tuple(cen[par][i] + J[b][1][i] for i in range(3))
    for b in BONES:
        eb = arm.edit_bones.new(b); eb.head = S @ Vector(jp[b]); eb.tail = eb.head + Vector((0, 0, 0.25))
    for b in BONES:
        if J[b][0]: arm.edit_bones[b].parent = arm.edit_bones[J[b][0]]
    bpy.ops.object.mode_set(mode='OBJECT')
    col = {'Torso': (.55, .6, .66), 'Head': (.9, .78, .6), 'Right Arm': (.88, .48, .25), 'Right Leg': (.78, .38, .17), 'Left Arm': (.25, .52, .85), 'Left Leg': (.16, .39, .68)}
    for b in BONES[1:]:
        sz = J[b][6] if b != 'Head' else (1.25, 1, 1); me = bpy.data.meshes.new('%s.%s' % (name, b)); bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts: v.co = S @ (Vector((v.co.x * sz[0], v.co.y * sz[1], v.co.z * sz[2])) + Vector(cen[b]))
        bm.to_mesh(me); bm.free()
        mo = bpy.data.objects.new('%s.%s' % (name, b), me); mo.color = col[b] + (1.0,); bpy.context.collection.objects.link(mo)
        mat = bpy.data.materials.new('%s.%s' % (name, b)); mat.diffuse_color = col[b] + (1.0,); me.materials.append(mat)
        vg = mo.vertex_groups.new(name=b); vg.add(list(range(len(me.vertices))), 1.0, 'REPLACE')
        md = mo.modifiers.new('Armature', 'ARMATURE'); md.object = ob; mo.parent = ob
    for pb in ob.pose.bones: pb.rotation_mode = 'QUATERNION'
    _B['name'] = None; return use(ob.name)

def _basis(b, v):
    """semantic vector -> (quaternion, location) for the pose bone, whatever the rig's bone roll / axes are"""
    from mathutils import Vector
    A = _B['B'][b].transposed() @ _B['S']; M = A @ _m3(sem2rw(b, v)) @ A.transposed()
    return M.to_quaternion(), (A @ Vector((v[3], v[4], -v[5]))) * _B['k']
def _unbasis(b, q, loc):
    from mathutils import Vector
    A = _B['B'][b].transposed() @ _B['S']; Rw = A.transposed() @ q.to_matrix() @ A
    t = (A.transposed() @ Vector(loc)) / _B['k']
    return rw2sem(b, _t9(Rw)) + [t.x, t.y, -t.z]

def build(set_range=True):
    """write the current clip as a Blender action (timing follows the scene fps; clip fps may differ)"""
    bpy = _bpy(); c = cur(); o = _arm(); sc = bpy.context.scene; fs = frames(c)
    if not fs: raise ValueError('cannot build an empty clip')
    f0 = fs[0]; scene_fps = sc.render.fps / sc.render.fps_base; ratio = scene_fps / c['fps']
    # Match sample()'s pre-first-key holding without inheriting stale channels from another action.
    import copy
    c = copy.deepcopy(c)
    initial = sample(c, f0)
    for b in BONES:
        if b in o.pose.bones: c['keys'][f0]['b'].setdefault(b, initial.get(b, [0.0] * 6))
    F = lambda f: 1.0 + (f - f0) * ratio
    act = bpy.data.actions.new(c['name']); act.use_fake_user = True
    ad = o.animation_data_create(); prev = ad.action; note = ''
    if prev is not None and not prev.use_fake_user: prev.use_fake_user = True; note = ' (previous action "%s" kept with fake user)' % prev.name
    ad.action = act
    for pb in o.pose.bones:
        if pb.name in BONES:
            pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
    locb = {b for f in fs for b, v in c['keys'][f]['b'].items() if any(abs(x) > 1e-6 for x in v[3:])}
    last = {}; tokmap = {}
    for f in fs:
        k = c['keys'][f]
        for b, v in k['b'].items():
            pb = o.pose.bones[b]; q, loc = _basis(b, v)
            if b in last and q.dot(last[b]) < 0: q.negate()
            last[b] = q.copy(); pb.rotation_quaternion = q; pb.keyframe_insert('rotation_quaternion', frame=F(f), group=b)
            if b in locb: pb.location = loc; pb.keyframe_insert('location', frame=F(f), group=b)
            tokmap[(b, round(F(f), 3))] = k['e'] or c['ease']
    for fc in _fcs(act):
        m = re.match(r'pose\.bones\["(.+)"\]\.(rotation_quaternion|location)', fc.data_path)
        if not m: continue
        for kp in fc.keyframe_points:
            t = tokmap.get((m.group(1), round(kp.co[0], 3)))
            if t: kp.interpolation, kp.easing = BL[t]
        fc.update()
    if not _fcs(act): raise RuntimeError('keyframe_insert produced no fcurves (action slot problem?) - report this')
    if set_range: sc.frame_start = 1; sc.frame_end = int(math.ceil(F(fs[-1]))); sc.frame_set(1)
    return 'built "%s" frames 1-%d (scene %gfps)%s' % (act.name, math.ceil(F(fs[-1])), scene_fps, note)

def read(action=None, name=None, slot=None):
    """Blender action (default: the active one) -> current clip (key frames, easing and pose recovered from the fcurves)"""
    bpy = _bpy(); o = _arm(); sc = bpy.context.scene
    act = bpy.data.actions[action] if isinstance(action, str) else (action or (o.animation_data.action if o.animation_data else None))
    if act is None: raise ValueError('no action to read')
    slot = slot or (getattr(o.animation_data, 'action_slot', None) if o.animation_data and act == o.animation_data.action else None)
    if slot is None and len(getattr(act, 'slots', [])) > 1: raise ValueError('multi-slot action: pass the intended ActionSlot to read(slot=...)')
    fcs = _fcs(act, slot); frs = sorted({round(kp.co[0], 3) for fc in fcs for kp in fc.keyframe_points})
    inv = {v: k for k, v in BL.items()}; c = clip(name or act.name, sc.render.fps / sc.render.fps_base, False, 'out'); chans = {}
    for fc in fcs:
        m = re.match(r'pose\.bones\["(.+)"\]\.(rotation_quaternion|location)\Z', fc.data_path)
        if m: chans.setdefault((m.group(1), m.group(2)), {})[fc.array_index] = fc
    from mathutils import Quaternion
    for f in frs:
        key = c['keys'].setdefault(float(f), {'e': None, 'b': {}})
        for b in BONES:
            rq = chans.get((b, 'rotation_quaternion'))
            if not rq or len(rq) < 4: continue
            if not any(abs(kp.co[0] - f) < 1e-3 for kp in rq[0].keyframe_points): continue
            q = Quaternion([rq[i].evaluate(f) for i in range(4)]); lc = chans.get((b, 'location'))
            loc = [lc[i].evaluate(f) if lc and i in lc else 0.0 for i in range(3)]
            key['b'][b] = _unbasis(b, q, loc)
            kp = next(k for k in rq[0].keyframe_points if abs(k.co[0] - f) < 1e-3)
            key['e'] = inv.get((kp.interpolation, kp.easing if kp.interpolation not in ('LINEAR', 'CONSTANT') else 'AUTO'), 'io' if kp.interpolation == 'BEZIER' else 'out')
    _S['clip'] = c; return 'read "%s": %d keys' % (act.name, len(frs))

_D3 = {'0': '111101101101111', '1': '010110010010111', '2': '111001111100111', '3': '111001111001111', '4': '101101111001001',
       '5': '111100111001111', '6': '111100111101111', '7': '111001001001001', '8': '111101111101111', '9': '111101111001111'}
def _stamp(img, txt, x, y, sc=3):
    import numpy as np
    for ci, ch in enumerate(txt):
        g = _D3.get(ch)
        if not g: continue
        for i, bit in enumerate(g):
            if bit == '1':
                r, cc = divmod(i, 3); img[y + r * sc:y + (r + 1) * sc, x + (ci * 4 + cc) * sc:x + (ci * 4 + cc + 1) * sc, :3] = 0.0
def sheet(fr=None, n=8, views=('3q', 'side'), tile=224, cols=4, path=None, zoom=1.0, even=False):
    """contact sheet PNG of the rig (workbench render in a temporary scene; your scene is untouched).
       fr: scene frames (default: key frames of the current action, <= n of them).  views: front 3q side back (or azimuth degrees)."""
    bpy = _bpy(); import numpy as np, tempfile
    from mathutils import Vector
    o = _arm(); act = o.animation_data.action if o.animation_data else None
    if fr is None:
        ks = sorted({round(kp.co[0]) for fc in _fcs(act) for kp in fc.keyframe_points}) if act else [bpy.context.scene.frame_current]
        a, b = act.frame_range if act else (ks[0], ks[0])
        if even or len(ks) < 2: ks = sorted({int(round(a + (b - a) * i / max(n - 1, 1))) for i in range(n)})
        elif len(ks) > n: ks = [ks[round(i * (len(ks) - 1) / (n - 1))] for i in range(n)]
        fr = ks
    path = path or os.path.join(tempfile.gettempdir(), 'r6_sheet.png')
    V = {'front': 0, '3q': 35, 'side': 90, 'back': 180}; S = _B['S']; k = _B['k']; mw = o.matrix_world.to_3x3()
    up = mw @ (S @ Vector((0, 1, 0))); right = mw @ (S @ Vector((1, 0, 0))); front = -(mw @ (S @ Vector((0, 0, 1)))); up.normalize(); right.normalize(); front.normalize()
    made = {'obj': [], 'mesh': [], 'cam': [], 'world': [], 'img': []}; colors = {}; sc = bpy.data.scenes.new('__r6sheet')
    try:
        r = sc.render; r.engine = 'BLENDER_WORKBENCH'; r.resolution_x = r.resolution_y = tile; r.resolution_percentage = 100; r.film_transparent = False
        r.image_settings.file_format = 'PNG'; r.image_settings.color_mode = 'RGBA'
        sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'; sh = sc.display.shading; sh.light = 'STUDIO'; sh.color_type = 'OBJECT'; sh.show_object_outline = True; sh.show_cavity = False
        w = bpy.data.worlds.new('__r6w'); w.color = (.9, .91, .93); sc.world = w; made['world'].append(w)
        for ob in [o] + list(o.children_recursive):
            sc.collection.objects.link(ob)
            if ob.type == 'MESH':
                colors[ob.name] = tuple(ob.color); n_ = ob.name
                ob.color = (.88, .48, .25, 1) if 'Right' in n_ else (.25, .52, .85, 1) if 'Left' in n_ else (.9, .78, .6, 1) if 'Head' in n_ else (.55, .6, .66, 1)
        me = bpy.data.meshes.new('__r6g'); made['mesh'].append(me)
        gs = 14.0 * k; me.from_pydata([(-gs, -gs, 0), (gs, -gs, 0), (gs, gs, 0), (-gs, gs, 0)], [], [(0, 1, 2, 3)])
        g = bpy.data.objects.new('__r6g', me); g.matrix_world = o.matrix_world.copy(); g.color = (.72, .74, .76, 1); sc.collection.objects.link(g); made['obj'].append(g)
        cd = bpy.data.cameras.new('__r6c'); cd.type = 'ORTHO'; cd.ortho_scale = 8.4 * k / zoom; made['cam'].append(cd)
        cam = bpy.data.objects.new('__r6c', cd); sc.collection.objects.link(cam); made['obj'].append(cam); sc.camera = cam
        tgt = o.matrix_world @ (S @ Vector((0, 2.9 * k, 0)))
        tiles = {}
        for f in fr:
            sc.frame_set(int(f))
            for v in views:
                az = math.radians(V[v] if isinstance(v, str) else v); el = math.radians(8)
                d = front * (math.cos(el) * math.cos(az)) + right * (math.cos(el) * math.sin(az)) + up * math.sin(el)
                cam.location = tgt + d * 40 * k; cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
                p = os.path.join(tempfile.gettempdir(), '__r6t.png'); sc.render.filepath = p
                bpy.ops.render.render(write_still=True, scene=sc.name)
                im = bpy.data.images.load(p); made['img'].append(im)
                a = np.empty(im.size[0] * im.size[1] * 4, dtype=np.float32); im.pixels.foreach_get(a)
                tiles[(f, v)] = np.flipud(a.reshape(im.size[1], im.size[0], 4)).copy()
                bpy.data.images.remove(im); made['img'].pop()
        nv = len(views); rows = math.ceil(len(fr) / cols); W = cols * tile; H = rows * nv * tile
        canvas = np.ones((H, W, 4), dtype=np.float32)
        for i, f in enumerate(fr):
            rr, cc = divmod(i, cols)
            for vi, v in enumerate(views):
                y = (rr * nv + vi) * tile; x = cc * tile; canvas[y:y + tile, x:x + tile] = tiles[(f, v)]
                if vi == 0: _stamp(canvas, str(int(f)), x + 4, y + 4)
        canvas[::tile, :, :3] = .35; canvas[:, ::tile, :3] = .35
        out = bpy.data.images.new('r6_sheet', W, H, alpha=True); out.pixels.foreach_set(np.flipud(canvas).ravel()); out.filepath_raw = path; out.file_format = 'PNG'; out.save()
        old = _B.get('img'); _B['img'] = out.name
        if old and old != out.name and old in bpy.data.images and bpy.data.images[old].users == 0: bpy.data.images.remove(bpy.data.images[old])
    finally:
        for ob in made['obj']: bpy.data.objects.remove(ob, do_unlink=True)
        for m in made['mesh']: bpy.data.meshes.remove(m)
        for cdd in made['cam']: bpy.data.cameras.remove(cdd)
        for ww in made['world']: bpy.data.worlds.remove(ww)
        bpy.data.scenes.remove(sc)
        for nme, col_ in colors.items():
            if nme in bpy.data.objects: bpy.data.objects[nme].color = col_
        p = os.path.join(tempfile.gettempdir(), '__r6t.png')
        if os.path.exists(p): os.remove(p)
    return 'sheet %s %dx%d frames=%s views=%s (tiles: left->right, top->bottom; first view row labelled with the frame)  next: r6.show()' % (path, W, H, [int(f) for f in fr], list(views))

def show():
    """put the last sheet into every Image Editor area, so get_screenshot_of_area_as_image('IMAGE_EDITOR') can see it.
       If there is no Image Editor yet, call the MCP tool jump_to_tab_by_space_type('IMAGE_EDITOR', allow_edits=True) first."""
    bpy = _bpy(); im = bpy.data.images.get(_B.get('img') or ''); n = 0
    if im is None: return 'no sheet yet: r6.sheet()'
    for w in bpy.context.window_manager.windows:
        for a in w.screen.areas:
            if a.type == 'IMAGE_EDITOR': a.spaces.active.image = im; a.tag_redraw(); n += 1
    return 'shown in %d Image Editor area(s)' % n if n else 'no IMAGE_EDITOR area: call jump_to_tab_by_space_type("IMAGE_EDITOR", allow_edits=True), then r6.show()'

def selftest():
    """end-to-end check inside Blender on throw-away data (everything is named __r6test* and removed afterwards):
       rig -> clip -> action -> readback -> Blender deformation == Roblox FK -> sheet render"""
    bpy = _bpy(); import tempfile; from mathutils import Vector
    log = []; sc = bpy.context.scene; keep = (dict(_B), _S['clip'], sc.frame_start, sc.frame_end, sc.frame_current)
    imgs0 = set(bpy.data.images.keys())
    try:
        rig('__r6test', (30, 30, 0)); o = bpy.data.objects['__r6test']; log.append('rig %d bones' % len(o.data.bones))
        new('__r6test_clip', 30, False, 'out')
        table("""f   ra         la        t                       h        rl       ease
                 0   0          0         0                       0        0        out
                 8   80,10,30   -45,0,15  12,20,5,0.1,-0.3,0.2   -10,25   40       io
                 16  -30,-40,60 60,25,-20 -20,-35,-8,-0.2,0.2,-0.1 15,-20,5 -60,10,20 lin""")
        orig = cur(); log.append(build()); ratio = sc.render.fps / sc.render.fps_base / orig['fps']; log.append(read())
        c = cur(); fs = frames(c)
        for f, ref in ((fs[1], {'Right Arm': [80, 10, 30], 'Left Arm': [-45, 0, 15]}), (fs[2], {'Right Arm': [-30, -40, 60], 'Torso': [-20, -35, -8, -0.2, 0.2, -0.1]})):
            for b, v in ref.items():
                got = c['keys'][f]['b'][b]; err = max(abs(x - y) for x, y in zip(got, v + [0] * (6 - len(v))))
                assert err < 0.05, 'readback %s f%g err %.3f' % (b, f, err)
        log.append('readback ok'); S = _B['S']; k = _B['k']; f0 = frames(orig)[0]
        for cf in (8, 16):
            F = 1 + cf * ratio; sc.frame_set(int(F), subframe=F - int(F)); dg = bpy.context.evaluated_depsgraph_get(); fkp = fk(sample(orig, f0 + cf))
            for b in ('Right Arm', 'Left Leg', 'Head', 'Torso'):
                ev = bpy.data.objects['__r6test.' + b].evaluated_get(dg); me = ev.to_mesh()
                cen = sum((v.co for v in me.vertices), Vector()) / len(me.vertices); ev.to_mesh_clear()
                want = S @ Vector(fkp[b][0]) * k; d = (cen - want).length
                assert d < 0.02, 'FK mismatch %s clip-frame %d: %.3f (blender %s vs roblox %s)' % (b, cf, d, tuple(round(x, 2) for x in cen), tuple(round(x, 2) for x in want))
        log.append('blender deformation == roblox fk')
        out = os.path.join(tempfile.gettempdir(), '__r6test_sheet.png'); sheet(path=out, n=3, tile=96)
        assert os.path.getsize(out) > 500; os.remove(out); log.append('sheet ok')
        res = 'PASS: ' + ' | '.join(log)
    except Exception:
        import traceback; res = 'FAIL: ' + ' | '.join(log) + ' || ' + traceback.format_exc()[-800:]
    finally:
        for ob in [x for x in bpy.data.objects if x.name.startswith('__r6test')]: bpy.data.objects.remove(ob, do_unlink=True)
        for coll in ('meshes', 'armatures', 'actions', 'materials'):
            for x in [y for y in getattr(bpy.data, coll) if y.name.startswith('__r6test')]: getattr(bpy.data, coll).remove(x)
        for nm in set(bpy.data.images.keys()) - imgs0: bpy.data.images.remove(bpy.data.images[nm])
        _B.clear(); _B.update(keep[0]); _S['clip'] = keep[1]; sc.frame_start, sc.frame_end = keep[2], keep[3]; sc.frame_set(keep[4])
    return res
