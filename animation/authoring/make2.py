"""v2 build:  python make2.py [--resolve] [--review N0 N1 STEP]

  1. v2.prepare()          authored keys, impacts, time-warp, Blender Bezier actions (curve mode)
  2. overlap solver        pose solver on impact keys + smooth dummy push (cached in out/v2/solved_keys.json; --resolve redoes it)
  3. direction (v1 shots/effects) re-run on the final curves, effects in v2 mode (glow, sparks, continuous trails)
  4. camera v2, export     out/v2/shot.json + out/v2/fx2d.json
"""
import argparse
import contextlib
import hashlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import choreo as C       # noqa: E402
import r6                # noqa: E402
import v2                # noqa: E402
import qa2               # noqa: E402
import spacing           # noqa: E402
import camera2           # noqa: E402
import export2           # noqa: E402
import fx as fxlib       # noqa: E402

OUTV2 = export2.OUTV2
CACHE = os.path.join(OUTV2, 'solved_keys.json')
SOURCES = ['choreo.py', 'actor.py', 'timeline.py', 'spacing.py', 'posefix.py', 'blcurves.py', 'v2.py'] + \
          sorted(f for f in os.listdir(HERE) if f.startswith('beat_') and f.endswith('.py'))


def src_hash():
    h = hashlib.sha1()
    for f in SOURCES:
        h.update(open(os.path.join(HERE, f), 'rb').read())
    return h.hexdigest()


def _dump_clip(c):
    return {repr(f): {'e': k['e'], 'b': k['b']} for f, k in c['keys'].items()}


def _load_clip(c, d):
    c['keys'] = {float(f): {'e': k['e'], 'b': {b: list(v) for b, v in k['b'].items()}} for f, k in d.items()}


def solve_or_load(S, resolve=False, verbose=True, allow_solve=True):
    hsh = src_hash()
    if not resolve and os.path.exists(CACHE):
        d = json.load(open(CACHE))
        if d.get('hash') == hsh:
            _load_clip(C.P.clip, d['P']); _load_clip(C.D.clip, d['D'])
            v2.build_curves()
            if verbose: print('overlap solver: cached keys loaded (%s)' % hsh[:10])
            return d.get('log', [])
        if verbose: print('overlap solver: sources changed, re-solving')
    if not allow_solve:
        raise RuntimeError('overlap-solver cache is stale: run "python run_all2.py --stage make" first')
    log, _ = spacing.solve2(S, v2.build_curves, iters=9, verbose=verbose)
    # final strike-contact touch-up (IK only, no stepping) on the story keys, then rebuild
    for A in (C.P, C.D):
        A.rig.evalfn = None; A.rig.invalidate()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        C.solve_contacts(chase=False, passes=1)
    log += [l for l in buf.getvalue().splitlines() if l.startswith('contact')]
    v2.build_curves()
    os.makedirs(OUTV2, exist_ok=True)
    with open(CACHE, 'w') as fh:
        json.dump({'hash': hsh, 'P': _dump_clip(C.P.clip), 'D': _dump_clip(C.D.clip), 'log': log}, fh)
    return log


def build(resolve=False, verbose=True, export=True, allow_solve=True):
    S = v2.prepare(verbose=verbose)
    S.solve_log = solve_or_load(S, resolve, verbose, allow_solve)
    # ---- direction on the final curves (effects in v2 mode)
    fxlib.V2 = True
    import direction as DR
    import direction2
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        DR.direct_all(); direction2.direct_all2()
    S.bake = qa2.Bake(S.warp)
    S.cam, S.cuts = camera2.build(S.warp, S.bake, verbose=verbose)
    if export:
        S.paths = export2.export(S.warp, S.bake, S.cam, S.cuts, DR.FXL.f3, DR.FXL.f2, DR.FXL.sfx, DR.TAG_VIS, C.P_VIS, DR.DUMMY_HURT, verbose=verbose)
    else:
        S.paths = (os.path.join(OUTV2, 'shot.json'), os.path.join(OUTV2, 'fx2d.json'))
    S.DR = DR
    return S


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--resolve', action='store_true')
    a = ap.parse_args()
    build(a.resolve)
