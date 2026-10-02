#!/usr/bin/env python3
"""Offline tests (no Blender): python3 tests/test_core.py
   1 rest FK  2 sem<->cf round trip  3 direction conventions  4 table/lint/cycle  5 .rbxmx write->parse round trip
   6 database (study-only, no presets) + collision lint  7 Blender-layer maths (_basis/_unbasis + armature chain) against Roblox FK with random bone rolls"""
import os, sys, math, random, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); SK = os.path.join(os.path.dirname(HERE), 'scripts')
sys.path.insert(0, SK); sys.path.insert(0, HERE)
import r6, rbx, db
ok = []
def check(name, cond, extra=''):
    ok.append(bool(cond)); print(('PASS ' if cond else 'FAIL ') + name + (' ' + str(extra) if extra and not cond else ''))
def close(a, b, e=1e-6): return all(abs(x - y) < e for x, y in zip(a, b))

# 1 rest FK = canonical R6 layout
fk0 = r6.fk({})
want = {'HumanoidRootPart': (0, 3, 0), 'Torso': (0, 3, 0), 'Head': (0, 4.5, 0), 'Right Arm': (1.5, 3, 0), 'Left Arm': (-1.5, 3, 0), 'Right Leg': (0.5, 1, 0), 'Left Leg': (-0.5, 1, 0)}
check('rest FK positions', all(close(fk0[b][0], p) for b, p in want.items()), {b: fk0[b][0] for b in want})

# 2 semantic <-> CFrame round trip (random poses, all bones)
random.seed(7); worst = 0
for b in r6.BONES:
    for _ in range(200):
        lim = (80, 80, 80) if b != 'HumanoidRootPart' else (80, 170, 170)      # centre bones: pitch is the middle Euler angle (|.|<90)
        v = [random.uniform(-l, l) for l in lim] + [random.uniform(-1, 1) for _ in range(3)]
        w = r6.cf2sem(b, r6.sem2cf(b, v)); worst = max(worst, max(abs(x - y) for x, y in zip(v, w)))
check('sem<->cf round trip', worst < 1e-6, worst)

# 3 direction conventions (documented in the cheat sheet)
def tip(b, v):
    P, Q = r6.fk({b: v})[b]; return r6.mv(Q, (0, -1, 0)) if r6.J[b][4] else r6.mv(Q, (0, 1, 0))
a0 = tip('Right Arm', [0]); a1 = tip('Right Arm', [60]); a2 = tip('Right Arm', [0, 0, 60])
check('arm pitch+ swings the tip to the FRONT (-Z)', a1[2] < a0[2] - 0.5, (a0, a1))
check('arm roll+ swings the tip OUTWARD (+X for the right arm)', a2[0] > a0[0] + 0.5, (a0, a2))
t1 = r6.mv(r6.fk({'Torso': [30]})['Torso'][1], (0, 1, 0)); check('torso pitch+ leans the top to the FRONT', t1[2] < -0.3, t1)
t2 = r6.mv(r6.fk({'Torso': [0, 0, 30]})['Torso'][1], (0, 1, 0)); check('torso roll+ tilts to the character RIGHT', t2[0] > 0.3, t2)
t3 = r6.mv(r6.fk({'Torso': [0, 40]})['Torso'][1], (0, 0, -1)); check('torso yaw+ turns the front to the RIGHT', t3[0] > 0.3, t3)
l1 = r6.fk({'Right Leg': [50]})['Right Leg']; check('leg pitch+ swings the foot forward', l1[0][2] < 0 and r6.foot_y({'Right Leg': [50]}) is not None)

# 4 DSL / lint / cycle
r6.new('T', 30, False, 'out')
r6.table("""f ra la rl ll t h ease
0 0 0 0 0 0 0 out
8 40 -40 -30 30 0,0,0,0,.1 5 io
16 -40 40 30 -30 0,0,0,0,.05 -5 lin""")
c = r6.cur(); check('table builds 3 keys', len(c['keys']) == 3 and c['keys'][8.0]['e'] == 'io')
check('lint clean on sane clip', r6.check() == 'clean', r6.check())
r6.key(30, ra=[400]); check('lint flags 400 deg arm', r6.check() != 'clean'); r6.cur()['keys'].pop(30.0)
r6.cycle(); fs = r6.frames(r6.cur()); check('cycle closes loop', r6.cur()['keys'][fs[-1]]['b'] == r6.cur()['keys'][fs[0]]['b'])
r6.copy(0, 24, mirror=True); check('mirror swaps arm sides', r6.cur()['keys'][24.0]['b']['Left Arm'] == r6.cur()['keys'][0.0]['b']['Right Arm'])

# 4b segments: stash/add (sequencing, repeats, travel, seam fill)
r6.new('seg', 30, True, 'lin'); r6.table('f ra rl hrp\n0 -30 30 -\n4 0 0 0,0,0,0,0.5\n8 30 -30 -'); r6.stash('seg')
r6.new('master', 60, False, 'lin'); r6.add('seg', at=1.0, times=2, travel=3.0); mc = r6.cur(); mf = r6.frames(mc)
check('add(): 2 repetitions share the seam (5 keys @60fps from 1.0s)', mf == [60.0, 68.0, 76.0, 84.0, 92.0] or len(mf) == 5 and mf[0] == 60.0, mf)
check('add(travel): root advances 3 studs per repetition', abs(mc['keys'][mf[-1]]['b']['HumanoidRootPart'][5] - 3.0 * 2) < 1e-6 or abs(mc['keys'][mf[-1]]['b']['HumanoidRootPart'][5] - 6.0) < 1e-6)
check('add(): first key has all 6 R6 bones', set(r6.BONES[1:]) <= set(mc['keys'][mf[0]]['b']))
r6.add('seg', at=0.0, mirror=True, speed=2.0); check('add(mirror,speed) works', 0.0 in r6.cur()['keys'])
r6.new('master2', 60, False, 'lin'); r6.add('seg', at=0.0, times=2, travel=3.0); r6.add('seg', at=r6.length(r6.cur()), travel=2.0)   # second segment continues from the root's x/z
m2 = r6.cur(); last = r6.frames(m2)[-1]
check('add(root=auto): the next segment continues from the previous root (no teleport)', abs(m2['keys'][last]['b']['HumanoidRootPart'][5] - 8.0) < 1e-6, m2['keys'][last]['b']['HumanoidRootPart'])

# 5 .rbxmx round trip through the writer and the parser
r6.new('RT', 30, False, 'out')
r6.table("""f ra la t h ease
0 0 0 0 0 out
8 40,10,20 -40,0,-15 12,20,5,0.1,-0.3,0.2 5,-10 io
16 -40 40 -20,-35,-8 -5 lin""")
p = os.path.join(tempfile.mkdtemp(), 'rt.rbxmx'); r6.export(p)
back = rbx.sequences(p); c2 = r6.from_raw(back[0], 30); c1 = r6.cur()
check('rbxmx keys on whole frames', sorted(c2['keys']) == sorted(c1['keys']), sorted(c2['keys']))
err = max(max(abs(x - y) for x, y in zip(c1['keys'][f]['b'][b], c2['keys'][f]['b'][b])) for f in c1['keys'] for b in c1['keys'][f]['b'])
check('rbxmx pose round trip (<1e-3)', err < 1e-3, err)
check('rbxmx easing round trip', all(c1['keys'][f]['e'] == c2['keys'][f]['e'] for f in (0.0, 8.0, 16.0)), [(c1['keys'][f]['e'], c2['keys'][f]['e']) for f in c1['keys']])

# 6 database
ids = list(db.db()['anims']); check('db has the 6 curated KeyframeSequences', len(ids) >= 6 and all(db.get(i).get('desc') for i in ids))
check('db find works', 'manji.yuji' in ' '.join(db.find('acrobatic combo spin')))
check('db style loaded', 'STYLE PROFILE' in db.style_rules())
check('no preset loader exists (database = style reference only)', not hasattr(r6, 'load'))
try:
    db.show('manji.yuji_start', 'keys'); blocked = False
except ValueError:
    blocked = True
check('db blocks keyframe output', blocked)
check('db flags warn that DB poses interpenetrate', all(any('torso' in f for f in db.get(i).get('flags', [])) for i in ('manji.dummy', 'manji.yuji_start', 'manji.yuji')))
check('style has READABILITY + ORIGINALITY rules', all(k in db.style_rules() for k in ('READABILITY', 'ORIGINALITY')))
# collision lint is INFO by default (style may break the shoulder), W only in strict mode
def lint_of(txt, strict=False):
    r6.new('c', 30, False, 'lin'); r6.table(txt); return r6.lint(r6.cur(), strict=strict)
inw = 'f t ra ease\n0 0 0 lin\n6 0 0,0,-68 lin\n12 0 0 lin'
loose = lint_of(inw); strict = lint_of(inw, True)
check('arm rolled -68 into the torso: INFO (allowed for style)', any(m.startswith('I ') and 'ra intersects t ' in m for m in loose) and not any(m.startswith('W') and 'intersects' in m for m in loose), loose)
check('same pose in strict mode: W', any(m.startswith('W') and 'ra intersects t ' in m for m in strict), strict)
check('arm roll -68 is inside the (style) joint limits', not any('roll' in m and m.startswith('W') for m in loose), loose)
for name, tx in (('arm out 90', 'f ra la ease\n0 0 0 lin\n8 0,0,90 0,0,90 lin\n16 0 0 lin'), ('arm front 80 + roll 10', 'f ra ease\n0 0 lin\n8 80,0,10 lin\n16 0 lin'), ('leg front 70', 'f rl ll ease\n0 0 0 lin\n8 70 -30 lin\n16 0 0 lin')):
    check('%s has no collision note' % name, not any('intersects' in m for m in lint_of(tx, True)), lint_of(tx, True))
check('track() keys one bone on its own frames', (r6.new('t', 60, False, 'lin'), r6.track('ra', '0:0 10:40,0,5@io 20:0'), r6.track('t', '5:3'))[0] is not None and sorted(r6.cur()['keys']) == [0.0, 5.0, 10.0, 20.0] and r6.cur()['keys'][10.0]['e'] == 'io')
r6.new('t2', 60, False, 'lin'); r6.track('ra', '0:0 20:40 40:80'); r6.track('t', '0:0,0,0 40:0,40,0'); r6.track('rl', '0:0 40:0'); r6.plant()
tt = r6.sample(r6.cur(), 20.0)['Torso']; check('plant() samples the interpolated torso, not zeros', abs(tt[1] - 20.0) < 1e-6, tt)
check('hits() reports depth', any(h[2] > 0.5 for h in r6.hits({'Right Arm': [0, 0, -68, 0, 0, 0]})))
check('rest pose has no hits', r6.hits({}) == [])

# 7 Blender-layer maths with a numpy mathutils stand-in: bone rolls/axes are random, the result must equal Roblox FK
import numpy as np, mathutils_shim; mathutils_shim.install()
from mathutils import Matrix, Vector
def randrot(rng):
    q = rng.normal(size=4); q /= np.linalg.norm(q); w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
rng = np.random.default_rng(3)
for trial, rolled in enumerate((False, True)):
    S = Matrix(((-1, 0, 0), (0, 0, 1), (0, 1, 0))) if not rolled else Matrix(randrot(rng))       # roblox->blender axes (a random rotation proves independence)
    Bm = {b: Matrix(randrot(rng)) if rolled else Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0))) for b in r6.BONES}
    kscale = 1.0 if not rolled else 1.37
    r6._B.update(name='fake', S=S, k=kscale, B=Bm)
    cen = {b: p[0] for b, p in r6.fk({}).items()}; jp = {b: (cen[b] if r6.J[b][0] is None else tuple(cen[r6.J[b][0]][i] + r6.J[b][1][i] for i in range(3))) for b in r6.BONES}
    head = {b: (S @ Vector(jp[b])) * kscale for b in r6.BONES}                                 # rest head positions (armature space)
    worst = 0
    for _ in range(40):
        pose = {b: [random.uniform(-70, 70) for _ in range(3)] + [random.uniform(-.8, .8) for _ in range(3)] for b in r6.BONES}
        # Blender chain: M_c = M_p * M_p_rest^-1 * M_c_rest * Basis_c   (4x4)
        def T4(R, t): M = np.eye(4); M[:3, :3] = R; M[:3, 3] = t; return M
        rest = {b: T4(Bm[b].m, head[b].a) for b in r6.BONES}; posem = {}
        for b in r6.BONES:
            q, loc = r6._basis(b, pose[b]); basis = T4(q.to_matrix().m, loc.a)
            par = r6.J[b][0]; posem[b] = (posem[par] @ np.linalg.inv(rest[par]) @ rest[b] if par else rest[b]) @ basis
        want = r6.fk(pose)
        for b in r6.BONES[1:]:
            skin = posem[b] @ np.linalg.inv(rest[b])                                           # skinning matrix of the bone
            c0 = np.append((S @ Vector(cen[b])).a * kscale, 1.0); got = (skin @ c0)[:3]         # where the part centre goes
            exp = (S @ Vector(want[b][0])).a * kscale; worst = max(worst, float(np.abs(got - exp).max()))
            R = skin[:3, :3]; Rexp = S.m @ np.array(want[b][1]).reshape(3, 3) @ S.m.T; worst = max(worst, float(np.abs(R - Rexp).max()))
    check('blender chain == roblox FK (%s axes)' % ('random bone rolls + random S + scale 1.37' if rolled else 'canonical'), worst < 1e-6, worst)
    # unbasis is the inverse of basis
    w2 = 0
    for b in r6.BONES:
        v = [random.uniform(-70, 70) for _ in range(3)] + [random.uniform(-.8, .8) for _ in range(3)]; q, loc = r6._basis(b, v); w2 = max(w2, max(abs(x - y) for x, y in zip(r6._unbasis(b, q, loc), v)))
    check('_unbasis(_basis(v)) == v (%s)' % ('rolled' if rolled else 'canonical'), w2 < 1e-6, w2)
print('\n%d/%d passed' % (sum(ok), len(ok))); sys.exit(0 if all(ok) else 1)
