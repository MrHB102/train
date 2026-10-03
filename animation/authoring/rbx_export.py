"""Roblox export of the v2 animation (for swapping in your own avatar in Roblox Studio).

Writes out/roblox/MrHB_fight.rbxmx and Dummy_fight.rbxmx: one KeyframeSequence each, baked from the same Blender curves
that drive the video (60 keyframes per second, linear between them, so Roblox plays the Bezier motion faithfully).

Root motion: Roblox animations cannot move the HumanoidRootPart, so the whole-body travel is folded into the RootJoint
(the Torso pose).  In Studio: anchor both rigs' HumanoidRootParts at the SAME CFrame (the scene origin, facing the same
way), load each KeyframeSequence on its rig and play them together - the bodies travel relative to that origin exactly as
in the video.  KeyframeMarkers carry the story events: "Hit" (value = strength 1-4) on every impact, "Hide"/"Show" for
the player's blink-teleports, so effects / sounds / transparency can be scripted with GetMarkerReachedSignal.
"""
import math
import os

import choreo as C
import rig as rg
import r6

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUTR = os.path.join(ROOT, 'out', 'roblox')
LIMBS = ('Head', 'Left Arm', 'Right Arm', 'Left Leg', 'Right Leg')


def folded(pose):
    """pose with the HRP motion folded into the Torso (HRP at rest) -> same world transforms for every part"""
    p = rg.Rig.__new__(rg.Rig)
    fk = r6.fk(pose)
    P, Q = fk['Torso']
    rot = r6.rw2sem('Torso', Q)
    t = (P[0], P[1] - r6.HIP_Y, P[2])
    out = {b: list(v) for b, v in pose.items() if b in LIMBS}
    out['Torso'] = [rot[0], rot[1], rot[2], t[0], t[1], -t[2]]
    return out


def _esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def write(path, name, frames, markers):
    """frames: [(t_seconds, {bone: sem6})]; markers: {index: [(name, value)]}"""
    L = ['<roblox version="4">']; n = [0]

    def ref():
        n[0] += 1; return 'RBX%d' % n[0]

    def pose(nm, sem, kids):
        cf = r6.sem2cf(nm, sem)
        return ('<Item class="Pose" referent="%s"><Properties><string name="Name">%s</string>'
                '<CoordinateFrame name="CFrame"><X>%.5f</X><Y>%.5f</Y><Z>%.5f</Z>' % (ref(), _esc(nm), cf[0], cf[1], cf[2]) +
                ''.join('<R%d%d>%.6f</R%d%d>' % (i, j, cf[3 + i * 3 + j], i, j) for i in range(3) for j in range(3)) +
                '</CoordinateFrame><token name="EasingDirection">0</token><token name="EasingStyle">0</token>'
                '<float name="Weight">1</float></Properties>' + kids + '</Item>')
    L.append('<Item class="KeyframeSequence" referent="%s"><Properties><string name="Name">%s</string><bool name="Loop">false</bool>'
             '<token name="Priority">2</token></Properties>' % (ref(), _esc(name)))
    for i, (t, P) in enumerate(frames):
        limbs = ''.join(pose(b, P[b], '') for b in LIMBS if b in P)
        torso = pose('Torso', P['Torso'], limbs)
        hrp = ('<Item class="Pose" referent="%s"><Properties><string name="Name">HumanoidRootPart</string>'
               '<CoordinateFrame name="CFrame"><X>0</X><Y>0</Y><Z>0</Z><R00>1</R00><R01>0</R01><R02>0</R02><R10>0</R10><R11>1</R11>'
               '<R12>0</R12><R20>0</R20><R21>0</R21><R22>1</R22></CoordinateFrame><token name="EasingDirection">0</token>'
               '<token name="EasingStyle">0</token><float name="Weight">0</float></Properties>%s</Item>' % (ref(), torso))
        mk = ''.join('<Item class="KeyframeMarker" referent="%s"><Properties><string name="Name">%s</string><string name="Value">%s</string>'
                     '</Properties></Item>' % (ref(), _esc(a), _esc(str(b))) for a, b in markers.get(i, []))
        L.append('<Item class="Keyframe" referent="%s"><Properties><string name="Name">Keyframe</string><float name="Time">%.5f</float>'
                 '</Properties>%s%s</Item>' % (ref(), t, hrp, mk))
    L.append('</Item></roblox>')
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(L))
    return path


def export(S, step=2, verbose=True):
    """S: v2 state after make2.build. step=2 -> 60 keyframes per second from the 120 fps curves"""
    os.makedirs(OUTR, exist_ok=True)
    w = S.warp
    n_out = w.n_total
    idx = list(range(0, n_out, step))
    if idx[-1] != n_out - 1: idx.append(n_out - 1)
    hits = {}
    for f, kind, s in S.DR.FXL.sfx:
        if kind in ('hit', 'crash', 'boom'):
            hits.setdefault(int(round(w.out(f))), max(s, hits.get(int(round(w.out(f))), 0)))
    paths = []
    for cid, actor, nm, fn in (('P', C.P, 'MrHB_fight', 'MrHB_fight.rbxmx'), ('D', C.D, 'Dummy_fight', 'Dummy_fight.rbxmx')):
        frames = []; markers = {}
        prev_vis = None
        for k, n in enumerate(idx):
            af = w.af(n)
            pose = actor.rig.pose(af)                 # curves + floor constraint (exactly what is rendered)
            frames.append((n / 120.0, folded(pose)))
            if cid == 'P':
                vis = C.P_VIS[max(0, min(C.N - 1, int(math.floor(af + 1e-6))))]
                if prev_vis is not None and vis != prev_vis:
                    markers.setdefault(k, []).append(('Show' if vis else 'Hide', ''))
                prev_vis = vis
        for nh, s in hits.items():
            k = min(range(len(idx)), key=lambda j: abs(idx[j] - nh))
            markers.setdefault(k, []).append(('Hit', s))
        paths.append(write(os.path.join(OUTR, fn), nm, frames, markers))
        if verbose:
            print('roblox: %s  %d keyframes (%.2f s), %d markers, %d KB' % (fn, len(frames), frames[-1][0], sum(len(v) for v in markers.values()), os.path.getsize(paths[-1]) // 1024))
    return paths


def verify(path, actor, warp, samples=12):
    """read the .rbxmx back with the skill's parser and compare part positions with the curves (max error in studs)"""
    import rbx
    seq = rbx.sequences(path)[0]
    worst = 0.0
    step = max(1, len(seq['kfs']) // samples)
    for kf in seq['kfs'][::step]:
        pose = {}
        for nm, p in kf['poses'].items():
            if nm in r6.J and p.get('w', 1.0) > 0:
                pose[nm] = r6.cf2sem(nm, p['cf'])
        fa = r6.fk(pose)
        fb = actor.rig.fk(warp.af(kf['t'] * 120.0))
        for b in rg.PARTS:
            worst = max(worst, rg.dist(fa[b][0], fb[b][0]))
    return worst
