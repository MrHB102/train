"""v2 timing: the 18 fps authoring grid ("story frames", af) is mapped onto a 120 fps output timeline by a time-warp.

Why a warp and not a re-key: every pose, contact and effect of the choreography stays exactly where it was authored; only the
duration of each story-frame interval changes.  That is what the director asked for:

  * preparation is slow and readable  -> the wind-up interval before every strike chamber is stretched
  * the action is fast                -> the chamber->contact interval is kept short (and eased in, see blcurves)
  * impacts land                      -> a hit-stop (stretched interval right after contact, scaled by strength)
  * big moments breathe               -> slow-motion ramps on the launches, crashes and the finisher
  * a few long, purely flowing parts are tightened a little so the whole piece stays cohesive

Both characters, the camera rig and all 'story-clock' effects go through the same warp, so they never drift apart.
Each story frame boundary lands on an integer output frame (nodes), so every authored key and every contact is on a real
rendered frame.
"""
import bisect
import math

FPS_STORY = 18
FPS_OUT = 120
BASE = FPS_OUT / FPS_STORY            # 6.667 output frames per story frame at normal speed


class Warp:
    """piecewise-linear, strictly increasing map story frame (float) <-> output frame (float); nodes at integer story frames"""

    def __init__(self, nodes):
        self.nodes = list(nodes)                 # nodes[i] = output frame of story frame i (int, strictly increasing)
        self.N = len(self.nodes) - 1             # story frames covered: [0, N]
        self.n_total = self.nodes[-1]            # output frames: 0 .. n_total-1

    def out(self, af):
        if af <= 0: return float(self.nodes[0]) + af * BASE
        if af >= self.N: return float(self.nodes[-1]) + (af - self.N) * BASE
        i = int(math.floor(af)); t = af - i
        return self.nodes[i] + (self.nodes[i + 1] - self.nodes[i]) * t

    def key(self, af):
        """output frame for an authored key (integer for integer story frames)"""
        if abs(af - round(af)) < 1e-6 and 0 <= round(af) <= self.N:
            return float(self.nodes[int(round(af))])
        return self.out(af)

    def af(self, n):
        """inverse: story frame (float) shown at output frame n"""
        if n <= self.nodes[0]: return (n - self.nodes[0]) / BASE
        if n >= self.nodes[-1]: return self.N + (n - self.nodes[-1]) / BASE
        i = bisect.bisect_right(self.nodes, n) - 1
        a, b = self.nodes[i], self.nodes[i + 1]
        return i + (n - a) / (b - a)

    def speed(self, af):
        """story frames per output frame relative to normal speed (1 = real time, 0.5 = half speed)"""
        i = max(0, min(self.N - 1, int(math.floor(af))))
        return BASE / (self.nodes[i + 1] - self.nodes[i])

    def seconds(self):
        return self.n_total / FPS_OUT


# ------------------------------------------------------------------------------------------------ the timing design
# hand-tuned moments (story frames). factor = interval duration multiplier (2 = half speed). ramp = story frames to blend in/out.
SLOWMO = [
    # (f0, f1, factor, ramp_in, ramp_out, why)
    (72, 76, 1.6, 0, 3, 'uppercut launch'),
    (99, 104, 2.2, 1, 4, 'double-axe -> meteor crash'),
    (133, 136, 1.5, 1, 2, 'front-flip axe kick'),
    (159, 162, 1.8, 0, 3, 'double drop-kick'),
    (208, 213, 2.0, 0, 3, 'palm blast'),
    (244, 249, 1.6, 2, 2, 'hammer-throw release'),
    (285, 289, 1.6, 0, 3, 'dragon uppercut'),
    (296, 299, 1.6, 0, 3, 'bicycle kick'),
    (336, 338, 1.4, 0, 2, 'pillar 1'),
    (341, 343, 1.4, 0, 2, 'pillar 2'),
    (346, 350, 1.6, 0, 3, 'pillar 3'),
    (396, 400, 1.5, 0, 3, 'lob'),
    (489, 492, 1.4, 0, 2, 'super-leap'),
    (527, 532, 1.5, 1, 0, 'freeze before the grab'),
    (539, 546, 2.5, 1, 6, 'head-first slam'),
]
# preparations that are not strikes (reach / coil / crouch): slow and readable
PREP = [
    (23, 29, 1.45, 'coil before the first dash'),
    (222, 225, 1.6, 'reaching for the ankle (hammer throw)'),
    (327, 330, 1.6, 'stomp wind-up'),
    (484, 489, 1.5, 'crouch before the super-leap'),
    (263, 268, 1.2, 'handspring entry'),
]
# purely flowing / waiting stretches tightened a little so the total stays cohesive
TIGHTEN = [
    (444, 484, 0.82, 'aura charge hold'),
    (557, 610, 0.9, 'aftermath walk'),
]
# hit-stop multipliers on [h, h+1] by strength; heavy hits also stretch [h+1, h+2]
HITSTOP = {1: 1.5, 2: 2.0, 3: 2.6, 4: 3.2}
WIND = 1.8          # wind-up interval multiplier (preparation)
WIND_CAP = 5.0      # max extra story frames a wind-up may gain
STRIKE = 0.88       # chamber -> contact multiplier (the action itself stays fast)
NO_WIND = set(range(497, 526)) | {182, 187, 192, 197, 202, 208}      # barrage and blink strikes: no wind-up stretch
NO_STOP = set(range(497, 526))                                      # barrage: rhythm, no hit-stops


def design(n_story, hits, contacts, attacker_clip, limb_of_hit, verbose=False):
    """hits: {frame: strength} of primary strikes; contacts: list of (frame, limb bone name) for the attacker
    attacker_clip: r6 clip of the attacker (to find chamber / wind-up keys of the striking limb).
    Returns (Warp, report lines)."""
    mul = [1.0] * n_story              # multiplier of interval [i, i+1]
    why = [[] for _ in range(n_story)]
    rep = []

    def apply(i, k, tag):
        if 0 <= i < n_story:
            mul[i] *= k; why[i].append(tag)

    keys = sorted(attacker_clip['keys'])
    for h, s in sorted(hits.items()):
        limb = limb_of_hit.get(h)
        if limb and h not in NO_WIND:
            lk = [f for f in keys if f < h and limb in attacker_clip['keys'][f]['b']]
            if len(lk) >= 2:
                k1, k0 = lk[-1], lk[-2]
                span = k1 - k0
                k = min(WIND, 1.0 + WIND_CAP / max(span, 1e-6))
                for i in range(int(k0), int(k1)):
                    apply(i, k, 'wind-up f%d' % h)
                for i in range(int(k1), int(h)):
                    apply(i, STRIKE, 'strike f%d' % h)
                rep.append('hit f%-3d s%d  wind-up [%g,%g] x%.2f  strike [%g,%d] x%.2f' % (h, s, k0, k1, k, k1, h, STRIKE))
        if h not in NO_STOP:
            apply(h, HITSTOP[s], 'hit-stop f%d' % h)
            if s >= 3: apply(h + 1, 1.0 + (HITSTOP[s] - 1) * 0.35, 'hit-stop tail f%d' % h)

    def ramped(f0, f1, k, rin, rout, tag):
        for i in range(f0 - rin, f1 + rout):
            if i < f0: w = (i - (f0 - rin) + 1) / (rin + 1)
            elif i >= f1: w = 1 - (i - f1 + 1) / (rout + 1)
            else: w = 1.0
            apply(i, 1.0 + (k - 1.0) * w, tag)

    for f0, f1, k, rin, rout, tag in SLOWMO:
        ramped(f0, f1, k, rin, rout, 'slow-mo: ' + tag)
    for f0, f1, k, tag in PREP:
        ramped(f0, f1, k, 1, 1, 'prep: ' + tag)
    for f0, f1, k, tag in TIGHTEN:
        ramped(f0, f1, k, 2, 2, 'tighten: ' + tag)

    mul = [max(0.6, min(4.5, m)) for m in mul]
    # nodes: cumulative, rounded, strictly increasing (>= 3 output frames per story frame)
    nodes = [0]; acc = 0.0
    for i in range(n_story):
        acc += BASE * mul[i]
        nodes.append(max(nodes[-1] + 3, int(round(acc))))
    w = Warp(nodes)
    if verbose:
        for l in rep: print(l)
    return w, mul, why, rep
