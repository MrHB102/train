"""v2 build: authored keys -> time-warp -> Blender Bezier actions -> everything evaluated from the F-curves at 120 fps.

    import v2; S = v2.prepare()      # S.warp, S.act, S.eval ...; C.P.rig / C.D.rig now answer from the curves

Stages
  1. choreo.build()                      authored keys + strike contacts solved on the 18 fps story grid (unchanged authoring)
  2. probe                               runs the v1 direction once only to read the impact table (frames + strengths)
  3. timeline.design                     time-warp: slow preparations, fast strikes, hit-stops, slow-motion ramps
  4. blcurves.build_action               Blender actions with role-based interpolation, keys on integer 120 fps frames
  5. rigs switch to curve mode           every later query (contacts QA, camera, effects) reads the curves
"""
import contextlib
import importlib
import io
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import choreo as C       # noqa: E402
import cam as camlib     # noqa: E402
import rig as rg         # noqa: E402
import r6                # noqa: E402
import timeline as TL    # noqa: E402
import blcurves as BC    # noqa: E402


class State:
    pass


S = State()


def hidden_runs():
    runs = []; f = 0
    while f < C.N:
        if not C.P_VIS[f]:
            g = f
            while g + 1 < C.N and not C.P_VIS[g + 1]: g += 1
            runs.append((f, g)); f = g + 1
        else:
            f += 1
    return runs


def probe_impacts():
    """run the v1 direction once (story-grid sampling) to read the impact table, then reset camera / effects state"""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        import direction, direction2
        direction.direct_all(); direction2.direct_all2()
    sfx = list(direction.FXL.sfx)
    C.CAM = camlib.Camera(C.N)
    import direction, direction2  # noqa: F811
    importlib.reload(direction); importlib.reload(direction2)
    return sfx


def primary_contacts():
    """first frame of every strike contact of the player (hit-stop / drag frames removed) -> striking bone"""
    out = {}
    allf = {(c['limb'], c['f']) for c in C.CONTACTS if c['att'] is C.P}
    for c in C.CONTACTS:
        if c['att'] is not C.P: continue
        if (c['limb'], c['f'] - 1) in allf: continue
        out.setdefault(c['f'], r6.SHORT[c['limb']])
    return out


def prepare(verbose=True):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        C.build()
    S.contacts_txt = [l for l in buf.getvalue().splitlines() if l.startswith('contact')]
    S.sfx = probe_impacts()
    hits = {}
    for f, kind, s in S.sfx:
        if kind == 'hit': hits[f] = max(hits.get(f, 0), s)
    S.hits = hits
    S.limb_of_hit = primary_contacts()
    for f in S.limb_of_hit:
        hits.setdefault(f, 2)
    S.warp, S.mul, S.why, S.rep = TL.design(C.N, hits, C.CONTACTS, C.P.clip, S.limb_of_hit)
    w = S.warp
    if verbose:
        print('warp: %d story frames (%.2f s @18) -> %d output frames = %.2f s @120' % (C.N, C.N / 18, w.n_total, w.seconds()))
    # ---- roles
    strikes = {f: set() for f in hits}
    for c in C.CONTACTS:
        if c['att'] is C.P and c['f'] in strikes: strikes[c['f']].add(r6.SHORT[c['limb']])
    runs = hidden_runs()
    pk = r6.frames(C.P.clip)
    breaks = []
    for h0, h1 in runs:
        ka = max(f for f in pk if f < h0); kb = min(f for f in pk if f > h1)
        breaks.append((ka, kb))
    S.breaks = breaks
    def d_still(f0, f1):
        a = r6.fk(r6.sample(C.D.clip, f0))['HumanoidRootPart'][0]; b = r6.fk(r6.sample(C.D.clip, f1))['HumanoidRootPart'][0]
        return rg.dist(a, b) < 0.35
    S.spec = {'P': BC.Spec(strikes=strikes, breaks=breaks),
              'D': BC.Spec(struck=strikes, stationary=d_still)}
    build_curves()
    return S


def build_curves():
    """(re)build both actions from the current keys and switch the rigs to curve evaluation"""
    w = S.warp
    S.act = {}; S.eval = {}
    for cid, actor, nm in (('P', C.P, 'MrHB'), ('D', C.D, 'Dummy')):
        act, slot = BC.build_action(nm, actor.clip, w, S.spec[cid])
        ev = BC.ActionEval(act, slot)
        S.act[cid] = (act, slot); S.eval[cid] = ev
        if getattr(S, 'floor_lift', False):
            S.lift_info = getattr(S, 'lift_info', {}); S.lift_info[cid] = BC.add_floor_lift(act, slot, ev, w.n_total, rg.lowest_point)
        actor.rig.evalfn = (lambda e: (lambda f: e.pose(w.out(f))))(ev)
        actor.rig.invalidate()


def frames_out():
    """story frame shown at each output frame"""
    return [S.warp.af(n) for n in range(S.warp.n_total)]


if __name__ == '__main__':
    prepare()
    for l in S.rep: print(l)
