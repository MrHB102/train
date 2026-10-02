#!/usr/bin/env python3
"""r6-animator MCP server (stdio, stdlib only).  Companion of the OFFICIAL Blender MCP - it does not talk to Blender.
It gives the model cheap access to the animation database, the linter, offline image previews and Roblox export,
so those never have to be pasted through execute_blender_code.

Register once:   claude mcp add r6-animator -- python3 <this file>        (or run install.py, which does it for you)
Tools (kept terse on purpose, every description costs tokens in every session):
  r6_find     search reference summaries                    r6_show    summary and aggregate metrics only
  r6_style    learned house-style rules                     r6_ingest  add the KeyframeSequences of a .rbxm/.rbxmx to the DB
  r6_lint     lint an authored r6 table                     r6_preview PNG of project-authored motion only
  r6_qa       sampled support/loop checks                   r6_video_reference prepare real video frames; analysis requires vision
  r6_export   r6 table -> .rbxmx for Roblox Studio          r6_boot    the one-line Blender bootstrap with the absolute path
"""
import sys, os, json, base64, tempfile, traceback, io, contextlib

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import r6, db

def _clip(a):
    """throw-away clip from an r6 table ({table,fps,loop}); the working clip is restored by the caller"""
    if not a.get('table'): raise ValueError('give "table" (r6 table text)')
    r6.new(a.get('name', 'clip'), float(a.get('fps', 30)), bool(a.get('loop', False)), a.get('ease', 'out')); r6.table(a['table'])
    import math
    if not r6.cur()['keys']: raise ValueError('table has no keys')
    if any(not math.isfinite(f) or any(not math.isfinite(v) for vals in k['b'].values() for v in vals) for f,k in r6.cur()['keys'].items()):
        raise ValueError('non-finite frame or pose')
    return r6.cur()

@contextlib.contextmanager
def _scratch():
    saved = r6._S['clip']
    try: yield
    finally: r6._S['clip'] = saved

def t_find(a): return '\n'.join(db.find(a['query'], int(a.get('n', 6))))
def t_show(a):
    tr = [float(x) for x in a['t'].split('-')] if a.get('t') else None
    return db.show(a['id'], a.get('mode', 'brief'), a['bones'].split(',') if a.get('bones') else None, tr, int(a.get('max', 0)))
def t_style(a): return db.style_rules()
def t_ingest(a):
    ids = {}
    for kv in a.get('ids', []): k, v = kv.split('='); ids[k] = v
    return '\n'.join(db.ingest(a['path'], a.get('prefix'), ids))
def t_lint(a):
    with _scratch(): _clip(a); return r6.check()
def t_export(a):
    with _scratch(): _clip(a); return r6.export(a.get('path') or os.path.join(tempfile.gettempdir(), r6.cur()['name'] + '.rbxmx'), bool(a.get('bake', False)))
def t_boot(a): return 'import sys; sys.path.insert(0, %r); import r6' % HERE
def t_preview(a):
    if a.get('id'): raise ValueError('Database previews are disabled; give a project-authored table')
    try: import preview
    except Exception as e: return 'preview needs matplotlib+numpy (pip install matplotlib numpy): %s' % e
    with _scratch():
        c = _clip(a)
        n = int(a.get('n', 8)); views = tuple(a.get('views', '3q,side').split(','))
        p = os.path.join(tempfile.gettempdir(), 'r6_preview_%d.png' % os.getpid())
        preview.sheet(c, p, n=n, views=views, tile=float(a.get('tile', 2.4)), cols=int(a.get('cols', 4)), fr=[float(x) for x in a['fr']] if a.get('fr') else ('keys' if a.get('keys') else None), zoom=float(a.get('zoom', 1.0)))
        with open(p, 'rb') as f: data = base64.b64encode(f.read()).decode()
        return [{'type': 'text', 'text': '%s %.2fs: %s, rows = views %s' % (c['name'], r6.length(c), 'key frames' if a.get('keys') else '%d frames evenly spaced' % n, ','.join(views))},
                {'type': 'image', 'data': data, 'mimeType': 'image/png'}]

def t_qa(a):
    import qa
    with _scratch(): return json.dumps(qa.assess(_clip(a), a.get('plan')), ensure_ascii=False)

def t_video(a):
    import video_reference
    r = video_reference.prepare(a['source'], a['out'], float(a.get('start',0)), float(a.get('duration',10)), int(a.get('frames',12)), a.get('times'))
    with open(r['contact_sheet'],'rb') as f: data=base64.b64encode(f.read()).decode()
    return [{'type':'text','text':json.dumps(r,ensure_ascii=False)},
            {'type':'image','mimeType':'image/jpeg','data':data}]

S = lambda props, req=(): {'type': 'object', 'properties': props, 'required': list(req)}
STR = lambda d: {'type': 'string', 'description': d}
NUM = lambda d: {'type': 'number', 'description': d}
SRC = {'table': STR('r6 table text (header: f bones... ease)'), 'fps': NUM('clip fps, default 30'), 'loop': {'type': 'boolean'}}
TOOLS = [
    ('r6_find', 'Search the R6 animation database (ranked, 1 line each).', S({'query': STR('words, e.g. "run loop tail"'), 'n': NUM('max rows')}, ['query']), t_find),
    ('r6_show', 'Reference-only summary and aggregate metrics. No poses, keys, loading or retargeting.', S({'id': STR('reference id'), 'mode': {'type': 'string', 'enum': ['brief']}}, ['id']), t_show),
    ('r6_style', 'Learned house-style rules (timing, easing, poses, follow-through, camera).', S({}), t_style),
    ('r6_ingest', 'Add every KeyframeSequence of a .rbxm/.rbxmx to the database (analysed + pose-to-pose reduced).', S({'path': STR('file'), 'prefix': STR('id prefix'), 'ids': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Source/Name=newid'}}, ['path']), t_ingest),
    ('r6_lint', 'Lint an r6 table: joint limits, limbs through the body, sunk feet, pops, loop gap, missing torso motion.', S(SRC, ['table']), t_lint),
    ('r6_preview', 'Offline PNG of your project-authored table only. Not Blender playback or a quality certificate.', S(dict(SRC, n=NUM('frames, default 8'), views=STR('comma list, default 3q,side'), keys={'type': 'boolean', 'description': 'key frames instead of even sampling'}, tile=NUM('tile size, default 2.4'), zoom=NUM('window zoom, 1.8 = shoulders close-up'), fr={'type': 'array', 'items': {'type': 'number'}, 'description': 'explicit frames'}), ['table']), t_preview),
    ('r6_qa', 'Sample an authored R6 table for finite channels, declared ground/support and loop pose/velocity. No visual or Blender certification.', S(dict(SRC, plan={'type':'object','description':'duration_s, grounded intervals and plants with bone/start_s/end_s/tolerance; seconds/studs'}), ['table']), t_qa),
    ('r6_video_reference', 'Prepare actual local/public video as timestamped frames, contact sheet and proxy. You must visually inspect before analysis; no keyframes extracted.', S({'source':STR('local file or public HTTP(S) video URL'), 'out':STR('new/empty output folder'), 'start':NUM('source seconds, default 0'), 'duration':NUM('seconds, default 10, maximum 120'), 'frames':NUM('2–64 samples, default 12'), 'times':{'type':'array','items':{'type':'number'},'description':'optional absolute source sample times'}}, ['source','out']), t_video),
    ('r6_export', 'Write a .rbxmx KeyframeSequence (for Roblox Studio) from an r6 table.', S(dict(SRC, path=STR('output file'), bake={'type': 'boolean'}), ['table']), t_export),
    ('r6_boot', 'One-line python that makes `import r6` work inside Blender (for execute_blender_code).', S({}), t_boot),
]
BYNAME = {t[0]: t for t in TOOLS}

def handle(m):
    mid, meth, p = m.get('id'), m.get('method'), m.get('params') or {}
    if meth == 'initialize':
        return {'protocolVersion': p.get('protocolVersion', '2024-11-05'), 'capabilities': {'tools': {}}, 'serverInfo': {'name': 'r6-animator', 'version': '3.0.0'},
                'instructions': 'Author original motion. Database summaries are inspiration only; no keys/raw/presets. Video preparation is not visual analysis. Blender uses a separate connection.'}
    if meth == 'ping': return {}
    if meth == 'tools/list': return {'tools': [{'name': n, 'description': d, 'inputSchema': s} for n, d, s, _ in TOOLS]}
    if meth == 'tools/call':
        name = p.get('name'); a = p.get('arguments') or {}
        if name not in BYNAME: raise KeyError('unknown tool ' + str(name))
        try:
            with contextlib.redirect_stdout(sys.stderr): out = BYNAME[name][3](a)
            return {'content': out if isinstance(out, list) else [{'type': 'text', 'text': str(out)}]}
        except Exception as e:
            return {'isError': True, 'content': [{'type': 'text', 'text': '%s: %s' % (type(e).__name__, e)}]}
    raise LookupError(meth)

def main():
    out = sys.stdout
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        try: m = json.loads(line)
        except Exception: continue
        if 'id' not in m: continue                       # notification (initialized, cancelled, ...)
        try: res = {'jsonrpc': '2.0', 'id': m['id'], 'result': handle(m)}
        except LookupError as e: res = {'jsonrpc': '2.0', 'id': m['id'], 'error': {'code': -32601, 'message': 'method not found: %s' % e}}
        except Exception as e: res = {'jsonrpc': '2.0', 'id': m['id'], 'error': {'code': -32603, 'message': str(e), 'data': traceback.format_exc()[-400:]}}
        out.write(json.dumps(res, separators=(',', ':')) + '\n'); out.flush()

if __name__ == '__main__': main()
