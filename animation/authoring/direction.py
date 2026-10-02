"""Camera, effects and tags for each beat. Runs after the poses and the strike contacts are solved, so every position is
read from the final rigs (nothing here moves a character)."""
import math

import choreo as C
import cam as camlib
import fx as fxlib
import rig as rg
from beat_air import CRASH, K1, K2, K3, K4, K5

P, D, CAM = C.P, C.D, C.CAM
FXL = fxlib.FX(CAM, {'P': P, 'D': D})
TAG_VIS = [0.0] * C.N
DUMMY_HURT = [False] * C.N


def fixed(f):
    return lambda _f: (0, 0, 0)


def at(rigfn, f):
    """constant anchor frozen at frame f"""
    pt = rigfn(f)
    return lambda _f: pt


def mid(f):
    a, b = P.rig.torso(f), D.rig.torso(f)
    return tuple((x + y) / 2 for x, y in zip(a, b))


def mid_head(f):
    a, b = P.rig.head(f), D.rig.head(f)
    return tuple((x + y) / 2 for x, y in zip(a, b))


def hurt(f0, f1):
    for f in range(f0, f1 + 1):
        if 0 <= f < C.N: DUMMY_HURT[f] = True


def tag(f0, f1, fade=3):
    """name tag visible f0..f1 with a pop-in overshoot and a short fade-out"""
    for f in range(f0, f1 + 1):
        a = f - f0
        pop = [0.0, 1.35, 1.1, 1.0][min(a, 3)] if a < 4 else 1.0
        out = min(1.0, (f1 - f) / fade + 0.0) if f1 - f < fade else 1.0
        TAG_VIS[f] = max(TAG_VIS[f], pop * max(out, 0.0))


def hit(f, att, limb, tip, s, d=None, **kw):
    p = att.rig.point(f, limb, tip)
    if d is None:
        d = rg.sub(D.rig.torso(f), P.rig.torso(f)); d = rg.unit((d[0], 0.0, d[2]))
    FXL.impact(f, p, d, s=s, **kw)
    return p


# ================================================================ framing helpers
def line(f):
    d = rg.sub(D.rig.torso(f), P.rig.torso(f)); d = rg.unit((d[0], 0.0, d[2]))
    return d if rg.norm(d) > 0.1 else (1.0, 0.0, 0.0)


def line_fixed(f):
    d = line(f)
    return lambda _f: d


def body(actor, f, pad=0.0):
    """head top + both soles + hands: the pose's silhouette"""
    r = actor.rig
    h = r.head(f); pts = [(h[0], h[1] + 0.7, h[2]), r.sole(f, 'l'), r.sole(f, 'r'), r.fist(f, 'l'), r.fist(f, 'r'), r.torso(f)]
    return pts


def both(f):
    return body(P, f) + body(D, f)


def hands_and_target(f):
    return [P.rig.fist(f, 'r'), P.rig.fist(f, 'l'), D.rig.chest(f), D.rig.head(f), P.rig.head(f)]


# ================================================================ f0-76
def direct_opening():
    # S1: extreme close-up on the face; the head snaps up to stare into the lens
    CAM.auto(0, 10, lambda f: [P.rig.head(f)], keys=[
        dict(f=0, az=150, el=-10, fill=0.95, fov=34, roll=-5, e='out', mind=1.4, shift=(0.0, 0.0)),
        dict(f=9, az=165, el=-6, fill=1.0, fov=28, roll=-2, mind=1.2)], line=line, follow=0.7, name='cu-face')
    FXL.sparkle(7, 11, P.rig.point(8, 'h', (0.28, 0.06, -0.62)), r=0.55)
    # S2: over-the-shoulder wide; slow push-in while the player coils
    CAM.auto(10, 30, both, keys=[
        dict(f=10, az=-14, el=7, fill=0.92, fov=66, roll=2, e='io', mind=4),
        dict(f=22, az=-9, el=5, fill=0.86, fov=58, roll=0, e='in', mind=3),
        dict(f=29, az=-5, el=3, fill=0.72, fov=46, roll=-3, shift=(0.0, 0.0))], line=line, follow=0.6, name='ots-wide')
    tag(12, 31)
    FXL.dust_burst(26, P.rig.sole(26, 'r'), s=0.6, n=5, dur=6)


def direct_dash_strike():
    # dash (f30-35): side tracking with a stretching lens, framed ahead of the player
    lead = lambda f: [P.rig.head(f), P.rig.sole(f, 'l'), P.rig.sole(f, 'r'), rg.add(P.rig.torso(f), rg.mul(line(f), 3.2))]
    CAM.auto(30, 35, lead, keys=[
        dict(f=30, az=88, el=2, fill=0.8, fov=58, roll=-3, e='out', mind=4),
        dict(f=34, az=82, el=0, fill=0.75, fov=74, roll=-7, mind=4)], line=line, follow=0.7, name='dash-track')
    p0 = P.rig.sole(30, 'r')
    FXL.shockwave(30, p0, r=3.2, dur=5, wall=False)
    FXL.dust_burst(30, p0, s=1.3, n=12, dur=9, spread=3.0)
    FXL.dash('P', 30, 35, col='#9fd6ff')
    FXL.trail('P', 'ra', (0, -1.0, 0), 31, 35, col='#ffffff', w=0.2)
    # impact close-up (f35-44): low 3/4 angle, then follows the dummy as it is thrown
    imp = lambda f: ([P.rig.fist(36, 'r'), D.rig.chest(36), P.rig.head(36), D.rig.head(36)] if f < 39 else
                     [D.rig.head(f), D.rig.sole(f, 'l'), D.rig.sole(f, 'r'), P.rig.head(39)] if f < 42 else body(D, f))
    CAM.auto(35, 45, imp, keys=[
        dict(f=35, az=62, el=-12, fill=0.74, fov=40, roll=3, e='out', mind=3),
        dict(f=38, az=70, el=-6, fill=0.7, fov=44, roll=2, e='io', mind=3),
        dict(f=44, az=96, el=2, fill=0.55, fov=54, roll=-2, mind=4)], line=line_fixed(36), follow=0.55, name='impact-cu')
    hit(C.IMPACT1, P, 'ra', (0, -1.0, 0), s=3, kind='hit', debris=14)
    FXL.trail('P', 'ra', (0, -1.0, 0), 34, 36, col='#ffffff', w=0.24, k=2)
    hurt(36, 47)
    FXL.e3(t='ghost', c='D', f0=38, f1=45, lags=[2, 4], col='#ffe9b0', a=0.38, decay=0.6, fade=True)
    FXL.e2(t='lines', f0=38, f1=45, mode='parallel', ang=None, n=22, a=0.7, col='#ffffff', who='D')
    FXL.e2(t='mblur', f0=39, f1=45, who='D', len=10)


def direct_crash():
    lp = D.rig.torso(C.LAND)
    CAM.auto(45, 56, lambda f: both(f), keys=[
        dict(f=45, az=84, el=6, fill=0.9, fov=62, roll=1, e='out', mind=6),
        dict(f=55, az=76, el=4, fill=0.8, fov=54, roll=0, mind=5)], line=line_fixed(50), follow=0.45, name='crash-wide')
    FXL.impact(C.LAND, (lp[0], 0.4, lp[2]), (1, 0.4, 0), s=3, kind='crash', ground=True, debris=16)
    FXL.shockwave(C.LAND, (lp[0], 0, lp[2]), r=7.0, dur=7)
    FXL.dust_burst(C.LAND, (lp[0], 0, lp[2]), s=2.0, n=18, dur=10, spread=4.2, drift_dir=(1, 0, 0), drift=4.0)
    for f in range(C.LAND + 1, C.LAND + 5):
        FXL.dust_burst(f, D.rig.torso(f), s=0.9, n=6, dur=7, spread=1.4, drift_dir=(1, 0, 0), drift=3.0)
    hurt(48, 53)
    FXL.dash('P', 42, 50, col='#9fd6ff')
    FXL.trail('P', 'la', (0, -1.0, 0), 44, 50, col='#cfe9ff', w=0.15, k=2)
    dp = D.rig.sole(53, 'r')
    FXL.dust_burst(52, (dp[0], 0, dp[2]), s=0.8, n=7, dur=6)


def direct_combo():
    # five hits, five different cameras: a hard cut on (almost) every strike
    lf = line_fixed(60)
    pair = lambda f: [P.rig.head(f), D.rig.head(f), P.rig.fist(f, 'r'), P.rig.fist(f, 'l'), D.rig.torso(f), P.rig.torso(f)]
    CAM.auto(55, 59, pair, keys=[dict(f=55, az=92, el=2, fill=0.9, fov=42, roll=-2, e='out', mind=3), dict(f=58, az=90, el=2, fill=0.92, fov=36, roll=-3, mind=3)], line=lf, follow=0.8, name='combo-1')
    CAM.auto(59, 63, pair, keys=[dict(f=59, az=128, el=-9, fill=0.88, fov=46, roll=5, e='out', mind=3), dict(f=62, az=122, el=-7, fill=0.9, fov=41, roll=6, mind=3)], line=lf, follow=0.8, name='combo-2')
    CAM.auto(63, 67, pair, keys=[dict(f=63, az=-58, el=6, fill=0.88, fov=44, roll=-5, e='out', mind=3), dict(f=66, az=-52, el=5, fill=0.9, fov=39, roll=-6, mind=3)], line=lf, follow=0.8, name='combo-3')
    CAM.auto(67, 71, lambda f: both(f), keys=[dict(f=67, az=96, el=-14, fill=0.82, fov=54, roll=2, e='out', mind=3), dict(f=70, az=92, el=-12, fill=0.84, fov=48, roll=3, mind=3)], line=lf, follow=0.8, name='combo-4')
    CAM.auto(71, 79, lambda f: [P.rig.head(f), D.rig.head(f), D.rig.sole(f, 'l'), P.rig.sole(f, 'r')], keys=[
        dict(f=71, az=40, el=-18, fill=0.8, fov=46, roll=-4, e='out', mind=3), dict(f=78, az=70, el=-24, fill=0.7, fov=58, roll=-6, mind=3)], line=lf, follow=0.6, name='combo-5-launch')
    hit(56, P, 'la', (0, -1.0, 0), 1)
    hit(59, P, 'ra', (0, -1.0, 0), 2)
    hit(64, P, 'la', (0, -1.0, 0), 2)
    hit(68, P, 'rl', (0, -0.85, 0), 2)
    hit(72, P, 'ra', (0, -1.0, 0), 3, flash='white')
    for f0 in (56, 59, 64, 68, 72):
        hurt(f0, f0 + 2)
    for f in (56, 59, 64, 68):
        FXL.trail('P', 'la' if f in (56, 64) else ('rl' if f == 68 else 'ra'), (0, -1.0, 0) if f != 68 else (0, -0.85, 0), f - 2, f, col='#ffffff', w=0.15, k=2)
    FXL.trail('P', 'ra', (0, -1.0, 0), 70, 72, col='#ffffff', w=0.24, k=3)
    for f in (56, 59, 64, 68):
        FXL.dust_burst(f, P.rig.sole(f, 'l'), s=0.5, n=4, dur=5, spread=1.2)
    FXL.dust_burst(72, P.rig.sole(72, 'l'), s=1.1, n=10, dur=8, spread=2.4)


def slash_plane(f, who, horizontal=True):
    """(centre, u, v) for a kick arc around the actor: horizontal sweep or vertical (line/up) sweep"""
    c = who.rig.torso(f); L_ = line(f)
    if horizontal: return c, L_, (-L_[2], 0.0, L_[0])
    return c, L_, (0.0, 1.0, 0.0)


def direct_air():
    lf = line_fixed(84)
    # launch rise: low angle looking up into the sky glare
    CAM.auto(79, 84, lambda f: [P.rig.head(f), D.rig.head(f), D.rig.sole(f, 'l'), P.rig.sole(f, 'r')], keys=[
        dict(f=79, az=75, el=-30, fill=0.7, fov=62, roll=-6, e='io', mind=4), dict(f=83, az=88, el=-12, fill=0.74, fov=56, roll=-3, mind=4)], line=lf, follow=0.6, name='air-rise')
    FXL.e3(t='ghost', c='P', f0=76, f1=83, lags=[2, 4, 6], col='#9fd6ff', a=0.4, decay=0.66, fade=True)
    FXL.e3(t='ghost', c='D', f0=73, f1=82, lags=[2, 4], col='#ffe9b0', a=0.3, decay=0.6, fade=True)
    FXL.e2(t='lines', f0=74, f1=83, mode='parallel', ang=90, n=18, a=0.7, col='#ffffff', who='P')
    FXL.dust_burst(75, P.rig.sole(75, 'r'), s=1.6, n=14, dur=9, spread=3.4)
    FXL.shockwave(75, P.rig.sole(75, 'r'), r=4.5, dur=6, wall=False)
    FXL.sfx.append((75, 'whoosh', 3))
    tight = lambda f: [P.rig.head(f), D.rig.head(f), P.rig.torso(f), D.rig.torso(f), P.rig.sole(f, 'r'), D.rig.sole(f, 'r')]
    CAM.auto(84, 87, tight, keys=[dict(f=84, az=92, el=0, fill=0.82, fov=42, roll=-3, e='out', mind=3), dict(f=86, az=96, el=2, fill=0.85, fov=38, roll=-4, mind=3)], line=lf, follow=0.8, name='air-k1')
    CAM.auto(87, 90, tight, keys=[dict(f=87, az=145, el=-8, fill=0.82, fov=44, roll=4, e='out', mind=3), dict(f=89, az=150, el=-6, fill=0.85, fov=40, roll=5, mind=3)], line=lf, follow=0.8, name='air-k2')
    CAM.auto(90, 94, tight, keys=[dict(f=90, az=28, el=14, fill=0.86, fov=36, roll=-5, e='out', mind=3), dict(f=93, az=34, el=14, fill=0.88, fov=32, roll=-6, mind=3)], line=lf, follow=0.8, name='air-k3')
    CAM.auto(94, 99, lambda f: [P.rig.head(f), D.rig.head(f), P.rig.sole(f, 'r'), D.rig.sole(f, 'r')], keys=[
        dict(f=94, az=70, el=-14, fill=0.8, fov=50, roll=-4, e='io', mind=3), dict(f=98, az=150, el=-8, fill=0.74, fov=54, roll=4, mind=3)], line=lf, follow=0.8, name='air-k4-orbit')
    # axe slam and the fall (high angle -> follows the meteor down)
    CAM.auto(99, 103, lambda f: [P.rig.head(f), D.rig.head(f), D.rig.sole(f, 'l')], keys=[
        dict(f=99, az=80, el=34, fill=0.82, fov=48, roll=3, e='out', mind=3), dict(f=102, az=88, el=18, fill=0.7, fov=62, roll=-2, mind=4)], line=lf, follow=0.7, name='air-slam')
    CAM.auto(103, 112, lambda f: [P.rig.head(f), P.rig.sole(f, 'r'), D.rig.torso(CRASH + 3), D.rig.head(CRASH + 3), D.rig.sole(CRASH + 3, 'l')], keys=[
        dict(f=103, az=84, el=6, fill=0.78, fov=60, roll=1, e='out', mind=10), dict(f=111, az=76, el=3, fill=0.7, fov=52, roll=0, mind=10)], line=lf, follow=0.5, name='crater-wide')
    # strikes
    hit(84, P, 'rl', (0, -0.85, 0), 2)
    hit(87, P, 'll', (0, -0.85, 0), 2)
    hit(90, P, 'rl', (0, -0.85, 0), 3)
    hit(94, P, 'rl', (0, -0.95, 0), 3, flash='white')
    pt = hit(99, P, 'ra', (0, -1.0, 0), 4, d=(0.0, -1.0, 0.0), flash='impact')
    for f in (84, 87, 90, 94, 99):
        hurt(f, f + 3)
    # kick arcs
    c, u, v = slash_plane(90, P, True)
    FXL.slash(89, 92, (c[0], c[1] + 0.2, c[2]), u, v, r=2.9, a0=-2.6, a1=0.4, th=0.22)
    c, u, v = slash_plane(94, P, False)
    FXL.slash(92, 96, (c[0], c[1], c[2]), u, v, r=2.8, a0=-3.4, a1=-0.4, th=0.24)
    FXL.e3(t='ghost', c='P', f0=92, f1=97, lags=[1, 2, 3], col='#cfe9ff', a=0.42, decay=0.7, fade=True)
    for f in (84, 87, 90, 94):
        FXL.trail('P', 'rl' if f != 87 else 'll', (0, -0.9, 0), f - 2, f, col='#ffffff', w=0.2, k=3)
    # meteor: ghosts, streaks, vertical speed lines, then the crater
    FXL.e3(t='ghost', c='D', f0=100, f1=102, lags=[1, 2, 3, 4], col='#ffffff', a=0.5, decay=0.75)
    FXL.e3(t='ghost', c='P', f0=100, f1=103, lags=[1, 2, 3], col='#9fd6ff', a=0.45, decay=0.72)
    for f in range(100, 103):
        a_, b_ = D.rig.torso(f - 1), D.rig.torso(f)
        FXL.e3(t='streak', f0=f, f1=f, p0=list(rg.add(a_, (0, 3.5, 0))), p1=list(b_), w=1.1, col='#ffffff', a=0.9)
    FXL.e2(t='lines', f0=100, f1=102, mode='parallel', ang=90, n=28, a=0.85, col='#ffffff', who='D')
    FXL.e2(t='mblur', f0=100, f1=102, who='D', len=22)
    cp = D.rig.torso(CRASH)
    FXL.impact(CRASH, (cp[0], 0.5, cp[2]), (0, 1, 0), s=4, kind='crash', ground=True, debris=36, flash='impact')
    FXL.shockwave(CRASH, (cp[0], 0, cp[2]), r=13.0, dur=9, h=2.4)
    FXL.shockwave(CRASH + 2, (cp[0], 0, cp[2]), r=8.0, dur=7, wall=False, col='#bfe3ff')
    FXL.dust_burst(CRASH, (cp[0], 0, cp[2]), s=2.6, n=22, dur=14, spread=6.0)
    FXL.crack(CRASH, (cp[0], 0, cp[2]), s=12.0, seed=11, keep=True, fade_at=150)
    hurt(CRASH, CRASH + 40)
    FXL.dust_burst(CRASH + 1, P.rig.sole(CRASH + 1, 'r'), s=1.8, n=14, dur=10, spread=3.5)
    FXL.shockwave(CRASH + 1, P.rig.sole(CRASH + 1, 'r'), r=5.0, dur=6, wall=False)


def direct_all():
    direct_opening()
    direct_dash_strike()
    direct_crash()
    direct_combo()
    direct_air()
