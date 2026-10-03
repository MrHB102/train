"""v2 spacing solver: removes player x dummy interpenetration from the final (120 fps, Bezier) motion.

For every output frame the exact minimum push of the dummy along the horizontal player->dummy line that separates every pair
of body boxes is computed analytically (SAT: for each separating axis the push that opens a gap is linear in the push
distance).  Allowed contacts (the striking limb around its impact frame, grabs) are excluded.  The push signal is dilated
with 0.2 s ramps and smoothed, so the dummy eases away instead of popping, and is written back into the dummy's root keys
(extra keys are inserted where the dummy's keys are sparse).  Strike contacts are then re-solved (IK + stride) on the story
keys, the Blender curves rebuilt, and the loop repeats until nothing is left.
"""
import math

import numpy as np

import choreo as C
import rig as rg
import r6
import qa2

PARTS = qa2.PARTS
HALF = qa2.HALF
WIN = []
LOCK = [(224.5, 247.5, 'hammer throw: the dummy hangs from the hands')]     # story windows where the dummy is carried


def allowed_rules():
    allow = []
    for c in C.CONTACTS:
        if c['att'] is C.P:
            allow.append((c['f'] - 0.6, c['f'] + 1.6, r6.SHORT[c['limb']], r6.SHORT[c['bone']], 0.6 + max(0.0, 1.0 - abs(c['tip'][1]))))
            allow.append((c['f'] - 0.6, c['f'] + 1.6, r6.SHORT[c['limb']], None, 0.3))
    allow += [(224.5, 247.5, 'Left Arm', None, 0.9), (224.5, 247.5, 'Right Arm', None, 0.9),
              (531.5, 541.5, 'Right Arm', 'Head', 0.9), (377.4, 379.6, 'Head', None, 0.4)]
    return allow


def _axes(Q):
    return [np.array((Q[0], Q[3], Q[6])), np.array((Q[1], Q[4], Q[7])), np.array((Q[2], Q[5], Q[8]))]


def push_needed(pa, qa, ha, pb, qb, hb, u, margin=0.04):
    """smallest t >= 0 such that box B moved by t*u no longer overlaps box A (inf if impossible along u)"""
    A = _axes(qa); B = _axes(qb)
    c = np.asarray(pb) - np.asarray(pa)
    best = math.inf
    cand = A + B + [np.cross(a, b) for a in A for b in B]
    for ax in cand:
        n = np.linalg.norm(ax)
        if n < 1e-6: continue
        ax = ax / n
        R = sum(ha[i] * abs(A[i] @ ax) for i in range(3)) + sum(hb[i] * abs(B[i] @ ax) for i in range(3)) + margin
        s = c @ ax
        if abs(s) >= R: return 0.0
        p = u @ ax
        if abs(p) < 1e-4: continue
        t = max((R - s) / p, (-R - s) / p)
        if t < 4.0: best = min(best, t)
    return best


def _need(P, D, i, af, allow, u):
    need = 0.0
    for a, pa in enumerate(PARTS):
        for b, pb in enumerate(PARTS):
            if np.linalg.norm(P[i, a, :3] - D[i, b, :3]) > 2.9: continue
            dep = qa2.depth(tuple(P[i, a, :3]), tuple(P[i, a, 3:]), HALF[pa], tuple(D[i, b, :3]), tuple(D[i, b, 3:]), HALF[pb])
            if dep <= 0.02: continue
            if any(f0 <= af <= f1 and (ap is None or ap == pa) and (bp is None or bp == pb) and dep <= md for f0, f1, ap, bp, md in allow):
                continue
            t = push_needed(P[i, a, :3], P[i, a, 3:], HALF[pa], D[i, b, :3], D[i, b, 3:], HALF[pb], u)
            need = max(need, t if math.isfinite(t) else 4.0)
    return need


def contact_windows():
    return sorted({(c['f'] - 0.6, c['f'] + 1.6) for c in C.CONTACTS if c['att'] is C.P})


def profile(B, allow):
    """per output frame: required push (studs) and its direction. Candidates: the horizontal player->dummy line, and straight
    up when the dummy is airborne above the player; one direction is chosen per contiguous run (no zig-zag)."""
    P, D = B.parts['P'], B.parts['D']
    n = B.n
    ph = np.zeros(n); pv = np.full(n, np.inf); Uh = np.zeros((n, 3))
    up = np.array([0.0, 1.0, 0.0])
    for i in range(n):
        af = B.af[i]
        d = D[i, 0, :3] - P[i, 0, :3]; d[1] = 0.0
        L = np.linalg.norm(d)
        Uh[i] = d / L if L > 0.25 else np.array([1.0, 0.0, 0.0])
        if any(a <= af <= b for a, b, _ in LOCK): continue
        if any(a <= af <= b for a, b in WIN): continue           # impact windows belong to the pose solver
        ph[i] = _need(P, D, i, af, allow, Uh[i])
        if ph[i] > 0.0 and D[i, 0, 1] > P[i, 0, 1] + 0.3 and D[i, :, 1].min() > 1.4:
            pv[i] = _need(P, D, i, af, allow, up)
    push = ph.copy(); U = Uh.copy()
    i = 0
    while i < n:
        if ph[i] <= 1e-4: i += 1; continue
        j = i
        while j + 1 < n and ph[j + 1] > 1e-4: j += 1
        if np.isfinite(pv[i:j + 1]).all() and pv[i:j + 1].sum() < 0.7 * ph[i:j + 1].sum():
            push[i:j + 1] = pv[i:j + 1]; U[i:j + 1] = up
        i = j + 1
    return push, U


def envelope(push, ramp=24, sigma=3.0):
    """tent dilation (ramps of `ramp` output frames on both sides) then a light gaussian smoothing"""
    n = len(push)
    e = push.copy()
    idx = np.nonzero(push > 1e-4)[0]
    for i in idx:
        lo, hi = max(0, i - ramp), min(n, i + ramp + 1)
        k = np.arange(lo, hi)
        e[lo:hi] = np.maximum(e[lo:hi], push[i] * np.clip(1 - np.abs(k - i) / ramp, 0, 1))
    if sigma > 0:
        r = int(3 * sigma); x = np.arange(-r, r + 1); g = np.exp(-x * x / (2 * sigma * sigma)); g /= g.sum()
        e2 = np.convolve(np.pad(e, r, mode='edge'), g, mode='valid')
        e = np.maximum(e, e2)             # never smooth below what is needed
    return e


def apply_push(env, U, warp, insert_gap=2.5):
    """write the push into the dummy's root keys; insert keys where they are too sparse to carry it"""
    keys = r6.frames(C.D.clip)
    hrp_keys = [f for f in keys if 'HumanoidRootPart' in C.D.clip['keys'][f]['b']]
    # insert extra keys (current displayed pose) at the peaks that fall between sparse keys
    active = np.nonzero(env > 0.03)[0]
    new = set()
    for i in active:
        af = warp.af(i)
        fa = round(af)
        near = min(abs(fa - k) for k in hrp_keys) if hrp_keys else 99
        if near >= insert_gap - 1e-6 and fa not in new:
            lo = max([k for k in hrp_keys if k < fa], default=None); hi = min([k for k in hrp_keys if k > fa], default=None)
            if lo is None or hi is None or hi - lo < 2 * insert_gap: continue
            new.add(float(fa))
    for f in sorted(new):
        pose = C.D.rig.evalfn(f) if C.D.rig.evalfn else r6.sample(C.D.clip, f)
        r6.put(C.D.clip, f, None, **pose)
    hrp_keys = [f for f in r6.frames(C.D.clip) if 'HumanoidRootPart' in C.D.clip['keys'][f]['b']]
    moved = 0
    for f in hrp_keys:
        if any(a <= f <= b for a, b, _ in LOCK): continue
        if any(a <= f <= b for a, b in WIN): continue
        n = int(round(warp.key(f)))
        if n < 0 or n >= len(env) or env[n] < 1e-3: continue
        v = U[n] * env[n]
        h = C.D.clip['keys'][f]['b']['HumanoidRootPart']
        h[3] += v[0]; h[4] += v[1]; h[5] -= v[2]
        moved += 1
    C.D.rig.invalidate()
    return moved, len(new)


def solve(S, rebuild, iters=4, verbose=True):
    """S: v2 state (warp, eval). rebuild(): rebuild curves from keys and re-enable curve evaluation."""
    allow = allowed_rules()
    log = []
    for it in range(iters):
        B = qa2.Bake(S.warp)
        push, U = profile(B, allow)
        mx = float(push.max()); cnt = int((push > 0.03).sum())
        log.append('spacing pass %d: max push needed %.2f studs on %d output frames' % (it, mx, cnt))
        if verbose: print(log[-1])
        if mx < 0.03:
            return log, B
        env = envelope(push)
        moved, ins = apply_push(env, U, S.warp)
        # strike contacts on the story keys (sample mode: identical to the curves at the keys)
        for A in (C.P, C.D):
            A.rig.evalfn = None; A.rig.invalidate()
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            C.solve_contacts(chase=True)
        rebuild()
        if verbose: print('   moved %d dummy root keys, inserted %d keys, contacts re-solved' % (moved, ins))
    B = qa2.Bake(S.warp)
    return log, B


def insert_keys_for(runs, warp, inside_only=True):
    """add player + dummy keys (current displayed pose) at the deepest frame of overlap runs that the keys do not cover"""
    added = []
    pk = set(C.P.clip['keys']); dk = set(C.D.clip['keys'])
    for r in runs:
        af_mid = warp.af(int(round((r['n0'] + r['n1']) / 2)))
        if inside_only and not any(a <= af_mid <= b for a, b in WIN): continue
        if any(a <= af_mid <= b for a, b, _ in LOCK): continue
        if min(abs(af_mid - k) for k in pk | dk) < 0.08: continue
        f = round(af_mid, 4)
        for A in (C.P, C.D):
            pose = A.rig.evalfn(f) if A.rig.evalfn else r6.sample(A.clip, f)
            r6.put(A.clip, f, None, **pose)
        added.append(f)
    return added


def solve2(S, rebuild, iters=3, verbose=True):
    """pose solver on overlapping keys (plus keys inserted at overlapping in-betweens of impact windows), then a smooth
    dummy push on everything outside the impact windows; repeated"""
    import posefix
    WIN[:] = contact_windows()
    allow = allowed_rules()
    log = []
    for it in range(iters):
        for A in (C.P, C.D):
            A.rig.evalfn = None; A.rig.invalidate()
        ko = posefix.key_overlaps()
        log.append('pass %d: %d overlapping keys (worst %.2f)' % (it, len(ko), max([w for f, w in ko], default=0)))
        if verbose: print(log[-1], flush=True)
        log += posefix.run([f for f, w in ko], verbose=False)
        rebuild()
        B = qa2.Bake(S.warp)
        push, U = profile(B, allow)
        mx = float(push.max()); cnt = int((push > 0.03).sum())
        log.append('   in-between push needed: max %.2f studs on %d output frames' % (mx, cnt))
        if verbose: print(log[-1], flush=True)
        if mx >= 0.03:
            env = envelope(push)
            moved, ins = apply_push(env, U, S.warp)
            log.append('   moved %d dummy root keys, inserted %d keys' % (moved, ins))
            if verbose: print(log[-1], flush=True)
            rebuild()
            B = qa2.Bake(S.warp)
        runs = qa2.collisions(B, allow)
        added = insert_keys_for(runs, S.warp)
        log.append('   %d overlap runs left, %d in-between keys inserted inside impact windows' % (len(runs), len(added)))
        if verbose: print(log[-1], flush=True)
        if not ko and mx < 0.03 and not added: break
    # final targeted pass: a key exactly at the deepest frame of every remaining deep run, solved once more
    import posefix
    for A in (C.P, C.D):
        A.rig.evalfn = None; A.rig.invalidate()
    rebuild()
    B = qa2.Bake(S.warp)
    runs = [r for r in qa2.collisions(B, allow) if r['max'] > 0.45]
    peaks = []
    pk = set(C.P.clip['keys']) | set(C.D.clip['keys'])
    for r in runs:
        best, bf = -1, None
        for i in range(r['n0'], r['n1'] + 1):
            af = B.af[i]
            if any(a <= af <= b for a, b, _ in LOCK): continue
            if bf is None or i == (r['n0'] + r['n1']) // 2: bf = round(float(af), 3)
        if bf is None or min(abs(bf - k) for k in pk) < 0.03: continue
        for A in (C.P, C.D):
            pose = A.rig.evalfn(bf) if A.rig.evalfn else r6.sample(A.clip, bf)
            r6.put(A.clip, bf, None, **pose)
        peaks.append(bf)
    for A in (C.P, C.D):
        A.rig.evalfn = None; A.rig.invalidate()
    log += posefix.run(peaks, verbose=False)
    log.append('final targeted pass: %d keys at the deepest remaining frames' % len(peaks))
    if verbose: print(log[-1], flush=True)
    rebuild()
    B = qa2.Bake(S.warp)
    return log, B
