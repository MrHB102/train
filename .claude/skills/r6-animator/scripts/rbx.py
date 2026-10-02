#!/usr/bin/env python3
"""rbx.py - Roblox .rbxm/.rbxmx (binary or XML) -> KeyframeSequence extractor.  stdlib only.

CLI:  python rbx.py FILE [FILE...]        # prints one-line summary per KeyframeSequence
API:  sequences(path) -> list[dict]       # raw sequences (joint-space CFrames, see below)
      write_rbxmx(seq, path)              # raw sequence -> .rbxmx that Studio can import

Raw sequence = {name, loop, priority, hip, path, kfs:[{t, name, poses:{pose_name:{cf:[x,y,z,r00..r22],
                 es:int, ed:int, w:float}}, markers:[...]}]}   (cf is the Roblox Pose.CFrame as-is)
"""
import struct, sys, os, re, math
import xml.etree.ElementTree as ET

# ------------------------------------------------------------------ LZ4 (block) -------------------
def lz4_block(src, usize):
    dst = bytearray(); i = 0; n = len(src)
    while i < n:
        tok = src[i]; i += 1; ll = tok >> 4
        if ll == 15:
            while True:
                b = src[i]; i += 1; ll += b
                if b != 255: break
        dst += src[i:i + ll]; i += ll
        if i >= n: break
        off = src[i] | (src[i + 1] << 8); i += 2; ml = tok & 15
        if ml == 15:
            while True:
                b = src[i]; i += 1; ml += b
                if b != 255: break
        ml += 4; s = len(dst) - off
        if off >= ml: dst += dst[s:s + ml]
        else:
            for k in range(ml): dst.append(dst[s + k])
    if len(dst) != usize: raise ValueError("lz4 size mismatch %d!=%d" % (len(dst), usize))
    return bytes(dst)

# ------------------------------------------------------------------ binary helpers ----------------
def _deint(d, o, cnt, size):
    """interleaved big-endian values -> list of unsigned ints; returns (vals, new_offset)"""
    raw = d[o:o + cnt * size]
    out = []
    for i in range(cnt):
        v = 0
        for j in range(size): v = (v << 8) | raw[j * cnt + i]
        out.append(v)
    return out, o + cnt * size

def _zz(v): return (v >> 1) ^ -(v & 1)
def _f(v): return struct.unpack('<f', struct.pack('<I', ((v >> 1) | ((v & 1) << 31)) & 0xFFFFFFFF))[0]

# the 24 axis-aligned rotations Roblox encodes with a one-byte id
_ROT = {
 0x02:(1,0,0,0,1,0,0,0,1), 0x03:(1,0,0,0,0,-1,0,1,0), 0x05:(1,0,0,0,-1,0,0,0,-1), 0x06:(1,0,0,0,0,1,0,-1,0),
 0x07:(0,1,0,1,0,0,0,0,-1), 0x09:(0,0,1,1,0,0,0,1,0), 0x0a:(0,-1,0,1,0,0,0,0,1), 0x0c:(0,0,-1,1,0,0,0,-1,0),
 0x0d:(0,1,0,0,0,1,1,0,0), 0x0e:(0,0,-1,0,1,0,1,0,0), 0x10:(0,-1,0,0,0,-1,1,0,0), 0x11:(0,0,1,0,-1,0,1,0,0),
 0x14:(-1,0,0,0,1,0,0,0,-1), 0x15:(-1,0,0,0,0,1,0,1,0), 0x17:(-1,0,0,0,-1,0,0,0,1), 0x18:(-1,0,0,0,0,-1,0,-1,0),
 0x19:(0,1,0,-1,0,0,0,0,1), 0x1b:(0,0,-1,-1,0,0,0,1,0), 0x1c:(0,-1,0,-1,0,0,0,0,-1), 0x1e:(0,0,1,-1,0,0,0,-1,0),
 0x1f:(0,1,0,0,0,-1,-1,0,0), 0x20:(0,0,1,0,1,0,-1,0,0), 0x22:(0,-1,0,0,0,1,-1,0,0), 0x23:(0,0,-1,0,-1,0,-1,0,0)}

_WANT = {'KeyframeSequence', 'Keyframe', 'Pose', 'KeyframeMarker', 'Folder', 'Model', 'Animation', 'Motor6D', 'Part', 'MeshPart'}

class RootList(list):
    insts = {}

def _read_values(d, o, t, cnt):
    """decode one PROP column; returns list or None when type unsupported"""
    if t == 0x01:  # string
        out = []
        for _ in range(cnt):
            l, = struct.unpack_from('<I', d, o); o += 4
            out.append(d[o:o + l].decode('utf-8', 'replace')); o += l
        return out
    if t == 0x02: return [bool(x) for x in d[o:o + cnt]]
    if t == 0x03: return [_zz(x) for x in _deint(d, o, cnt, 4)[0]]
    if t == 0x04: return [_f(x) for x in _deint(d, o, cnt, 4)[0]]
    if t == 0x05: return list(struct.unpack_from('<%dd' % cnt, d, o))
    if t == 0x12: return _deint(d, o, cnt, 4)[0]
    if t == 0x13:
        v = [_zz(x) for x in _deint(d, o, cnt, 4)[0]]; a = 0; out = []
        for x in v: a += x; out.append(a)
        return out
    if t == 0x10:  # CFrame
        rots = []
        for _ in range(cnt):
            rid = d[o]; o += 1
            if rid == 0:
                rots.append(struct.unpack_from('<9f', d, o)); o += 36
            else: rots.append(_ROT[rid])
        xs, o = _deint(d, o, cnt, 4); ys, o = _deint(d, o, cnt, 4); zs, o = _deint(d, o, cnt, 4)
        return [[_f(xs[i]), _f(ys[i]), _f(zs[i])] + list(rots[i]) for i in range(cnt)]
    return None

class Inst:
    __slots__ = ('id', 'cls', 'p', 'kids', 'parent')
    def __init__(s, i, c): s.id = i; s.cls = c; s.p = {}; s.kids = []; s.parent = None

def parse_binary(b):
    ncls, ninst = struct.unpack_from('<ii', b, 16); o = 32
    classes = {}; insts = {}; roots = RootList(); roots.insts = insts
    while o < len(b):
        name = b[o:o + 4]; cl, ul, _ = struct.unpack_from('<III', b, o + 4); o += 16
        if cl == 0: d = b[o:o + ul]; o += ul
        else: d = lz4_block(b[o:o + cl], ul); o += cl
        if name == b'INST':
            cid, l = struct.unpack_from('<II', d, 0); cname = d[8:8 + l].decode(); p = 8 + l
            svc = d[p]; p += 1; cnt, = struct.unpack_from('<I', d, p); p += 4
            ids = [_zz(x) for x in _deint(d, p, cnt, 4)[0]]; a = 0; refs = []
            for x in ids: a += x; refs.append(a)
            classes[cid] = (cname, refs)
            for r in refs: insts[r] = Inst(r, cname)
        elif name == b'PROP':
            cid, l = struct.unpack_from('<II', d, 0); pname = d[8:8 + l].decode(); t = d[8 + l]
            cname, refs = classes[cid]
            if cname not in _WANT: continue
            try: vals = _read_values(d, 9 + l, t, len(refs))
            except Exception: vals = None
            if vals is None: continue
            for r, v in zip(refs, vals): insts[r].p[pname] = v
        elif name == b'PRNT':
            cnt, = struct.unpack_from('<I', d, 1); p = 5
            ch, p = _deint(d, p, cnt, 4); pa, p = _deint(d, p, cnt, 4)
            a = 0; chs = []
            for x in ch: a += _zz(x); chs.append(a)
            a = 0; pas = []
            for x in pa: a += _zz(x); pas.append(a)
            for c, pr in zip(chs, pas):
                if pr == -1: roots.append(insts[c])
                else: insts[c].parent = insts[pr]; insts[pr].kids.append(insts[c])
        elif name.startswith(b'END'): break
    return roots

def parse_xml(text):
    root = ET.fromstring(text); roots = []
    def conv(e, parent):
        ins = Inst(0, e.get('class')); ins.parent = parent
        pr = e.find('Properties')
        if pr is not None and ins.cls in _WANT:
            for p in pr:
                n = p.get('name'); t = p.tag
                if t == 'string': ins.p[n] = p.text or ''
                elif t == 'bool': ins.p[n] = (p.text or '').strip() == 'true'
                elif t in ('float', 'double'): ins.p[n] = float(p.text)
                elif t in ('int', 'token'): ins.p[n] = int(p.text)
                elif t == 'CoordinateFrame':
                    g = lambda k: float(p.find(k).text)
                    ins.p[n] = [g('X'), g('Y'), g('Z')] + [g('R%d%d' % (i, j)) for i in range(3) for j in range(3)]
        for c in e.findall('Item'): ins.kids.append(conv(c, ins))
        return ins
    for e in root.findall('Item'): roots.append(conv(e, None))
    return roots

def _walk(n):
    yield n
    for k in n.kids: yield from _walk(k)

def _pose_walk(po, out):
    nm = po.p.get('Name', '?')
    if nm not in out or po.p.get('Weight', 1.0) > 0:
        out[nm] = {'cf': list(po.p.get('CFrame', [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1])),
                   'es': po.p.get('EasingStyle', 0), 'ed': po.p.get('EasingDirection', 0),
                   'w': po.p.get('Weight', 1.0)}
    for k in po.kids:
        if k.cls == 'Pose': _pose_walk(k, out)

def load(path):
    with open(path, 'rb') as f: b = f.read()
    if b[:8] == b'<roblox!': return parse_binary(b)
    return parse_xml(b.decode('utf-8', 'replace'))

def sequences(path):
    out = []
    for r in load(path):
        for n in _walk(r):
            if n.cls != 'KeyframeSequence': continue
            ctx = []; a = n.parent
            while a is not None: ctx.append(a.p.get('Name', a.cls)); a = a.parent
            kfs = []
            for kf in n.kids:
                if kf.cls != 'Keyframe': continue
                poses = {}
                for po in kf.kids:
                    if po.cls == 'Pose': _pose_walk(po, poses)
                mk = [m.p.get('Name', '') for m in kf.kids if m.cls == 'KeyframeMarker']
                kfs.append({'t': kf.p.get('Time', 0.0), 'name': kf.p.get('Name', 'Keyframe'), 'poses': poses, 'markers': mk})
            kfs.sort(key=lambda k: k['t'])
            out.append({'name': n.p.get('Name', 'KeyframeSequence'), 'loop': n.p.get('Loop', False),
                        'priority': n.p.get('Priority', 1000), 'hip': n.p.get('AuthoredHipHeight', 0.0),
                        'path': '/'.join(reversed(ctx)), 'kfs': kfs})
    return out

def rig_info(path):
    """Motor6D C0/C1 found in the file (to confirm the rig is the canonical R6)."""
    out = {}; R = load(path); ins = getattr(R, 'insts', {})
    for r in R:
        for n in _walk(r):
            if n.cls == 'Motor6D':
                p0 = ins.get(n.p.get('Part0')); p1 = ins.get(n.p.get('Part1'))
                key = (n.parent.p.get('Name', '?') if n.parent else '?') + '/' + n.p.get('Name', '?')
                out[key] = {'C0': n.p.get('C0'), 'C1': n.p.get('C1'),
                            'p0': p0.p.get('Name') if p0 else None, 'p1': p1.p.get('Name') if p1 else None}
    return out

# ------------------------------------------------------------------ writer (.rbxmx) ---------------
def write_rbxmx(seqs, path):
    """seqs: raw sequence dict or list of them (same schema as sequences()). Studio: drag into the Animation Editor / Insert."""
    if isinstance(seqs, dict): seqs = [seqs]
    L = ['<roblox version="4">']; n = [0]
    def ref():
        n[0] += 1; return 'RBX%d' % n[0]
    def esc(s): return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    def pose(name, d, kids):
        cf = d['cf']; x = ['<Item class="Pose" referent="%s"><Properties>' % ref(),
            '<string name="Name">%s</string>' % esc(name),
            '<CoordinateFrame name="CFrame"><X>%.6g</X><Y>%.6g</Y><Z>%.6g</Z>' % tuple(cf[:3]) +
            ''.join('<R%d%d>%.7g</R%d%d>' % (i, j, cf[3 + i * 3 + j], i, j) for i in range(3) for j in range(3)) + '</CoordinateFrame>',
            '<token name="EasingDirection">%d</token><token name="EasingStyle">%d</token>' % (d.get('ed', 1), d.get('es', 5)),
            '<float name="Weight">%.6g</float></Properties>' % d.get('w', 1.0)]
        return ''.join(x) + kids + '</Item>'
    # canonical R6 pose tree: HumanoidRootPart > Torso > (Head, Left Arm, Right Arm, Left Leg, Right Leg)
    ident = {'cf': [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1], 'es': 0, 'ed': 0, 'w': 0.0}
    for s in seqs:
        L.append('<Item class="KeyframeSequence" referent="%s"><Properties><string name="Name">%s</string>'
                 '<bool name="Loop">%s</bool><token name="Priority">%d</token></Properties>' % (ref(), esc(s['name']), 'true' if s['loop'] else 'false', s['priority']))
        for k in s['kfs']:
            P = k['poses']
            limbs = ''.join(pose(nm, P[nm], '') for nm in ('Head', 'Left Arm', 'Right Arm', 'Left Leg', 'Right Leg') if nm in P)
            torso = pose('Torso', P.get('Torso', ident), limbs)
            hrp = pose('HumanoidRootPart', P.get('HumanoidRootPart', ident), torso)
            L.append('<Item class="Keyframe" referent="%s"><Properties><string name="Name">%s</string><float name="Time">%.6g</float></Properties>%s</Item>'
                     % (ref(), esc(k.get('name', 'Keyframe')), k['t'], hrp))
        L.append('</Item>')
    L.append('</roblox>')
    with open(path, 'w', encoding='utf-8') as f: f.write('\n'.join(L))
    return path

if __name__ == '__main__':
    for f in sys.argv[1:]:
        ss = sequences(f)
        print('%s: %d KeyframeSequence' % (os.path.basename(f), len(ss)))
        for s in ss:
            ln = s['kfs'][-1]['t'] if s['kfs'] else 0
            print('  %-28s kf=%-3d len=%.3fs loop=%s prio=%s path=%s' % (s['name'], len(s['kfs']), ln, s['loop'], s['priority'], s['path']))
