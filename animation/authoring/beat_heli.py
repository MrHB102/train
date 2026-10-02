"""BEAT 9 - HELICOPTER (f246-312): long speed-dash after the thrown dummy, handspring into a handstand spin (three leg sweeps at head
height), handspring out, rising dragon uppercut that corkscrews up with the dummy, bicycle kick at the apex that knocks it across the arena.

The player arrives from the +X side, so "toward the dummy" is -X here (S = -1)."""
import math

import choreo as C
from choreo import (P, D, H, Hc, Hr, Rm, Rx, Ry, Rz, unwrap, wobble, YP, YD, GUARD, contact, author, hide, yaw_near, yaw_of, Rbasis, Rspin)
import rig as rg
import r6
from beat_air import sm, eo, L
from beat_kicks import END
import beat_blink as BB

S = -1.0                              # world sign of the direction player -> dummy
H1, H2, H3 = 270, 273, 276            # helicopter leg sweeps
UP = 285                              # rising uppercut
BIKE = 296                            # bicycle kick
SPIN0 = 267


def face(dx, dz, ref):
    return yaw_near(yaw_of(dx, dz), ref)


@author
def beat_heli():
    lx, lz = END['hammer_land']                 # where the dummy lies after the throw
    cx0, cz0, pyaw = END['p_after_hammer']
    DZ = lz
    DX = lx
    # ================================================================= dummy
    f_lie = BB.SP1 + 16
    hd0 = rg.unit(rg.sub(D.rig.head(f_lie), D.rig.torso(f_lie)))
    prev = tuple(D.cell('hrp'))
    for i, f in enumerate(range(260, 265)):
        u = [0.18, 0.5, 0.95, 1.08, 1.0][i]
        hd = rg.unit(rg.lerp(hd0, (0, 1, 0), min(u, 1.0))); fr = rg.unit(rg.lerp((0, 1, 0), (-S, 0, 0), min(u, 1.0)))   # ends facing the player (+X)
        cell = unwrap(prev, Hr(DX + 0.1 * i, 0.0 if u < 0.9 else 3.0 + (0.4 if u > 1.0 else 0), DZ, Rbasis(hd, fr))); prev = cell
        D.k(f, 'out', hrp=cell, t=(-2, 0, 0), h=(8, 0, 0), ra=(10 + wobble(i, 28, 4, 3), 0, 14), la=(10 - wobble(i, 28, 4, 3), 0, 14), rl=(0, 0, 3), ll=(0, 0, 3))
    yawD = yaw_near(90.0, D.cell('hrp')[1])                         # facing +X, at the player
    DXc = DX + 0.4
    BB.d_pose(266, (DXc, DZ), yaw=yawD, ease='io')
    # three head-height sweeps spin it and shove it along (toward -X)
    yaw_acc = D.cell('hrp')[1]
    for k, f in enumerate((H1, H2, H3)):
        yaw_acc += 110
        px_ = DXc + S * 0.25 * (k + 1)
        BB.d_pose(f, (px_, DZ), yaw=yaw_acc, t=(4, 36, 14), h=(6, 84 if k % 2 == 0 else -84, 18), ra=(50, 0, 70), la=(-24, 0, 36), roll=6 * (1 if k % 2 == 0 else -1))
        BB.d_pose(f + 1, (px_ + S * 0.12, DZ), yaw=yaw_acc + 30, t=(4, 40, 14), h=(6, 88 if k % 2 == 0 else -88, 18))
        BB.d_pose(f + 2, (px_ + S * 0.2, DZ), yaw=yaw_acc + 100, ease='out', t=(2, 10, 4), h=(2, 20, 6))
    DXs = DXc + S * 0.75
    yaw_fin = yaw_acc + 220
    BB.d_pose(UP - 2, (DXs, DZ), yaw=yaw_fin, ease='io', t=(0, 0, 0), h=(0, 0, 0))
    # uppercut launch: rises to an apex at f295 (low gravity = hang time), tumbling lazily
    g, v0 = 44.0, 26.0
    prevc = tuple(D.cell('hrp'))
    dpath = {}
    for i, f in enumerate(range(UP, BIKE)):
        t_ = i / 18.0
        y = 3.2 + v0 * t_ - 0.5 * g * t_ * t_
        hd = rg.unit((-S * (0.1 + 0.05 * i), 1, 0)); fr = rg.unit((S * 0.0 - S, 0.25, 0))
        cell = unwrap(prevc, Hr(DXs + S * 0.18 * i, y, DZ, Rspin(Rbasis(hd, fr), 6 * i))); prevc = cell
        D.k(f, 'lin', hrp=cell, t=(-26 + 2 * i + wobble(i, 8, 5, 7), 0, 0), h=(-54 + 3 * i + wobble(i, 12, 4.6, 7), 0, 0), ra=(70 + wobble(i, 18, 4.4, 8), 0, 40),
            la=(76 + wobble(i, 18, 4.8, 8, 1), 0, 44), rl=(20 + wobble(i, 14, 4.2, 8), 0, 4), ll=(14 + wobble(i, 14, 4.6, 8, 2), 0, 4))
        dpath[f] = (DXs + S * 0.18 * i, y)
    xA, yA = dpath[BIKE - 1]
    # bicycle kick: knocked flat toward -X, spinning on its long axis, lands and slides
    D.k(BIKE, 'lin', hrp=Hr(xA + S * 0.6, yA + 0.1, DZ, Rbasis((-S * 0.5, 1, 0), (-S, 0.2, 0))), t=(-40, 0, 0), h=(-60, 0, 0), ra=(80, 0, 60), la=(86, 0, 64), rl=(30, 0, 4), ll=(24, 0, 4))
    D.k(BIKE + 1, 'lin', t=(-44, 0, 0), h=(-64, 0, 0))
    prev = tuple(D.cell('hrp'))
    for i, f in enumerate(range(BIKE + 2, BIKE + 9)):
        t_ = (i + 1) / 18.0
        y = max(yA + 1.0 * t_ - 0.5 * 40 * t_ * t_, 0.55)
        cell = unwrap(prev, Hr(xA + S * (0.6 + 2.0 * (i + 1)), y, DZ, Rspin(Rbasis((S, 0.15, 0), (0, 1, 0)), 40 * (i + 1)))); prev = cell
        D.k(f, 'lin', hrp=cell, t=(8 + wobble(i, 8, 5, 6), 0, 0), h=(-20 + wobble(i, 12, 4.5, 6), 6, 0), ra=(-60 + wobble(i, 14, 4, 6), 0, 40), la=(-66 + wobble(i, 14, 4, 6, 1), 0, 46), rl=(10, 0, 6), ll=(4, 0, 6))
    xe = xA + S * (0.6 + 2.0 * 7)
    for i, f in enumerate(range(BIKE + 9, BIKE + 15)):
        cell = unwrap(prev, Hr(xe + S * [0.9, 1.6, 2.1, 2.45, 2.65, 2.75][i], [0.8, 0.3, 0.0, 0.0, 0.0, 0.0][i], DZ, Rbasis((S, 0.05, 0), (0, 1, 0)))); prev = cell
        D.k(f, 'lin' if i < 2 else 'out', hrp=cell, t=(-4, 0, 0), h=(-24 + wobble(i, 8, 4, 4), 6, 0), ra=(60, 0, 80 - 3 * i), la=(54, 0, 86 - 3 * i), rl=(10, 0, 18 + 2 * i), ll=(4, 0, 22 + 2 * i))
    END['heli_land'] = (xe + S * 2.75, DZ)

    # ================================================================= player
    # speed-dash toward the dummy (starts right after the release)
    tx, tz = DXc - S * 3.0, DZ + 0.2                  # arrives on the +X side
    yaw_run = face(tx - cx0, tz - cz0, pyaw)
    P.k(250, 'out', hrp=H(cx0 - 0.4, 0.55, cz0, yaw_run, pitch=52), t=(0, 30, 0), h=(-48, -30), ra=(-42, 0, 24), la=(-58, 0, 16), rl=(-38, 0, 6), ll=(34, 0, 6))
    for i, f in enumerate(range(251, 261)):
        u = (f - 250) / 11.0
        e = 1 - (1 - u) ** 2
        P.k(f, 'lin', hrp=H(L(cx0, tx, e), 0.35 + 0.2 * (1 - u), L(cz0, tz, e), yaw_run, pitch=L(50, 26, u)), rl=((30, 0, 6) if i % 2 == 0 else (-40, 0, 6)),
            ll=((-40, 0, 6) if i % 2 == 0 else (34, 0, 6)), la=(-8 if f > 258 else -58, 0, 14))
    P.k(261, 'out', hrp=H(tx - S * 0.3, 0.0, tz, yaw_run, pitch=18), t=(8, 36, 0, 0, -0.6), h=(-14, -30), ra=(-30, 0, 20), la=(60, 0, 10), ll=(56, 0, 8), rl=(-56, 0, 8))
    # handspring into a handstand (f263-265)
    cx, cz = DXc - S * 2.1, DZ                         # pivot, 2.1 studs from the dummy on the +X side
    yaw_h = face(S, 0, P.cell('hrp')[1])
    P.k(263, 'in', hrp=H(cx - S * 0.6, 0.0, cz, yaw_h, pitch=0), t=(40, 0, 0, 0, -1.2), h=(-20, 0), ra=(100, 0, 14), la=(100, 0, 14), ll=(66, 0, 10), rl=(66, 0, 10))
    P.k(264, 'lin', hrp=H(cx - S * 0.2, 1.8, cz, yaw_h, pitch=90), t=(0, 0, 0), h=(-20, 0), ra=(150, 0, 14), la=(150, 0, 14), ll=(10, 0, 20), rl=(10, 0, 20))
    P.k(265, 'lin', hrp=H(cx, 2.6, cz, yaw_h, pitch=170), ra=(180, 0, 10), la=(180, 0, 10), ll=(0, 0, 60), rl=(0, 0, 60), h=(-30, 0, 0))
    # helicopter: 60 deg/frame; the right leg points along (cos th, sin th) in (x, z); align that with the dummy at H1, then every 3 frames a leg crosses it
    dxh, dzh = (DXs + S * 0.0) - cx, DZ - cz
    ang0 = math.degrees(math.atan2(dzh, dxh))
    rate = 60.0
    th_h1 = yaw_near(ang0, yaw_h + rate * (H1 - SPIN0) + 0.0)
    th_fn = lambda f: th_h1 + rate * (f - H1)
    for f in range(SPIN0, 279):
        P.k(f, 'lin', hrp=H(cx, -3.0, cz, th_fn(f), pitch=180), t=(0, 0, 0), h=(-30, 0, 0), ra=(180, 0, 10), la=(180, 0, 10), ll=(0, 0, 76), rl=(0, 0, 76))
    # handspring out (f279-281), crouch for the uppercut
    thend = th_fn(278)
    yaw_u = yaw_near(yaw_of(S, 0), thend + 40)
    P.k(279, 'lin', hrp=H(cx, 2.4, cz, thend + 20, pitch=235), ra=(150, 0, 14), la=(150, 0, 14), ll=(10, 0, 20), rl=(10, 0, 20), t=(0, 0, 0))
    P.k(280, 'lin', hrp=H(cx + S * 0.3, 1.4, cz, yaw_u, pitch=300), ra=(120, 0, 14), la=(120, 0, 14), ll=(40, 0, 10), rl=(40, 0, 10))
    P.k(281, 'out', hrp=H(cx + S * 0.7, 0.0, cz, yaw_u, pitch=360), t=(40, 0, 0, 0, -1.1), h=(-20, 0), ra=(-10, 0, 12), la=(-10, 0, 12), ll=(70, 0, 12), rl=(70, 0, 12))
    # dragon uppercut (f285): corkscrew up under the dummy, then ride it up
    P.k(283, 'in', hrp=H(DXs - S * 2.1, 0.0, DZ, yaw_u, pitch=360), t=(36, 20, 0, 0, -1.1), ra=(-24, 0, 12), la=(60, 0, 20), ll=(66, 0, 12), rl=(70, 0, 12))
    for i, f in enumerate(range(UP, BIKE)):
        t_ = i / 18.0
        yd = 3.2 + v0 * t_ - 0.5 * g * t_ * t_
        yp = max(1.4, min(yd - 1.9, 3.0 + 28 * t_ - 0.5 * 40 * t_ * t_))
        spin = 150 * (i + 1) if i < 4 else 600
        P.k(f, 'lin', hrp=Hc(DXs - S * 1.9 + S * 0.18 * i, yp + 1.0, DZ, yaw_u + spin, pitch=360 - 8 + 3 * i),
            t=(-14, 0, 0), h=(-10, 0, 0), ra=(172, 0, 6), la=(70, 0, 40), ll=(-14, 0, 6), rl=(24, 0, 8))
    # bicycle kick (f296): back-somersault, scissor legs; the heel meets the dummy at the top of the flip
    yb = yaw_u + 600
    ys = [yA - 1.4, yA - 1.6, yA - 1.5, yA - 1.2, yA - 1.0, yA - 1.4, yA - 2.4, yA - 3.8, yA - 5.6, yA - 7.2]
    for i, f in enumerate(range(BIKE - 4, BIKE + 6)):
        pit = 360 - [20, 60, 110, 160, 200, 250, 300, 345, 360, 360][i]
        P.k(f, 'lin' if i < 8 else 'out', hrp=Hc(xA - S * 1.5 + S * 0.35 * i, max(ys[i] + 1.0, 1.6), DZ, yb, pitch=pit), t=(0, 0, 0), h=(-10, 0), ra=(100, 0, 40), la=(100, 0, 40),
            ll=(50 if i < 3 else 150, 0, 6), rl=(100 if i in (4, 5) else 30, 0, 6))
    P.k(BIKE + 6, 'io', hrp=H(xA + S * 1.6, 0.0, DZ, yb, pitch=360), t=(30, 10, 0, 0, -0.9), h=(-10, 0), ra=(30, 0, 24), la=(30, 0, 24), ll=(40, 0, 14), rl=(70, 0, 14))
    P.k(BIKE + 10, 'io', hrp=H(xA + S * 2.0, 0.0, DZ, yb, pitch=360), t=(14, 24, 0, 0, -0.4), h=(8, -24), la=GUARD['la'], ra=GUARD['ra'], ll=GUARD['ll'], rl=GUARD['rl'])
    END['heli_p'] = (xA + S * 2.0, DZ, yb)
    P.plant([261, 263, 281, 283, BIKE + 6, BIKE + 10])
    # ================================================================= contacts
    contact(H1, P, 'rl', D, 'h', (0.25, 0.0, 0.0), name='heli sweep 1 (R leg)', tip=(0, -1.0, 0), win=0)
    contact(H2, P, 'll', D, 'h', (-0.25, 0.0, 0.0), name='heli sweep 2 (L leg)', tip=(0, -1.0, 0), win=0)
    contact(H3, P, 'rl', D, 'h', (0.25, 0.0, 0.0), name='heli sweep 3 (R leg)', tip=(0, -1.0, 0), win=0)
    contact(UP, P, 'ra', D, 'h', (0, -0.3, -0.45), name='dragon uppercut', air=True, win=0)
    contact(BIKE, P, 'll', D, 't', (0, 0.0, -0.5), name='bicycle kick', tip=(0, -1.0, 0), air=True, win=0)
