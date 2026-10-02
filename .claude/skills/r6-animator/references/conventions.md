# Conventions, rig data and math (read only when you need to debug a pose or a foreign rig)

## Roblox side (facts)
- A KeyframeSequence holds Keyframes (time in seconds); each Keyframe holds a tree of Poses named after the **part** (HumanoidRootPart > Torso > Head / Left Arm / Right Arm / Left Leg / Right Leg). Pose.CFrame is the Motor6D **Transform** in joint space (identity = rest). Part1.CFrame = Part0.CFrame · C0 · Transform · C1⁻¹.
- Easing on a Pose applies from that keyframe to the **next** one. EasingStyle: Linear 0, Constant 1, Elastic 2, Cubic 3 (deprecated, treated as CubicV2), Bounce 4, CubicV2 5. EasingDirection: In 0, Out 1, InOut 2.
- AnimationPriority: Idle 0 · Movement 1 · Action 2 · Core 1000 (the writer uses Action). Roblox Animation Editor default 30 fps; times are free, the database clips are authored at 60 fps. Weight-0 container poses are ignored.
- Roblox axes: Y up, −Z front, +X character's right. Rest: torso/HRP centre y = 3, head 4.5, arms (±1.5, 3), legs (±0.5, 1). Stud = 1 unit (the toolkit scales to the Blender rig automatically).

## Canonical R6 Motor6Ds (confirmed from the supplied files)
| joint (bone) | Part0 | C0 position | C1 position | rotation C0 = C1 |
|---|---|---|---|---|
| RootJoint (Torso) | HumanoidRootPart | 0,0,0 | 0,0,0 | (−1,0,0, 0,0,1, 0,1,0) |
| Neck (Head) | Torso | 0,1,0 | 0,−0.5,0 | same as RootJoint |
| Right Shoulder (Right Arm) | Torso | 1,0.5,0 | −0.5,0.5,0 | (0,0,1, 0,1,0, −1,0,0) |
| Left Shoulder (Left Arm) | Torso | −1,0.5,0 | 0.5,0.5,0 | (0,0,−1, 0,1,0, 1,0,0) |
| Right Hip (Right Leg) | Torso | 1,−1,0 | 0.5,1,0 | as Right Shoulder |
| Left Hip (Left Leg) | Torso | −1,−1,0 | −0.5,1,0 | as Left Shoulder |
Part sizes: HRP/Torso 2×2×1, Head 2×1×1 (mesh 1.25), limbs 1×2×1.

## Semantic pose vector (what you type)
`[pitch, yaw, roll, right, up, fwd]` in degrees / studs. It is a **mirror-symmetric** re-parametrisation of the Motor6D Transform: the raw Roblox rotations of the left and right limbs have opposite signs because the joint frames are mirrored; the semantic form removes that. `sem2cf` / `cf2sem` convert (round-trip error < 1e-6, tested). Euler order: limbs XYZ, centre bones (HRP, Torso, Head) YXZ — the middle angle (limbs: yaw, centre bones: pitch) must stay inside ±90° or the readback becomes ambiguous (does not affect building).
Translations are in the joint frame and are NOT mirrored (right = character +X for left AND right limbs; outward = +right for right limbs, -right for left limbs): `right/up/fwd` ≈ along the character's right/up/front when the parent is not rotated. Use `hrp` for whole-body travel and jumps, `t` for bob/weight shift.

## Blender side
- Pose bones use **quaternion** rotation (set by `build`); `_basis`/`_unbasis` map semantic ↔ pose-bone values for any bone roll/axes, using only bone head positions (`use()` derives front/right/up and the stud scale: shoulders are 2 studs apart). Verified numerically against Roblox FK with random bone rolls (tests/test_core.py).
- A foreign rig works when it has bones named `Torso Head "Right Arm" "Left Arm" "Right Leg" "Left Leg"` (HumanoidRootPart optional) with each bone head at its joint (shoulder, hip, neck) and parent chain Torso > limbs/head. Otherwise `r6.rig()` builds a canonical one (cube parts, vertex-group skinned).
- Blender 5 layered actions: `action.fcurves` is gone; the toolkit walks `layers[].strips[].channelbags[].fcurves`. `build()` creates a new action (named after the clip, fake user) and assigns it; the previous action is kept with a fake user.
- Timing: clip frame f → scene frame `1 + (f − f0) · scene_fps / clip_fps`. Scene fps is never changed.
- Easing map: lin→LINEAR · step→CONSTANT · in/out/io→CUBIC EASE_IN/OUT/IN_OUT · bi/bo/bio→BOUNCE · ei/eo/eio→ELASTIC (exactly the Roblox Pose styles; Roblox-side CubicV2).

## Euler / unwrap
Project-authored keys may use unwrapped angles (continuous across ±180°) to describe long spins; the reference database contains no keys. Quaternion shortcut warning in lint: > 120° between two keys of one bone → add an in-between key, otherwise Blender takes the short way round. Verify evaluated Blender playback; unwrapped numeric angles alone do not preserve winding after quaternion conversion.
