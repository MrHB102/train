"""BEAT 7 - BLINK STEPS (f170-222): the player teleports around the dummy, a different strike from a different side each time,
ending with a double palm blast.  BEAT 8 - HAMMER THROW (f222-282): ankle grab, three revolutions with the dummy at arm's length,
release across the arena.  The dummy is ATTACHED to the player's hands during the spin: its pose is computed from the player's."""
import math

import choreo as C
from choreo import (P, D, H, Hr, Rm, Rx, Ry, Rz, unwrap, wobble, YP, YD, GUARD, contact, author, hide, yaw_near, yaw_of, Rbasis, Rspin)
import rig as rg
import r6
from beat_air import sm, eo, L
from beat_kicks import END, KDROP

# blink hit frames
B1, B2, B3, B4, B5, B6 = 182, 187, 192, 197, 202, 208
POP0 = 174
STAND = dict(t=(0, 0, 0), h=(0, 0, 0), ra=(6, 0, 6), la=(6, 0, 6), rl=(0, 0, 3), ll=(0, 0, 3))

# --- player hit poses (character frame; each is the full extension, because a teleporting fighter appears mid-strike)
POSE = {
    'cross': dict(t=(14, -46, 0, 0, -0.5), h=(8, 40), ra=(92, 0, -4), la=(108, 0, -40), ll=(46, 0, 8), rl=(-44, 0, 12)),
    'chop': dict(t=(12, 44, 0, 0, -0.4), h=(6, -34), la=(90, 0, -22), ra=(106, 0, -34), ll=(44, 0, 8), rl=(-40, 0, 12)),
    'axe': dict(t=(-12, 0, 0), h=(10, 0), ra=(50, 0, 56), la=(60, 0, 56), ll=(-10, 0, 8), rl=(40, 0, 4)),
    'round': dict(t=(-6, -20, -18), h=(0, 24), ra=(80, 0, 52), la=(60, 0, 60), ll=(8, 0, 8), rl=(92, 0, -26)),
    'upper': dict(t=(-14, -38, 0, 0, 0.1), h=(14, 30), ra=(168, 0, 6), la=(104, 0, -36), ll=(-26, 0, 8), rl=(26, 0, 10)),
    'palm': dict(t=(10, 0, 0), h=(0, 0, 0), ra=(92, 0, 6), la=(92, 0, 6), ll=(40, 0, 8), rl=(-36, 0, 8)),
}


def look(pos, tgt, ref):
    return yaw_near(yaw_of(tgt[0] - pos[0], tgt[2] - pos[1]), ref)


def p_hit(f, kind, pos, y, tgt, pitch=0.0, push=0.12, extra=None):
    yaw = look(pos, tgt, P.cell('hrp')[1])
    d = rg.unit((tgt[0] - pos[0], 0, tgt[2] - pos[1]))
    cells = dict(POSE[kind])
    if extra: cells.update(extra)
    P.k(f, 'lin', hrp=H(pos[0], y, pos[1], yaw, pitch=pitch), **cells)
    P.k(f + 1, 'lin', hrp=H(pos[0] + d[0] * push, y, pos[1] + d[2] * push, yaw, pitch=pitch))
    P.k(f + 2, 'lin', hrp=H(pos[0] + d[0] * push * 1.4, y, pos[1] + d[2] * push * 1.4, yaw, pitch=pitch))


def d_pose(f, pos, y=0.0, yaw=-90.0, pitch=0.0, roll=0.0, ease='lin', **cells):
    c = dict(STAND); c.update(cells)
    D.k(f, ease, hrp=H(pos[0], y, pos[1], yaw_near(yaw, D.cell('hrp')[1]), pitch=pitch, roll=roll), **c)


@author
def beat_blink():
    xL, zL = END['xland'], 0.0
    # ---------------------------------------------------------------- dummy pops up where it landed (head-direction slerp from lying to upright)
    f_lie = KDROP + 13
    hd0 = rg.unit(rg.sub(D.rig.head(f_lie), D.rig.torso(f_lie)))
    prev = tuple(D.cell('hrp'))
    for i, f in enumerate(range(POP0, POP0 + 5)):
        u = [0.18, 0.5, 0.95, 1.08, 1.0][i]
        hd = rg.unit(rg.lerp(hd0, (0, 1, 0), min(u, 1.0)))
        fr = rg.unit(rg.lerp((0, 1, 0), (-1, 0, 0), min(u, 1.0)))
        cell = unwrap(prev, Hr(xL - 0.1 * i, 0.0 if u < 0.9 else 3.0 + (0.4 if u > 1.0 else 0), zL, Rbasis(hd, fr))); prev = cell
        D.k(f, 'out', hrp=cell, t=(-2, 0, 0), h=(8, 0, 0), ra=(10 + wobble(i, 28, 4, 3), 0, 14), la=(10 - wobble(i, 28, 4, 3), 0, 14), rl=(0, 0, 3), ll=(0, 0, 3))
    d_pose(POP0 + 6, (xL - 0.5, zL), ease='io')
    D.k(POP0 + 8, 'io', hrp=H(xL - 0.5, 0, zL, D.cell('hrp')[1]), t=(1.2, 2, 0), h=(1, 0, 0))
    DC = [xL - 0.5, zL]                                    # dummy's floor position, updated by every hit
    yawD = D.cell('hrp')[1]

    # ---------------------------------------------------------------- player: advance, then blink around the dummy
    xp = P.rig.root(KDROP + 11)[0]
    P.k(172, 'in', hrp=H(xp + 1.8, 0.1, 0.6, P.cell('hrp')[1], pitch=16), t=(8, 30, 0), h=(-6, -20), ra=(-20, 0, 10), la=(70, 0, 10), ll=(46, 0, 8), rl=(-40, 0, 12))
    P.k(177, 'out', hrp=H(DC[0] - 3.2, 0, 0.5, P.cell('hrp')[1]), t=(14, 30, 0, 0, -0.38), h=(8, -28, 0), la=GUARD['la'], ra=GUARD['ra'], ll=GUARD['ll'], rl=GUARD['rl'])
    P.plant([177])
    dummy_dir = lambda p: rg.unit((DC[0] - p[0], 0, DC[1] - p[1]))

    def push(d, k):
        DC[0] += d[0] * k; DC[1] += d[2] * k

    R_ = 2.3
    # 1) from behind: cross to the back
    hide(178, 181)
    pos = (DC[0] + R_, DC[1] + 0.3); p_hit(B1, 'cross', pos, 0.0, (DC[0], 0, DC[1]))
    d = dummy_dir(pos); push(d, 0.5)
    d_pose(B1, DC, yaw=yawD, t=(34, 0, 0), h=(-30, 0, 0), ra=(-34, 0, 30), la=(-38, 0, 34), rl=(-14, 0, 4), ll=(-10, 0, 4))
    d_pose(B1 + 1, (DC[0] + d[0] * 0.1, DC[1]), yaw=yawD, t=(40, 0, 0), h=(-36, 0, 0))
    d_pose(B1 + 3, DC, yaw=yawD, ease='out', t=(10, 0, 0), h=(0, 0, 0))
    hide(B1 + 3, B1 + 4)
    # 2) from its left: chop to the flank
    pos = (DC[0] + 0.4, DC[1] + R_); p_hit(B2, 'chop', pos, 0.0, (DC[0], 0, DC[1]))
    d = dummy_dir(pos); push(d, 0.5)
    d_pose(B2, DC, yaw=yawD, t=(6, 30, 18), h=(0, 40, 22), ra=(60, 0, 60), la=(-20, 0, 30), roll=6)
    d_pose(B2 + 1, DC, yaw=yawD, t=(6, 34, 20), h=(0, 44, 24), roll=7)
    d_pose(B2 + 3, DC, yaw=yawD, ease='out')
    hide(B2 + 3, B2 + 4)
    # 3) from above: axe kick on the crown
    pos = (DC[0] - 1.0, DC[1] + 0.2); p_hit(B3, 'axe', pos, 4.3, (DC[0], 0, DC[1]), pitch=14, push=0.0)
    d_pose(B3, DC, y=-0.35, yaw=yawD, t=(26, 0, 0), h=(44, 0, 0), ra=(150, 0, 40), la=(154, 0, 44), rl=(-6, 0, 12), ll=(-6, 0, 12))
    d_pose(B3 + 1, DC, y=-0.5, yaw=yawD, t=(30, 0, 0), h=(48, 0, 0))
    d_pose(B3 + 3, DC, yaw=yawD, ease='out')
    hide(B3 + 3, B3 + 4)
    # 4) from its right: roundhouse to the ribs
    pos = (DC[0] + 0.3, DC[1] - R_); p_hit(B4, 'round', pos, 0.1, (DC[0], 0, DC[1]))
    d = dummy_dir(pos); push(d, 0.6)
    d_pose(B4, DC, yaw=yawD, t=(4, -30, -22), h=(4, -70, -20), ra=(-30, 0, 30), la=(60, 0, 66), roll=-8)
    d_pose(B4 + 1, DC, yaw=yawD, t=(4, -34, -24), h=(4, -76, -22), roll=-9)
    d_pose(B4 + 3, DC, yaw=yawD, ease='out')
    hide(B4 + 3, B4 + 4)
    # 5) from the front: rising uppercut launches it a little
    pos = (DC[0] - R_, DC[1] - 0.2); p_hit(B5, 'upper', pos, 0.6, (DC[0], 0, DC[1]))
    d = dummy_dir(pos); push(d, 0.5)
    d_pose(B5, DC, y=0.9, yaw=yawD, pitch=-10, t=(-26, 0, 0), h=(-54, 0, 0), ra=(70, 0, 40), la=(76, 0, 44), rl=(20, 0, 4), ll=(14, 0, 4))
    d_pose(B5 + 1, DC, y=1.7, yaw=yawD, pitch=-14, t=(-30, 0, 0), h=(-58, 0, 0))
    d_pose(B5 + 3, DC, y=2.0, yaw=yawD, pitch=-6, t=(-8, 0, 0), h=(-10, 0, 0), ease='out')
    d_pose(B5 + 5, DC, y=0.0, yaw=yawD, pitch=0, ease='in')
    hide(B5 + 3, B5 + 5)
    # 6) double palm blast from behind: sends it flying across the arena toward the centre
    pos = (DC[0] + R_, DC[1] + 0.2); p_hit(B6, 'palm', pos, 0.0, (DC[0], 0, DC[1]), pitch=8, push=0.3)
    d = dummy_dir(pos)
    d_pose(B6, DC, yaw=yawD, t=(50, 0, 0), h=(-40, 0, 0), ra=(-40, 0, 20), la=(-44, 0, 24), rl=(-20, 0, 4), ll=(-16, 0, 4))
    d_pose(B6 + 1, (DC[0] - 0.1, DC[1]), y=0.15, yaw=yawD, t=(56, 0, 0), h=(-44, 0, 0))
    # flight toward -X: face-down, arms trailing, then a skid
    xs0 = DC[0] - 0.4
    prev = tuple(D.cell('hrp'))
    for i, f in enumerate(range(B6 + 2, B6 + 9)):
        t_ = i / 18.0
        y = 3.2 + 2.0 * t_ - 0.5 * 30 * t_ * t_
        hd = rg.unit(rg.lerp((-1, 0.2, 0), (-1, -0.1, 0), i / 6.0)); fr = rg.unit(rg.lerp((0.4, 1, 0), (0, 1, 0), i / 6.0))
        cell = unwrap(prev, Hr(xs0 - 1.9 * (i + 1), max(y, 0.55), DC[1], Rspin(Rbasis(hd, fr), 20 * i))); prev = cell
        D.k(f, 'lin', hrp=cell, t=(10 + wobble(i, 8, 5, 6), 0, 0), h=(-20 + wobble(i, 12, 4.5, 6), 6, 0), ra=(-60 + wobble(i, 14, 4, 6), 0, 40), la=(-66 + wobble(i, 14, 4, 6, 1), 0, 46), rl=(10, 0, 6), ll=(4, 0, 6))
    x_land = xs0 - 1.9 * 7
    for i, f in enumerate(range(B6 + 9, B6 + 14)):
        cell = unwrap(prev, Hr(x_land - [0.9, 1.5, 1.9, 2.15, 2.3][i], [0.5, 0.2, 0.0, 0.0, 0.0][i], DC[1], Rbasis((-1, 0.05, 0), (0, 1, 0)))); prev = cell
        D.k(f, 'lin' if i < 2 else 'out', hrp=cell, t=(-4, 0, 0), h=(-24 + wobble(i, 8, 4, 4), 6, 0), ra=(60, 0, 80 - 3 * i), la=(54, 0, 86 - 3 * i), rl=(10, 0, 18 + 2 * i), ll=(4, 0, 22 + 2 * i))
    END['dlie'] = (x_land - 2.3, DC[1])
    # player: palm follow-through, relax, then walk after it
    P.k(B6 + 5, 'out', hrp=H(pos[0] - 0.2, 0, pos[1], P.cell('hrp')[1], pitch=4), t=(14, 20, 0, 0, -0.4), h=(8, -20), la=GUARD['la'], ra=GUARD['ra'], ll=GUARD['ll'], rl=GUARD['rl'])
    END['blink_pos'] = pos

    # contacts (the solver nudges the attacker so the tip lands; the DC bookkeeping above is only the dummy's own path)
    contact(B1, P, 'ra', D, 't', (0, 0.2, 0.5), name='blink 1 cross (back)', win=0)
    contact(B2, P, 'la', D, 't', (-0.5, 0.2, 0.0), name='blink 2 chop (left flank)', win=0)
    contact(B3, P, 'rl', D, 'h', (0, 0.55, 0.0), name='blink 3 axe kick (crown)', tip=(0, -1.0, 0), air=True, win=0)
    contact(B4, P, 'rl', D, 't', (0.5, 0.3, 0.0), name='blink 4 roundhouse (ribs)', tip=(0, -0.85, 0), win=0)
    contact(B5, P, 'ra', D, 'h', (0, -0.3, -0.45), name='blink 5 uppercut (chin)', win=0)
    contact(B6, P, 'ra', D, 't', (0.35, 0.2, 0.5), name='blink 6 palm R', win=0)
    contact(B6, P, 'la', D, 't', (-0.35, 0.2, 0.5), name='blink 6 palm L', win=0)


# ====================================================================================== BEAT 8 - hammer throw
SP0 = 228          # first spin frame
SP1 = 246          # release frame
GRAB = 225


@author
def beat_hammer():
    xl, zl = END['dlie']
    # player runs to the dummy's feet, grabs both ankles, hoists, spins 2.75 turns, releases toward -X
    pos0 = END['blink_pos']
    hdg_to = lambda a, b: yaw_of(b[0] - a[0], b[1] - a[1])
    cx, cz = xl + 4.6, zl                               # player pivots here (dummy's ankles are 4.9 studs from the pivot), feet planted
    yaw0 = yaw_near(-90.0, P.cell('hrp')[1])             # facing -X, at the dummy's feet (its feet end is toward +X)
    P.k(214, 'out', hrp=H(pos0[0] - 3.0, 0.2, pos0[1], yaw_near(-90.0, P.cell('hrp')[1]), pitch=34), t=(0, 0, 0), h=(-30, 0), ra=(-40, 0, 12), la=(-30, 0, 12), ll=(40, 0, 6), rl=(-42, 0, 6))
    for i, f in enumerate(range(216, 223)):
        P.p(f, 'lin', rl=(40 if i % 2 else -40, 0, 6), ll=(-40 if i % 2 else 40, 0, 6))
    P.k(223, 'out', hrp=H(cx + 0.8, 0.0, cz, yaw0, pitch=22), t=(26, 0, 0, 0, -0.5), h=(-24, 0), ra=(70, 0, 8), la=(70, 0, 8), ll=(52, 0, 8), rl=(-50, 0, 8))
    P.k(GRAB, 'out', hrp=H(cx, 0.0, cz, yaw0), t=(48, 0, 0, 0, -1.0), h=(-34, 0), ra=(52, 0, 4), la=(52, 0, 4), ll=(54, 0, 10), rl=(-40, 0, 12))   # stoops to the ankles
    P.plant([GRAB])
    # --- spin: P pivots on the spot; its heading advances faster each frame
    n = SP1 - SP0
    raw = [(i + 1) ** 1.3 for i in range(n + 1)]
    rates = [r * 990.0 / sum(raw) for r in raw]            # 990 deg in total (2.75 turns): the release heading is 180, so the tangent is -X
    P.k(SP0 - 1, 'lin', hrp=H(cx, 0.0, cz, yaw0), t=(36, 0, 0, 0, -0.8), ra=(70, 0, 4), la=(70, 0, 4))
    theta = yaw0
    thetas = {}
    for i in range(n + 1):
        theta += rates[i]
        thetas[SP0 + i] = theta
    # the dummy hangs from the hands (grip point) with its body along the radial direction
    r_grip = 1.9
    dpos = {}
    for i in range(n + 1):
        f = SP0 + i
        th = thetas[f]
        k = i / n
        lean = -10 - 28 * sm(min(1.0, k * 1.6))
        P.k(f, 'lin', hrp=H(cx, 0.0, cz, th), t=(lean, 0, 0, 0, -0.3), h=(-6, 0), ra=(88, 0, 4), la=(88, 0, 4), ll=(30, 0, 14), rl=(-26, 0, 16))
    P.plant([SP0 + i for i in range(0, n + 1, 3)])
    prev = tuple(D.cell('hrp'))
    # (rebuild d during hoist) frames GRAB..SP0: dummy lifted from the floor by the hands
    for f in range(GRAB, SP1 + 1):
        if f < SP0:
            u = (f - GRAB) / (SP0 - GRAB)
            th = yaw0; lift = 0.4 + 2.0 * sm(u); tilt = -20 * u
        else:
            i = f - SP0; th = thetas[f]; k = i / n
            lift = 2.4 + 1.6 * sm(k); tilt = 18 * sm(k) - 4
        dir_ = (math.sin(th * math.pi / 180), 0.0, -math.cos(th * math.pi / 180))
        grip = (cx + dir_[0] * r_grip, 3.0 if f >= SP0 else 1.4 + 1.6 * (f - GRAB) / max(SP0 - GRAB, 1), cz + dir_[2] * r_grip)
        head_dir = rg.unit((dir_[0], math.sin(tilt * math.pi / 180), dir_[2]))
        # body centre = grip + 3 studs along the body (feet are in the hands)
        cen = (grip[0] + head_dir[0] * 3.0, max(grip[1] + head_dir[1] * 3.0 - (0 if f >= SP0 else 0.0), 0.6), grip[2] + head_dir[2] * 3.0)
        front = rg.unit(rg.lerp((0, 1, 0), (-dir_[2], 0.4, dir_[0]), 0.6))
        cell = unwrap(prev, Hr(cen[0], cen[1], cen[2], Rspin(Rbasis(head_dir, front), 0))); prev = cell
        a = f - GRAB
        D.k(f, 'lin', hrp=cell, t=(6 + wobble(a, 6, 5, 20), 0, 0), h=(-30 + wobble(a, 12, 4.4, 14), 0, 0), ra=(-70 + wobble(a, 16, 4, 14), 0, 30), la=(-76 + wobble(a, 16, 4, 14, 1), 0, 36), rl=(0, 0, 4), ll=(0, 0, 4))
        dpos[f] = cen
    # --- release: flies along the tangent (-X) with its last spin, lands far away and slides
    th = thetas[SP1]
    tang = (math.cos(th * math.pi / 180), 0.0, math.sin(th * math.pi / 180))
    cen = dpos[SP1]
    vx = -2.4
    prev = tuple(D.cell('hrp'))
    for i, f in enumerate(range(SP1 + 1, SP1 + 11)):
        t_ = (i + 1) / 18.0
        x = cen[0] + vx * (i + 1) * 1.0
        y = max(cen[1] + 3.0 * t_ - 0.5 * 24 * t_ * t_, 0.55)
        cell = unwrap(prev, Hr(x, y, cen[2], Rspin(Rbasis((-1, 0.1, 0), (0, 1, 0)), 36 * (i + 1)))); prev = cell
        D.k(f, 'lin', hrp=cell, t=(10 + wobble(i, 8, 5, 6), 0, 0), h=(-20 + wobble(i, 12, 4.5, 6), 6, 0), ra=(-60 + wobble(i, 14, 4, 6), 0, 40), la=(-66 + wobble(i, 14, 4, 6, 1), 0, 46), rl=(10, 0, 6), ll=(4, 0, 6))
    x_end = cen[0] + vx * 11
    for i, f in enumerate(range(SP1 + 11, SP1 + 17)):
        cell = unwrap(prev, Hr(x_end - [1.0, 1.8, 2.4, 2.8, 3.0, 3.1][i], [0.8, 0.3, 0.0, 0.0, 0.0, 0.0][i], cen[2], Rbasis((-1, 0.05, 0), (0, 1, 0)))); prev = cell
        D.k(f, 'lin' if i < 2 else 'out', hrp=cell, t=(-4, 0, 0), h=(-24 + wobble(i, 8, 4, 4), 6, 0), ra=(60, 0, 80 - 3 * i), la=(54, 0, 86 - 3 * i), rl=(10, 0, 18 + 2 * i), ll=(4, 0, 22 + 2 * i))
    END['hammer_land'] = (x_end - 3.1, cen[2])
    # player after the release: follow-through, then recovers and strides after it
    P.k(SP1 + 1, 'out', hrp=H(cx, 0.0, cz, thetas[SP1] + 40), t=(-30, 0, 0, 0, -0.3), ra=(80, 0, 4), la=(80, 0, 4))
    P.k(SP1 + 5, 'io', hrp=H(cx, 0.0, cz, thetas[SP1] + 90), t=(14, 20, 0, 0, -0.4), h=(8, -20), la=GUARD['la'], ra=GUARD['ra'], ll=GUARD['ll'], rl=GUARD['rl'])
    END['p_after_hammer'] = (cx, cz, thetas[SP1] + 90)
    contact(GRAB, P, 'ra', D, 'll', (0, -0.9, 0), name='grab ankle R', tip=(0, -1.0, 0), win=0)
    contact(GRAB, P, 'la', D, 'rl', (0, -0.9, 0), name='grab ankle L', tip=(0, -1.0, 0), win=0)
