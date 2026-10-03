"""BEAT 5 - calm / beckon (f114-124) and BEAT 6 - freestyle kick flurry (f124-176):
slide sweep -> front-flip axe kick -> pop-up -> side kick -> spinning hook kick -> cartwheel -> double drop-kick.

Yaw bookkeeping: both actors finished the air beat with a full turn already wound into their yaw, so this module works in
YPC / YDC (= heading + 360) and keeps every later turn continuous (no unwinding between keys)."""
import math

import choreo as C
from choreo import P, D, H, Hr, Rm, Rx, Ry, Rz, unwrap, wobble, YP, YD, GUARD, contact, author
import rig as rg
import r6
from beat_air import sm, eo, L, CRASH

YPC = YP + 360.0
YDC = YD + 360.0
PZ = 0.6
XD = 23.4                      # dummy stands here after the pop-up
KS, KF, KSIDE, KHOOK, KDROP = 128, 134, 141, 146, 159
CRASH_LAST = CRASH + 12
END = {}


@author
def beat_calm():
    x = D.rig.root(CRASH_LAST)[0]
    prev = tuple(D.cell('hrp'))
    D.k(116, 'out', ra=(90, 0, 40), la=(10, 0, 70))
    D.k(117, 'out', ra=(30, 0, 40))
    pop = [(118, -76, 'out'), (119, -34, 'out'), (120, 16, 'out'), (121, -5, 'io'), (122, 0, 'io')]
    for f, pit, e in pop:
        a = f - 118
        yaw = YDC + 50 * (1 - sm(a / 4.0))                    # the dummy untwists to face the player as it springs up
        cell = unwrap(prev, Hr(x - 0.15 * a, 0.0 if pit < -10 else 3.0, D.rig.root(CRASH_LAST)[2], Rm(Ry(yaw), Rx(pit)))); prev = cell
        D.k(f, e, hrp=cell, t=(-2, 0, 0), h=(8, 0, 0), ra=(10 + wobble(a, 28, 4, 3), 0, 14), la=(10 - wobble(a, 28, 4, 3), 0, 14), rl=(0, 0, 3), ll=(0, 0, 3))
    for i, f in enumerate((124, 127)):
        D.k(f, 'io', hrp=H(XD, 0, PZ - 0.6, YDC), t=(1.5 * (-1) ** i, 2, 0), h=(1.2 * (-1) ** i, 0, 0), ra=(6, 0, 6), la=(6, 0, 6))
    # player stands, rolls the neck, beckons with the lead hand, drops into guard
    px = 20.2
    P.k(116, 'io', hrp=H(px, 0, PZ, YPC), t=(4, 10, 0), h=(-4, -8, 0), ra=(10, 0, 10), la=(10, 0, 10), ll=(0, 0, 5), rl=(0, 0, 5))
    P.k(118, 'io', t=(2, -16, 0), h=(0, 18, -8), ra=(8, 0, 12), la=(104, 0, 16))
    P.k(120, 'io', h=(0, 18, 8), la=(92, 0, 26))
    P.k(121, 'out', la=(108, 0, 14))
    P.k(123, 'io', hrp=H(px + 0.3, 0, PZ, YPC), t=(14, 30, 0, 0, -0.38), h=(8, -28, 0), la=GUARD['la'], ra=GUARD['ra'], ll=GUARD['ll'], rl=GUARD['rl'])
    P.plant([116, 123])


@author
def beat_flurry():
    xd, yD = XD, PZ - 0.6
    # =============================================================== dummy script
    prev = tuple(D.cell('hrp'))
    # (f128) swept off its feet: rolls onto its side and hangs horizontally in the air
    seq = [(KS, 0.15, -14), (KS + 1, 1.2, -48), (KS + 2, 2.1, -80), (KS + 3, 2.5, -96), (KS + 4, 2.6, -102), (KS + 5, 2.6, -104), (KS + 6, 2.5, -106)]
    for i, (f, y, roll) in enumerate(seq):
        cell = unwrap(prev, Hr(xd + 0.12 * i, y, yD, Rm(Ry(YDC), Rz(roll)))); prev = cell
        D.k(f, 'lin', hrp=cell, t=(-6 + wobble(i, 8, 5, 4), 0, 0), h=(-14 + wobble(i, 10, 5, 4), 0, 0),
            ra=(48 + wobble(i, 12, 4, 4), 0, 50), la=(40 + wobble(i, 12, 4, 4, 1), 0, 56), rl=(-8, 0, 4), ll=(-12, 0, 4))
    # (f134) axe kick slams it into the floor; two bounces; pops upright
    for i, (f, y, roll) in enumerate([(KF, 2.4, -106), (KF + 1, 0.2, -92), (KF + 2, 1.9, -96), (KF + 3, 0.2, -90), (KF + 4, 0.9, -80)]):
        cell = unwrap(prev, Hr(xd + 0.9 + 0.12 * i, y, yD, Rm(Ry(YDC), Rz(roll)))); prev = cell
        D.k(f, 'lin', hrp=cell, t=(20 if i == 0 else -4, 0, 0), h=(18 if i == 0 else -10, 0, 0), ra=(40, 0, 60 - 6 * i), la=(34, 0, 66 - 6 * i), rl=(10, 0, 8), ll=(4, 0, 10))
    for f, roll, y, e in [(KF + 5, -40, 1.6, 'out'), (KF + 6, -8, 1.8, 'out')]:
        cell = unwrap(prev, Hr(xd + 1.6, y, yD, Rm(Ry(YDC), Rz(roll)))); prev = cell
        D.k(f, e, hrp=cell, t=(-2, 0, 0), h=(4, 0, 0), ra=(20, 0, 24), la=(20, 0, 24), rl=(0, 0, 3), ll=(0, 0, 3))
    # (f141) side kick to the chest: slides back on its heels, stiff and leaning
    xs = xd + 1.7
    D.k(KSIDE, 'lin', hrp=H(xs, 0.05, yD, YDC, pitch=-10), t=(-26, 0, 0), h=(-30, 0, 0), ra=(46, 0, 50), la=(52, 0, 56), rl=(12, 0, 4), ll=(8, 0, 4))
    D.k(KSIDE + 1, 'lin', hrp=H(xs + 0.12, 0.08, yD, YDC, pitch=-12), t=(-30, 0, 0), h=(-34, 0, 0))
    for i, f in enumerate(range(KSIDE + 2, KSIDE + 4)):
        D.k(f, 'out', hrp=H(xs + 0.9 + 0.7 * i, 0, yD, YDC, pitch=-10 + 3 * i), t=(-14 + 4 * i, 0, 0), h=(-14 + 4 * i, 0, 0), ra=(30 - 6 * i, 0, 36), la=(34 - 6 * i, 0, 40))
    # (f146) hook kick to the head: head whips round, the body spins like a top while sliding, then settles
    xh = xs + 2.6
    D.k(KHOOK - 1, 'out', hrp=H(xh, 0, yD, YDC, pitch=0), t=(2, 0, 0), h=(0, 0, 0), ra=(10, 0, 14), la=(10, 0, 14), rl=(0, 0, 3), ll=(0, 0, 3))
    spin_end = 0.0
    for i, f in enumerate(range(KHOOK, KHOOK + 7)):
        spin = 140 * 2.4 * (1 - math.exp(-(i + 1) * 0.55))
        spin_end = spin
        D.k(f, 'lin', hrp=H(xh + 0.45 * (i + 1), 0, yD, YDC + spin, pitch=-4, roll=10), t=(6, 40, 6), h=(8, 86 if i < 3 else 20, 14),
            ra=(40 + wobble(i, 14, 4, 6), 0, 66), la=(-20 + wobble(i, 14, 4, 6, 1), 0, 60), rl=(8, 0, 4), ll=(-6, 0, 4))
    D.k(KHOOK + 7, 'out', hrp=H(xh + 3.6, 0, yD, YDC + spin_end + 20, pitch=0), t=(1, 4, 0), h=(0, 6, 0), ra=(8, 0, 14), la=(8, 0, 14), rl=(0, 0, 3), ll=(0, 0, 3))
    xk = xh + 3.6
    yaw_k = YDC + spin_end + 20
    # (f159) double drop-kick: thrown back horizontally, lands and slides
    D.k(KDROP - 1, 'io', hrp=H(xk, 0, yD, yaw_k), t=(0, 0, 0), h=(0, 0, 0))
    D.k(KDROP, 'lin', hrp=H(xk + 0.3, 0.2, yD, yaw_k, pitch=-8), t=(-36, 0, 0), h=(-40, 0, 0), ra=(70, 0, 56), la=(76, 0, 60), rl=(26, 0, 4), ll=(18, 0, 4))
    D.k(KDROP + 1, 'lin', hrp=H(xk + 0.4, 0.25, yD, yaw_k, pitch=-10), t=(-40, 0, 0), h=(-44, 0, 0))
    prev = tuple(D.cell('hrp'))
    for i, f in enumerate(range(KDROP + 2, KDROP + 8)):
        t_ = i / 18.0
        y = 3.4 + 5.0 * t_ - 0.5 * 52 * t_ * t_
        cell = unwrap(prev, Hr(xk + 0.9 + 1.55 * i, max(y, 0.5), yD, Rm(Ry(yaw_k + 20 * i), Rx(-70 - 10 * min(i, 3)), Ry(-30 * i)))); prev = cell
        D.k(f, 'lin', hrp=cell, t=(-12 + wobble(i, 8, 5, 6), 0, 0), h=(-34 + wobble(i, 12, 4.5, 6), 6, 0), ra=(78 + wobble(i, 14, 4, 6), 0, 62), la=(66 + wobble(i, 14, 4, 6, 1), 0, 70), rl=(18, 0, 6), ll=(8, 0, 6))
    xe = xk + 0.9 + 1.55 * 5 + 1.0
    for i, f in enumerate(range(KDROP + 8, KDROP + 14)):
        cell = unwrap(prev, Hr(xe + [0.9, 1.6, 2.1, 2.45, 2.65, 2.75][i], [0.5, 1.0, 0.5, 0.15, 0.0, 0.0][i], yD, Rm(Ry(yaw_k + 130), Rx(-86 - i)))); prev = cell
        D.k(f, 'lin' if i < 3 else 'out', hrp=cell, t=(-4, 0, 0), h=(-24 + wobble(i, 8, 4, 4), 6, 0), ra=(60, 0, 80 - 3 * i), la=(54, 0, 86 - 3 * i), rl=(10, 0, 18 + 2 * i), ll=(4, 0, 22 + 2 * i))
    END['xland'] = xe + 2.75
    END['dummy_yaw'] = yaw_k + 130

    # =============================================================== player script
    px = 20.5
    P.k(125, 'out', hrp=H(px + 1.0, 0.1, PZ, YPC, pitch=18), t=(8, 30, 0), h=(-6, -20), ra=(-20, 0, 10), la=(70, 0, 10), ll=(46, 0, 8), rl=(-40, 0, 12))
    # (f128) slide-sweep: drop low, supporting hand on the floor, leg whips round at shin height
    P.k(KS - 1, 'in', hrp=H(px + 0.6, 0, PZ, YPC, pitch=6), t=(44, -24, 0, 0, -1.2), h=(-18, 18), ra=(24, 0, -2), la=(80, 0, 54), ll=(66, 0, 12), rl=(92, 0, 72))
    P.k(KS, 'lin', hrp=H(px + 1.1, 0, PZ, YPC, pitch=8), t=(46, -30, 0, 0, -1.3), ra=(20, 0, -4), rl=(92, 0, -10))
    P.k(KS + 1, 'out', hrp=H(px + 1.5, 0, PZ, YPC, pitch=4), t=(40, -10, 0, 0, -1.2), rl=(88, 0, -30))
    # spring into a front flip carrying P over the hovering dummy; heel drops on its belly at f134
    flips = [(KS + 2, 1.0, 0, 'out'), (KS + 3, 3.4, 100, 'lin'), (KS + 4, 5.0, 190, 'lin'), (KS + 5, 5.4, 262, 'lin'), (KF, 4.9, 318, 'lin'), (KF + 1, 3.0, 352, 'out')]
    for f, y, pit, e in flips:
        P.k(f, e, hrp=H(px + 2.6 + 0.5 * (f - KS - 2), y, PZ, YPC, pitch=pit), t=(10, 0, 0), h=(-10, 0), ra=(120, 0, 28), la=(120, 0, 28),
            ll=(70 if f < KF else 20, 0, 6), rl=(70 if f < KF else 110, 0, 6))
    P.k(KF + 2, 'io', hrp=H(px + 4.2, 0.0, PZ, YPC, pitch=360), t=(30, 14, 0, 0, -0.9), h=(10, -12), ra=(40, 0, 24), la=(40, 0, 24), ll=(60, 0, 12), rl=(60, 0, 12))
    P.k(KF + 4, 'out', hrp=H(px + 4.2, 0.0, PZ, YPC, pitch=360), t=(14, 24, 0, 0, -0.4), h=(8, -24), la=GUARD['la'], ra=GUARD['ra'], ll=GUARD['ll'], rl=GUARD['rl'])
    # (f141) side kick: turn side-on (left side to the target), chamber, thrust with the lead leg, torso leaning away
    P.k(KF + 6, 'io', hrp=H(px + 4.6, 0, PZ, YPC + 70, pitch=360), t=(0, 10, 10), h=(0, -60), ra=(80, 0, 50), la=(80, 0, 50), ll=(40, 0, 50), rl=(0, 0, 8))
    P.k(KSIDE, 'lin', hrp=H(px + 5.4, 0.0, PZ, YPC + 90, pitch=360), t=(0, 0, 26), h=(0, -70), ra=(70, 0, 80), la=(30, 0, 70), ll=(0, 0, 84), rl=(0, 0, 10))
    P.k(KSIDE + 1, 'lin', ll=(0, 0, 86))
    P.k(KSIDE + 3, 'out', hrp=H(px + 5.8, 0.0, PZ, YPC + 20, pitch=360), t=(14, 20, 0, 0, -0.4), h=(8, -20), la=GUARD['la'], ra=GUARD['ra'], ll=GUARD['ll'], rl=GUARD['rl'])
    # (f146) spinning hook kick: a full turn finishing with a high heel
    P.k(KHOOK - 2, 'in', hrp=H(px + 7.2, 0.0, PZ, YPC + 160, pitch=360), t=(10, 30, 0, 0, -0.4), h=(0, -30), ra=(90, 0, 40), la=(90, 0, 40), ll=(30, 0, 8), rl=(-20, 0, 10))
    P.k(KHOOK, 'lin', hrp=H(px + 8.3, 0.2, PZ, YPC + 360, pitch=360), t=(-8, -26, -22), h=(0, 30), ra=(70, 0, 80), la=(50, 0, 70), ll=(10, 0, 8), rl=(100, 0, -34))
    P.k(KHOOK + 1, 'lin', rl=(100, 0, -38))
    YP2 = YPC + 360
    P.k(KHOOK + 3, 'out', hrp=H(px + 8.8, 0.0, PZ, YP2, pitch=360), t=(16, 20, 0, 0, -0.4), h=(8, -20), ra=(90, 0, 30), la=(90, 0, 30), ll=(30, 0, 8), rl=(36, 0, 10))
    # cartwheel (f150-153) toward the dummy, then a leap into a double drop-kick (f159)
    cx = px + 9.0
    P.k(KHOOK + 3 + 1, 'in', hrp=H(cx, 0, PZ, YP2 + 90, pitch=360), t=(10, 0, 0, 0, -0.5), h=(0, 0), ra=(120, 0, 30), la=(120, 0, 30), ll=(20, 0, 20), rl=(20, 0, 20))
    for i, f in enumerate(range(150, 154)):
        y = [1.2, 3.8, 3.8, 1.2][i]
        P.k(f, 'lin', hrp=H(cx + 1.15 * (i + 1), y, PZ, YP2 + 90, pitch=360, roll=-(i + 1) * 90), ra=(170, 0, 60), la=(170, 0, 60), ll=(0, 0, 70), rl=(0, 0, 70), t=(0, 0, 0), h=(0, 0))
    P.k(154, 'out', hrp=H(cx + 5.2, 0.0, PZ, YP2 + 90, pitch=360, roll=-360), t=(30, 0, 0, 0, -0.8), h=(10, 0), ra=(30, 0, 20), la=(30, 0, 20), ll=(50, 0, 12), rl=(50, 0, 12))
    P.k(155, 'out', hrp=H(cx + 5.4, 0.0, PZ, YP2, pitch=360, roll=0), t=(36, 0, 0, 0, -1.0), h=(10, 0), ra=(20, 0, 20), la=(20, 0, 20), ll=(64, 0, 12), rl=(64, 0, 12))
    P.k(157, 'in', hrp=H(cx + 5.8, 1.7, PZ, YP2, pitch=330, roll=0), t=(-10, 0, 0), h=(-18, 0), ra=(70, 0, 30), la=(70, 0, 30), ll=(16, 0, 8), rl=(16, 0, 8))
    P.k(KDROP, 'lin', hrp=H(cx + 6.8, 1.9, PZ, YP2, pitch=288), t=(-4, 0, 0), h=(-10, 0), ra=(30, 0, 50), la=(30, 0, 50), ll=(10, 0, 10), rl=(10, 0, 10))
    P.k(KDROP + 1, 'lin', hrp=H(cx + 6.9, 1.9, PZ, YP2, pitch=288))
    P.k(KDROP + 4, 'out', hrp=H(cx + 7.6, 0.4, PZ, YP2, pitch=264), t=(-6, 0, 0), ra=(40, 0, 60), la=(40, 0, 60), ll=(8, 0, 12), rl=(8, 0, 12))
    P.k(KDROP + 7, 'io', hrp=H(cx + 8.2, 0.0, PZ, YP2, pitch=340), t=(30, 10, 0, 0, -0.9), h=(-10, 0), ra=(30, 0, 24), la=(30, 0, 24), ll=(40, 0, 14), rl=(70, 0, 14))
    P.k(KDROP + 11, 'io', hrp=H(cx + 8.6, 0.0, PZ, YP2, pitch=360), t=(14, 24, 0, 0, -0.4), h=(8, -24), la=GUARD['la'], ra=GUARD['ra'], ll=GUARD['ll'], rl=GUARD['rl'])
    END['yp2'] = YP2
    END['px'] = cx + 8.6
    P.plant([f for f in (KS - 1, KS, KS + 1, KF + 2, KF + 4, KSIDE, KSIDE + 3, KHOOK - 2, KHOOK, KHOOK + 3, 154, 155, KDROP + 7, KDROP + 11) if float(f) in P.clip['keys']])

    # =============================================================== contacts
    contact(KS, P, 'rl', D, 'll', (0, -0.5, -0.5), name='sweep', tip=(0, -0.85, 0), win=0)
    contact(KF, P, 'rl', D, 't', (0, 0.2, -0.5), name='front-flip axe kick', tip=(0, -1.0, 0), air=True)
    contact(KSIDE, P, 'll', D, 't', (0, 0.1, -0.5), name='side kick', tip=(0, -0.9, 0))
    contact(KHOOK, P, 'rl', D, 'h', (0.3, 0, -0.45), name='spinning hook kick', tip=(0, -0.9, 0))
    contact(KDROP, P, 'll', D, 't', (-0.3, 0.1, -0.5), name='drop-kick L', tip=(0, -1.0, 0), air=True)
    contact(KDROP, P, 'rl', D, 't', (0.3, 0.1, -0.5), name='drop-kick R', tip=(0, -1.0, 0), air=True)
