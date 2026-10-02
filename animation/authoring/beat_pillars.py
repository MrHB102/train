"""BEAT 10 - ROCK PILLARS (f306-362): a calm confident walk, a stomp, and three stone pillars erupt around the dummy and launch it.
BEAT 11 - JUGGLE (f362-424): the dummy falls back to the player, who keeps it up with a knee, an instep kick, a header, a thigh,
a knee and a scooping lob that sends it far up into the sky.  The player is on the +X side of the dummy, so S = -1."""
import math

import choreo as C
from choreo import (P, D, H, Hc, Hr, Rm, Rx, Ry, Rz, unwrap, wobble, YP, YD, GUARD, contact, author, hide, yaw_near, yaw_of, Rbasis, Rspin)
import rig as rg
import r6
from beat_air import sm, eo, L
from beat_kicks import END
import beat_blink as BB

S = -1.0
PIL = [336, 341, 346]                    # pillar eruptions
TJ = [366, 372, 378, 384, 390, 396]      # juggle touches; the last is the lob
LOB = TJ[-1]


def phi_basis(phi_deg, yaw_face=1.0):
    """upright dummy flipped about the world Z axis by phi (deg): head and front rotate together in the XY plane"""
    a = math.radians(phi_deg)
    head = (-math.sin(a) * yaw_face, math.cos(a), 0.0)
    front = (math.cos(a) * yaw_face, math.sin(a) * yaw_face, 0.0)
    return Rbasis(head, front)


@author
def beat_pillars():
    xl, zl = END['heli_land']
    xP, zP, yawP = END['heli_p']
    END['pillars'] = []
    # =============================================================== dummy
    f_lie = 311
    hd0 = rg.unit(rg.sub(D.rig.head(f_lie), D.rig.torso(f_lie)))
    prev = tuple(D.cell('hrp'))
    for i, f in enumerate(range(322, 327)):
        u = [0.18, 0.5, 0.95, 1.08, 1.0][i]
        hd = rg.unit(rg.lerp(hd0, (0, 1, 0), min(u, 1.0))); fr = rg.unit(rg.lerp((0, 1, 0), (-S, 0, 0), min(u, 1.0)))
        cell = unwrap(prev, Hr(xl + 0.1 * i, 0.0 if u < 0.9 else 3.0 + (0.4 if u > 1.0 else 0), zl, Rbasis(hd, fr))); prev = cell
        D.k(f, 'out', hrp=cell, t=(-2, 0, 0), h=(8, 0, 0), ra=(10 + wobble(i, 28, 4, 3), 0, 14), la=(10 - wobble(i, 28, 4, 3), 0, 14), rl=(0, 0, 3), ll=(0, 0, 3))
    yawD = yaw_near(90.0, D.cell('hrp')[1])
    dx0 = xl + 0.4
    BB.d_pose(328, (dx0, zl), yaw=yawD, ease='io')
    D.k(333, 'io', hrp=H(dx0, 0, zl, yawD), t=(1.5, 2, 0), h=(1, 0, 0))
    D.k(PIL[0] - 1, 'io', hrp=H(dx0, 0, zl, yawD), t=(2, 3, 0), h=(1.5, 0, 0))
    # ballistic path through the three eruptions
    pts = {}
    f = PIL[0]
    x = dx0; y = 3.2; vx, vy = 0.0, 30.0
    g = 62.0
    dt = 1.0 / 18
    seq_end = TJ[0] - 4                                  # f362: still falling, handed to the juggle beat
    for f in range(PIL[0], seq_end + 1):
        pts[f] = (x, y, vx, vy)
        if f + 1 == PIL[1]:
            vx = -5.0 * 1.0; vy = vy - g * dt            # pillar 2 shoves it sideways (-X)
        elif f + 1 == PIL[2]:
            vy = 26.0                                    # pillar 3 under it
        else:
            vy -= g * dt
        x += vx * dt; y += vy * dt
    prev = tuple(D.cell('hrp'))
    n = seq_end - PIL[0]
    for f in range(PIL[0], seq_end + 1):
        x, y, vx_, vy_ = pts[f]
        a = f - PIL[0]
        phi = 720.0 * sm(a / n)
        cell = unwrap(prev, Hr(x, max(y, 0.8), zl, Rspin(phi_basis(phi, 1.0), 14 * a))); prev = cell
        D.k(f, 'lin', hrp=cell, t=(8 + wobble(a, 10, 5, 9), 0, 0), h=(-14 + wobble(a, 14, 4.5, 9), 6, 0), ra=(70 + wobble(a, 18, 4.2, 9), 0, 52 + wobble(a, 10, 5, 9)),
            la=(66 + wobble(a, 18, 4.6, 9, 1), 0, 56), rl=(14 + wobble(a, 14, 4.2, 9), 0, 8), ll=(8 + wobble(a, 14, 4.6, 9, 2), 0, 8))
    END['fall'] = dict(f=seq_end, pos=pts[seq_end][:2], v=pts[seq_end][2:], phi=720.0, x=pts[seq_end][0])
    END['pillars'] = [dict(f=PIL[0], p=(dx0, zl), h=6.0, w=1.7, rot=10, tilt=0, f1=PIL[0] + 6),
                      dict(f=PIL[1], p=(dx0 - S * 2.0, zl), h=9.5, w=1.6, rot=-15, tilt=-6 * S, f1=PIL[1] + 6),
                      dict(f=PIL[2], p=(pts[PIL[2]][0], zl), h=14.0, w=2.0, rot=22, tilt=0, f1=PIL[2] + 8)]

    # =============================================================== player
    # walk toward it while the dummy lies there (calm), stop at 7.5 studs, stomp, conduct the pillars with the hands
    stop_x = xl - S * 7.6
    yw = yaw_near(yaw_of(S, 0), yawP)
    P.k(306, 'out', hrp=H(xP, 0, zP, yw), t=(8, 20, 0, 0, -0.4), h=(0, -20), la=GUARD['la'], ra=GUARD['ra'], ll=GUARD['ll'], rl=GUARD['rl'])
    steps = list(range(309, 329, 3))
    for i, f in enumerate(steps):
        u = (f - 306) / 22.0
        x = L(xP, stop_x, sm(u))
        s_ = 1 if i % 2 == 0 else -1
        P.k(f, 'lin', hrp=H(x, 0, zP, yw), t=(6, 8 * s_, 0, 0, 0.0), h=(-2, -4 * s_), ra=(-22 * s_ + 8, 0, 8), la=(22 * s_ + 8, 0, 8), rl=(28 * s_, 0, 6), ll=(-28 * s_, 0, 6))
    P.k(329, 'out', hrp=H(stop_x, 0, zP, yw), t=(2, 12, 0), h=(-4, -10), ra=(8, 0, 10), la=(8, 0, 10), rl=(60, 0, 6), ll=(0, 0, 5))        # raises the knee
    P.k(330, 'in', hrp=H(stop_x, 0, zP, yw), t=(14, 12, 0, 0, -0.5), h=(4, -10), ra=(30, 0, 14), la=(20, 0, 14), rl=(10, 0, 8), ll=(30, 0, 8))   # stomp
    P.k(332, 'io', hrp=H(stop_x, 0, zP, yw), t=(2, 6, 0), h=(0, -6), ra=(30, 0, 24), la=(30, 0, 24), rl=(0, 0, 14), ll=(0, 0, 14))
    P.k(PIL[0], 'out', t=(-4, 10, 0), h=(-14, 0), ra=(130, 0, 22), la=(24, 0, 10))
    P.k(PIL[1], 'out', t=(-6, -10, 0), h=(-18, 0), ra=(150, 0, 26), la=(130, 0, 22))
    P.k(PIL[2], 'out', t=(-12, 0, 0), h=(-30, 0), ra=(172, 0, 18), la=(172, 0, 18), rl=(6, 0, 12), ll=(6, 0, 12))
    P.k(PIL[2] + 4, 'io', t=(-8, 0, 0), h=(-34, 0), ra=(120, 0, 30), la=(120, 0, 30))
    P.k(PIL[2] + 8, 'io', t=(8, 0, 0), h=(-30, 0), ra=(20, 0, 14), la=(20, 0, 14))
    P.plant([329, 330, 332, 328])
    # dash under the falling dummy (f352-362)
    jx = pts[seq_end][0]
    px_j = jx - S * 2.1
    P.k(PIL[2] + 9, 'in', hrp=H(stop_x, 0, zP, yw, pitch=30), t=(0, 30, 0), h=(-40, -26), ra=(-40, 0, 20), la=(-52, 0, 16), rl=(-38, 0, 6), ll=(34, 0, 6))
    for i, f in enumerate(range(PIL[2] + 10, seq_end + 1)):
        u = (f - PIL[2] - 9) / (seq_end - PIL[2] - 8)
        P.k(f, 'lin', hrp=H(L(stop_x, px_j, 1 - (1 - u) ** 2), 0.3 * (1 - u), zP, yw, pitch=L(34, 10, u)), rl=((30, 0, 6) if i % 2 == 0 else (-40, 0, 6)), ll=((-40, 0, 6) if i % 2 == 0 else (34, 0, 6)))
    END['juggle_x'] = (jx, px_j)


@author
def beat_juggle():
    fall = END['fall']
    jx, px_j = END['juggle_x']
    zl = END['heli_land'][1]
    f0 = fall['f']
    # =============================================================== dummy: hops off each touch (6 frames, ~1.7 stud apex), flipping 360 deg per hop
    y0 = 2.5
    x = fall['pos'][0]
    prev = tuple(D.cell('hrp'))
    phi = fall['phi']
    # finish the fall onto the first touch
    y = fall['pos'][1]; vy = fall['v'][1]; vx = fall['v'][0]
    dt = 1.0 / 18
    g = 62.0
    ev = {}
    f = f0
    touch_set = set(TJ)
    seq = []
    for f in range(f0 + 1, LOB + 1):
        if f in touch_set:
            vy = 10.3 if f != LOB else 10.3; vx = 0.0
            y = y0 if f != TJ[0] else y
            if f == TJ[0]: y = max(y, y0)
        else:
            vy -= g * dt
        x += vx * dt; y += vy * dt
        if f == TJ[0]: y = y0
        seq.append((f, x, max(y, y0 - 0.0), vy))
    n_all = len(seq)
    for i, (f, x_, y_, vy_) in enumerate(seq):
        a = f - f0
        phi_f = fall['phi'] + 60.0 * a
        cell = unwrap(prev, Hr(x_, y_, zl, Rspin(phi_basis(phi_f, 1.0), 12 * a))); prev = cell
        D.k(f, 'lin', hrp=cell, t=(8 + wobble(a, 10, 5, 12), 0, 0), h=(-14 + wobble(a, 14, 4.5, 12), 6, 0), ra=(70 + wobble(a, 18, 4.2, 12), 0, 52), la=(66 + wobble(a, 18, 4.6, 12, 1), 0, 56),
            rl=(14 + wobble(a, 14, 4.2, 12), 0, 8), ll=(8 + wobble(a, 14, 4.6, 12, 2), 0, 8))
    END['juggle_pts'] = {f: (x_, y_) for f, x_, y_, _ in seq}
    xt = seq[-1][1]
    # lob: shoots up, high in the sky, tumbles and then hangs
    prev = tuple(D.cell('hrp'))
    phi_l = fall['phi'] + 60.0 * (LOB - f0)
    y_hang = 36.0
    for i, f in enumerate(range(LOB + 1, 500)):
        a = i + 1
        if a <= 16:
            y = 2.5 + (y_hang - 2.5) * (1 - (1 - a / 16.0) ** 2.2)
        else:
            y = y_hang - 6.0 * sm(min(1.0, (a - 16) / 70.0))
        x_ = xt + S * 0.06 * a
        spin = phi_l + 40.0 * math.sqrt(a) * 6
        cell = unwrap(prev, Hr(x_, y, zl, Rspin(phi_basis(spin, 1.0), 8 * a))); prev = cell
        D.k(f, 'lin', hrp=cell, t=(8 + wobble(a, 10, 7, 30), 0, 0), h=(-14 + wobble(a, 14, 6, 30), 6, 0), ra=(70 + wobble(a, 18, 6, 30), 0, 52), la=(66 + wobble(a, 18, 6.5, 30, 1), 0, 56),
            rl=(14 + wobble(a, 14, 6, 30), 0, 8), ll=(8 + wobble(a, 14, 6.3, 30, 2), 0, 8))
    END['sky'] = (xt + S * 0.06 * (500 - LOB), y_hang - 6.0, zl)

    # =============================================================== player: keepy-uppy
    yw = P.cell('hrp')[1]
    pz = P.cell('hrp')[5] * -1
    base = dict(t=(6, 10, 0), h=(-12, -8), ra=(40, 0, 40), la=(40, 0, 40))
    px = px_j
    # touch poses (the planted leg is the other one); contacts solve the exact strike point
    def settle(f, **extra):
        P.k(f, 'out', hrp=H(px, 0, pz, yw), **{**dict(t=(8, 8, 0, 0, -0.2), h=(-18, -6), ra=(50, 0, 50), la=(50, 0, 50), ll=(0, 0, 8), rl=(0, 0, 8)), **extra})
    settle(f0 + 2)
    # T1 knee (rl)
    P.k(TJ[0] - 2, 'out', hrp=H(px, 0, pz, yw), t=(6, 8, 0, 0, -0.2), h=(-12, -6), ra=(46, 0, 46), la=(46, 0, 46), rl=(60, 0, 8), ll=(0, 0, 8))
    P.k(TJ[0], 'lin', hrp=H(px, 0.1, pz, yw), t=(-4, 8, 0, 0, 0.0), h=(-8, -6), rl=(98, 0, 6), ll=(0, 0, 8))
    P.k(TJ[0] + 2, 'out', hrp=H(px, 0, pz, yw), t=(8, 8, 0, 0, -0.2), rl=(20, 0, 8))
    # T2 instep kick with the left foot, hopping
    P.k(TJ[1] - 2, 'out', hrp=H(px, 0, pz, yw), ll=(-30, 0, 10), rl=(0, 0, 8), t=(10, 12, 0, 0, -0.3))
    P.k(TJ[1], 'lin', hrp=H(px, 0.1, pz, yw), t=(-2, 12, 0, 0, 0.0), ll=(84, 0, 8), rl=(0, 0, 8))
    P.k(TJ[1] + 2, 'out', hrp=H(px, 0, pz, yw), t=(8, 8, 0, 0, -0.2), ll=(10, 0, 8))
    # T3 header: jump under it, neck snapping
    P.k(TJ[2] - 2, 'in', hrp=H(px, 0, pz, yw), t=(18, 0, 0, 0, -0.7), h=(-6, 0), ra=(30, 0, 40), la=(30, 0, 40), ll=(40, 0, 10), rl=(40, 0, 10))
    P.k(TJ[2], 'lin', hrp=H(px, 1.5, pz, yw, pitch=-4), t=(-8, 0, 0), h=(24, 0), ra=(100, 0, 40), la=(100, 0, 40), ll=(-10, 0, 8), rl=(-10, 0, 8))
    P.k(TJ[2] + 2, 'out', hrp=H(px, 0.2, pz, yw), t=(8, 8, 0, 0, -0.2), h=(-10, 0), ra=(50, 0, 50), la=(50, 0, 50), ll=(10, 0, 8), rl=(10, 0, 8))
    # T4 thigh (rl, higher)
    P.k(TJ[3] - 2, 'out', hrp=H(px, 0, pz, yw), rl=(50, 0, 8), ll=(0, 0, 8), t=(8, 8, 0, 0, -0.2))
    P.k(TJ[3], 'lin', hrp=H(px, 0.1, pz, yw), t=(-4, 8, 0, 0, 0.0), rl=(92, 0, 12), ll=(0, 0, 8))
    P.k(TJ[3] + 2, 'out', hrp=H(px, 0, pz, yw), t=(8, 8, 0, 0, -0.2), rl=(20, 0, 8))
    # T5 knee (ll)
    P.k(TJ[4] - 2, 'out', hrp=H(px, 0, pz, yw), ll=(60, 0, 8), rl=(0, 0, 8))
    P.k(TJ[4], 'lin', hrp=H(px, 0.1, pz, yw), t=(-4, 8, 0, 0, 0.0), ll=(98, 0, 6), rl=(0, 0, 8))
    P.k(TJ[4] + 2, 'out', hrp=H(px, 0, pz, yw), t=(8, 8, 0, 0, -0.2), ll=(20, 0, 8))
    # T6 scooping lob: low scoop, whole body drives up
    P.k(LOB - 2, 'in', hrp=H(px, 0, pz, yw), t=(24, 0, 0, 0, -0.9), h=(-10, 0), ra=(-30, 0, 30), la=(-30, 0, 30), rl=(-30, 0, 8), ll=(54, 0, 12))
    P.k(LOB, 'lin', hrp=H(px, 0.2, pz, yw, pitch=-6), t=(-14, 0, 0), h=(-24, 0), ra=(150, 0, 30), la=(150, 0, 30), rl=(-20, 0, 8), ll=(92, 0, 4))
    P.k(LOB + 3, 'out', hrp=H(px, 0.0, pz, yw), t=(-10, 0, 0), h=(-34, 0), ra=(176, 0, 18), rl=(4, 0, 8), ll=(8, 0, 8), la=(100, 0, 20))
    P.k(LOB + 12, 'io', t=(-4, 0, 0), h=(-34, 0), ra=(176, 0, 18), la=(20, 0, 14))        # points at the sky
    # header: nudge the player so the head meets the dummy's belly on the touch frame
    tgt = D.rig.point(TJ[2], 't', (0, -0.1, -0.5)); g_ = rg.sub(tgt, P.rig.head(TJ[2]))
    P.nudge_root([TJ[2]], dx=g_[0] * 0.9, dy=g_[1] * 0.9, dz=g_[2] * 0.9)
    P.plant([f for f in (f0 + 2, TJ[0] - 2, TJ[0] + 2, TJ[1] - 2, TJ[1] + 2, TJ[2] + 2, TJ[3] - 2, TJ[3] + 2, TJ[4] - 2, TJ[4] + 2, LOB - 2, LOB + 3) if float(f) in P.clip['keys']])
    # =============================================================== contacts
    contact(TJ[0], P, 'rl', D, 't', (0, -0.1, -0.5), name='juggle 1 knee', tip=(0, -0.55, 0), win=0)
    contact(TJ[1], P, 'll', D, 't', (0, 0.1, 0.0), name='juggle 2 instep', tip=(0, -1.0, 0), win=0)
    contact(TJ[3], P, 'rl', D, 't', (0, 0.1, 0.0), name='juggle 4 thigh', tip=(0, -0.7, 0), win=0)
    contact(TJ[4], P, 'll', D, 't', (0, -0.1, -0.5), name='juggle 5 knee', tip=(0, -0.55, 0), win=0)
    contact(LOB, P, 'll', D, 't', (0, 0.0, 0.0), name='juggle 6 lob', tip=(0, -1.0, 0), win=0)
    END['header'] = TJ[2]
