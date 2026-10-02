"""@Mr_HB vs training dummy: original choreography, 35 s @ 18 fps (630 frames, 120 BPM => 9 frames per beat).

Authored for this brief with the skill's R6 DSL (r6.new/put/sample/fk). Every pose, timing and contact below is project-authored.
Beat sheet and the reference-analysis limits are recorded in animation/animation-manifest.json.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rig as rg      # noqa: E402  (also puts the skill's scripts on sys.path)
import r6             # noqa: E402
import cam as camlib  # noqa: E402
from actor import Actor, H, Hc, hxyz, ballistic, wobble, lerp_cell  # noqa: E402

FPS = 18
N = 630
BEAT = 9           # frames per beat @120 BPM
D2R = math.pi / 180


# ---------------------------------------------------------------- tiny geometry/orientation helpers
def Rx(a): return r6.rx(a * D2R)
def Ry(a): return r6.ry(a * D2R)
def Rz(a): return r6.rz(a * D2R)
def Rm(*ms):
    out = ms[0]
    for m in ms[1:]: out = r6.mm(out, m)
    return out


def Hr(x, yc, z, R):
    """HRP cell with an arbitrary orientation matrix R (character frame) at body-centre position (x, yc, z)."""
    p, y, r = r6.rw2sem('HumanoidRootPart', R)
    return (p, y, r, x, yc - r6.HIP_Y, -z)


def Rbasis(head_dir, front_dir):
    """orientation matrix whose local +Y (head) points along head_dir and whose local front (-Z) points as close to front_dir as possible"""
    y = rg.unit(head_dir)
    f = rg.sub(front_dir, rg.mul(y, rg.dot(front_dir, y)))
    f = rg.unit(f)
    z = rg.mul(f, -1.0)
    x = rg.cross(y, z)
    return (x[0], y[0], z[0], x[1], y[1], z[1], x[2], y[2], z[2])


def Rspin(R, axis_local_y_deg):
    """extra twist about the body's own long axis (local Y)"""
    return Rm(R, Ry(axis_local_y_deg))


def yaw_of(dx, dz):
    """HRP yaw that faces the world direction (dx, dz): 0 faces -Z, +90 faces +X."""
    return math.degrees(math.atan2(dx, -dz))


def unwrap(prev, cur):
    """keep yaw/roll continuous between consecutive per-frame keys"""
    out = list(cur)
    for i in (0, 1, 2):
        while out[i] - prev[i] > 180: out[i] -= 360
        while out[i] - prev[i] < -180: out[i] += 360
    return tuple(out)


# ================================================================ beat registry
AUTHOR = []
DIRECT = []


def author(fn):
    AUTHOR.append(fn); return fn


def direct(fn):
    DIRECT.append(fn); return fn


# ---------------------------------------------------------------- cast
P = Actor('MrHB', FPS)
D = Actor('Dummy', FPS)
CAM = camlib.Camera(N)
FX3 = []     # events consumed by the three.js renderer
FX2 = []     # events consumed by the 2D post
HITS = []    # impact table: dict(f, attacker, bone, target, strength)
TAGS = {'P': {'text': '@Mr_HB', 'keys': []}}
P_VIS = [True] * N      # False = the player is blinked out (teleport frames)


def hide(f0, f1):
    for f in range(f0, f1 + 1):
        if 0 <= f < N: P_VIS[f] = False


def yaw_near(heading, ref):
    """the equivalent of `heading` (deg) closest to the reference yaw: keeps rotations continuous between keys"""
    return heading + 360.0 * round((ref - heading) / 360.0)
DUMMY_HURT = []   # frames with the hurt face

P0 = (-6.5, 0.0, 0.6)    # player start (x, y, z)
D0 = (2.2, 0.0, 0.0)     # dummy start
YP = yaw_of(D0[0] - P0[0], D0[2] - P0[2])      # player faces the dummy
YD = YP + 180.0

# ---------------------------------------------------------------- pose vocabulary (character frame, authored for this clip)
GUARD = dict(t=(10, 30, 0), h=(8, -28, 0), la=(85, 0, 5), ra=(100, 0, -25), ll=(28, 0, 6), rl=(-25, 0, 10))


def dummy_idle(f0, f1, x, z, yaw, step=6):
    """upright, loosely swaying training dummy"""
    for i, f in enumerate(range(f0, f1 + 1, step)):
        s = math.sin(i * 1.3)
        D.k(f, 'io', hrp=H(x, 0, z, yaw), t=(1.2 * s, 2 * s, 0), h=(1.0 * s, 0, 0), ra=(5 + s, 0, 6), la=(5 - s, 0, 6), rl=(0, 0, 3), ll=(0, 0, 3))


# ================================================================ BEAT 1 · HOOK  (f0-29)
@author
def beat_hook():
    # --- shot A (f0-9): extreme close-up, head snaps up to stare at the camera/dummy
    P.k(0, 'io', hrp=H(*P0, yaw=YP), t=(6, 18, 0, 0, -0.05), h=(24, -42, -8), la=(8, 0, 8), ra=(8, 0, 8), ll=(0, 0, 4), rl=(0, 0, 4))
    P.k(4, 'io', t=(7, 20, 0, 0, -0.05), h=(26, -44, -9))                       # slow drift, never frozen
    P.k(5, 'out', h=(22, -38, -7))                                              # tiny pre-move
    P.k(6, 'out', t=(4, 6, 0), h=(8, -8, -2))                                   # snap up
    P.k(7, 'io', t=(2, 0, 0), h=(-6, 3, 1))                                     # overshoot
    P.k(9, 'io', t=(3, 2, 0), h=(-3, 1, 0))
    # --- shot B (f10-29): ready stance, breathing, then coils for the dash
    P.k(11, 'io', hrp=H(*P0, yaw=YP), t=(10, 30, 0, 0, -0.3), h=(8, -28, 0), la=GUARD['la'], ra=GUARD['ra'], ll=GUARD['ll'], rl=GUARD['rl'])
    P.k(14, 'io', t=(14, 27, 0, 0, -0.38), h=(10, -26), la=(90, 0, 6), ra=(104, 0, -27), ll=(32, 0, 7), rl=(-28, 0, 11))
    P.k(17, 'io', t=(10, 30, 0, 0, -0.3), h=(8, -28), la=(85, 0, 5), ra=(100, 0, -25), ll=(28, 0, 6), rl=(-25, 0, 10))
    P.k(20, 'io', t=(15, 28, 0, 0, -0.4), h=(10, -26), la=(92, 0, 6), ra=(104, 0, -26), ll=(33, 0, 7), rl=(-28, 0, 11))
    P.p(21, 'in', ra=(72, 0, -14))
    P.p(22, 'in', ra=(24, 0, 4))
    P.k(23, 'in', hrp=H(P0[0] - 0.08, 0, P0[2], YP), t=(22, 38, 0, 0, -0.6), h=(12, -36), la=(70, 0, 8), ra=(-20, 0, 14), ll=(48, 0, 8), rl=(-40, 0, 12))
    P.k(26, 'in', hrp=H(P0[0] - 0.22, 0, P0[2], YP), t=(32, 44, 0, 0, -0.8), h=(16, -42), la=(52, 0, 10), ra=(-48, 0, 20), ll=(60, 0, 8), rl=(-52, 0, 14))
    P.k(29, 'io', hrp=H(P0[0] - 0.3, 0, P0[2], YP), t=(34, 46, 0, 0, -0.85), h=(18, -44), la=(50, 0, 10), ra=(-52, 0, 22), ll=(62, 0, 8), rl=(-54, 0, 14))
    dummy_idle(0, 36, D0[0], D0[2], YD)


# ================================================================ BEAT 2 · DASH STRIKE  (f30-71)
IMPACT1 = 36
DASH_END_X = -0.9


@author
def beat_dash():
    x0 = P0[0] - 0.3
    # burst: lean 50 deg, arm cocked back, scissoring legs; ease-out so the dash decelerates into the strike
    P.k(30, 'out', hrp=H(x0 + 0.5, 0.55, P0[2], YP, pitch=50), t=(0, 40, 0), h=(-48, -36), ra=(-42, 0, 24), la=(-58, 0, 16), rl=(-38, 0, 6), ll=(34, 0, 6))
    P.k(31, 'lin', rl=(30, 0, 6), ll=(-42, 0, 6))
    P.k(32, 'lin', rl=(-40, 0, 6), ll=(34, 0, 6))
    P.k(33, 'lin', hrp=H(DASH_END_X - 0.9, 0.35, P0[2], YP, pitch=42), rl=(32, 0, 6), ll=(-36, 0, 6), la=(-8, 0, 12))
    # brake with the lead leg planted, torso fully coiled
    P.k(34, 'out', hrp=H(DASH_END_X, 0.0, P0[2], YP, pitch=26), t=(4, 46, 0, 0, -0.5), h=(-20, -42), ra=(-56, 0, 26), la=(72, 0, 10), ll=(56, 0, 8), rl=(-56, 0, 8))
    # strike: torso unwinds, right fist drives through the target
    P.k(35, 'out', hrp=H(DASH_END_X + 0.35, 0.0, P0[2], YP, pitch=12), t=(10, -8, 0, 0, -0.55), h=(2, 6), ra=(62, 0, 4), la=(98, 0, -30), ll=(50, 0, 8), rl=(-50, 0, 10))
    P.k(IMPACT1, 'lin', hrp=H(DASH_END_X + 0.6, 0.0, P0[2], YP, pitch=6), t=(14, -46, 0, 0, -0.55), h=(8, 40), ra=(90, 0, -3), la=(112, 0, -40), ll=(48, 0, 8), rl=(-46, 0, 12))
    P.k(IMPACT1 + 1, 'lin', hrp=H(DASH_END_X + 0.72, 0.0, P0[2], YP, pitch=6), t=(15, -49, 0, 0, -0.55), ra=(92, 0, -3))      # hit-stop: fist drives through
    P.k(IMPACT1 + 2, 'lin', hrp=H(DASH_END_X + 0.74, 0.0, P0[2], YP, pitch=6), t=(15, -49, 0, 0, -0.55), ra=(92, 0, -3))
    P.k(IMPACT1 + 5, 'out', t=(12, -38, 0, 0, -0.5), h=(8, 34), ra=(74, 0, 2), la=(104, 0, -34))                               # recoil
    P.k(IMPACT1 + 9, 'io', hrp=H(DASH_END_X + 0.9, 0.0, P0[2], YP), t=(10, 24, 0, 0, -0.32), h=(8, -22), la=(86, 0, 5), ra=(100, 0, -24), ll=(30, 0, 6), rl=(-26, 0, 10))
    P.plant([f for f in range(IMPACT1, IMPACT1 + 10) if float(f) in P.clip['keys']])

    # ---- the dummy: takes the hit at its chest. Contact is solved afterwards (see solve_contacts)
    D.k(IMPACT1 - 1, 'lin', hrp=H(D0[0], 0, D0[2], YD), t=(0, 0, 0), h=(0, 0, 0), ra=(5, 0, 6), la=(5, 0, 6), rl=(0, 0, 3), ll=(0, 0, 3))
    D.k(IMPACT1, 'lin', hrp=H(D0[0] + 0.0, 0.18, D0[2], YD, pitch=-6), t=(-30, 0, 0), h=(12, 0, 0), ra=(24, 0, 54), la=(34, 0, 60), rl=(18, 0, 4), ll=(10, 0, 4))
    D.k(IMPACT1 + 1, 'lin', hrp=H(D0[0] + 0.12, 0.22, D0[2], YD, pitch=-9), t=(-36, 0, 0), h=(4, 0, 0), ra=(30, 0, 58), la=(40, 0, 64), rl=(22, 0, 4), ll=(14, 0, 4))    # hit-stop shudder
    D.k(IMPACT1 + 2, 'lin', hrp=H(D0[0] + 0.05, 0.2, D0[2], YD, pitch=-9), t=(-36, 0, 0), h=(-30, 0, 0), ra=(30, 0, 58), la=(40, 0, 64))                                    # head whips back
    # flight: horizontal, corkscrewing about the long axis, limbs trailing and fluttering
    p0 = (D0[0] + 0.5, 3.15, D0[2])
    f0 = IMPACT1 + 3

    def limbs(age):
        w = lambda a, p, d, ph=0: wobble(age, a, p, d, ph)
        return dict(t=(-12 + w(8, 5, 6), 0, w(6, 4, 6, 1)), h=(-34 + w(12, 4.5, 7), w(10, 5, 6), 0),
                    ra=(78 + w(14, 4.2, 8), 0, 62 + w(10, 5, 8, .6)), la=(66 + w(14, 4.6, 8, 1.4), 0, 70 + w(10, 4.4, 8, 2)),
                    rl=(20 + w(14, 4.4, 8, .3), 0, 6), ll=(8 + w(16, 4.8, 8, 2.2), 0, 6))
    prev = None
    path = []
    for f in range(f0, f0 + 7):
        a = f - f0; t = a / FPS
        vx, vy, g = 27.0, 4.5, 58.0
        x = p0[0] + vx * t - 0.5 * 0 * t * t; y = p0[1] + vy * t - 0.5 * g * t * t
        pitch = -50 - 38 * (1 - math.exp(-a / 1.6))
        R = Rm(Ry(YD), Rx(pitch), Ry(-34 * a))
        cell = Hr(x, max(y, 0.6), p0[2], R)
        if prev is not None: cell = unwrap(prev, cell)
        prev = cell
        c = limbs(a); c['hrp'] = cell
        D.k(f, 'lin', **c); path.append((x, y))
    return path


# ================================================================ BEAT 2b · CRASH, SLIDE, POP-UP, CHASE  (f40-55)
LAND = 46
DUMMY_X_AFTER = 14.7


@author
def beat_crash():
    prev = tuple(D.cell('hrp'))
    # touch-down on its back, bounce, slide (floor snap keeps it exactly on the ground), limbs sprawled then settling
    slide_x = [11.9, 12.9, 13.7, 14.2, 14.5, 14.65]
    for i, f in enumerate(range(LAND, LAND + 6)):
        a = i
        bounce = 0.55 * math.exp(-a * 0.9) * (1 if a < 3 else 0) * (1 - a * 0.3)
        R = Rm(Ry(YD), Rx(-86 - 2 * a), Ry(-30 * math.exp(-a * 0.8)))
        cell = unwrap(prev, Hr(slide_x[i], 0.0 + bounce, D0[2], R)); prev = cell
        w = lambda amp, per, dec, ph=0: wobble(a, amp, per, dec, ph)
        D.k(f, 'lin' if a < 3 else 'out', hrp=cell, t=(-4 + w(6, 5, 4), 0, 0), h=(-24 + w(10, 4, 4), 6 * math.exp(-a * .5), 0),
            ra=(60 + w(15, 4, 5), 0, 70 - 4 * a), la=(54 + w(15, 4, 5, 1), 0, 76 - 4 * a), rl=(10 + w(10, 4, 4), 0, 16 + 2 * a), ll=(4 + w(10, 4, 4, 2), 0, 20 + 2 * a))
    # pop-up: stiff sit-up rotation about the hips with overshoot, then loose wobble
    x = 14.7
    popup = [(52, -70, 'out'), (53, -28, 'out'), (54, 14, 'out'), (55, -4, 'io'), (56, 0, 'io')]
    for f, pit, e in popup:
        R = Rm(Ry(YD), Rx(pit))
        cell = unwrap(prev, Hr(x + 0.1 * (f - 52), 0.0 if pit < -10 else 3.0, D0[2], R)); prev = cell
        a = f - 52
        D.k(f, e, hrp=cell, t=(-2, 0, 0), h=(8, 0, 0), ra=(10 + wobble(a, 25, 4, 3), 0, 14), la=(10 - wobble(a, 25, 4, 3), 0, 14), rl=(0, 0, 3), ll=(0, 0, 3))
    for i, f in enumerate(range(57, 64, 3)):
        D.k(f, 'io', hrp=H(x + 0.5, 0, D0[2], YD), t=(1.5 * (-1) ** i, 2, 0), h=(1.2 * (-1) ** i, 0, 0), ra=(6, 0, 6), la=(6, 0, 6))

    # --- player: recoil, then a second, longer dash that skids to a stop in front of the dummy
    P.k(40, 'out', t=(10, -20, 0, 0, -0.4), ra=(72, 0, 2), la=(104, 0, -32))
    P.k(42, 'out', hrp=H(DASH_END_X + 1.0, 0.5, P0[2], YP, pitch=50), t=(0, 36, 0), h=(-46, -34), ra=(-40, 0, 22), la=(-56, 0, 16), rl=(-38, 0, 6), ll=(34, 0, 6))
    for f, (rl, ll) in zip(range(43, 50), [(30, -40), (-40, 32), (32, -38), (-38, 30), (30, -36), (-30, 26), (24, -20)]):
        P.p(f, 'lin', rl=(rl, 0, 6), ll=(ll, 0, 6))
    P.p(50, 'lin', la=(-10, 0, 12))
    P.k(51, 'out', hrp=H(11.45, 0.0, P0[2], YP, pitch=24), t=(6, 40, 0, 0, -0.5), h=(-16, -38), ra=(-36, 0, 22), la=(64, 0, 10), ll=(58, 0, 8), rl=(-56, 0, 8))
    P.k(54, 'io', hrp=H(11.8, 0.0, P0[2], YP), t=(10, 30, 0, 0, -0.3), h=(8, -28), la=GUARD['la'], ra=GUARD['ra'], ll=GUARD['ll'], rl=GUARD['rl'])
    P.p(52, 'out', ra=(20, 0, 4))


# ================================================================ BEAT 3 · GROUND COMBO  (f55-72)
@author
def beat_combo():
    xD = 15.2
    zP = P0[2]
    # ---- player (orthodox): jab f56 (head) - cross f59 (belly) - left hook f64 (head) - thrust kick f68 (belly) - uppercut f72 (chin, launch)
    P.k(55, 'out', t=(10, 24, 0, 0, -0.3), la=(112, 0, -34))                                         # jab chamber
    P.k(56, 'lin', hrp=H(12.75, 0, zP, YP), t=(10, 14, 0, 0, -0.3), h=(8, -18), la=(94, 0, 0), ra=(100, 0, -25), ll=(38, 0, 6), rl=(-32, 0, 10))     # JAB
    P.k(57, 'out', la=(100, 0, -12), t=(10, 30, 0, 0, -0.3), h=(8, -26))
    P.k(58, 'out', hrp=H(12.9, 0, zP, YP), t=(14, 48, 0, 0, -0.4), ra=(114, 0, -34), la=(104, 0, -34))                                                  # cross chamber
    P.k(59, 'lin', hrp=H(13.15, 0, zP, YP), t=(18, -46, 0, 0, -0.5), h=(10, 38), ra=(92, 0, -4), la=(108, 0, -40), ll=(46, 0, 8), rl=(-44, 0, 12))        # CROSS
    P.k(60, 'out', ra=(94, 0, -4), t=(18, -48, 0, 0, -0.5))                                                                                              # (hit-stop)
    P.k(62, 'out', hrp=H(13.1, 0, zP, YP), t=(10, -30, 0, 0, -0.4), h=(8, 30), ra=(100, 0, -20), la=(90, 0, 78), ll=(36, 0, 8), rl=(-34, 0, 12))        # hook chamber (left)
    P.k(64, 'lin', hrp=H(13.3, 0, zP, YP), t=(12, 44, 0, 0, -0.4), h=(6, -34), la=(90, 0, -22), ra=(106, 0, -34), ll=(44, 0, 8), rl=(-40, 0, 12))       # LEFT HOOK
    P.k(66, 'out', hrp=H(13.1, 0, zP, YP), t=(18, 20, 0, 0, -0.5), h=(8, -20), la=(100, 0, -26), ra=(104, 0, -26), ll=(30, 0, 8), rl=(24, 0, 6))        # kick chamber
    P.k(68, 'lin', hrp=H(13.2, 0.15, zP, YP, pitch=-10), t=(-10, 14, 0, 0, 0.0), h=(8, -14), la=(112, 0, -22), ra=(120, 0, -24), ll=(-14, 0, 10), rl=(98, 0, 4))   # THRUST KICK
    P.k(70, 'in', hrp=H(13.4, 0, zP, YP), t=(30, 20, 0, 0, -0.9), h=(12, -20), la=(50, 0, 10), ra=(18, 0, -8), ll=(60, 0, 10), rl=(-36, 0, 16))          # drop for the uppercut
    P.k(72, 'lin', hrp=H(13.55, 0.45, zP, YP, pitch=-4), t=(-14, -38, 0, 0, 0.1), h=(14, 30), ra=(168, 0, 6), la=(104, 0, -36), ll=(-26, 0, 8), rl=(26, 0, 10))   # UPPERCUT
    P.k(74, 'out', hrp=H(13.6, 0.55, zP, YP, pitch=-4), t=(-16, -40, 0, 0, 0.1), ra=(176, 0, 6))
    P.plant([f for f in (55, 56, 57, 58, 59, 60, 62, 64, 66, 70) if float(f) in P.clip['keys']])

    # ---- dummy reactions (each hit nudges it back along +X and folds/whips a different part of the body)
    base = dict(ra=(6, 0, 6), la=(6, 0, 6), rl=(0, 0, 3), ll=(0, 0, 3))
    D.k(55, 'out', hrp=H(xD, 0, D0[2], YD), t=(0, 0, 0), h=(0, 0, 0), **base)
    D.k(56, 'lin', hrp=H(xD + 0.35, 0.08, D0[2], YD, pitch=-6), t=(-10, 0, 0), h=(-42, 4, 0), ra=(20, 0, 30), la=(26, 0, 34))                         # head snaps back
    D.k(58, 'out', hrp=H(xD + 0.3, 0, D0[2], YD, pitch=-2), t=(-4, 0, 0), h=(-8, 0, 0), ra=(10, 0, 14), la=(12, 0, 14))
    D.k(59, 'lin', hrp=H(xD + 0.9, 0.1, D0[2], YD, pitch=4), t=(46, 0, 0), h=(34, 0, 0), ra=(-30, 0, 20), la=(-34, 0, 24), rl=(-18, 0, 4), ll=(-12, 0, 4))  # folds over the belly punch
    D.k(60, 'lin', hrp=H(xD + 1.0, 0.1, D0[2], YD, pitch=4), t=(50, 0, 0), h=(38, 0, 0))
    D.k(62, 'out', hrp=H(xD + 0.9, 0, D0[2], YD, pitch=0), t=(14, 0, 0), h=(6, 0, 0), ra=(8, 0, 12), la=(8, 0, 12), rl=(0, 0, 3), ll=(0, 0, 3))
    D.k(64, 'lin', hrp=H(xD + 1.2, 0.05, D0[2], YD + 36), t=(6, 40, 6), h=(0, 86, 14), ra=(40, 0, 70), la=(-30, 0, 20), rl=(8, 0, 4), ll=(-6, 0, 4))      # head whips sideways: left hook
    D.k(66, 'out', hrp=H(xD + 1.1, 0, D0[2], YD + 22), t=(2, 16, 0), h=(0, 22, 0), ra=(14, 0, 24), la=(10, 0, 20))
    D.k(68, 'lin', hrp=H(xD + 2.2, 0.6, D0[2], YD + 8, pitch=14), t=(54, 0, 0), h=(40, 0, 0), ra=(-40, 0, 16), la=(-44, 0, 20), rl=(-24, 0, 4), ll=(-18, 0, 4))   # doubled over the kick, shoved off the ground
    D.k(70, 'out', hrp=H(xD + 2.3, 0.0, D0[2], YD + 4, pitch=0), t=(30, 0, 0), h=(22, 0, 0), ra=(-10, 0, 14), la=(-12, 0, 14), rl=(0, 0, 3), ll=(0, 0, 3))
    D.k(72, 'lin', hrp=H(xD + 2.4, 0.2, D0[2], YD, pitch=-10), t=(-26, 0, 0), h=(-54, 0, 0), ra=(70, 0, 40), la=(76, 0, 44), rl=(20, 0, 4), ll=(14, 0, 4))    # chin snapped up
    return xD


# ================================================================ contacts (strike tip touches the target on the exact impact frame)
CONTACTS = []


def contact(f, att, limb, tgt, bone, local, slack=0.12, name='', tip=(0.0, -1.0, 0.0), air=False, win=1):
    """air=True lets the solver also move the attacker vertically (no planted feet to protect)"""
    CONTACTS.append(dict(f=f, att=att, limb=limb, tgt=tgt, bone=bone, local=local, slack=slack, name=name, tip=tip, air=air, win=win))


def solve_contacts(verbose=True, passes=3):
    """Make every strike tip touch its target on the exact impact frame: re-solve the limb by IK and, when the target is out of
    reach, step the attacker's root toward it (keys f-1..f+1) so the stride, not a stretched arm, closes the distance."""
    def gap_for(c):
        f = c['f']; a, t = c['att'], c['tgt']
        w = t.rig.point(f, c['bone'], c['local'])
        sh = a.rig.point(f, c['limb'], (0, 0.5, 0))
        d = rg.unit(rg.sub(w, sh)); w2 = rg.add(w, rg.mul(d, c['slack']))
        return w, w2
    for _ in range(passes):
        for c in CONTACTS:
            f = c['f']; a = c['att']
            for it in range(3):
                w, w2 = gap_for(c)
                res = a.aim(f, c['limb'], w2, tip=c['tip'])
                tip = a.rig.point(f, c['limb'], c['tip'])
                g = rg.sub(w2, tip)
                if rg.norm(g) < 0.04: break
                keys = [k for k in range(f - c['win'], f + c['win'] + 1) if float(k) in a.clip['keys']]
                a.nudge_root(keys, dx=g[0] * 0.85, dy=(g[1] * 0.85 if c['air'] else 0.0), dz=g[2] * 0.85)
    out = []
    for c in CONTACTS:
        f = c['f']; a, t = c['att'], c['tgt']
        w = t.rig.point(f, c['bone'], c['local'])
        tip = a.rig.point(f, c['limb'], c['tip'])
        out.append((c['name'] or '%s@f%d' % (c['limb'], f), f, round(rg.dist(tip, w), 3)))
    if verbose:
        for o in out: print('contact %-22s f%-4d tip-to-target=%.3f studs' % o)
    return out


# ================================================================ master build
@author
def contacts_opening():
    contact(IMPACT1, P, 'ra', D, 't', (0, 0.1, -0.5), name='dash-punch')
    contact(IMPACT1 + 1, P, 'ra', D, 't', (0, 0.1, -0.5), name='dash-punch hitstop')
    contact(IMPACT1 + 2, P, 'ra', D, 't', (0, 0.1, -0.5), name='dash-punch hitstop2')
    contact(56, P, 'la', D, 'h', (0, 0, -0.55), name='jab')
    contact(59, P, 'ra', D, 't', (0, -0.25, -0.5), name='cross')
    contact(60, P, 'ra', D, 't', (0, -0.25, -0.5), name='cross hitstop')
    contact(64, P, 'la', D, 'h', (0.35, 0, -0.4), name='left hook')
    contact(68, P, 'rl', D, 't', (0, -0.3, -0.5), name='thrust kick', tip=(0, -0.85, 0))
    contact(72, P, 'ra', D, 'h', (0, -0.3, -0.5), name='uppercut')


def build():
    import importlib
    for mod in ('beat_air', 'beat_kicks', 'beat_blink', 'beat_heli'):
        importlib.import_module(mod)
    for fn in AUTHOR:
        fn()
    solve_contacts()
