#!/usr/bin/env python3
"""db.py - the animation database (data/anims.json) + CLI.  stdlib only.  Output is deliberately tiny (token-cheap).

  python db.py ls                         one line per animation
  python db.py find walk run loop         ranked matches (tags + description)
  python db.py show ID                    description, style notes, phases, flags   (default, ~150 tokens)
  python db.py show ID                    reference notes and aggregate metrics ONLY; keys/raw are blocked
  python db.py style                      learned style rules (read this before animating in the house style)
  python db.py ingest FILE.rbxm [...]     extract every KeyframeSequence of a .rbxm/.rbxmx (binary or xml), analyse, add to the DB
        [--prefix manji] [--id Dummy/ManjiRaw=manji.dummy]   (keeps hand-written desc/tags/style of entries that already exist)
  python db.py set ID desc|tags|style|rig "text"   edit a curated field          python db.py reindex
  python db.py add clip.json [--id x]     add a clip dumped from Blender (r6.dump)
"""
import json, os, sys, re, math
HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(os.path.dirname(HERE), 'data')
sys.path.insert(0, HERE)
import r6

P_DB = os.path.join(DATA, 'anims.json'); P_IX = os.path.join(DATA, 'index.json'); P_ST = os.path.join(DATA, 'style.json')
_cache = {}
def _load(p, default):
    if p in _cache: return _cache[p]
    try:
        with open(p, encoding='utf-8') as f: _cache[p] = json.load(f)
    except FileNotFoundError: _cache[p] = default
    return _cache[p]
def reference_record(record):
    """Discard executable motion channels, including from older imported databases."""
    return {k: v for k, v in record.items() if k not in ('keys', 'raw', 'ext')}
def db():
    d = _load(P_DB, {'schema': 2, 'anims': {}})
    for v in d['anims'].values():
        for k in ('keys', 'raw', 'ext'): v.pop(k, None)
    d['schema'] = 2; d['policy'] = 'inspiration-only'
    return d
def get(i):
    a = db()['anims']
    if i not in a:
        m = [k for k in a if i.lower() in k.lower()]
        if len(m) == 1: return a[m[0]]
        raise KeyError("unknown id '%s'. try: %s" % (i, ', '.join(list(a)[:12])))
    return a[i]
def save():
    d = db(); os.makedirs(DATA, exist_ok=True)
    with open(P_DB, 'w', encoding='utf-8') as f: json.dump(d, f, separators=(',', ':'), ensure_ascii=False)
    with open(P_IX, 'w', encoding='utf-8') as f:
        json.dump([{'id': k, 'kind': v.get('kind'), 'len': v.get('len'), 'loop': v.get('loop'), 'tags': v.get('tags', []), 'd': (v.get('desc') or v.get('auto') or '')[:150]}
                   for k, v in d['anims'].items()], f, separators=(',', ':'), ensure_ascii=False)

# ------------------------------------------------------------------ ingest --------------------------
def _slug(s): return re.sub(r'[^a-z0-9]+', '_', s.lower()).strip('_')
def _ext_stats(names, series, fps, loop):
    """chain analysis for non-R6 joints (tail, ears...): dominant axis, amplitude, lag between neighbours"""
    out = {}
    chain = sorted([n for n in names if re.match(r'^[A-Za-z]+\d*$', n) and re.search(r'(Tail|tail)', n)], key=lambda n: int(re.sub(r'\D', '', n) or 1))
    if not chain: return out
    amps = []; lags = []; ax = None
    for n in chain:
        s = series[n]; rg = [max(v[j] for v in s) - min(v[j] for v in s) for j in range(3)]
        if ax is None: ax = max(range(3), key=lambda j: rg[j])
        amps.append(rg[ax] / 2)
    live = [n for n, a in zip(chain, amps) if a > 0.3]
    for a, b in zip(live, live[1:]):
        x = [v[ax] for v in series[a]]; y = [v[ax] for v in series[b]]; N = len(x)
        mx, my = sum(x) / N, sum(y) / N; best = (-9, 0)
        for sh in range(0, N // 2):
            c = sum((x[(i) % N] - mx) * (y[(i + sh) % N] - my) for i in range(N)) if loop else sum((x[i] - mx) * (y[i + sh] - my) for i in range(N - sh))
            if c > best[0]: best = (c, sh)
        lags.append(best[1])
    if lags:
        lags.sort(); out['tail'] = {'links': len(live), 'axis': 'xyz'[ax], 'amp_base': round(amps[0], 1), 'amp_tip': round(amps[len(live) - 1], 1),
                                    'amp_max': round(max(amps), 1), 'lag_frames_per_link': lags[len(lags) // 2], 'lag_ms_per_link': int(1000 * lags[len(lags) // 2] / fps)}
    return out

def ingest(path, prefix=None, ids=None, td=2.0, tp=0.03):
    import rbx, style
    ids = ids or {}; stem = re.sub(r'^[0-9a-f]{8}-', '', os.path.splitext(os.path.basename(path))[0]); prefix = prefix or _slug(stem)
    added = []
    for seq in rbx.sequences(path):
        names = set(n for k in seq['kfs'] for n in k['poses'])
        limbs = names & {'Head', 'Left Arm', 'Right Arm', 'Left Leg', 'Right Leg'}
        key = seq['path'].split('/')[0] + '/' + seq['name']
        aid = ids.get(key) or ids.get(seq['name']) or '%s.%s' % (prefix, _slug(seq['path'].split('/')[0] + '_' + seq['name']))
        old = db()['anims'].get(aid, {}); times = [k['t'] for k in seq['kfs']]
        rec = {'name': seq['name'], 'src': '%s | %s' % (os.path.basename(path), seq['path']), 'fps': style.grid_fps(times), 'len': round(times[-1], 3),
               'loop': bool(seq['loop']), 'prio': seq['priority']}
        if not limbs:                                                                   # camera / prop rig: keep raw, no R6 maths
            rec.update(kind='camera', rig=','.join(sorted(names)),
                       raw=[[round(k['t'], 4), {n: [round(x, 3) for x in p['cf'][:3]] + [round(math.degrees(a), 2) for a in r6.to_yxz(tuple(p['cf'][3:12]))]
                                               for n, p in k['poses'].items()}] for k in seq['kfs']])
            rec['auto'] = 'camera/prop rig (%s), %d keys, %.2fs; pose = [x,y,z, pitch,yaw,roll deg (YXZ)]' % (','.join(sorted(names)), len(seq['kfs']), times[-1])
        else:
            c = r6.from_raw(seq, rec['fps']); a = style.analyze(c, td, tp)
            ext = sorted(n for n in names if n not in r6.J)
            rec.update(kind='char', rig='r6' + ('+%d ext joints' % len(ext) if ext else ''), m=a['m'], phases=a['phases'], flags=a['flags'],
                       keys=r6.clip_json(a['keys'], 1), raw=r6.clip_json(c, 2), auto=style.auto_text(a))
            if ext:
                series = {n: [] for n in ext}; ser_t = []
                for k in seq['kfs']:
                    for n in ext:
                        p = k['poses'].get(n); cf = p['cf'] if p else [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1]
                        series[n].append([math.degrees(x) for x in r6.to_xyz(tuple(cf[3:12]))] + list(cf[:3]))
                rec['ext'] = {'joints': ext, 'frame': 'joint space: [rotX,rotY,rotZ deg (CFrame.Angles order), x,y,z]',
                              'raw': [[round(kf['t'], 4)] + [[round(v, 1) for v in series[n][i]] for n in ext] for i, kf in enumerate(seq['kfs'])]}
                rec['m_ext'] = _ext_stats(ext, series, rec['fps'], rec['loop'])
        for f in ('desc', 'tags', 'style', 'rig_note'):
            if f in old: rec[f] = old[f]
        db()['anims'][aid] = reference_record(rec); added.append(aid)
    save(); return added

def add_clip(path, aid=None):
    import style
    with open(path, encoding='utf-8') as f: d = json.load(f)
    c = r6.clip_from_json(d['keys'], d.get('name', 'clip'), d.get('fps', 30), d.get('loop', False)); a = style.analyze(c)
    aid = aid or 'mine.' + _slug(d.get('name', 'clip'))
    db()['anims'][aid] = {'name': d.get('name', 'clip'), 'src': 'blender', 'fps': c['fps'], 'len': round(r6.length(c), 3), 'loop': c['loop'], 'kind': 'char', 'rig': 'r6',
                          'm': a['m'], 'phases': a['phases'], 'flags': a['flags'], 'keys': r6.clip_json(a['keys'], 1), 'raw': r6.clip_json(c, 2), 'auto': style.auto_text(a)}
    db()['anims'][aid] = reference_record(db()['anims'][aid])
    save(); return aid

# ------------------------------------------------------------------ query / print -------------------
def table(keys, fps, bones=None):
    raise ValueError('Database pose tables are disabled. Study summaries and author new motion.')
def one(k, v):
    return '%-18s %4.2fs %-6s %-24s %s' % (k, v.get('len', 0), v.get('kind', ''), ','.join(v.get('tags', []))[:24], (v.get('desc') or v.get('auto') or '')[:90])
def find(q, n=6):
    toks = [t.lower() for t in re.split(r'\W+', q) if t]; rows = []
    for k, v in db()['anims'].items():
        hay = ' '.join([k, v.get('name', ''), ' '.join(v.get('tags', [])), v.get('desc', ''), v.get('auto', ''), ' '.join(v.get('style', []))]).lower()
        s = sum((3 if t in v.get('tags', []) else 0) + hay.count(t) for t in toks)
        if s: rows.append((s, k, v))
    rows.sort(key=lambda r: -r[0]); return [one(k, v) for s, k, v in rows[:n]] or ['no match; try: db.py ls']
def show(i, mode='brief', bones=None, t_rng=None, mx=0):
    a = get(i); i = [k for k, v in db()['anims'].items() if v is a][0]
    if mode != 'brief':
        raise ValueError('Reference-only database: keys/raw are disabled. Author original poses from the brief.')
    o = ['%s  "%s"  %s  %.2fs @%sfps loop=%s  rig=%s' % (i, a['name'], a['kind'], a['len'], a['fps'], a['loop'], a['rig']), 'tags: ' + ', '.join(a.get('tags', []))]
    o.append(a.get('desc') or a.get('auto', '')); o += ['- ' + s for s in a.get('style', [])]
    if a.get('phases'): o.append('phases: ' + ' | '.join('%s %.2f-%.2fs%s' % (p[0], p[1], p[2], (' %s' % p[4]) if p[0] == 'snap' else '') for p in a['phases']))
    if a.get('m_ext'): o.append('ext: ' + json.dumps(a['m_ext']))
    if a.get('m'): o.append('aggregate metrics: ' + json.dumps(a['m'], ensure_ascii=False))
    for f in a.get('flags', []): o.append('! ' + f)
    return '\n'.join(o)
def style_rules():
    s = _load(P_ST, {})
    if not s: return 'no style profile yet: run  python db.py ingest ...  then build style.json'
    o = ['STYLE PROFILE  (%s)' % s.get('basis', ''), s.get('application', 'Conditional inspiration only.')]
    for sec, items in s.get('rules', {}).items(): o.append('[%s]' % sec); o += ['- ' + x for x in items]
    return '\n'.join(o)

def main(a):
    if not a or a[0] in ('-h', '--help'): print(__doc__); return
    c, r = a[0], a[1:]
    if c == 'ls': print('\n'.join(one(k, v) for k, v in db()['anims'].items()))
    elif c == 'find': print('\n'.join(find(' '.join(r))))
    elif c == 'show':
        g = lambda f: r[r.index(f) + 1] if f in r else None
        tr = [float(x) for x in g('--t').split('-')] if g('--t') else None
        print(show(r[0], 'keys' if '--keys' in r else 'raw' if '--raw' in r else 'brief', g('--bones').split(',') if g('--bones') else None, tr, int(g('--max') or 0)))
    elif c == 'style': print(style_rules())
    elif c == 'reindex': save(); print('ok')
    elif c == 'set':
        if r[1] not in ('desc', 'tags', 'style', 'rig_note'):
            raise ValueError('Only desc/tags/style/rig_note can be curated')
        x = get(r[0]); x[r[1]] = [s.strip() for s in r[2].split(',')] if r[1] in ('tags', 'style') else r[2]; save(); print('ok')
    elif c == 'add': print(add_clip(r[0], r[r.index('--id') + 1] if '--id' in r else None))
    elif c == 'ingest':
        pre = r[r.index('--prefix') + 1] if '--prefix' in r else None
        ids = {}
        for i, x in enumerate(r):
            if x == '--id': k, v = r[i + 1].split('='); ids[k] = v
        files = [x for i, x in enumerate(r) if not x.startswith('--') and (i == 0 or r[i - 1] not in ('--prefix', '--id'))]
        for f in files: print(f, '->', ', '.join(ingest(f, pre, ids)))
    else: print(__doc__)

if __name__ == '__main__':
    try: main(sys.argv[1:])
    except (ValueError, KeyError, IndexError, OSError) as e:
        print('%s: %s' % (type(e).__name__, e), file=sys.stderr); sys.exit(2)
