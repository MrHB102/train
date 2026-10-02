"""BEAT 12 - FLOW CHARGE (f406-490): solo freestyle (540 spin kick, back-somersault, slide, power pose) while the dummy hangs in the sky.
BEAT 13 - SKY FINISHER (f490-541): super-leap, 14-punch barrage, freeze, face grab, dive and a head-first slam into the floor (impact f541).
BEAT 14 - AFTERMATH (f541-630): kneeling in the crater, rising, walking out of the dust, final stance.
The player is on the +X side of the dummy (S = -1)."""
import math

import choreo as C
from choreo import (P, D, H, Hc, Hr, Rm, Rx, Ry, Rz, unwrap, wobble, YP, YD, GUARD, contact, author, hide, yaw_near, yaw_of, Rbasis, Rspin)
import rig as rg
import r6
from beat_air import sm, eo, L
from beat_kicks import END
import beat_blink as BB
from beat_pillars import phi_basis, LOB

S = -1.0
SPIN0, SPIN1 = 410, 418
FLIP0, FLIP1 = 421, 427
SLIDE0, SLIDE1 = 428, 436
JUMP0, JUMP1 = 489, 497
BAR0, NBAR = 498, 14
WIND0 = BAR0 + 2 * NBAR + 1          # 527
GRAB = WIND0 + 5                     # 532
DIVE0, SLAM = GRAB + 1, GRAB + 8     # 533 .. 540
HEROS = SLAM + 1


@author
def beat_finale():
    sx, sy, sz = END['sky']
    jx, px_j = END['juggle_x']
    yw = P.cell('hrp')[1]
    pz = -P.cell('hrp')[5]
    # =============================================================== P: flow charge on the ground
    # spin kick (540 deg) with a high leg, no target: just energy
    P.k(SPIN0 - 1, 'in', hrp=H(px_j, 0, pz, yw), t=(20, 20, 0, 0, -0.6), h=(-14, -10), ra=(60, 0, 50), la=(60, 0, 50), ll=(40, 0, 12), rl=(-20, 0, 12))
    for i, f in enumerate(range(SPIN0, SPIN1 + 1)):
        u = (f - SPIN0) / (SPIN1 - SPIN0)
        yawf = yw + 540.0 * sm(u)
        hop = 0.8 * math.sin(math.pi * u)
        P.k(f, 'lin', hrp=H(px_j + S * 1.2 * sm(u), hop, pz, yawf), t=(-6, 0, -12), h=(0, 20), ra=(80, 0, 70), la=(60, 0, 70), ll=(8, 0, 8), rl=(96, 0, -20) if 3 <= i <= 6 else (30, 0, 12))
    yw1 = yw + 540.0
    # land in a crouch
    P.k(SPIN1 + 1, 'out', hrp=H(px_j + S * 1.2, 0, pz, yw1), t=(30, 0, 0, 0, -0.9), h=(-12, 0), ra=(30, 0, 30), la=(30, 0, 30), ll=(60, 0, 14), rl=(60, 0, 14))
    P.k(SPIN1 + 3, 'io', t=(26, 0, 0, 0, -0.8), ra=(34, 0, 34), la=(34, 0, 34))
    # back-somersault
    xb = px_j + S * 1.2
    P.k(FLIP0 - 1, 'in', hrp=H(xb, 0, pz, yw1), t=(34, 0, 0, 0, -1.0), ra=(-20, 0, 20), la=(-20, 0, 20), ll=(66, 0, 14), rl=(66, 0, 14))
    for i, f in enumerate(range(FLIP0, FLIP1 + 1)):
        u = (f - FLIP0) / (FLIP1 - FLIP0)
        P.k(f, 'lin', hrp=Hc(xb - S * 1.6 * u, 3.0 + 4.6 * math.sin(math.pi * u), pz, yw1, pitch=-360 * u), t=(10, 0, 0), h=(-10, 0), ra=(120, 0, 30), la=(120, 0, 30), ll=(80, 0, 8), rl=(80, 0, 8))
    P.k(FLIP1 + 1, 'out', hrp=H(xb - S * 1.8, 0, pz, yw1, pitch=-360), t=(28, 0, 0, 0, -0.9), ra=(30, 0, 24), la=(30, 0, 24), ll=(56, 0, 12), rl=(56, 0, 12))
    # slide-step
    xs0 = xb - S * 1.8
    for i, f in enumerate(range(SLIDE0, SLIDE1 + 1)):
        u = (f - SLIDE0) / (SLIDE1 - SLIDE0)
        P.k(f, 'lin', hrp=H(xs0 + S * 5.0 * (1 - (1 - u) ** 2), 0, pz, yw1, pitch=-360 + 14), t=(10, -30, 0, 0, -0.6), h=(-6, 30), ra=(-30, 0, 40), la=(80, 0, 40), ll=(70, 0, 10), rl=(-50, 0, 14))
    xe = xs0 + S * 5.0
    # power pose: fists clenched at the sides, legs wide, chest out
    yw2 = yw_near = yw1
    P.k(SLIDE1 + 3, 'out', hrp=H(xe, 0, pz, yw1, pitch=-360), t=(-4, 0, 0, 0, -0.5), h=(-30, 0), ra=(8, 0, 20), la=(8, 0, 20), ll=(0, 0, 22), rl=(0, 0, 22))
    for i, f in enumerate(range(SLIDE1 + 8, 482, 6)):
        k = 1 if i % 2 == 0 else -1
        P.k(f, 'io', hrp=H(xe, 0, pz, yw1, pitch=-360), t=(-4 + k, 0, 0, 0, -0.5 - 0.05 * k), h=(-32 + k, 0), ra=(8 + 2 * k, 0, 24 + 2 * k), la=(8 - 2 * k, 0, 24 - 2 * k), ll=(0, 0, 22), rl=(0, 0, 22))
    # sink to a crouch for the leap
    P.k(484, 'in', hrp=H(xe, 0, pz, yw1, pitch=-360), t=(30, 0, 0, 0, -1.0), h=(-34, 0), ra=(-20, 0, 18), la=(-20, 0, 18), ll=(62, 0, 16), rl=(62, 0, 16))
    P.k(488, 'io', t=(36, 0, 0, 0, -1.2), ra=(-30, 0, 20), la=(-30, 0, 20), ll=(70, 0, 18), rl=(70, 0, 18))
    P.plant([SPIN1 + 1, SPIN1 + 3, FLIP0 - 1, FLIP1 + 1, SLIDE1 + 3, 484, 488] + list(range(SLIDE1 + 8, 482, 6)))
    END['charge_pos'] = (xe, pz, yw1)

    # =============================================================== super-leap to the dummy (hanging at (sx, sy))
    # P rockets up the sky; face -X, fists leading
    # dummy keeps hanging (slow drift) until the barrage
    yawP = yaw_near(yaw_of(S, 0), yw1)
    p_hit_x = sx - S * 2.3
    for i, f in enumerate(range(JUMP0, JUMP1 + 1)):
        u = (f - JUMP0) / (JUMP1 - JUMP0)
        e = 1 - (1 - u) ** 2.4
        P.k(f, 'lin', hrp=Hc(L(xe, p_hit_x, e), L(3.0, sy, e), pz, yawP, pitch=-370), t=(-8, 0, 0), h=(-30, 0), ra=(-18, 0, 12), la=(-22, 0, 12), ll=(-20, 0, 6), rl=(-24, 0, 6))
    END['leap_to'] = (p_hit_x, sy)

    # =============================================================== barrage on the hanging dummy
    prevd = tuple(D.cell('hrp'))
    dx = sx
    dy = sy
    base_t = dict(t=(8, 0, 0), h=(-14, 0, 0))
    for k in range(NBAR):
        fh = BAR0 + 2 * k
        right = (k % 2 == 0)
        tw = 40 if right else -40
        dxk = dx + S * 0.2 * k
        jit = 0.1 * (1 if k % 2 else -1)
        # player: strike on the even frame, recover/chamber the other hand on the odd one
        px_ = dxk - S * 2.35
        yP = dy
        if right:
            P.k(fh, 'lin', hrp=Hc(px_, yP, pz, yawP), t=(10, -tw, 0), h=(4, 28), ra=(92, 0, -2), la=(100, 0, -34), ll=(14, 0, 14), rl=(-6, 0, 14))
            P.k(fh + 1, 'lin', hrp=Hc(px_ + S * 0.15, yP, pz, yawP), t=(10, -tw * 0.6, 0), ra=(84, 0, 0), la=(110, 0, -40))
        else:
            P.k(fh, 'lin', hrp=Hc(px_, yP, pz, yawP), t=(10, -tw, 0), h=(4, -28), la=(92, 0, -2), ra=(100, 0, -34), ll=(14, 0, 14), rl=(-6, 0, 14))
            P.k(fh + 1, 'lin', hrp=Hc(px_ + S * 0.15, yP, pz, yawP), t=(10, -tw * 0.6, 0), la=(84, 0, 0), ra=(110, 0, -40))
        # dummy: pinned in the air, jolting from each blow
        ph = 0.0
        fold = 24 + 6 * (k % 3)
        D.k(fh, 'lin', hrp=Hc(dxk + jit, dy + 0.1 * (k % 2), sz, yaw_near(90.0, prevd[1]), pitch=-6 * (k % 3)), t=(fold, 10 * (1 if right else -1), 6), h=(-30 + 10 * (k % 2), 14 * (1 if right else -1), 0),
            ra=(-40 + 10 * k % 30, 0, 40), la=(-30 - 6 * (k % 4), 0, 44), rl=(10, 0, 8), ll=(4, 0, 8))
        D.k(fh + 1, 'lin', hrp=Hc(dxk + jit + S * 0.1, dy, sz, yaw_near(90.0, prevd[1]), pitch=-4), t=(fold - 10, 0, 2), h=(-12, 0, 0), ra=(10, 0, 30), la=(14, 0, 34))
    dxe = dx + S * 0.2 * NBAR
    # freeze, windup: dummy left stunned and floating upright, P rears back; the face grab
    P.k(WIND0, 'out', hrp=Hc(dxe - S * 2.9, dy, pz, yawP), t=(14, 50, 0), h=(0, -30), ra=(-60, 0, 20), la=(100, 0, -30), ll=(20, 0, 14), rl=(-20, 0, 14))
    P.k(WIND0 + 3, 'lin', hrp=Hc(dxe - S * 3.0, dy, pz, yawP), t=(16, 56, 0), h=(0, -34), ra=(-66, 0, 24), la=(104, 0, -34))
    D.k(WIND0, 'out', hrp=Hc(dxe, dy + 0.6, sz, yaw_near(90.0, prevd[1]), pitch=0), t=(-6, 0, 0), h=(-24, 0, 0), ra=(20, 0, 34), la=(24, 0, 36), rl=(6, 0, 6), ll=(2, 0, 6))
    D.k(WIND0 + 3, 'io', hrp=Hc(dxe, dy + 0.9, sz, yaw_near(90.0, prevd[1]), pitch=-3), t=(-8, 0, 0), h=(-30, 0, 0))
    # grab: palm on the face
    P.k(GRAB, 'lin', hrp=Hc(dxe - S * 2.0, dy + 1.4, pz, yawP, pitch=14), t=(10, -30, 0), h=(0, 20), ra=(96, 0, 4), la=(-30, 0, 30), ll=(24, 0, 14), rl=(-20, 0, 14))
    D.k(GRAB, 'lin', hrp=Hc(dxe, dy + 0.9, sz, yaw_near(90.0, prevd[1]), pitch=-3), t=(-14, 0, 0), h=(-36, 0, 0), ra=(40, 0, 30), la=(36, 0, 32))
    # dive: P above, hand clamped on the face; dummy falls upright then flips head-first into the floor
    ydm = dy + 0.9
    yawd = yaw_near(90.0, D.cell('hrp')[1])
    prevd = tuple(D.cell('hrp'))
    for f in range(DIVE0, SLAM + 1):
        u = (f - GRAB) / float(SLAM - GRAB)
        y = L(ydm, 0.0, u * u * 1.0)
        x_ = dxe + S * 0.35 * (f - GRAB)
        flip = 0.0 if f < SLAM - 2 else 180.0 * sm((f - (SLAM - 3)) / 3.0)
        # dummy: upright, front toward P, flipping head-over about the Z axis at the end (head leads into the floor)
        cell = unwrap(prevd, Hr(x_, max(y, 0.3) if f < SLAM else 0.0, sz, Rspin(phi_basis(-flip, 1.0), 0))); prevd = cell
        D.k(f, 'lin', hrp=cell, t=(-14 + wobble(f - GRAB, 8, 4, 6), 0, 0), h=(-36 + wobble(f - GRAB, 10, 4, 6), 0, 0), ra=(60 + wobble(f - GRAB, 18, 3.6, 8), 0, 50), la=(54 + wobble(f - GRAB, 18, 3.9, 8, 1), 0, 56), rl=(16, 0, 8), ll=(10, 0, 8))
        yp = max(y + 4.1 * (1 - sm(max(0.0, (f - SLAM + 2) / 2.0))) + 0.5, 1.0)
        P.k(f, 'lin', hrp=Hc(x_ - S * 1.4, yp, pz, yawP, pitch=24 + 24 * u), t=(10, -20, 0), h=(-10, 20), ra=(120, 0, 4), la=(-50, 0, 40), ll=(-30, 0, 14), rl=(-40, 0, 14))
    # slam frame: P kneels on the dummy, palm still on the face
    x_s = dxe + S * 0.35 * (SLAM - GRAB)
    END['crater'] = (x_s, sz)
    P.k(HEROS, 'out', hrp=H(x_s - S * 1.5, 0.0, pz, yawP, pitch=0), t=(40, -20, 0, 0, -1.2), h=(-20, 20), ra=(70, 0, 4), la=(-30, 0, 30), ll=(80, 0, 14), rl=(-70, 0, 14))
    P.plant([HEROS])
    # the dummy rests head-down in the crater, legs up, then topples
    prevd = tuple(D.cell('hrp'))
    for i, f in enumerate(range(HEROS, HEROS + 8)):
        a = i
        flip = 180.0 + [0, -4, -12, -26, -44, -62, -76, -86][i] * 1.0
        cell = unwrap(prevd, Hr(x_s - S * 0.1 * i, 0.0, sz, phi_basis(-flip, 1.0))); prevd = cell
        D.k(f, 'lin' if i < 4 else 'out', hrp=cell, t=(-4 + wobble(a, 8, 5, 4), 0, 0), h=(-20 + wobble(a, 8, 4, 4), 4, 0), ra=(70, 0, 60 + 3 * a), la=(76, 0, 66 + 3 * a), rl=(-10 + wobble(a, 10, 5, 4), 0, 14 + 2 * a), ll=(-14 + wobble(a, 10, 5, 4, 1), 0, 18 + 2 * a))
    # it stays where it fell, face-down in the crater, with a last twitch of the legs
    x_f = x_s - S * 0.1 * 7
    for i, f in enumerate((HEROS + 12, HEROS + 24, HEROS + 40, 629)):
        D.k(f, 'io', hrp=Hr(x_f, 0.0, sz, phi_basis(-86.0, 1.0)), t=(-3, 0, 0), h=(-16 + 3 * (i % 2), 6, 0), ra=(70, 0, 80 + 2 * (i % 2)), la=(76, 0, 86), rl=(-10 + 6 * (i % 2), 0, 14 + 2 * (i % 2)), ll=(-14, 0, 18))

    # =============================================================== contacts
    for k in range(NBAR):
        fh = BAR0 + 2 * k
        limb = 'ra' if k % 2 == 0 else 'la'
        contact(fh, P, limb, D, 't', (0.15 * (1 if k % 2 else -1), 0.1 + 0.15 * (k % 3), -0.5), name='barrage %d' % (k + 1), air=True, win=0, slack=0.1)
    contact(GRAB, P, 'ra', D, 'h', (0, 0, -0.62), name='face grab', air=True, win=0, slack=0.0)
    for f in range(DIVE0, SLAM + 1):
        contact(f, P, 'ra', D, 'h', (0, 0.0, -0.62), name='face grab dive f%d' % f, air=True, win=0, slack=0.0)


@author
def beat_aftermath():
    xc, zc = END['crater']
    yawP = P.cell('hrp')[1]
    # kneeling in the crater, slow rise, nonchalant turn, walks out of the dust, final stance facing the camera
    P.k(HEROS + 8, 'io', hrp=H(xc - S * 1.5, 0.0, zc, yawP), t=(34, -20, 0, 0, -1.0), h=(-14, 20), ra=(60, 0, 8), la=(-24, 0, 30), ll=(76, 0, 14), rl=(-66, 0, 14))
    P.k(HEROS + 16, 'io', hrp=H(xc - S * 1.5, 0.0, zc, yawP), t=(20, -10, 0, 0, -0.7), h=(-10, 10), ra=(40, 0, 14), la=(10, 0, 20), ll=(50, 0, 12), rl=(-40, 0, 12))
    P.k(HEROS + 26, 'io', hrp=H(xc - S * 1.5, 0.0, zc, yawP), t=(6, 0, 0, 0, -0.1), h=(-4, 0), ra=(10, 0, 14), la=(10, 0, 14), ll=(4, 0, 10), rl=(4, 0, 10))
    # turns his back on the crater and strolls toward the camera side; stops for the closing pose
    yaw_end = yaw_near(180.0, yawP + 180)
    x_end = xc - S * 4.0
    for i, f in enumerate(range(HEROS + 30, 612, 3)):
        u = (f - (HEROS + 30)) / float(612 - (HEROS + 30))
        s_ = 1 if i % 2 == 0 else -1
        yawf = L(yawP, yaw_end, sm(min(1.0, u * 1.8)))
        P.k(f, 'lin', hrp=H(L(xc - S * 1.5, x_end, sm(u)), 0, L(zc, zc + 5.0, sm(u)), yawf), t=(4, 6 * s_, 0), h=(-2, -4 * s_), ra=(-18 * s_ + 6, 0, 8), la=(18 * s_ + 6, 0, 8), rl=(24 * s_, 0, 6), ll=(-24 * s_, 0, 6))
    # closing stance: weight on one hip, one hand up
    P.k(618, 'out', hrp=H(x_end, 0, zc + 5.0, yaw_end), t=(-4, -14, 0, 0, -0.1), h=(-6, 14, 4), ra=(22, 0, 24), la=(172, 0, 64), ll=(0, 0, 14), rl=(0, 0, 4))
    P.k(629, 'io', hrp=H(x_end, 0, zc + 5.0, yaw_end), t=(-5, -16, 0, 0, -0.12), h=(-8, 16, 5), ra=(24, 0, 26), la=(176, 0, 68), ll=(0, 0, 15), rl=(0, 0, 4))
    P.plant([618, 629])
    END['final'] = (x_end, zc + 5.0)
