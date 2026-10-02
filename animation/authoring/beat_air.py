"""BEAT 4 - AIR COMBO (f72-110): uppercut launch -> leap -> kick / back kick / roundhouse / flip kick -> double axe slam -> meteor crash."""
import math

import choreo as C
from choreo import P, D, H, Hc, Hr, Rm, Rx, Ry, Rz, unwrap, wobble, YP, YD, GUARD, contact, author
import rig as rg
import r6


def sm(a):
    a = max(0.0, min(1.0, a)); return a * a * (3 - 2 * a)


def eo(a):
    a = max(0.0, min(1.0, a)); return 1 - (1 - a) ** 2


def L(a, b, t):
    return a + (b - a) * t


# frames of the five air strikes + slam and crash
K1, K2, K3, K4, K5 = 84, 87, 90, 94, 99
CRASH = 102
Z = 0.0


@author
def beat_air():
    # ------------------------------------------------------------------ dummy first (the player is placed relative to it)
    x0 = 17.7
    prev = tuple(D.cell('hrp'))
    dpath = {}

    def dkey(f, x, y, yaw=YD, pitch=0.0, roll=0.0, ease='lin', **limbs):
        nonlocal prev
        cell = Hr(x, y, Z, Rm(Ry(yaw), Rx(pitch), Rz(roll)))
        cell = unwrap(prev, cell); prev = cell
        D.k(f, ease, hrp=cell, **limbs)
        dpath[f] = (x, y)

    # launch: rises to an apex at f83 (ballistic), tumbling back, limbs trailing
    for f in range(73, 84):
        t = (f - 72) / 18.0
        y = 3.5 + 27.8 * t - 22.75 * t * t
        x = x0 + 0.25 * (f - 72)
        a = f - 72
        w = lambda amp, per, dec, ph=0: wobble(a, amp, per, dec, ph)
        dkey(f, x, y, yaw=YD + 4.5 * a, pitch=-12 - 2.2 * a,
             t=(-18 + w(10, 5, 7), 0, w(6, 4, 7)), h=(-50 + w(12, 4.5, 6) , w(14, 5, 8), 0),
             ra=(74 + w(18, 4.4, 8), 0, 40 + w(12, 5, 8, .5)), la=(66 + w(18, 4.8, 8, 1.2), 0, 48 + w(12, 5, 8, 2)),
             rl=(16 + w(14, 4.2, 8, .3), 0, 6), ll=(6 + w(16, 4.6, 8, 2.2), 0, 6))

    # --- hit 1 (f84, front thrust kick to the belly): doubles over, pushed back
    dkey(K1, 18.9, 12.0, yaw=YD + 40, pitch=-6, t=(56, 0, 0), h=(36, 0, 0), ra=(-34, 0, 20), la=(-38, 0, 24), rl=(-22, 0, 4), ll=(-16, 0, 4))
    dkey(K1 + 1, 19.0, 12.05, yaw=YD + 40, pitch=-6, t=(60, 0, 0), h=(40, 0, 0))                       # hit-stop
    dkey(K1 + 2, 19.1, 12.1, yaw=YD + 52, pitch=-14, t=(30, 0, 0), h=(14, 0, 0), ra=(20, 0, 30), la=(26, 0, 34), rl=(10, 0, 4), ll=(4, 0, 4))
    # --- hit 2 (f87, spinning back kick to the chest): arches back, arms flung, spun around
    dkey(K2 - 1, 19.5, 12.15, yaw=YD + 70, pitch=-10, t=(8, 0, 0), h=(0, 0, 0), ra=(30, 0, 30), la=(30, 0, 30))
    dkey(K2, 20.5, 12.1, yaw=YD + 96, pitch=-14, t=(-38, 0, 0), h=(-52, 0, 0), ra=(84, 0, 48), la=(90, 0, 52), rl=(24, 0, 4), ll=(18, 0, 4))
    dkey(K2 + 1, 20.6, 12.1, yaw=YD + 100, pitch=-14, t=(-42, 0, 0), h=(-56, 0, 0))
    dkey(K2 + 2, 20.7, 12.2, yaw=YD + 130, pitch=-10, t=(-14, 0, 0), h=(-20, 0, 0), ra=(50, 0, 36), la=(54, 0, 40))
    # --- hit 3 (f90, roundhouse to the head): head whips round, the whole dummy corkscrews
    dkey(K3 - 1, 20.9, 12.2, yaw=YD + 190, pitch=-6, t=(0, 0, 0), h=(0, 0, 0))
    dkey(K3, 21.5, 12.3, yaw=YD + 250, pitch=-6, t=(6, 50, 8), h=(10, 88, 16), ra=(60, 0, 70), la=(-30, 0, 30), rl=(10, 0, 4), ll=(-6, 0, 4))
    dkey(K3 + 1, 21.6, 12.3, yaw=YD + 262, pitch=-6, t=(6, 54, 8), h=(10, 90, 16))
    dkey(K3 + 2, 21.8, 12.4, yaw=YD + 330, pitch=-12, t=(4, 30, 4), h=(6, 50, 8), ra=(40, 0, 50), la=(30, 0, 40))
    dkey(K3 + 3, 21.9, 12.5, yaw=YD + 380, pitch=-14, t=(0, 10, 0), h=(0, 14, 0), ra=(20, 0, 30), la=(22, 0, 30))
    # --- hit 4 (f94, flip kick under the chin): snapped up and flipped backwards
    dkey(K4 - 1, 21.9, 12.3, yaw=YD + 400, pitch=-10, t=(-6, 0, 0), h=(0, 0, 0))
    dkey(K4, 22.0, 12.9, yaw=YD + 410, pitch=-26, t=(-30, 0, 0), h=(-62, 0, 0), ra=(70, 0, 46), la=(76, 0, 50), rl=(24, 0, 4), ll=(20, 0, 4))
    dkey(K4 + 1, 22.0, 13.1, yaw=YD + 410, pitch=-30, t=(-34, 0, 0), h=(-66, 0, 0))
    dkey(K4 + 2, 22.1, 13.6, yaw=YD + 410, pitch=-70, t=(-14, 0, 0), h=(-30, 0, 0), ra=(40, 0, 36), la=(46, 0, 40))
    dkey(K4 + 3, 22.2, 13.7, yaw=YD + 410, pitch=-120, t=(0, 0, 0), h=(-10, 0, 0))
    dkey(K4 + 4, 22.2, 13.5, yaw=YD + 410, pitch=-170, t=(0, 0, 0), h=(0, 0, 0), ra=(20, 0, 36), la=(24, 0, 40))
    # --- hit 5 (f99, double axe fists on the head/shoulders): driven straight down like a meteor
    dkey(K5 - 1, 22.2, 13.2, yaw=YD + 410, pitch=-220, t=(0, 0, 0), h=(0, 0, 0))
    dkey(K5, 22.4, 12.6, yaw=YD + 410, pitch=-300, t=(40, 0, 0), h=(34, 0, 0), ra=(-20, 0, 28), la=(-24, 0, 32), rl=(-16, 0, 4), ll=(-10, 0, 4))
    for i, (f, y, pit) in enumerate([(K5 + 1, 9.0, -330), (K5 + 2, 4.2, -352), (CRASH, 1.0, -450)]):
        dkey(f, 22.6 + 0.5 * i, y, yaw=YD + 410, pitch=pit, t=(16 - 12 * i, 0, 0), h=(10 - 25 * i, 0, 0), ra=(70, 0, 60), la=(76, 0, 66), rl=(20, 0, 8), ll=(14, 0, 8))
    # bounce in the crater, settle starfished
    for i, f in enumerate(range(CRASH + 1, CRASH + 7)):
        b = 0.9 * math.exp(-i * 0.85) * (1 if i < 3 else 0.2)
        a = i
        dkey(f, 23.2 + 0.1 * i, 0.0 + b, yaw=YD + 410, pitch=-450 - 2 * i,
             t=(-4 + wobble(a, 6, 5, 4), 0, 0), h=(-20 + wobble(a, 8, 4, 4), 8, 0),
             ra=(70, 0, 76 - 3 * i), la=(76, 0, 80 - 3 * i), rl=(10, 0, 18 + 2 * i), ll=(4, 0, 22 + 2 * i), ease='out')
    D.k(CRASH + 12, 'io', t=(-3, 0, 0), h=(-16, 6, 0))

    # ------------------------------------------------------------------ player (relative to the dummy)
    px, pz = P.rig.root(74)[0], P.rig.root(74)[2]
    P.k(73, 'lin', t=(-16, -40, 0, 0, 0.1), ra=(176, 0, 6))                                        # uppercut follow-through
    P.k(74, 'in', hrp=H(px, 0, pz, YP), t=(30, 12, 0, 0, -0.9), h=(10, -10), ra=(30, 0, 18), la=(30, 0, 18), ll=(58, 0, 14), rl=(60, 0, 14))   # load
    # take-off: stretched, arms up
    P.k(75, 'out', hrp=H(px + 0.5, 0.9, pz, YP), t=(-6, 0, 0), h=(-16, 0), ra=(172, 0, 16), la=(172, 0, 16), ll=(8, 0, 4), rl=(-6, 0, 4))
    px84 = 18.9 - 2.5                                                      # 2.5 studs behind the dummy at the first air strike
    for f in range(76, 84):
        u = (f - 75) / 9.0
        y = L(0.9, 12.0 - 3.0, eo(u))
        x = L(px + 0.5, px84, sm(u))
        pit = L(0, 12, sm(u))
        P.k(f, 'lin', hrp=H(x, y, pz, YP, pitch=pit), t=(-4 + 6 * u, 0, 0), h=(-14, 0), ra=(L(172, 90, sm(u)), 0, 16), la=(L(172, 100, sm(u)), 0, 16 - 40 * u),
            ll=(L(8, -20, u), 0, 6), rl=(L(-6, 36, u), 0, 6))
    # KICK 1 (f84) front thrust
    P.k(K1, 'lin', hrp=H(px84 + 0.5, 12.0 - 3.0 + 0.2, pz, YP, pitch=-10), t=(-24, 10, 0), h=(8, -10), ra=(30, 0, 64), la=(-36, 0, 50), ll=(-18, 0, 8), rl=(98, 0, 4))
    P.k(K1 + 1, 'lin', t=(-24, 10, 0), rl=(100, 0, 4))
    P.k(K1 + 2, 'out', hrp=H(px84 + 1.2, 12.0 - 3.0 + 0.4, pz, YP + 100, pitch=-4), t=(12, 20, 0), h=(6, -10), ra=(70, 0, 30), la=(70, 0, 30), ll=(18, 0, 8), rl=(30, 0, 8))
    # BACK KICK (f87): half turn, back to the target, leg thrown behind
    P.k(K2, 'lin', hrp=H(px84 + 2.2, 12.0 - 3.0 + 0.5, pz, YP + 180, pitch=0), t=(54, 0, 0), h=(-30, 80, 0), ra=(24, 0, 80), la=(24, 0, 80), ll=(-96, 0, 6), rl=(24, 0, 8))
    P.k(K2 + 1, 'lin', ll=(-98, 0, 6))
    P.k(K2 + 2, 'out', hrp=H(px84 + 2.6, 12.0 - 3.0 + 0.6, pz, YP + 270, pitch=0), t=(10, -10, -14), h=(0, -30), ra=(70, 0, 40), la=(70, 0, 40), ll=(12, 0, 8), rl=(54, 0, 40))
    # ROUNDHOUSE (f90): full turn finishes with a horizontal high kick
    P.k(K3, 'lin', hrp=H(px84 + 3.5, 12.0 - 3.0 + 1.0, pz, YP + 360, pitch=0), t=(-6, -20, -18), h=(0, 24), ra=(80, 0, 52), la=(60, 0, 60), ll=(8, 0, 8), rl=(92, 0, -26))
    P.k(K3 + 1, 'lin', rl=(92, 0, -30), t=(-6, -22, -20))
    P.k(K3 + 3, 'out', hrp=H(px84 + 3.9, 12.0 - 3.0 + 0.3, pz, YP + 360, pitch=4), t=(20, 10, 0), h=(8, -10), ra=(80, 0, 26), la=(80, 0, 26), ll=(30, 0, 8), rl=(40, 0, 10))
    # FLIP KICK (f94): tuck, back-somersault, heel up under the chin
    P.k(K3 + 3, 'out', hrp=H(px84 + 3.9, 12.0 - 3.0 + 0.3, pz, YP + 360, pitch=4), t=(20, 10, 0), h=(8, -10), ra=(80, 0, 26), la=(80, 0, 26), ll=(30, 0, 8), rl=(40, 0, 10))
    P.k(K4, 'lin', hrp=H(px84 + 4.3, 12.0 - 3.0 + 0.4, pz, YP + 360, pitch=-125), t=(0, 0, 0), h=(-10, 0), ra=(120, 0, 30), la=(120, 0, 30), ll=(40, 0, 6), rl=(112, 0, 4))
    P.k(K4 - 1, 'lin', hrp=H(px84 + 4.0, 12.0 - 3.0 + 0.1, pz, YP + 360, pitch=-60), t=(0, 0, 0), h=(0, 0), ra=(100, 0, 30), la=(100, 0, 30), ll=(70, 0, 6), rl=(74, 0, 6))
    P.k(K4 + 1, 'lin', hrp=H(px84 + 4.4, 12.0 - 3.0 + 0.6, pz, YP + 360, pitch=-190), rl=(114, 0, 4))
    P.k(K4 + 2, 'lin', hrp=H(px84 + 4.6, 12.0 - 3.0 + 1.2, pz, YP + 360, pitch=-262), t=(0, 0, 0), ll=(60, 0, 6), rl=(70, 0, 6), ra=(60, 0, 24), la=(60, 0, 24))
    P.k(K4 + 3, 'lin', hrp=H(px84 + 4.8, 12.0 - 3.0 + 1.8, pz, YP + 360, pitch=-320), ll=(30, 0, 6), rl=(30, 0, 6))
    P.k(K4 + 4, 'out', hrp=H(px84 + 5.0, 12.0 - 3.0 + 2.6, pz, YP + 360, pitch=-360), t=(6, 0, 0), h=(-6, 0), ra=(172, 0, 18), la=(172, 0, 18), ll=(0, 0, 4), rl=(0, 0, 4))
    # DOUBLE AXE (f99): above the dummy, both fists slam down on it
    P.k(K5 - 1, 'in', hrp=H(px84 + 5.2, 12.0 - 3.0 + 3.0, pz, YP + 360, pitch=-8), t=(-16, 0, 0), h=(-10, 0), ra=(178, 0, 12), la=(178, 0, 12), ll=(30, 0, 6), rl=(30, 0, 6))
    P.k(K5, 'lin', hrp=H(px84 + 5.3, 12.0 - 3.0 + 2.6, pz, YP + 360, pitch=24), t=(42, 0, 0), h=(20, 0), ra=(112, 0, -6), la=(112, 0, -6), ll=(-14, 0, 8), rl=(-20, 0, 8))
    # dive after it
    for i, (f, y) in enumerate([(K5 + 1, 9.5), (K5 + 2, 5.0), (CRASH, 1.6)]):
        P.k(f, 'lin', hrp=H(21.4 - 0.5 * i, y, pz, YP + 360, pitch=62 - 4 * i), t=(0, 0, 0), h=(-30, 0), ra=(168, 0, 6), la=(168, 0, 6), ll=(-6, 0, 4), rl=(-10, 0, 4))
    # hero landing (f103): one fist on the floor, knee bent, cape of dust
    P.k(CRASH + 1, 'out', hrp=H(20.2, 0.0, pz, YP + 360, pitch=0), t=(52, 6, 0, 0, -1.05), h=(-40, 0), ra=(18, 0, 18), la=(-30, 0, 30), ll=(-62, 0, 14), rl=(104, 0, 10))
    P.k(CRASH + 6, 'io', t=(50, 6, 0, 0, -1.0), ra=(16, 0, 18))
    P.k(CRASH + 12, 'io', hrp=H(20.2, 0.0, pz, YP + 360), t=(34, 10, 0, 0, -0.7), h=(-22, 0), ra=(20, 0, 14), la=(20, 0, 14), ll=(-40, 0, 12), rl=(80, 0, 12))
    P.plant([CRASH + 1, CRASH + 6, CRASH + 12])

    # ------------------------------------------------------------------ strike contacts
    contact(K1, P, 'rl', D, 't', (0, -0.3, -0.5), name='air front kick', tip=(0, -0.85, 0), air=True)
    contact(K1 + 1, P, 'rl', D, 't', (0, -0.3, -0.5), name='air front kick hs', tip=(0, -0.85, 0), air=True)
    contact(K2, P, 'll', D, 't', (0, 0.2, -0.5), name='air back kick', tip=(0, -0.85, 0), air=True)
    contact(K3, P, 'rl', D, 'h', (0.3, 0, -0.45), name='air roundhouse', tip=(0, -0.85, 0), air=True)
    contact(K4, P, 'rl', D, 'h', (0, -0.55, -0.1), name='flip kick', tip=(0, -0.95, 0), air=True)
    contact(K5, P, 'ra', D, 'h', (0.3, 0.4, 0.0), name='double axe R', air=True)
    contact(K5, P, 'la', D, 'h', (-0.3, 0.4, 0.0), name='double axe L', air=True)
