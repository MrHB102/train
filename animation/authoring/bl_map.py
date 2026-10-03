"""Semantic R6 pose (skill r6.py: pitch, yaw, roll, right, up, fwd) <-> Blender pose-bone channels on the canonical R6 rig.

On the canonical rig every bone's local frame is the character frame rotated 180 deg about Y (A = diag(-1, 1, -1)), so
  limbs  : rotation_mode 'ZYX', euler = (-P, Y, -R)      centre bones (HRP, Torso, Head): 'ZXY', euler = (-P, Y, -R)
  location = (-right, up, fwd) * stud_scale
where (P, Y, R) are the raw angles r6.sem2rw uses (semantic * sign table r6.SG).  Euler keys keep multi-turn spins and give
one editable F-curve per semantic angle in the Graph Editor."""
import math

import rig  # noqa: F401  (puts the skill scripts on sys.path)
import r6

D2R = math.pi / 180.0
MODE = {b: ('ZYX' if b in r6.LIMB else 'ZXY') for b in r6.BONES}


def sem_to_channels(bone, v, k=1.0):
    sp, sy, sr = r6.SG[bone]
    P, Y, R = v[0] * sp * D2R, v[1] * sy * D2R, v[2] * sr * D2R
    return (-P, Y, -R), (-v[3] * k, v[4] * k, v[5] * k)


def channels_to_sem(bone, euler, loc, k=1.0):
    sp, sy, sr = r6.SG[bone]
    P, Y, R = -euler[0], euler[1], -euler[2]
    return [P / D2R / sp, Y / D2R / sy, R / D2R / sr, -loc[0] / k, loc[1] / k, loc[2] / k]
