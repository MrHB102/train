"""Camera + effects for beats 5-14 (f103-630). Reads the final rigs; moves nothing."""
import math

import choreo as C
import direction as DR
from direction import P, D, CAM, FXL, line, line_fixed, body, both, hit, hurt, tag, mid, mid_head, TAG_VIS
import rig as rg
from beat_kicks import END, KS, KF, KSIDE, KHOOK, KDROP
import beat_blink as BB
import beat_heli as BH
import beat_pillars as BP
import beat_finale as BF


def lv(vec):
    u = rg.unit(vec)
    return lambda _f: u


def pair(f):
    return [P.rig.head(f), D.rig.head(f), P.rig.sole(f, 'r'), D.rig.sole(f, 'r'), P.rig.torso(f), D.rig.torso(f)]


def pj(f):
    return [P.rig.head(f), D.rig.head(f), P.rig.torso(f), D.rig.torso(f), P.rig.fist(f, 'r'), P.rig.sole(f, 'l'), D.rig.sole(f, 'l')]


def pf(f):
    return [P.rig.head(f), P.rig.sole(f, 'l'), P.rig.sole(f, 'r'), P.rig.fist(f, 'l'), P.rig.fist(f, 'r')]


def dflight(f):
    return [D.rig.head(f), D.rig.sole(f, 'l'), D.rig.sole(f, 'r'), D.rig.torso(f)]


def A(f0, f1, subj, keys, ln, follow=0.7, name=''):
    CAM.auto(f0, f1, subj, keys=keys, line=ln, follow=follow, name=name)


# ===================================================================== BEAT 5-6 : calm + kick flurry
def direct_kicks():
    lf = lv((1, 0, 0))                         # player -> dummy points along +X in this stretch
    A(112, 118, lambda f: pf(f) + [D.rig.torso(116)], [dict(f=112, az=70, el=-10, fill=0.8, fov=50, roll=2, e='io', mind=7), dict(f=117, az=80, el=-6, fill=0.78, fov=46, roll=0, mind=7)], lf, 0.6, 'calm-hero')
    A(118, 124, pair, [dict(f=118, az=90, el=3, fill=0.85, fov=56, roll=-1, e='io', mind=7), dict(f=123, az=88, el=2, fill=0.8, fov=50, roll=0, mind=7)], lf, 0.6, 'calm-two')
    FXL.dust_burst(120, (D.rig.root(120)[0], 0, D.rig.root(120)[2]), s=1.0, n=8, dur=7)
    hurt(103, 123)
    # approach + sweep
    A(124, 128, pair, [dict(f=124, az=90, el=3, fill=0.88, fov=56, roll=-2, e='out', mind=7), dict(f=127, az=88, el=1, fill=0.8, fov=50, roll=-3, mind=7)], lf, 0.7, 'approach')
    A(128, 132, lambda f: [P.rig.head(f), P.rig.sole(f, 'r'), D.rig.head(f), D.rig.sole(f, 'l')], [dict(f=128, az=100, el=-12, fill=0.86, fov=44, roll=4, e='out', mind=5), dict(f=131, az=96, el=-6, fill=0.88, fov=42, roll=5, mind=5)], lf, 0.8, 'sweep')
    hit(KS, P, 'rl', (0, -0.85, 0), 2, ground=False)
    FXL.shockwave(KS, P.rig.sole(KS, 'r'), r=3.4, dur=5, wall=False)
    FXL.dust_burst(KS, P.rig.sole(KS, 'r'), s=1.4, n=12, dur=8, spread=3.0)
    c, u, v = DR.slash_plane(KS, P, True)
    FXL.slash(KS - 1, KS + 2, (c[0], 0.9, c[2]), u, v, r=2.6, a0=-2.4, a1=0.3, th=0.2)
    FXL.trail('P', 'rl', (0, -0.9, 0), KS - 2, KS + 1, col='#ffffff', w=0.2, k=3)
    # flip + axe kick
    A(132, 136, lambda f: both(f), [dict(f=132, az=72, el=14, fill=0.82, fov=54, roll=-4, e='io', mind=7), dict(f=135, az=120, el=18, fill=0.8, fov=50, roll=3, mind=7)], lf, 0.7, 'flip')
    FXL.e3(t='ghost', c='P', f0=KS + 2, f1=KF + 1, lags=[1, 2, 3], col='#9fd6ff', a=0.4, decay=0.7, fade=True)
    pt = hit(KF, P, 'rl', (0, -1.0, 0), 3, d=(0, -1, 0), ground=False)
    FXL.dust_burst(KF + 1, (D.rig.torso(KF + 1)[0], 0, D.rig.torso(KF + 1)[2]), s=1.8, n=14, dur=9, spread=3.5)
    FXL.crack(KF + 1, (D.rig.torso(KF + 1)[0], 0, D.rig.torso(KF + 1)[2]), s=6.0, seed=3, keep=True, fade_at=170)
    FXL.shockwave(KF + 1, (D.rig.torso(KF + 1)[0], 0, D.rig.torso(KF + 1)[2]), r=5.5, dur=6)
    FXL.sfx.append((KF + 1, 'crash', 2)); FXL.sfx.append((KF + 3, 'crash', 1))
    hurt(KS, KF + 9)
    A(136, 141, lambda f: both(f), [dict(f=136, az=86, el=-10, fill=0.84, fov=52, roll=-2, e='io', mind=7), dict(f=140, az=90, el=-6, fill=0.82, fov=48, roll=-1, mind=7)], lf, 0.7, 'bounces')
    # side kick
    A(141, 146, pair, [dict(f=141, az=96, el=2, fill=0.86, fov=40, roll=3, e='out', mind=5), dict(f=145, az=100, el=2, fill=0.9, fov=36, roll=4, mind=5)], lf, 0.8, 'side-kick')
    hit(KSIDE, P, 'll', (0, -0.9, 0), 2)
    FXL.trail('P', 'll', (0, -0.9, 0), KSIDE - 2, KSIDE, col='#ffffff', w=0.2, k=3)
    FXL.dust_burst(KSIDE + 1, D.rig.sole(KSIDE + 1, 'l'), s=1.2, n=9, dur=7, drift_dir=(1, 0, 0), drift=3.0)
    hurt(KSIDE, KSIDE + 3)
    # spinning hook kick
    A(146, 151, lambda f: [P.rig.head(f), D.rig.head(f), P.rig.torso(f), D.rig.sole(f, 'l')], [dict(f=146, az=28, el=10, fill=0.86, fov=38, roll=-5, e='out', mind=5), dict(f=150, az=40, el=10, fill=0.88, fov=34, roll=-6, mind=5)], lf, 0.8, 'hook-kick')
    hit(KHOOK, P, 'rl', (0, -0.9, 0), 3)
    c, u, v = DR.slash_plane(KHOOK, P, True)
    FXL.slash(KHOOK - 2, KHOOK + 1, (c[0], c[1] + 1.2, c[2]), u, v, r=2.8, a0=-2.8, a1=0.5, th=0.22)
    FXL.e3(t='ghost', c='P', f0=KHOOK - 3, f1=KHOOK, lags=[1, 2, 3], col='#cfe9ff', a=0.4, decay=0.7, fade=True)
    FXL.e3(t='ghost', c='D', f0=KHOOK + 1, f1=KHOOK + 7, lags=[1, 2], col='#dfeaff', a=0.2, decay=0.6, fade=True)
    hurt(KHOOK, KHOOK + 8)
    # cartwheel
    A(151, 158, lambda f: pf(f) + [D.rig.torso(f)], [dict(f=151, az=88, el=0, fill=0.84, fov=58, roll=-3, e='io', mind=7), dict(f=157, az=84, el=-2, fill=0.8, fov=54, roll=-2, mind=7)], lf, 0.6, 'cartwheel')
    FXL.e3(t='ghost', c='P', f0=150, f1=156, lags=[1, 2, 3, 4], col='#9fd6ff', a=0.4, decay=0.7, fade=True)
    FXL.dash('P', 150, 156, col='#9fd6ff', lags=(2, 4), lines=True, mblur=10)
    FXL.dust_burst(154, P.rig.sole(154, 'r'), s=1.0, n=7, dur=7)
    # drop-kick and the dummy's flight
    A(158, 162, lambda f: [P.rig.head(f), D.rig.head(f), P.rig.sole(f, 'l'), D.rig.sole(f, 'l')], [dict(f=158, az=112, el=-6, fill=0.84, fov=44, roll=4, e='out', mind=5), dict(f=161, az=118, el=-4, fill=0.86, fov=40, roll=5, mind=5)], lf, 0.8, 'dropkick')
    hit(KDROP, P, 'll', (0, -1.0, 0), 3)
    FXL.trail('P', 'll', (0, -1.0, 0), KDROP - 3, KDROP, col='#ffffff', w=0.24, k=3)
    FXL.e3(t='ghost', c='D', f0=KDROP + 2, f1=KDROP + 8, lags=[2, 4], col='#ffe9b0', a=0.35, decay=0.6, fade=True)
    FXL.e2(t='lines', f0=KDROP + 2, f1=KDROP + 8, mode='parallel', ang=None, n=22, a=0.7, col='#ffffff', who='D')
    A(162, 172, lambda f: dflight(f) + [P.rig.head(f)], [dict(f=162, az=84, el=4, fill=0.84, fov=56, roll=-2, e='io', mind=8), dict(f=171, az=80, el=6, fill=0.78, fov=54, roll=0, mind=8)], lf, 0.5, 'dummy-flight')
    ld = D.rig.torso(KDROP + 10)
    FXL.impact(KDROP + 10, (ld[0], 0.4, ld[2]), (-1, 0.3, 0), s=2, kind='crash', ground=True, debris=10)
    FXL.dust_burst(KDROP + 10, (ld[0], 0, ld[2]), s=1.4, n=12, dur=9, spread=3.5, drift_dir=(1, 0, 0), drift=3.0)
    hurt(KDROP, KDROP + 16)


# ===================================================================== BEAT 7 : blink steps
def direct_blink():
    lm = lv((-1, 0, 0))
    A(172, 182, lambda f: pair(f), [dict(f=172, az=90, el=2, fill=0.86, fov=56, roll=-1, e='io', mind=7), dict(f=181, az=96, el=3, fill=0.8, fov=50, roll=0, mind=7)], lm, 0.6, 'blink-setup')
    FXL.dust_burst(176, (D.rig.root(176)[0], 0, D.rig.root(176)[2]), s=1.0, n=8, dur=7)
    sh = [(BB.B1, 40, 4), (BB.B2, -70, -3), (BB.B3, 30, -14), (BB.B4, 80, 4), (BB.B5, 150, -6), (BB.B6, 60, 3)]
    ends = [BB.B2, BB.B3, BB.B4, BB.B5, BB.B6, BB.B6 + 4]
    for (fh, az, roll), fe in zip(sh, ends):
        A(fh - 1 if fh != BB.B1 else 182, fe, lambda f, fh=fh: [P.rig.head(fh), P.rig.sole(fh, 'r'), P.rig.sole(fh, 'l'), P.rig.fist(fh, 'r'), P.rig.fist(fh, 'l'), D.rig.head(f), D.rig.sole(f, 'l'), D.rig.sole(f, 'r')],
          [dict(f=fh, az=az, el=0 if fh != BB.B3 else 18, fill=0.86, fov=48, roll=roll, e='out', mind=7), dict(f=fe, az=az + 8, el=2, fill=0.88, fov=44, roll=roll * 1.2, mind=7)], lm, 0.8, 'blink-hit')
    kinds = {BB.B1: ('ra', (0, -1.0, 0), 2), BB.B2: ('la', (0, -1.0, 0), 2), BB.B3: ('rl', (0, -1.0, 0), 3), BB.B4: ('rl', (0, -0.85, 0), 3), BB.B5: ('ra', (0, -1.0, 0), 3), BB.B6: ('ra', (0, -1.0, 0), 4)}
    for fh, (limb, tip, s) in kinds.items():
        hit(fh, P, limb, tip, s, flash=('impact' if fh == BB.B6 else None))
        hurt(fh, fh + 3)
        # teleport streak from where the player was to where it appears + after-images
        prevf = max(f for f in range(fh - 6, fh) if C.P_VIS[f]) if any(C.P_VIS[f] for f in range(fh - 6, fh)) else fh - 2
        a_, b_ = P.rig.torso(prevf), P.rig.torso(fh)
        FXL.e3(t='streak', f0=fh - 1, f1=fh, p0=list(a_), p1=list(b_), w=0.7, col='#bfe3ff', a=0.9)
        FXL.e3(t='streak', f0=fh, f1=fh + 1, p0=list(rg.add(a_, (0, 1.2, 0))), p1=list(rg.add(b_, (0, 1.2, 0))), w=0.3, col='#ffffff', a=0.8)
        FXL.e3(t='ghost', c='P', f0=fh, f1=fh + 2, lags=[3, 5, 7], col='#9fd6ff', a=0.4, decay=0.7, fade=True)
        FXL.dust_burst(fh, P.rig.sole(fh, 'r') if limb != 'rl' or fh != BB.B3 else D.rig.sole(fh, 'l'), s=0.6, n=5, dur=5)
        FXL.sfx.append((fh - 1, 'blink', 2))
    c, u, v = DR.slash_plane(BB.B4, P, True)
    FXL.slash(BB.B4 - 1, BB.B4 + 2, (c[0], c[1] + 0.2, c[2]), u, v, r=2.7, a0=-2.6, a1=0.4, th=0.2)
    c, u, v = DR.slash_plane(BB.B5, P, False)
    FXL.slash(BB.B5 - 1, BB.B5 + 2, (c[0], c[1], c[2]), u, v, r=2.6, a0=-3.0, a1=-0.3, th=0.2)
    # palm blast flight
    FXL.e3(t='ghost', c='D', f0=BB.B6 + 2, f1=BB.B6 + 9, lags=[2, 4], col='#ffe9b0', a=0.35, decay=0.6, fade=True)
    FXL.e2(t='lines', f0=BB.B6 + 2, f1=BB.B6 + 9, mode='parallel', ang=None, n=22, a=0.7, col='#ffffff', who='D')
    FXL.e3(t='ring', f0=BB.B6, f1=BB.B6 + 6, p=list(P.rig.fist(BB.B6, 'r')), n=[-1, 0, 0], r0=0.3, r1=6.5, w=0.5, col='#ffffff', a0=0.9, a1=0.0)
    A(BB.B6 + 4, 222, lambda f: dflight(f) + [P.rig.head(f)], [dict(f=BB.B6 + 4, az=86, el=3, fill=0.84, fov=58, roll=-2, e='io', mind=9), dict(f=221, az=84, el=5, fill=0.8, fov=56, roll=0, mind=9)], lm, 0.5, 'blast-follow')
    ld = D.rig.torso(BB.B6 + 11)
    FXL.impact(BB.B6 + 10, (ld[0], 0.4, ld[2]), (-1, 0.3, 0), s=2, kind='crash', ground=True, debris=10)
    FXL.dust_burst(BB.B6 + 10, (ld[0], 0, ld[2]), s=1.4, n=12, dur=9, spread=3.5, drift_dir=(-1, 0, 0), drift=3.0)
    hurt(BB.B6, BB.B6 + 16)


# ===================================================================== BEAT 8 : hammer throw
def direct_hammer():
    lm = lv((-1, 0, 0))
    A(222, 228, lambda f: pf(f) + [D.rig.torso(f), D.rig.sole(f, 'r')], [dict(f=222, az=96, el=2, fill=0.84, fov=52, roll=2, e='io', mind=6), dict(f=227, az=100, el=-4, fill=0.84, fov=44, roll=3, mind=6)], lm, 0.7, 'run-grab')
    FXL.dash('P', 214, 223, col='#9fd6ff', lines=True, mblur=12)
    FXL.trail('P', 'ra', (0, -1.0, 0), 224, 226, col='#ffffff', w=0.2, k=2)
    # the orbit: camera circles the thrower while the dummy whirls
    c0 = lambda f: [P.rig.head(f), D.rig.torso(f), P.rig.sole(f, 'r')]
    A(228, 247, c0, [dict(f=228, az=0, el=-10, fill=0.62, fov=52, roll=-6, e='in', mind=8), dict(f=238, az=-300, el=6, fill=0.6, fov=54, roll=0, mind=8), dict(f=246, az=-640, el=-4, fill=0.58, fov=58, roll=6, mind=8)], lm, 0.9, 'orbit')
    FXL.e3(t='ghost', c='D', f0=BB.SP0 + 4, f1=BB.SP1, lags=[1, 2], col='#dfeaff', a=0.26, decay=0.65)
    FXL.e3(t='ghost', c='P', f0=BB.SP0 + 6, f1=BB.SP1, lags=[1, 2], col='#9fd6ff', a=0.3, decay=0.6)
    for i, f in enumerate(range(BB.SP0, BB.SP1, 3)):
        pp = P.rig.sole(f, 'r')
        FXL.dust_burst(f, (pp[0], 0, pp[2]), s=0.7 + 0.1 * i, n=6, dur=6, spread=2.2)
    FXL.e3(t='ring', f0=BB.SP0, f1=BB.SP1, p=[P.rig.root(BB.SP0)[0], 0.06, P.rig.root(BB.SP0)[2]], n=[0, 1, 0], r0=1.5, r1=7.5, w=0.6, col='#ffffff', a0=0.5, a1=0.1)
    # release
    cen = D.rig.torso(BB.SP1)
    FXL.impact(BB.SP1 + 1, cen, (-1, 0.0, 0), s=3, kind='whoosh', shake=True, debris=0)
    FXL.e3(t='ghost', c='D', f0=BB.SP1 + 1, f1=BB.SP1 + 10, lags=[2, 4, 6], col='#ffe9b0', a=0.4, decay=0.65, fade=True)
    FXL.e2(t='lines', f0=BB.SP1 + 1, f1=BB.SP1 + 10, mode='parallel', ang=None, n=26, a=0.8, col='#ffffff', who='D')
    FXL.e2(t='mblur', f0=BB.SP1 + 1, f1=BB.SP1 + 10, who='D', len=16)
    A(247, 259, lambda f: dflight(f) + [P.rig.head(f)], [dict(f=247, az=100, el=3, fill=0.8, fov=62, roll=-3, e='io', mind=10), dict(f=258, az=84, el=6, fill=0.74, fov=56, roll=0, mind=10)], lm, 0.45, 'throw-flight')
    ld = D.rig.torso(BB.SP1 + 13)
    FXL.impact(BB.SP1 + 13, (ld[0], 0.4, ld[2]), (-1, 0.3, 0), s=3, kind='crash', ground=True, debris=14)
    FXL.dust_burst(BB.SP1 + 13, (ld[0], 0, ld[2]), s=1.6, n=14, dur=10, spread=4.0, drift_dir=(-1, 0, 0), drift=4.0)
    FXL.shockwave(BB.SP1 + 13, (ld[0], 0, ld[2]), r=7.0, dur=7)
    hurt(BB.GRAB, BB.SP1 + 20)


# ===================================================================== BEAT 9 : helicopter
def direct_heli():
    lm = lv((-1, 0, 0))
    FXL.dash('P', 250, 261, col='#9fd6ff', lines=True, mblur=18)
    FXL.dash('P', 250, 261, col='#ffffff', lags=(1, 3), lines=False, mblur=0, dust=False)
    A(259, 267, lambda f: pf(f) + [D.rig.torso(f)], [dict(f=259, az=86, el=3, fill=0.8, fov=56, roll=-3, e='out', mind=7), dict(f=266, az=90, el=-4, fill=0.8, fov=50, roll=0, mind=6)], lm, 0.6, 'handspring')
    A(267, 278, lambda f: [P.rig.head(f), D.rig.head(f), P.rig.sole(f, 'l'), P.rig.sole(f, 'r'), D.rig.sole(f, 'l'), P.rig.fist(f, 'l'), P.rig.fist(f, 'r')], [
        dict(f=267, az=88, el=-6, fill=0.8, fov=50, roll=-4, e='io', mind=5), dict(f=272, az=140, el=-10, fill=0.8, fov=48, roll=3, mind=5), dict(f=277, az=200, el=-4, fill=0.8, fov=48, roll=-3, mind=5)], lm, 0.8, 'heli-orbit')
    for f_, limb in ((BH.H1, 'rl'), (BH.H2, 'll'), (BH.H3, 'rl')):
        hit(f_, P, limb, (0, -1.0, 0), 2, d=rg.unit(rg.sub(D.rig.torso(f_), P.rig.torso(f_))))
        c = P.rig.torso(f_)
        FXL.e3(t='ring', f0=f_ - 1, f1=f_ + 4, p=[c[0], c[1] + 1.0, c[2]], n=[0, 1, 0], r0=1.5, r1=4.2, w=0.5, col='#ffffff', a0=0.8, a1=0.0)
        hurt(f_, f_ + 3)
    FXL.e3(t='ghost', c='P', f0=BH.SPIN0, f1=278, lags=[1, 2, 3], col='#ffd27a', a=0.4, decay=0.7)
    for f in range(BH.SPIN0, 278, 2):
        pp = P.rig.root(f)
        FXL.dust_burst(f, (pp[0], 0, pp[2]), s=0.6, n=4, dur=5, spread=2.0)
    A(278, 285, lambda f: pf(f) + [D.rig.head(f)], [dict(f=278, az=92, el=2, fill=0.8, fov=50, roll=2, e='io', mind=7), dict(f=284, az=70, el=-12, fill=0.8, fov=44, roll=4, mind=6)], lm, 0.7, 'crouch')
    A(285, 296, lambda f: [P.rig.head(f), D.rig.head(f), P.rig.sole(f, 'l'), D.rig.sole(f, 'l')], [dict(f=285, az=60, el=-26, fill=0.82, fov=46, roll=-5, e='out', mind=5), dict(f=290, az=82, el=-14, fill=0.8, fov=54, roll=-2, mind=6), dict(f=295, az=100, el=2, fill=0.78, fov=50, roll=2, mind=6)], lm, 0.7, 'dragon-rise')
    hit(BH.UP, P, 'ra', (0, -1.0, 0), 3, d=(0, 1, 0), flash='white')
    FXL.e3(t='ghost', c='P', f0=BH.UP, f1=BH.BIKE, lags=[1, 2, 3, 4], col='#ff9a5a', a=0.45, decay=0.7, fade=True)
    FXL.e3(t='ring', f0=BH.UP, f1=BH.UP + 6, p=list(P.rig.sole(BH.UP, 'l')), n=[0, 1, 0], r0=0.6, r1=5.0, w=0.8, col='#ffd27a', a0=0.9, a1=0.0)
    FXL.dust_burst(BH.UP, P.rig.sole(BH.UP - 1, 'l'), s=1.5, n=12, dur=9, spread=3.0)
    FXL.e2(t='lines', f0=BH.UP + 1, f1=BH.UP + 8, mode='parallel', ang=90, n=18, a=0.7, col='#ffffff', who='P')
    A(296, 304, lambda f: [P.rig.head(f), D.rig.head(f), P.rig.sole(f, 'l'), D.rig.sole(f, 'l')], [dict(f=296, az=84, el=4, fill=0.8, fov=44, roll=3, e='out', mind=5), dict(f=303, az=88, el=4, fill=0.7, fov=52, roll=0, mind=6)], lm, 0.7, 'bicycle')
    hit(BH.BIKE, P, 'll', (0, -1.0, 0), 3, flash='white')
    c, u, v = DR.slash_plane(BH.BIKE - 1, P, False)
    FXL.slash(BH.BIKE - 3, BH.BIKE + 1, (c[0], c[1], c[2]), u, v, r=2.8, a0=-3.4, a1=-0.2, th=0.24)
    FXL.e3(t='ghost', c='D', f0=BH.BIKE + 2, f1=BH.BIKE + 9, lags=[2, 4], col='#ffe9b0', a=0.35, decay=0.6, fade=True)
    FXL.e2(t='lines', f0=BH.BIKE + 2, f1=BH.BIKE + 9, mode='parallel', ang=None, n=22, a=0.7, col='#ffffff', who='D')
    A(304, 312, lambda f: dflight(f) + [P.rig.head(f)], [dict(f=304, az=84, el=5, fill=0.82, fov=60, roll=-2, e='io', mind=9), dict(f=311, az=80, el=6, fill=0.78, fov=56, roll=0, mind=9)], lm, 0.45, 'bike-flight')
    ld = D.rig.torso(BH.BIKE + 10)
    FXL.impact(BH.BIKE + 10, (ld[0], 0.4, ld[2]), (-1, 0.3, 0), s=2, kind='crash', ground=True, debris=10)
    FXL.dust_burst(BH.BIKE + 10, (ld[0], 0, ld[2]), s=1.4, n=12, dur=9, spread=3.5, drift_dir=(-1, 0, 0), drift=3.0)
    hurt(BH.H1, BH.BIKE + 16)


# ===================================================================== BEAT 10-11 : pillars + juggle
def direct_pillars():
    lm = lv((-1, 0, 0))
    xl = END['heli_land'][0]
    # calm walk: low wide shot, slow dolly
    A(312, 330, lambda f: both(f), [dict(f=312, az=88, el=-4, fill=0.9, fov=62, roll=0, e='io', mind=12), dict(f=329, az=92, el=-2, fill=0.8, fov=54, roll=0, mind=10)], lm, 0.5, 'walk-wide')
    # stomp: ground cracks race to the dummy
    sp = P.rig.sole(330, 'r')
    A(330, 336, lambda f: both(f), [dict(f=330, az=84, el=-12, fill=0.88, fov=52, roll=3, e='out', mind=9), dict(f=335, az=76, el=-18, fill=0.82, fov=46, roll=5, mind=9)], lm, 0.6, 'stomp')
    FXL.shockwave(330, sp, r=6.0, dur=7)
    FXL.dust_burst(330, sp, s=1.3, n=12, dur=9, spread=3.0)
    dx = END['pillars'][0]['p'][0]
    for i, f in enumerate(range(330, 337)):
        u = (f - 329) / 7.0
        FXL.crack(f, (L_(sp[0], dx, u), 0, sp[2]), s=2.6 + 1.2 * i, rot=0.0, seed=i % 4, keep=True, fade_at=380)
    FXL.cam.shake(330, amp=0.2, roll=0.8, decay=5, seed=77)
    FXL.sfx.append((330, 'crash', 2))
    cams = [(336, 341, 70, 8), (341, 346, -80, -6), (346, 354, 40, 3)]
    for (f0, f1, az, roll) in cams:
        A(f0, f1, lambda f: [D.rig.head(f), D.rig.sole(f, 'l'), P.rig.head(f)] + [(END['pillars'][0]['p'][0], 0, END['pillars'][0]['p'][1])],
          [dict(f=f0, az=az, el=-8, fill=0.8, fov=50, roll=roll, e='out', mind=9), dict(f=f1 - 1, az=az + 12, el=2, fill=0.74, fov=54, roll=roll * 0.5, mind=9)], lm, 0.6, 'pillar-cam')
    for pl in END['pillars']:
        p = (pl['p'][0], 0.0, pl['p'][1])
        FXL.e3(t='pillar', f0=pl['f'], f1=pl['f1'], p=list(p), w=pl['w'], h=pl['h'], rot=pl['rot'], tilt=pl['tilt'])
        FXL.dust_burst(pl['f'], p, s=1.8, n=14, dur=10, spread=3.5)
        FXL.e3(t='ring', f0=pl['f'], f1=pl['f'] + 5, p=[p[0], 0.06, p[2]], n=[0, 1, 0], r0=0.8, r1=pl['h'] * 0.7, w=1.0, col='#ffffff', a0=0.9, a1=0.0)
        FXL.crack(pl['f'], p, s=5.0, seed=pl['f'], keep=True, fade_at=390)
        FXL.cam.shake(pl['f'], amp=0.3, roll=1.2, decay=6, seed=pl['f'])
        FXL.cam.punch(pl['f'], dfov=-5, decay=3)
        FXL.e3(t='debris', f0=pl['f1'], f1=pl['f1'] + 14, p=[p[0], pl['h'] * 0.5, p[2]], n=22, size=[0.25, 0.7], speed=9, seed=pl['f'], life=1.0, grav=30, up=0.3, flat=1.0, col='#9aa4b8')
        FXL.e2(t='star', f0=pl['f'], f1=pl['f'] + 2, p=[p[0], pl['h'] * 0.5, p[2]], r=1.0, col='#ffffff', seed=pl['f'], rays=14)
        FXL.e2(t='ca', f0=pl['f'], f1=pl['f'] + 3, amt=4.0)
        FXL.sfx.append((pl['f'], 'crash', 3))
    hurt(336, 366)
    FXL.e3(t='ghost', c='D', f0=336, f1=362, lags=[2, 4], col='#ffe9b0', a=0.28, decay=0.6, fade=True)
    FXL.e3(t='ghost', c='P', f0=BP.PIL[2] + 9, f1=BP.TJ[0] - 4, lags=[2, 4, 6], col='#9fd6ff', a=0.45, decay=0.66, fade=True)
    FXL.e2(t='lines', f0=BP.PIL[2] + 9, f1=BP.TJ[0] - 4, mode='parallel', ang=None, n=20, a=0.7, col='#ffffff', who='P')
    A(354, 366, lambda f: [D.rig.head(f), D.rig.sole(f, 'l'), P.rig.head(f), P.rig.sole(f, 'r')], [dict(f=354, az=96, el=-4, fill=0.8, fov=56, roll=0, e='io', mind=10), dict(f=365, az=90, el=2, fill=0.8, fov=50, roll=0, mind=8)], lm, 0.45, 'dash-under')


def L_(a, b, t):
    return a + (b - a) * max(0.0, min(1.0, t))


def direct_juggle():
    lm = lv((-1, 0, 0))
    shots = [(366, 372, 90, 0), (372, 378, 130, 3), (378, 384, 60, -3), (384, 390, -90, 4), (390, 396, 100, -2)]
    for (f0, f1, az, roll) in shots:
        A(f0, f1, lambda f: [P.rig.head(f), P.rig.sole(f, 'r'), D.rig.head(f), D.rig.sole(f, 'l')], [dict(f=f0, az=az, el=-2, fill=0.8, fov=46, roll=roll, e='io', mind=5), dict(f=f1 - 1, az=az + 6, el=0, fill=0.82, fov=42, roll=roll * 0.6, mind=5)], lm, 0.7, 'juggle-cut')
    for f_, limb, tip, s in ((BP.TJ[0], 'rl', (0, -0.55, 0), 1), (BP.TJ[1], 'll', (0, -1.0, 0), 1), (BP.TJ[3], 'rl', (0, -0.7, 0), 1), (BP.TJ[4], 'll', (0, -0.55, 0), 1)):
        hit(f_, P, limb, tip, s, d=(0, 1, 0))
    p_h = P.rig.head(BP.TJ[2])
    FXL.impact(BP.TJ[2], p_h, (0, 1, 0), s=2)
    for f in BP.TJ[:5]:
        hurt(f, f + 2)
    # lob: huge, skyward
    A(396, 408, lambda f: [P.rig.head(f), P.rig.sole(f, 'r'), D.rig.head(f)], [dict(f=396, az=96, el=-6, fill=0.8, fov=50, roll=-3, e='out', mind=6), dict(f=401, az=84, el=-34, fill=0.6, fov=64, roll=0, mind=9), dict(f=407, az=84, el=-50, fill=0.55, fov=70, roll=2, mind=12)], lm, 0.4, 'lob-up')
    hit(BP.LOB, P, 'll', (0, -1.0, 0), 3, d=(0, 1, 0), flash='white')
    FXL.e3(t='ghost', c='D', f0=BP.LOB + 1, f1=BP.LOB + 14, lags=[2, 4, 6], col='#ffffff', a=0.4, decay=0.66, fade=True)
    FXL.e2(t='lines', f0=BP.LOB + 1, f1=BP.LOB + 14, mode='parallel', ang=90, n=24, a=0.8, col='#ffffff', who='D')
    FXL.dust_burst(BP.LOB, P.rig.sole(BP.LOB, 'r'), s=1.8, n=14, dur=10, spread=3.5)
    hurt(BP.LOB, 500)


# ===================================================================== BEAT 12 : flow charge
def direct_charge():
    lm = lv((-1, 0, 0))
    pp = lambda f: [P.rig.head(f), P.rig.sole(f, 'l'), P.rig.sole(f, 'r'), P.rig.fist(f, 'l'), P.rig.fist(f, 'r')]
    A(408, 421, pp, [dict(f=408, az=70, el=2, fill=0.74, fov=50, roll=2, e='io', mind=7), dict(f=414, az=100, el=-2, fill=0.7, fov=48, roll=-3, mind=7), dict(f=420, az=84, el=2, fill=0.74, fov=52, roll=0, mind=7)], lm, 0.7, 'spin')
    FXL.e3(t='ghost', c='P', f0=BF.SPIN0 + 1, f1=BF.SPIN1, lags=[1, 2, 3], col='#ff8a8a', a=0.4, decay=0.7)
    FXL.e3(t='ring', f0=BF.SPIN0, f1=BF.SPIN1 + 3, p=[P.rig.root(BF.SPIN0)[0], 0.06, P.rig.root(BF.SPIN0)[2]], n=[0, 1, 0], r0=1.0, r1=9.0, w=0.8, col='#ffffff', a0=0.7, a1=0.0)
    c, u, v = DR.slash_plane(BF.SPIN0 + 4, P, True)
    FXL.slash(BF.SPIN0 + 2, BF.SPIN0 + 7, (c[0], c[1] + 0.8, c[2]), u, v, r=3.0, a0=-3.0, a1=0.6, th=0.2)
    FXL.dust_burst(BF.SPIN1 + 1, P.rig.sole(BF.SPIN1 + 1, 'r'), s=1.6, n=14, dur=10, spread=3.6)
    FXL.sfx.append((BF.SPIN0 + 4, 'whoosh', 3))
    A(421, 428, pp, [dict(f=421, az=88, el=4, fill=0.7, fov=52, roll=-4, e='io', mind=8), dict(f=427, az=82, el=14, fill=0.7, fov=50, roll=3, mind=8)], lm, 0.6, 'flip')
    FXL.e3(t='ghost', c='P', f0=BF.FLIP0, f1=BF.FLIP1, lags=[1, 2, 3, 4], col='#ff8a8a', a=0.42, decay=0.72, fade=True)
    FXL.dust_burst(BF.FLIP1 + 1, P.rig.sole(BF.FLIP1 + 1, 'r'), s=1.2, n=10, dur=8)
    A(428, 440, pp, [dict(f=428, az=100, el=-2, fill=0.74, fov=52, roll=3, e='io', mind=7), dict(f=438, az=70, el=2, fill=0.72, fov=50, roll=-3, mind=7)], lm, 0.7, 'slide')
    FXL.dash('P', BF.SLIDE0, BF.SLIDE1, col='#ff8a8a', lags=(2, 4), lines=True, mblur=12)
    xe, pz, yw1 = END['charge_pos']
    # slow orbit while the power builds; the sky and the dummy hang above
    A(440, 470, lambda f: [P.rig.head(f), P.rig.sole(f, 'l'), P.rig.sole(f, 'r')], [dict(f=440, az=60, el=-4, fill=0.7, fov=50, roll=-3, e='io', mind=6), dict(f=455, az=110, el=-14, fill=0.66, fov=52, roll=2, mind=6), dict(f=469, az=165, el=-22, fill=0.62, fov=54, roll=-2, mind=6)], lm, 0.9, 'charge-orbit')
    A(470, 484, lambda f: [P.rig.head(f), P.rig.sole(f, 'r'), D.rig.head(f)], [dict(f=470, az=90, el=-36, fill=0.62, fov=62, roll=0, e='io', mind=11), dict(f=483, az=88, el=-44, fill=0.58, fov=66, roll=3, mind=11)], lm, 0.9, 'look-up')
    A(484, 489, lambda f: [P.rig.head(f), P.rig.torso(f), P.rig.fist(f, 'l'), P.rig.fist(f, 'r')], [dict(f=484, az=-30, el=-10, fill=0.85, fov=48, roll=-3, e='in', mind=6), dict(f=488, az=-22, el=-6, fill=0.9, fov=38, roll=-2, mind=5.5)], lm, 0.8, 'charge-push')
    FXL.aura('P', 440, 488, col='#ff3040', a=0.55, scale=1.16, ramp=True)
    FXL.aura('P', 470, 488, col='#ffe27a', a=0.4, scale=1.3, ramp=True)
    FXL.grade(436, 488, sat=0.75, contrast=1.15, vig=0.5, tint=(0.9, 0.95, 1.08), ramp=10)
    px, pzz = P.rig.root(440)[0], P.rig.root(440)[2]
    for i, f in enumerate(range(442, 486, 4)):
        ang = i * 1.2
        FXL.crack(f, (px + math.cos(ang) * (1.5 + i * 0.5), 0, pzz + math.sin(ang) * (1.5 + i * 0.5)), s=3.0 + 0.5 * i, seed=i, keep=True, fade_at=520)
        FXL.e3(t='debris', f0=f, f1=f + 40, p=[px + math.cos(ang + 1) * (2 + i * 0.4), 0.2, pzz + math.sin(ang + 1) * (2 + i * 0.4)], n=4, size=[0.2, 0.55], speed=2.2, seed=i + 40, life=2.6, grav=-3.0, up=0.9, flat=0.2, col='#c9d2e4')
    for f in range(442, 486, 8):
        FXL.shockwave(f, (px, 0, pzz), r=5.0 + (f - 442) * 0.07, dur=9, wall=False, col='#ff9aa5')
        FXL.cam.shake(f, amp=0.06, roll=0.3, decay=4, seed=f)
    FXL.dust_burst(450, (px, 0, pzz), s=1.2, n=10, dur=22, spread=6.0, rise=2.6)
    FXL.sfx.append((440, 'charge', 3))
    hurt(BP.LOB, 500)


# ===================================================================== BEAT 13 : sky finisher
def direct_sky():
    lm = lv((-1, 0, 0))
    A(489, 498, lambda f: [P.rig.head(f), P.rig.sole(f, 'l'), D.rig.head(f)], [dict(f=489, az=90, el=-30, fill=0.62, fov=62, roll=-3, e='out', mind=12), dict(f=497, az=84, el=-10, fill=0.7, fov=58, roll=0, mind=10)], lm, 0.55, 'leap')
    FXL.shockwave(BF.JUMP0, P.rig.sole(BF.JUMP0 - 1, 'r'), r=9.0, dur=9, h=2.4)
    FXL.dust_burst(BF.JUMP0, P.rig.sole(BF.JUMP0 - 1, 'r'), s=2.4, n=18, dur=14, spread=6.0)
    FXL.crack(BF.JUMP0, P.rig.sole(BF.JUMP0 - 1, 'r'), s=10.0, seed=9, keep=True, fade_at=540)
    FXL.e3(t='ghost', c='P', f0=BF.JUMP0, f1=BF.JUMP1, lags=[1, 2, 3, 4], col='#ff6a7a', a=0.5, decay=0.72)
    for f in range(BF.JUMP0 + 1, BF.JUMP1 + 1):
        a_, b_ = P.rig.torso(f - 1), P.rig.torso(f)
        FXL.e3(t='streak', f0=f, f1=f, p0=list(a_), p1=list(b_), w=1.0, col='#ff8a9a', a=0.9)
    FXL.e2(t='lines', f0=BF.JUMP0, f1=BF.JUMP1, mode='parallel', ang=90, n=30, a=0.85, col='#ffffff', who='P')
    FXL.flash(BF.JUMP0, 'white', a=0.8)
    FXL.cam.shake(BF.JUMP0, amp=0.4, roll=2.0, decay=6, seed=5)
    FXL.grade(BF.JUMP0, BF.JUMP0 + 8, sat=1.1, contrast=1.1, vig=0.3, ramp=3)
    FXL.sfx.append((BF.JUMP0, 'boom', 4))
    # barrage: a fresh angle every 4 frames (two punches), shakes and stars on every blow
    az_list = [90, 150, 40, -90, 125, 70, 165]
    for i in range(7):
        f0 = BF.BAR0 + 4 * i - (1 if i else 0)
        f1 = BF.BAR0 + 4 * (i + 1)
        A(f0, f1, lambda f: [P.rig.head(f), D.rig.head(f), P.rig.sole(f, 'l'), D.rig.sole(f, 'l'), P.rig.sole(f, 'r'), D.rig.sole(f, 'r'), P.rig.fist(f, 'r'), P.rig.fist(f, 'l')],
          [dict(f=f0, az=az_list[i], el=(6 if i % 2 else -6), fill=0.86, fov=46, roll=(4 if i % 2 else -4), e='out', mind=8), dict(f=f1 - 1, az=az_list[i] + 6, el=2, fill=0.9, fov=40, roll=(3 if i % 2 else -3), mind=8)], lm, 0.85, 'barrage')
    for k in range(BF.NBAR):
        fh = BF.BAR0 + 2 * k
        limb = 'ra' if k % 2 == 0 else 'la'
        hit(fh, P, limb, (0, -1.0, 0), 2 if k % 4 == 3 else 1, d=(-1, 0.2, 0))
        FXL.trail('P', limb, (0, -1.0, 0), fh - 1, fh, col='#ffffff', w=0.2, k=2)
        FXL.sfx.append((fh, 'hit', 1))
        if k % 2 == 1:
            FXL.lines_radial(fh, fh + 1, D.rig.torso(fh), n=22, a=0.7, inner=0.12)
    FXL.e3(t='ghost', c='P', f0=BF.BAR0, f1=BF.WIND0 - 1, lags=[1, 2], col='#ff8a8a', a=0.28, decay=0.6)
    hurt(BF.BAR0, BF.HEROS + 30)
    # freeze: slow push-in, drained colour, a pulse ring
    A(BF.WIND0 - 1, BF.GRAB, lambda f: [P.rig.head(f), D.rig.head(f), P.rig.fist(f, 'r'), D.rig.torso(f)], [dict(f=BF.WIND0 - 1, az=95, el=-4, fill=0.74, fov=48, roll=-2, e='in', mind=5), dict(f=BF.GRAB - 1, az=90, el=0, fill=0.8, fov=38, roll=-4, mind=4)], lm, 0.9, 'freeze')
    FXL.grade(BF.WIND0 - 1, BF.GRAB, sat=0.25, contrast=1.35, vig=0.65, tint=(0.9, 0.95, 1.1), ramp=2)
    FXL.e3(t='ring', f0=BF.WIND0, f1=BF.WIND0 + 5, p=list(D.rig.torso(BF.WIND0)), n=[-1, 0, 0], r0=0.5, r1=7.0, w=0.4, col='#ffffff', a0=0.8, a1=0.0)
    FXL.aura('P', BF.WIND0, BF.GRAB, col='#ffe27a', a=0.6, scale=1.25, ramp=False)
    FXL.sfx.append((BF.WIND0, 'charge', 3))
    # the grab, the dive, the slam
    A(BF.GRAB, BF.DIVE0 + 2, lambda f: [P.rig.head(f), P.rig.fist(f, 'r'), D.rig.head(f)], [dict(f=BF.GRAB, az=72, el=2, fill=0.9, fov=34, roll=4, e='out', mind=3, cu=True), dict(f=BF.DIVE0 + 1, az=80, el=14, fill=0.9, fov=38, roll=5, mind=3, cu=True)], lm, 0.9, 'grab')
    FXL.impact(BF.GRAB, D.rig.head(BF.GRAB), (-1, 0, 0), s=2, flash='white')
    FXL.sfx.append((BF.GRAB, 'hit', 3))
    A(BF.DIVE0 + 2, BF.SLAM - 1, lambda f: [P.rig.head(f), D.rig.head(f), D.rig.sole(f, 'l'), D.rig.sole(f, 'r')], [dict(f=BF.DIVE0 + 2, az=100, el=36, fill=0.7, fov=66, roll=-5, e='in', mind=6), dict(f=BF.SLAM - 2, az=96, el=8, fill=0.7, fov=70, roll=3, mind=6)], lm, 0.55, 'dive')
    A(BF.SLAM - 1, BF.SLAM + 2, lambda f: [P.rig.head(f), D.rig.head(f), D.rig.sole(f, 'l'), P.rig.sole(f, 'r')], [dict(f=BF.SLAM - 1, az=88, el=-4, fill=0.7, fov=56, roll=0, mind=5), dict(f=BF.SLAM + 1, az=80, el=-2, fill=0.74, fov=50, roll=0, mind=5)], lm, 0.8, 'slam')
    FXL.e3(t='ghost', c='D', f0=BF.DIVE0, f1=BF.SLAM, lags=[1, 2, 3], col='#dfeaff', a=0.32, decay=0.7)
    FXL.e3(t='ghost', c='P', f0=BF.DIVE0, f1=BF.SLAM, lags=[1, 2, 3], col='#ff8a9a', a=0.5, decay=0.72)
    for f in range(BF.DIVE0, BF.SLAM + 1):
        a_, b_ = D.rig.torso(f - 1), D.rig.torso(f)
        FXL.e3(t='streak', f0=f, f1=f, p0=list(rg.add(a_, (0, 4.0, 0))), p1=list(b_), w=1.4, col='#ffffff', a=0.9)
    FXL.e2(t='lines', f0=BF.DIVE0, f1=BF.SLAM, mode='parallel', ang=90, n=34, a=0.9, col='#ffffff', who='D')
    FXL.e2(t='mblur', f0=BF.DIVE0, f1=BF.SLAM, who='D', len=26)
    FXL.grade(BF.DIVE0, BF.SLAM, sat=1.2, contrast=1.15, vig=0.4, tint=(1.05, 1.0, 0.95), ramp=2)
    cp = D.rig.head(BF.SLAM)
    END['crater_pt'] = cp
    FXL.impact(BF.SLAM, (cp[0], 0.5, cp[2]), (0, 1, 0), s=4, kind='crash', ground=True, debris=60, flash='impact')
    FXL.shockwave(BF.SLAM, (cp[0], 0, cp[2]), r=20.0, dur=12, h=3.6)
    FXL.shockwave(BF.SLAM + 2, (cp[0], 0, cp[2]), r=11.0, dur=9, wall=False, col='#bfe3ff')
    FXL.shockwave(BF.SLAM + 4, (cp[0], 0, cp[2]), r=26.0, dur=14, wall=False, col='#ffffff')
    FXL.dust_burst(BF.SLAM, (cp[0], 0, cp[2]), s=3.0, n=26, dur=18, spread=8.0)
    FXL.crack(BF.SLAM, (cp[0], 0, cp[2]), s=18.0, seed=21, keep=True, fade_at=620)
    FXL.crack(BF.SLAM + 1, (cp[0], 0, cp[2]), s=26.0, seed=7, rot=1.0, keep=True, fade_at=620)
    FXL.e2(t='ca', f0=BF.SLAM, f1=BF.SLAM + 8, amt=18.0)
    FXL.e2(t='flash', f0=BF.SLAM + 1, f1=BF.SLAM + 3, kind='white', a=1.0)
    FXL.grade(BF.SLAM + 3, BF.SLAM + 30, sat=0.9, contrast=1.1, vig=0.4, ramp=8)
    FXL.cam.shake(BF.SLAM, amp=0.9, roll=4.0, decay=10, seed=99)
    FXL.sfx.append((BF.SLAM, 'boom', 4))
    hurt(BF.HEROS, 630)


# ===================================================================== BEAT 14 : aftermath, outro
def direct_outro():
    lm = lv((-1, 0, 0))
    cp = END['crater_pt']
    A(BF.SLAM + 2, 565, lambda f: [P.rig.head(f), P.rig.sole(f, 'r'), D.rig.sole(f, 'l'), D.rig.head(f)], [
        dict(f=BF.SLAM + 2, az=84, el=2, fill=0.7, fov=54, roll=0, e='out', mind=10), dict(f=555, az=70, el=14, fill=0.55, fov=56, roll=-2, mind=14), dict(f=564, az=60, el=22, fill=0.5, fov=58, roll=-3, mind=16)], lm, 0.6, 'crater-crane')
    for f in range(BF.SLAM + 3, BF.SLAM + 22, 3):
        FXL.dust_burst(f, (cp[0] + (f - BF.SLAM) * 0.1, 0, cp[2]), s=1.6, n=10, dur=14, spread=6.0, rise=2.0)
    FXL.e3(t='debris', f0=BF.SLAM + 3, f1=BF.SLAM + 30, p=[cp[0], 0.3, cp[2]], n=18, size=[0.2, 0.6], speed=10, seed=88, life=1.4, grav=24, up=1.0, flat=0.7, col='#9aa4b8')
    # P rises, walks off; wide pull-back
    A(565, 596, lambda f: [P.rig.head(f), P.rig.sole(f, 'l'), P.rig.sole(f, 'r'), D.rig.sole(f, 'l')], [dict(f=565, az=60, el=18, fill=0.55, fov=58, roll=-3, e='io', mind=16), dict(f=595, az=100, el=8, fill=0.6, fov=54, roll=1, mind=14)], lm, 0.6, 'walk-away')
    A(596, 612, lambda f: [P.rig.head(f), P.rig.sole(f, 'l'), P.rig.sole(f, 'r')], [dict(f=596, az=-118, el=-6, fill=0.7, fov=52, roll=-3, e='io', mind=8), dict(f=611, az=-96, el=-8, fill=0.72, fov=46, roll=2, mind=7)], lm, 0.7, 'turn')
    # closing hero shot facing the lens: warm grade, name tag, title
    A(612, 630, lambda f: [P.rig.head(f), P.rig.sole(f, 'l'), P.rig.sole(f, 'r'), P.rig.fist(f, 'l')], [dict(f=612, az=-90, el=-12, fill=0.74, fov=46, roll=-2, e='out', mind=7), dict(f=629, az=-86, el=-6, fill=0.68, fov=40, roll=0, mind=7)], lm, 0.8, 'hero-end')
    FXL.grade(596, 630, sat=1.15, contrast=1.1, vig=0.45, tint=(1.04, 1.0, 0.94), ramp=12)
    tag(606, 629, fade=1)
    FXL.text(614, 630, '@Mr_HB', pos=(0.5, 0.86), size=0.2, col='#ffffff', anim='pop')
    FXL.sparkle(618, 622, P.rig.head(618), r=0.6)
    FXL.sfx.append((612, 'boom', 1))
    # the dummy is back for a final twitch of the leg
    hurt(BF.HEROS, 630)


def direct_all2():
    direct_kicks()
    direct_blink()
    direct_hammer()
    direct_heli()
    direct_pillars()
    direct_juggle()
    direct_charge()
    direct_sky()
    direct_outro()
