#!/usr/bin/env python3
"""style.py - measure HOW an R6 clip moves (timing, holds, snaps, easing, overshoot, travel, spin ...) and reduce dense
   keyframes to the pose-to-pose key poses an animator would have set.  stdlib only; used by db.py, not by the AI directly.
   analyze(clip) -> {'m':metrics,'phases':[...],'flags':[...],'keys':reduced clip,'auto':text}
"""
import math, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r6

CH = 6
def grid_fps(times):
    """smallest common frame rate that puts every key on a whole frame"""
    for fps in (24, 30, 45, 48, 60, 72, 90, 120, 240):
        if all(abs(t * fps - round(t * fps)) < 0.06 for t in times): return fps
    return 60

def _unwrap(seq):
    out = [seq[0]]
    for v in seq[1:]:
        p = out[-1]
        while v - p > 180: v -= 360
        while v - p < -180: v += 360
        out.append(v)
    return out

def matrix(c, bones=None):
    """clip -> (times_s, {bone:[[6]*n]}) sampled at every key time, missing bones interpolated, angles unwrapped"""
    fs = r6.frames(c); f0 = fs[0]; T = [(f - f0) / c['fps'] for f in fs]; M = {}
    for b in (bones or r6.BONES[1:]):
        if not any(b in c['keys'][f]['b'] for f in fs): continue
        cols = []
        for f in fs:
            p = r6.sample(c, f); cols.append(p.get(b, [0.0] * 6))
        for ch in range(3): u = _unwrap([v[ch] for v in cols]); [v.__setitem__(ch, x) for v, x in zip(cols, u)]
        M[b] = cols
    return T, M

def _tol(ch, td, tp): return td if ch < 3 else tp
def _seg_err(T, M, i, j, tk, td, tp):
    """max normalised error of the eased straight line i->j over inner keys"""
    e = 0.0
    for k in range(i + 1, j):
        a = r6.ease((T[k] - T[i]) / (T[j] - T[i]), tk)
        for b, col in M.items():
            for ch in range(CH):
                p = col[i][ch] + (col[j][ch] - col[i][ch]) * a
                e = max(e, abs(p - col[k][ch]) / _tol(ch, td, tp))
    return e
def _best(T, M, i, j, td, tp, toks=('lin', 'out', 'in', 'io')):
    best = ('lin', 9e9)
    for tk in toks:
        e = _seg_err(T, M, i, j, tk, td, tp)
        if e < best[1] - 1e-9: best = (tk, e)
    return best

def reduce_keys(c, td=2.0, tp=0.03):
    """pose-to-pose reduction: fewest keys (+ easing per segment) that stay within td degrees / tp studs of every authored key"""
    T, M = matrix(c); n = len(T)
    if n < 3: return c
    keep = {0, n - 1}; stack = [(0, n - 1)]
    while stack:                                               # 1) Ramer-Douglas-Peucker with linear segments
        i, j = stack.pop()
        if j - i < 2: continue
        worst, wk = 0.0, -1
        for k in range(i + 1, j):
            a = (T[k] - T[i]) / (T[j] - T[i]); e = 0.0
            for b, col in M.items():
                for ch in range(CH): e = max(e, abs(col[i][ch] + (col[j][ch] - col[i][ch]) * a - col[k][ch]) / _tol(ch, td, tp))
            if e > worst: worst, wk = e, k
        if worst > 1.0: keep.add(wk); stack += [(i, wk), (wk, j)]
    ks = sorted(keep)
    changed = True
    while changed:                                             # 2) drop keys that an eased segment can replace
        changed = False
        for x in range(1, len(ks) - 1):
            i, j = ks[x - 1], ks[x + 1]; tk, e = _best(T, M, i, j, td, tp)
            if e <= 1.0: del ks[x]; changed = True; break
    out = r6.clip(c['name'], c['fps'], c['loop'], 'out'); fs = r6.frames(c)
    for x, k in enumerate(ks):
        tk = _best(T, M, k, ks[x + 1], td, tp)[0] if x < len(ks) - 1 else 'lin'
        out['keys'][fs[k]] = {'e': tk, 'b': {b: list(col[k]) for b, col in M.items()}}
    return out

def _ang(b, a, z):
    Ra = r6.sem2rw(b, a[:3]); Rz = r6.sem2rw(b, z[:3]); R = r6.mm(r6.mt(Ra), Rz)
    return math.degrees(math.acos(max(-1.0, min(1.0, (R[0] + R[4] + R[8] - 1) / 2))))

def analyze(c, td=2.0, tp=0.03):
    fs = r6.frames(c); fps = c['fps']; T, M = matrix(c); n = len(T); dur = T[-1]; fs_all0 = fs[0]
    flags = []; mt = {'n_raw': n, 'dur': round(dur, 3), 'fps': fps}
    # --- per-segment speeds (max over bones, deg/s) -------------------------------------------------
    seg = []
    for k in range(n - 1):
        dt = T[k + 1] - T[k]; w = 0.0; tot = 0.0
        for b, col in M.items():
            a = _ang(b, col[k], col[k + 1]); tot += a; w = max(w, a)
        seg.append((w / dt, tot / dt, dt, w, tot))
    sp = sorted(s[0] for s in seg); med = sp[len(sp) // 2] if sp else 0
    rest = lambda k: sum(abs(x) for col in M.values() for x in col[k]) < 1.0
    # --- bookends: first/last key far from its neighbour while neighbours are calm -> capture artefact -
    trim0 = trim1 = 0
    if n > 6 and seg[0][0] > max(6 * med, 1500) and not rest(0): trim0 = 1; flags.append('first key (t=0) is a %.0f deg jump from key 2 in %.0f ms: looks like a capture/reset pose, excluded from the key poses' % (seg[0][3], seg[0][2] * 1000))
    if n > 6 and seg[-1][0] > max(6 * med, 1500) and not rest(n - 1): trim1 = 1; flags.append('last key (t=%.2fs) is a %.0f deg jump from the previous key in %.0f ms: looks like a capture/reset pose, excluded from the key poses' % (T[-1], seg[-1][3], seg[-1][2] * 1000))
    if trim0 or trim1:
        c2 = r6.clip(c['name'], fps, c['loop'], c['ease'])
        for f in fs[trim0:n - trim1]: c2['keys'][f] = c['keys'][f]
        c = c2; c['_t0'] = (r6.frames(c)[0] - fs_all0) / fps; fs = r6.frames(c); T, M = matrix(c); n = len(T); dur = T[-1]
        seg = seg[trim0:len(seg) - trim1]
    mt['trim'] = [trim0, trim1]
    # --- dense resample (one sample per grid frame) for energy / holds / bursts ------------------------
    f0 = fs[0]; nf = int(round((fs[-1] - f0))) + 1; en = []; dd = []
    prev = None
    for i in range(nf):
        p = r6.sample(c, f0 + i); cur = {b: [x for x in p.get(b, [0.0] * 6)] for b in M}
        if prev is not None:
            e = 0.0; mx = 0.0
            for b in M: a = _ang(b, prev[b], cur[b]); e += a; mx = max(mx, a)
            en.append(e * fps); dd.append(mx * fps)
        prev = cur
    sm = [sum(en[max(0, i - 1):i + 2]) / len(en[max(0, i - 1):i + 2]) for i in range(len(en))]
    pk = max(sm) if sm else 0; mean = sum(sm) / len(sm) if sm else 0
    cyc = pk / mean < 2.5 if mean else True                  # continuous / cyclic motion: no snaps, no holds
    snap_thr = max(1500.0, 0.30 * pk); hold_thr = min(1200.0, 0.12 * pk)
    holds = []; bursts = []; i = 0; t0 = round(c.get('_t0', 0.0), 4)
    while i < len(sm) and not cyc:
        j = i
        if sm[i] < hold_thr:
            while j < len(sm) and sm[j] < hold_thr: j += 1
            if j - i >= max(3, fps // 10): holds.append((i, j))
        elif sm[i] >= snap_thr:
            while j < len(sm) and sm[j] >= snap_thr * 0.4: j += 1
            bursts.append((i, j))
        else: j = i + 1
        i = max(j, i + 1)
    phases = []
    for a, b in holds: phases.append(['hold', round(t0 + a / fps, 2), round(t0 + b / fps, 2), int(sum(sm[a:b]) / (b - a))])
    for a, b in bursts:
        who = {}
        for k in range(a, min(b, nf - 1)):
            for bn in M: who[bn] = who.get(bn, 0) + _ang(bn, r6.sample(c, f0 + k).get(bn, [0.0] * 6), r6.sample(c, f0 + k + 1).get(bn, [0.0] * 6))
        top = sorted(who, key=lambda x: -who[x])[:3]
        phases.append(['snap', round(t0 + a / fps, 2), round(t0 + b / fps, 2), int(max(sm[a:b])), ' '.join(r6.KEY[x] for x in top)])
    phases.sort(key=lambda p: p[1])
    mt['cyclic'] = bool(cyc); mt['hold_pct'] = round(100 * sum(b - a for a, b in holds) / max(len(sm), 1))
    mt['holds'] = len(holds); mt['t0'] = t0; mt['max_hold_s'] = round(max([(b - a) / fps for a, b in holds] or [0]), 2)
    mt['bursts'] = len(bursts); mt['burst_ms_med'] = int(1000 * sorted([(b - a) / fps for a, b in bursts] or [0])[len(bursts) // 2]) if bursts else 0
    mt['peak_dps'] = int(pk); mt['mean_dps'] = int(mean); mt['punch'] = round(pk / mean, 1) if mean else 0
    # --- range of motion, travel, spin ------------------------------------------------------------------
    rom = {}
    for b, col in M.items():
        r = [round(max(v[ch] for v in col) - min(v[ch] for v in col)) for ch in range(3)]
        if max(r) >= 3: rom[r6.KEY[b]] = r
    mt['rom'] = rom
    if 'Torso' in M:
        col = M['Torso']; hc = matrix(c, ('HumanoidRootPart',))[1].get('HumanoidRootPart'); path = 0.0
        P = [[col[k][ch] + (hc[k][ch] if hc else 0.0) for ch in (3, 4, 5)] for k in range(len(col))]      # torso + root translation
        for k in range(len(P) - 1): path += math.sqrt(sum((P[k + 1][i] - P[k][i]) ** 2 for i in range(3)))
        mt['travel'] = round(path, 2); mt['bob'] = round(max(p[1] for p in P) - min(p[1] for p in P), 2)
        mt['spin'] = int(sum(_ang('Torso', col[k], col[k + 1]) for k in range(len(col) - 1)))
    # --- easing character of the bursts: where is 50 % of the travel reached? (<.5 fast-start/ease-out, >.5 slow-start) ----
    half = []; over = []
    for a, b in bursts:
        if b - a < 3: continue
        bn = max(M, key=lambda x: _ang(x, r6.sample(c, f0 + a).get(x, [0.0] * 6), r6.sample(c, f0 + min(b, nf - 1)).get(x, [0.0] * 6)))
        v0 = r6.sample(c, f0 + a).get(bn, [0.0] * 6); v1 = r6.sample(c, f0 + min(b, nf - 1)).get(bn, [0.0] * 6)
        ch = max(range(3), key=lambda k: abs(v1[k] - v0[k])); tot = v1[ch] - v0[ch]
        if abs(tot) < 8: continue
        prog = [(r6.sample(c, f0 + a + t).get(bn, [0.0] * 6)[ch] - v0[ch]) / tot for t in range(0, b - a + 1)]
        h = next((t for t, x in enumerate(prog) if x >= 0.5), len(prog) - 1) / max(len(prog) - 1, 1); half.append(h)
        over.append(max(0.0, max(prog) - 1.0))
    if half: mt['ease_bias'] = round(sum(half) / len(half), 2)          # <0.45 out-ish, >0.55 in-ish
    if over: mt['overshoot_pct'] = int(100 * sum(over) / len(over))
    # --- loop / periodicity ---------------------------------------------------------------------------------
    if c['loop'] and n > 6:
        a = c['keys'][fs[0]]['b']; z = c['keys'][fs[-1]]['b']
        mt['loop_gap'] = round(max([max(abs(x - y) for x, y in zip(a.get(b, [0] * 6), z.get(b, [0] * 6))) for b in set(a) | set(z)] or [0]), 1)
    red = reduce_keys(c, td, tp); mt['n_key'] = len(red['keys'])
    segs = r6.frames(red); ease = {}
    for f in segs[:-1]: e = red['keys'][f]['e']; ease[e] = ease.get(e, 0) + 1
    mt['ease'] = ease
    gaps = [(segs[i + 1] - segs[i]) / fps for i in range(len(segs) - 1)]
    mt['key_gap_s'] = [round(min(gaps), 3), round(sorted(gaps)[len(gaps) // 2], 3), round(max(gaps), 3)] if gaps else []
    return {'m': mt, 'phases': phases, 'flags': flags, 'keys': red, 'clip': c}

def auto_text(a, name=''):
    m = a['m']; s = ['%.2fs @%dfps, %d authored keys -> %d key poses' % (m['dur'], m['fps'], m['n_raw'], m['n_key'])]
    if m.get('hold_pct', 0) >= 20: s.append('%d%% of the time is held (longest hold %.2fs)' % (m['hold_pct'], m['max_hold_s']))
    if m.get('bursts'): s.append('%d snap bursts, median %d ms, peak %d deg/s (punch x%.1f over the mean)' % (m['bursts'], m['burst_ms_med'], m['peak_dps'], m['punch']))
    if m.get('spin', 0) > 360: s.append('torso turns %d deg in total' % m['spin'])
    if m.get('travel', 0) > 2: s.append('torso travels %.1f studs' % m['travel'])
    big = sorted(m['rom'].items(), key=lambda kv: -max(kv[1]))[:3]
    if big: s.append('biggest movers: ' + ', '.join('%s %d deg' % (k, max(v)) for k, v in big))
    return '; '.join(s)

if __name__ == '__main__':
    import rbx, json
    for f in sys.argv[1:]:
        for sq in rbx.sequences(f):
            c = r6.from_raw(sq, grid_fps([k['t'] for k in sq['kfs']]))
            if not any(b in c['keys'][r6.frames(c)[0]]['b'] for b in ('Right Arm', 'Head', 'Left Leg')): continue
            a = analyze(c); print(sq['name'], json.dumps(a['m'])); print('  ', auto_text(a)); print('  ', a['phases'][:8], a['flags'])
