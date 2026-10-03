"""Effect authoring: turns a few story-level calls (impact, dash, landing...) into renderer events.

3D events (scene.js): ghost, aura, ring, wall, debris, crack, dust, slash, streak  -> shot.json 'fx'
2D events (post.py):  star, lines, flash, shards, ca, mblur, rblur, grade, text, sparkle, smear -> fx2d.json
Every call also records an entry in the impact/sfx table used by the audio synth.
"""
import math
import random

import rig as rg


V2 = False          # set by the v2 pipeline: continuous trails, impact glow / sparks / flash light


class FX:
    def __init__(self, cam, actors):
        self.cam = cam
        self.A = actors          # {'P': Actor, 'D': Actor}
        self.f3 = []
        self.f2 = []
        self.sfx = []            # (frame, kind, strength)
        self.seed = 1

    def _s(self):
        self.seed += 1
        return self.seed

    # ------------------------------------------------------------------ primitive emitters
    def e3(self, **kw): self.f3.append(kw)
    def e2(self, **kw): self.f2.append(kw)

    # ------------------------------------------------------------------ story-level effects
    def impact(self, f, p, d=(1, 0, 0), s=2, ground=False, shake=True, kind='hit', col='#ffffff', sfx=True, flash=None, debris=None):
        """strike landing at world point p moving along d. s: 1 light, 2 medium, 3 heavy, 4 mega."""
        d = rg.unit(d)
        R = {1: 0.55, 2: 0.9, 3: 1.35, 4: 2.1}[s]
        self.e2(t='star', f0=f, f1=f + (1 if s == 1 else 2 if s == 2 else 3), p=list(p), r=R, col=col, seed=self._s(), rays=10 + 2 * s)
        self.e2(t='shards', f0=f, f1=f + 3, p=list(p), n=4 + 3 * s, r=R * 1.9, seed=self._s(), d=list(d))
        self.e3(t='ring', f0=f, f1=f + (3 if s < 3 else 5), p=list(p), n=list(d), r0=0.25, r1=R * 1.5, w=1.0, col=col, a0=0.9, a1=0.0)
        if s >= 2:
            self.e3(t='ring', f0=f + 1, f1=f + 5, p=list(p), n=list(d), r0=0.1, r1=R * 2.1, w=0.5, col='#bfe3ff', a0=0.7, a1=0.0)
        nd = debris if debris is not None else {1: 0, 2: 5, 3: 12, 4: 22}[s]
        if nd:
            self.e3(t='debris', f0=f, f1=f + 14, p=list(p), n=nd, size=[0.12, 0.12 + 0.07 * s], speed=7 + 3 * s, seed=self._s(), life=0.8, grav=34, up=0.5, flat=0.8, dir=list(d), dirSpeed=4 + 3 * s)
        if shake:
            self.cam.shake(f, amp=(0.05, 0.14, 0.28, 0.5)[s - 1], roll=(0.4, 1.0, 1.8, 3.0)[s - 1], decay=(4, 5, 6, 8)[s - 1], seed=self._s())
            self.cam.punch(f, dfov=(-1.2, -3, -6, -11)[s - 1], decay=(2.5, 3, 4, 5)[s - 1])
        if s >= 2:
            self.e2(t='ca', f0=f, f1=f + 3, amt=(0, 2.0, 4.5, 8.0, 14.0)[s])
        if s >= 3 or flash:
            self.e2(t='flash', f0=f, f1=f, kind=flash or ('impact' if s >= 4 else 'white'), a=1.0 if s >= 4 else 0.5)
        if s >= 3:
            self.e2(t='rblur', f0=f, f1=f + 2, p=list(p), amt=0.012 * s)
        if ground:
            self.crack(f, (p[0], 0, p[2]), s=1.2 + s * 0.9, seed=self._s())
        if V2:
            # hot core flash (lights the fighters for a few frames) + spark burst along the strike direction
            self.e3(t='glow', clk='real', f0=f, f1=f + (1 if s < 3 else 2), p=list(p), r=0.45 + 0.25 * s, i=0.75, col='#fff1d8', light=0.5 + 0.3 * s)
            self.e3(t='sparks', clk='real', f0=f, f1=f + 4, p=list(p), n=8 + 6 * s, speed=12 + 5 * s, dir=list(d), seed=self._s(), life=0.26 + 0.05 * s)
        if sfx:
            self.sfx.append((f, kind, s))

    def crack(self, f, p, s=3.0, rot=None, seed=1, keep=True, fade_at=None):
        self.e3(t='crack', f0=f, f1=f, p=[p[0], 0, p[2]], s=s, rot=rot if rot is not None else random.Random(seed).random() * 6.28, seed=seed, keep=keep, fadeAt=fade_at)

    def dust_burst(self, f, p, s=1.0, n=10, col='#cdd5de', spread=2.6, rise=1.4, dur=8, drift_dir=None, drift=0.0):
        self.e3(t='dust', f0=f, f1=f + dur, p=[p[0], 0, p[2]], n=int(n * s * 0.7) + 2, spread=spread * s, rise=rise * s, size=0.95 * s, col=col, a=0.4, seed=self._s(), dir=drift_dir, drift=drift)

    def shockwave(self, f, p, r=6.0, dur=6, col='#ffffff', wall=True, ring=True, h=1.6):
        if ring:
            self.e3(t='ring', f0=f, f1=f + dur, p=[p[0], 0.05, p[2]], n=[0, 1, 0], r0=0.6, r1=r, w=1.3, col=col, a0=0.95, a1=0.0)
        if wall:
            self.e3(t='wall', f0=f, f1=f + dur, p=[p[0], 0.0, p[2]], r0=0.6, r1=r * 0.9, h0=0.3, h1=h, col=col, a0=0.7)

    def dash(self, who, f0, f1, col='#8fc8ff', lags=(2, 4, 6), a=0.5, lines=True, ang=None, dust=True, mblur=14, foot=True):
        """speed-dash look: stepped after-images, parallel speed lines, dust kicked up at the feet, directional blur"""
        self.e3(t='ghost', c=who, f0=f0, f1=f1, lags=list(lags), col=col, a=a, decay=0.66, fade=True)
        if lines:
            self.e2(t='lines', f0=f0, f1=f1, mode='parallel', ang=ang, n=26, a=0.8, col='#ffffff', who=who)
        if mblur:
            self.e2(t='mblur', f0=f0, f1=f1, who=who, len=mblur)
        if dust:
            act = self.A[who]
            for f in range(f0, f1 + 1, 2):
                p = act.rig.sole(f, 'r')
                self.dust_burst(f, p, s=0.7, n=5, dur=7, spread=1.6, rise=0.9)
        self.sfx.append((f0, 'whoosh', 2))

    def trail(self, who, bone, tip_local, f0, f1, col='#ffffff', w=0.18, a=0.9, k=3):
        """limb-tip motion streak: a short ribbon through the last k frame positions (a stepped smear).
        v2: one continuous ribbon event that the renderer rebuilds every output frame from the limb's real path"""
        if V2:
            import r6
            self.e3(t='trail', c=who, part=r6.SHORT[bone], tip=list(tip_local), f0=f0 - 0.6, f1=f1 + 0.6, len=min(2.4, 0.75 * k + 0.4), w=w, col=col, a=a)
            return
        act = self.A[who]
        for f in range(f0, f1 + 1):
            for j in range(k):
                pa = act.rig.point(f - j - 1, bone, tip_local); pb = act.rig.point(f - j, bone, tip_local)
                if rg.dist(pa, pb) < 0.25: continue
                self.e3(t='streak', f0=f, f1=f, p0=list(pa), p1=list(pb), w=w * (1 - j * 0.22), col=col, a=a * (1 - j * 0.28))

    def slash(self, f0, f1, p, u, v, r=2.6, a0=-2.2, a1=0.9, col='#ffffff', th=0.2, rin=0.78):
        self.e3(t='slash', f0=f0, f1=f1, p=list(p), u=list(u), v=list(v), r=r, a0=a0, a1=a1, col=col, th=th, rin=rin)

    def aura(self, who, f0, f1, col='#ff3b4a', a=0.55, scale=1.2, ramp=True):
        self.e3(t='aura', c=who, f0=f0, f1=f1, col=col, a=a, scale=scale, ramp=ramp)

    def flash(self, f, kind='white', a=1.0, f1=None):
        self.e2(t='flash', f0=f, f1=f if f1 is None else f1, kind=kind, a=a)

    def lines_radial(self, f0, f1, p, n=30, a=0.8, col='#ffffff', inner=0.18):
        self.e2(t='lines', f0=f0, f1=f1, mode='radial', p=list(p), n=n, a=a, col=col, inner=inner)

    def grade(self, f0, f1, **kw):
        self.e2(t='grade', f0=f0, f1=f1, **kw)

    def text(self, f0, f1, text, pos=(0.5, 0.5), size=0.1, col='#ffffff', anim='pop', **kw):
        self.e2(t='text', f0=f0, f1=f1, text=text, pos=list(pos), size=size, col=col, anim=anim, **kw)

    def sparkle(self, f0, f1, p, r=0.5, col='#ffffff'):
        self.e2(t='sparkle', f0=f0, f1=f1, p=list(p), r=r, col=col)
