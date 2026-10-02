"""Build everything the renderer/post need from the choreography:  python make.py [--review F0 F1 STEP] [--frames N] [--scale S]"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import choreo as C
import direction as DR
import rig as rg
import review

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'out'))


def build(frames=None):
    C.build()
    DR.direct_all()
    n = frames or C.N
    cam = C.CAM.track()[:n]
    focus = [[(C.P.rig.torso(f)[i] + C.D.rig.torso(f)[i]) / 2 for i in range(3)] for f in range(n)]
    tags = {'P': {'text': '@Mr_HB', 'vis': [round(v, 3) for v in DR.TAG_VIS[:n]]}}
    shot = os.path.join(OUT, 'shot.json')
    rg.export_shot(shot, {'P': {'rig': C.P.rig, 'kind': 'player', 'vis': [1 if v else 0 for v in C.P_VIS[:n]]},
                          'D': {'rig': C.D.rig, 'kind': 'dummy', 'hurt': DR.DUMMY_HURT[:n]}},
                   n, cam, fx=DR.FXL.f3, tags=tags, focus=focus)
    with open(os.path.join(OUT, 'fx2d.json'), 'w') as fh:
        json.dump({'fps': C.FPS, 'frames': n, 'events': DR.FXL.f2, 'sfx': DR.FXL.sfx, 'cam': [[round(x, 4) for x in c] for c in cam],
                   'chars': {'P': {'head': [list(C.P.rig.head(f)) for f in range(n)], 'torso': [list(C.P.rig.torso(f)) for f in range(n)]},
                             'D': {'head': [list(C.D.rig.head(f)) for f in range(n)], 'torso': [list(C.D.rig.torso(f)) for f in range(n)]}}},
                  fh, separators=(',', ':'))
    return shot, n


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--review', nargs=3, type=int); ap.add_argument('--frames', type=int)
    ap.add_argument('--scale', type=float, default=0.28); ap.add_argument('--cols', type=int, default=6); ap.add_argument('--name', default='directed')
    a = ap.parse_args()
    shot, n = build(a.frames)
    print('shot', shot, n, 'frames;', len(DR.FXL.f3), '3D fx,', len(DR.FXL.f2), '2D fx')
    if a.review:
        f0, f1, st = a.review
        fr = list(range(f0, min(f1, n - 1) + 1, st))
        print(review.review(shot, fr, a.name, scale=a.scale, cols=a.cols))
