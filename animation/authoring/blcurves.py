"""Blender F-curves are the single source of motion in v2.

Authored r6 clips (keys on the 18 fps story grid) become Blender Actions (Blender 5 layered actions: one slot, one keyframe
strip) whose F-curves are the canonical-R6 pose-bone channels (Euler, see bl_map).  Key times go through the time-warp
(timeline.Warp: story frame -> 120 fps output frame) and every key gets the Blender interpolation that fits its role:

  default                                BEZIER, handles AUTO_CLAMPED (Blender's own default ease: smooth, no overshoot)
  attacker, chamber -> contact           QUART (>=2 story frames) / CUBIC  EASE_IN: slow start, fastest at the contact
  target, key before it is struck        CONSTANT on the pose channels (it does not react before the touch); its root keeps
                                         moving unless it is standing still
  target, after the hit (limb channels)  BACK EASE_OUT (whip + settle)
  teleport (player hidden between keys)  CONSTANT, and the keys on both sides get flat handles so the jump does not bend
                                         the visible motion around it
The same Actions are evaluated here with FCurve.evaluate (Blender's own code) for rendering, QA, the camera and the Roblox
bake, and they are saved in the .blend: the video, the .blend and the .rbxmx move identically.
"""
import bpy

import rig as rg  # noqa: F401  (sys.path for the skill)
import r6
import bl_map

BONES = r6.BONES
POSE_BONES = ('Torso', 'Head', 'Left Arm', 'Right Arm', 'Left Leg', 'Right Leg')


def _new_action(name):
    act = bpy.data.actions.get(name)
    if act:
        bpy.data.actions.remove(act)
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    slot = act.slots.new(id_type='OBJECT', name=name)
    layer = act.layers.new('Layer')
    strip = layer.strips.new(type='KEYFRAME')
    return act, slot, strip.channelbag(slot, ensure=True)


def _near(x, arr, eps=1e-6):
    return any(abs(x - a) < eps for a in arr)


class Spec:
    """role information for one actor"""

    def __init__(self, strikes=None, struck=(), breaks=(), stationary=None):
        self.strikes = dict(strikes or {})        # story frame where this actor's strike lands -> bones that drive it
        self.struck = sorted(set(struck))         # story frames where this actor is hit
        self.breaks = list(breaks)                # [(ka, kb)] consecutive keys with a teleport between them
        self.stationary = stationary or (lambda f0, f1: False)


def _strike_bone(spec, f, bone):
    for h, bones in spec.strikes.items():
        if abs(f - h) < 1e-6 and (bone in bones or bone in ('Torso', 'HumanoidRootPart')):
            return True
    return False


def roles(clip, bone, frames, spec):
    """per key: (interpolation, easing, back) of the segment that starts at that key"""
    out = []
    for i, f in enumerate(frames):
        if i + 1 >= len(frames):
            out.append(('BEZIER', None, None)); continue
        nxt = frames[i + 1]
        tok = clip['keys'][f]['e'] or clip['ease']
        r = ('BEZIER', None, None)
        if tok == 'step' or any(abs(f - a) < 1e-6 and abs(nxt - b) < 1e-6 for a, b in spec.breaks):
            r = ('CONSTANT', None, None)
        elif _near(nxt, spec.struck) and (bone != 'HumanoidRootPart' or spec.stationary(f, nxt)):
            r = ('CONSTANT', None, None)
        elif _strike_bone(spec, nxt, bone):
            r = ('QUART', 'EASE_IN', None) if nxt - f >= 1.99 else ('CUBIC', 'EASE_IN', None)
        elif bone in POSE_BONES and bone != 'Torso' and any(0 <= f - h < 0.5 for h in spec.struck) and nxt - f >= 1.99:
            r = ('BACK', 'EASE_OUT', 1.15)
        out.append(r)
    return out


def build_action(name, clip, warp, spec, stud=1.0):
    """clip keys -> Blender Action. Returns (action, slot)."""
    act, slot, cb = _new_action(name)
    all_frames = r6.frames(clip)
    flat_left = {a for a, b in spec.breaks}       # key before a teleport: flat incoming handle
    flat_right = {b for a, b in spec.breaks}      # key after a teleport: flat outgoing handle
    for b in BONES:
        frames = [f for f in all_frames if b in clip['keys'][f]['b']]
        if not frames:
            continue
        vals = []
        for f in frames:
            e, l = bl_map.sem_to_channels(b, clip['keys'][f]['b'][b], stud)
            vals.append(list(e) + list(l))
        rl = roles(clip, b, frames, spec)
        xs = [warp.key(f) for f in frames]
        for ch in range(6):
            if ch >= 3 and b != 'HumanoidRootPart' and all(abs(v[ch]) < 1e-9 for v in vals):
                continue                              # limbs never translate: no location curves
            path = 'pose.bones["%s"].%s' % (b, 'rotation_euler' if ch < 3 else 'location')
            fc = cb.fcurves.new(path, index=ch % 3, group_name=b)
            kp = fc.keyframe_points
            kp.add(len(frames))
            co = []
            for x, v in zip(xs, vals):
                co += [x, v[ch]]
            kp.foreach_set('co', co)
            for k, (ip, ease, back) in zip(kp, rl):
                k.handle_left_type = 'AUTO_CLAMPED'; k.handle_right_type = 'AUTO_CLAMPED'
                k.interpolation = ip
                if ease: k.easing = ease
                if back: k.back = back
            fc.update()
            # teleports: flatten the handles that face the jump so the visible motion is not bent by it;
            # chamber keys (start of an eased-in strike) also get a flat incoming handle: the body settles into the coil
            # (a moving hold) instead of being stopped dead by the zero-velocity start of the ease-in
            for i, f in enumerate(frames):
                k = kp[i]
                if rl[i][1] == 'EASE_IN' and i > 0 and f not in flat_left:
                    k.handle_left_type = 'FREE'
                    dx = (xs[i] - xs[i - 1]) / 3.0
                    k.handle_left = (xs[i] - dx, vals[i][ch])
                if f in flat_left and i > 0:
                    k.handle_left_type = 'FREE'
                    dx = (xs[i] - xs[i - 1]) / 3.0
                    k.handle_left = (xs[i] - dx, vals[i][ch])
                if f in flat_right and i + 1 < len(frames):
                    k.handle_right_type = 'FREE'
                    dx = (xs[i + 1] - xs[i]) / 3.0
                    k.handle_right = (xs[i] + dx, vals[i][ch])
            fc.update()
    return act, slot


class ActionEval:
    """evaluate an Action built by build_action at (fractional) output frames -> semantic pose {bone: [6]}"""

    def __init__(self, act, slot, stud=1.0):
        self.act, self.slot, self.stud = act, slot, stud
        cb = None
        for l in act.layers:
            for s in l.strips:
                cb = s.channelbag(slot)
        self.ch = {}
        for fc in cb.fcurves:
            if not fc.data_path.startswith('pose.bones'): continue
            b = fc.data_path.split('"')[1]
            kind = 0 if fc.data_path.endswith('rotation_euler') else 3
            self.ch[(b, kind + fc.array_index)] = fc

    def pose(self, n):
        out = {}
        for b in BONES:
            if (b, 0) not in self.ch:
                continue
            e = [self.ch[(b, i)].evaluate(n) for i in range(3)]
            l = [self.ch[(b, 3 + i)].evaluate(n) if (b, 3 + i) in self.ch else 0.0 for i in range(3)]
            out[b] = bl_map.channels_to_sem(b, e, l, self.stud)
        return out


def add_floor_lift(act, slot, ev, n_total, lowest_point):
    """The floor constraint (no part below y=0: the body is lifted by the penetration) as an object-level F-curve in the same
    action: location Z of the armature object, keyed (linear) on every output frame where it is active, zero elsewhere.
    The bone curves stay exactly as authored; the .blend then moves exactly like the render."""
    cb = None
    for l in act.layers:
        for s in l.strips:
            cb = s.channelbag(slot)
    old = cb.fcurves.find('location', index=2)
    if old: cb.fcurves.remove(old)
    lift = [max(0.0, -lowest_point(ev.pose(n))) for n in range(n_total)]
    keys = []
    for n in range(n_total):
        on = lift[n] > 1e-4
        near = any(lift[m] > 1e-4 for m in (n - 1, n + 1) if 0 <= m < n_total)
        if on or near or n in (0, n_total - 1):
            keys.append((float(n), lift[n] if on else 0.0))
    fc = cb.fcurves.new('location', index=2, group_name='FloorLift')
    kp = fc.keyframe_points; kp.add(len(keys))
    co = [c for k in keys for c in k]
    kp.foreach_set('co', co)
    kp.foreach_set('interpolation', [1] * len(keys))
    fc.update()
    return sum(1 for x in lift if x > 1e-4), max(lift)
