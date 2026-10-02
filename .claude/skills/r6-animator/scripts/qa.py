#!/usr/bin/env python3
"""Sample project-authored canonical R6 motion. This is not a Blender/visual quality certificate."""
import argparse
import json
import math
from pathlib import Path
import sys
import r6


def read_clip(path):
    d = json.loads(Path(path).read_text(encoding='utf-8'))
    validate_source(d)
    return r6.clip_from_json(d['keys'], d.get('name', 'authored'), d['fps'], d.get('loop', False))


def validate_source(d):
    fps = d.get('fps')
    if isinstance(fps, bool) or not isinstance(fps, (float, int)) or not math.isfinite(fps) or fps <= 0:
        raise ValueError('positive finite fps is required')
    if not isinstance(d.get('keys'), list) or not d['keys']:
        raise ValueError('authored keys must be a non-empty list')
    prev = -math.inf
    for row in d['keys']:
        if not isinstance(row, list) or len(row) != 3:
            raise ValueError('each key must be [seconds, pose_dict, easing]')
        t, pose, e = row
        if not isinstance(t, (int, float)) or not math.isfinite(t) or t < 0 or t <= prev:
            raise ValueError('key times must be finite, nonnegative and strictly increasing')
        prev = t
        if not isinstance(pose, dict): raise ValueError('pose must be an object')
        for b, v in pose.items():
            if b not in r6.SHORT and b not in r6.BONES: raise ValueError(f'unknown bone {b}')
            if not isinstance(v, list) or not 1 <= len(v) <= 6 or any(isinstance(x, bool) or not isinstance(x, (int,float)) or not math.isfinite(x) for x in v):
                raise ValueError(f'invalid channels for {b}')
        if e not in r6.TOK: raise ValueError(f'unknown easing {e}')


def sole(pose, bone):
    p, q = r6.fk(pose)[bone]
    v = r6.mv(q, (0, -r6.J[bone][6][1]/2, 0))
    return tuple(a+b for a,b in zip(p,v))


def samples(start, end, fps):
    n = max(1, math.ceil((end-start)*fps))
    if n > 20000: raise ValueError('window exceeds 20000 samples; split long shots')
    return [start + (end-start)*i/n for i in range(n+1)]


def assess(c, plan=None):
    plan = plan or {}
    if not c['keys']: raise ValueError('empty clip')
    f0, f1 = r6.frames(c)[0], r6.frames(c)[-1]
    fps, duration = c['fps'], r6.length(c)
    findings = []
    for f, k in c['keys'].items():
        if not math.isfinite(f) or any(not math.isfinite(v) for vals in k['b'].values() for v in vals):
            raise ValueError('non-finite frame or pose channel')
    def fail(kind, detail): findings.append({'severity':'error','check':kind,'detail':detail})
    def window(a,b):
        if not (math.isfinite(a) and math.isfinite(b) and 0 <= a <= b <= duration+1e-6):
            raise ValueError('plan window is outside clip duration')
        return samples(a,b,fps)
    def pose(t): return r6.sample(c, f0+t*fps)
    if 'duration_s' in plan and abs(duration-plan['duration_s']) > 0.5/fps:
        fail('duration', f'expected {plan["duration_s"]}s, got {duration}s')
    ground = []
    for a,b in plan.get('grounded', []):
        ys = [(t, min(r6.foot_y(pose(t)).values())) for t in window(a,b)]
        tol = float(plan.get('ground_tolerance', 0.03))
        if tol < 0 or not math.isfinite(tol): raise ValueError('invalid ground tolerance')
        bad = [(t,y) for t,y in ys if abs(y) > tol]
        ground.append({'interval_s':[a,b], 'min_y':min(y for _,y in ys), 'max_y':max(y for _,y in ys), 'bad_samples':len(bad)})
        if bad: fail('ground', f'{len(bad)} samples outside floor tolerance in {a}–{b}s; first={bad[0]}')
    plants = []
    for w in plan.get('plants', []):
        bone = r6.SHORT.get(w['bone'], w['bone'])
        if bone not in ('Right Leg','Left Leg'): raise ValueError('plants must name rl/ll or leg bones')
        ts = window(w['start_s'],w['end_s']); anchor=sole(pose(ts[0]),bone)
        drift = max(math.dist(sole(pose(t),bone),anchor) for t in ts)
        tol=float(w.get('tolerance',0.05))
        if tol < 0 or not math.isfinite(tol): raise ValueError('invalid plant tolerance')
        plants.append({'bone':bone,'interval_s':[ts[0],ts[-1]],'max_sole_drift_studs':drift})
        if drift > tol: fail('plant', f'{bone} drifts {drift:.5f} studs; tolerance {tol}')
    loop = {'status':'not-applicable'}
    if c.get('loop'):
        if duration <= 1/fps: raise ValueError('loop needs more than one frame of duration')
        pa,pb = pose(0),pose(duration); pc,pd = pose(1/fps),pose(duration-1/fps)
        metrics={'pose_deg':0.0,'pose_studs':0.0,'velocity_deg_s':0.0,'velocity_studs_s':0.0}
        def delta(a,b,j): return (a-b+180)%360-180 if j<3 else a-b
        for bone in r6.BONES:
            vs=[p.get(bone,[0.0]*6) for p in (pa,pb,pc,pd)]
            for j in range(6):
                unit='deg' if j<3 else 'studs'
                gap=abs(delta(vs[1][j],vs[0][j],j))
                vel=abs(delta(vs[2][j],vs[0][j],j)*fps-delta(vs[1][j],vs[3][j],j)*fps)
                metrics['pose_'+unit]=max(metrics['pose_'+unit],gap)
                metrics['velocity_'+unit+'_s']=max(metrics['velocity_'+unit+'_s'],vel)
        limits={'pose_deg':plan.get('loop_pose_tolerance_deg',0.5),'pose_studs':plan.get('loop_pose_tolerance_studs',0.02),
                'velocity_deg_s':plan.get('loop_velocity_tolerance_deg_s',5),'velocity_studs_s':plan.get('loop_velocity_tolerance_studs_s',0.05)}
        for k,value in metrics.items():
            limit=float(limits[k])
            if not math.isfinite(limit) or limit<0: raise ValueError('invalid seam tolerance')
            if value>limit: fail('loop',f'{k}={value:.5f} exceeds {limit}')
        loop={'status':'assessed','metrics':metrics,'tolerances':limits}
    return {'schema':1,'name':c['name'],'duration_s':duration,'fps':fps,'passed':not findings,
            'scope':'offline canonical R6 checks only; not Blender evaluation or visual certification',
            'ground_status':'assessed' if ground else 'not-assessed', 'ground':ground,
            'plants_status':'assessed' if plants else 'not-assessed','plants':plants,'loop':loop,
            'findings':findings,'lint':r6.lint(c,strict=True),'visual_status':'not-assessed'}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('clip');ap.add_argument('--plan');ap.add_argument('--out')
    a=ap.parse_args()
    try:
        result=assess(read_clip(a.clip),json.loads(Path(a.plan).read_text()) if a.plan else None)
        output=json.dumps(result,ensure_ascii=False,indent=2)
        if a.out: Path(a.out).write_text(output+'\n',encoding='utf-8')
        print(output);return 0 if result['passed'] else 1
    except (ValueError,KeyError,TypeError,OSError) as e:
        print(f'{type(e).__name__}: {e}',file=sys.stderr);return 2

if __name__=='__main__': sys.exit(main())
