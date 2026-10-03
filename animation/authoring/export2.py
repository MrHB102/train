"""v2 exporter: everything the renderer / post / audio need for the 120 fps timeline.

  out/v2/shot.json   fps 120, story_fps 18, tau[n] (story frame shown at output frame n), per-output-frame part transforms of
                     both characters, visibility / hurt face / name tag, camera v2 (+ focus distance, aperture), 3D effects
  out/v2/fx2d.json   2D effects (story timing + clock), sfx table in output seconds, per-output-frame head/torso positions
Effect clocks: 'story' effects live in story time (they slow down in slow motion and freeze in hit-stops); 'real' effects
(flashes, stars, shards, sparks, impact glow and rings, titles) always play at real speed from the output frame where they start.
"""
import json
import math
import os

import numpy as np

import choreo as C
import rig as rg
import timeline as TL

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUTV2 = os.path.join(ROOT, 'out', 'v2')
REAL_2D = {'star', 'shards', 'flash', 'ca', 'rblur', 'sparkle', 'text'}
REAL_3D = {'glow', 'sparks'}


def _clock3(e):
    if e.get('clk'): return e['clk']
    if e['t'] in REAL_3D: return 'real'
    if e['t'] == 'ring' and abs((e.get('n') or [0, 1, 0])[1]) < 0.95: return 'real'      # impact rings (not ground shockwaves)
    return 'story'


def _stamp(e, clk, warp):
    e = dict(e); e['clk'] = clk
    if clk == 'real': e['n0'] = int(round(warp.out(e['f0'])))
    return e


def _ghost_dense(e):
    """denser after-image train at 120 fps: in-between copies at half the authored spacing, dimmer"""
    lags = e.get('lags') or [2, 4, 6]
    if len(lags) >= 2:
        step = min(b - a for a, b in zip(lags, lags[1:]))
        new = []
        for l in lags:
            new.append(l)
        extra = [l - step / 2.0 for l in lags if l - step / 2.0 > 0]
        e['lags'] = sorted(set(new + extra))
        e['decay'] = (e.get('decay', 0.7)) ** 0.5
        e['a'] = e.get('a', 0.5) * 0.85
    return e


def sample_story(arr, af, interp=False):
    if interp:
        i = int(math.floor(af)); t = af - i
        a = arr[max(0, min(len(arr) - 1, i))]; b = arr[max(0, min(len(arr) - 1, i + 1))]
        return a + (b - a) * t
    return arr[max(0, min(len(arr) - 1, int(math.floor(af + 1e-6))))]


def export(warp, bake, camv2, cuts, fx3, fx2, sfx, tag_vis, p_vis, d_hurt, w=1080, h=1920, verbose=True):
    os.makedirs(OUTV2, exist_ok=True)
    n = warp.n_total
    tau = [float(bake.af[i]) for i in range(n)]
    shot = {'fps': TL.FPS_OUT, 'story_fps': TL.FPS_STORY, 'frames': n, 'width': w, 'height': h, 'tau': [round(t, 5) for t in tau],
            'cuts': cuts, 'chars': {}}
    for cid, kind in (('P', 'player'), ('D', 'dummy')):
        parts = {}
        for j, b in enumerate(rg.PARTS):
            A = bake.parts[cid][:, j, :]
            parts[b] = [[round(float(x), 4) for x in A[i, :3]] + [round(float(x), 5) for x in A[i, 3:]] for i in range(n)]
        d = {'kind': kind, 'parts': parts}
        if cid == 'P': d['vis'] = [1 if sample_story(p_vis, t) else 0 for t in tau]
        if cid == 'D': d['hurt'] = [bool(sample_story(d_hurt, t)) for t in tau]
        shot['chars'][cid] = d
    shot['cam'] = [[round(x, 5) for x in c] for c in camv2]
    shot['focus'] = [[round(float(x), 3) for x in (bake.parts['P'][i, 0, :3] + bake.parts['D'][i, 0, :3]) / 2] for i in range(n)]
    shot['tags'] = {'P': {'text': '@Mr_HB', 'vis': [round(float(sample_story(tag_vis, t, True)), 3) for t in tau]}}
    ev3 = []
    for e in fx3:
        e = dict(e)
        if e['t'] == 'ghost': e = _ghost_dense(e)
        ev3.append(_stamp(e, _clock3(e), warp))
    shot['fx'] = sorted(ev3, key=lambda e: e['f0'])
    with open(os.path.join(OUTV2, 'shot.json'), 'w') as fh:
        json.dump(shot, fh, separators=(',', ':'))
    ev2 = [_stamp(e, 'real' if e['t'] in REAL_2D else 'story', warp) for e in fx2]
    fx = {'fps': TL.FPS_OUT, 'story_fps': TL.FPS_STORY, 'frames': n, 'tau': shot['tau'], 'events': ev2,
          'sfx': [[round(warp.out(f) / TL.FPS_OUT, 4), k, s] for f, k, s in sfx], 'cam': shot['cam'], 'cuts': cuts,
          'chars': {cid: {'head': [[round(float(x), 3) for x in bake.parts[cid][i, 1, :3]] for i in range(n)],
                          'torso': [[round(float(x), 3) for x in bake.parts[cid][i, 0, :3]] for i in range(n)]} for cid in ('P', 'D')},
          'warp_nodes': warp.nodes}
    with open(os.path.join(OUTV2, 'fx2d.json'), 'w') as fh:
        json.dump(fx, fh, separators=(',', ':'))
    if verbose:
        print('export v2: %d output frames (%.2f s @120), %d 3D fx, %d 2D fx, %d sfx' % (n, n / 120, len(ev3), len(ev2), len(sfx)))
    return os.path.join(OUTV2, 'shot.json'), os.path.join(OUTV2, 'fx2d.json')
