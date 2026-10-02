"""Blocking review helper:  python run_review.py NAME F0 F1 [STEP] [--cam side|3q|front|back] [--scale 0.28] [--cols 6]
Builds the choreography (all beats defined so far), exports a shot with a neutral follow camera and renders a contact sheet."""
import sys, argparse
sys.path.insert(0, '.')
import choreo as C
import rig as rg
import cam as camlib
import review

ap = argparse.ArgumentParser()
ap.add_argument('name'); ap.add_argument('f0', type=int); ap.add_argument('f1', type=int); ap.add_argument('step', type=int, nargs='?', default=2)
ap.add_argument('--cam', default='side'); ap.add_argument('--scale', type=float, default=0.28); ap.add_argument('--cols', type=int, default=6)
ap.add_argument('--fov', type=float, default=62); ap.add_argument('--focus', default='mid'); ap.add_argument('--dist', type=float, default=17); ap.add_argument('--list')
a = ap.parse_args()

C.build()
frames = [int(x) for x in a.list.split(',')] if a.list else list(range(a.f0, a.f1 + 1, a.step))
n = max(a.f1, max(frames)) + 1
rigs = {'mid': [C.P.rig, C.D.rig], 'P': [C.P.rig], 'D': [C.D.rig]}[a.focus]
cam = camlib.debug_track(rigs, n, a.cam, a.fov, a.dist)
hair = [[[0, 0, 0]] * 11] * n
focus = [[(C.P.rig.torso(f)[i] + C.D.rig.torso(f)[i]) / 2 for i in range(3)] for f in range(n)]
rg.export_shot('../out/test/review.json', {'P': {'rig': C.P.rig, 'kind': 'player'}, 'D': {'rig': C.D.rig, 'kind': 'dummy'}}, n, cam, tags=None, focus=focus)
print(review.review('../out/test/review.json', frames, a.name, scale=a.scale, cols=a.cols))
