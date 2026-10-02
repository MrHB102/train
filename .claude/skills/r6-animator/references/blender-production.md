# Blender production beyond canonical R6

## Rig and scene preflight
Inspect `bpy.app.version_string`, fps/fps_base, scene units, armatures, active action/slot, NLA tracks, drivers, constraints, mesh bindings and camera. Save a new working version before substantial edits. Choose the intended rig by name and preserve other objects/actions. Never run “select all → delete” as setup on a user file. Do not build an R6 proxy and pretend it is the supplied character.

Map actual animator controls to root/hips/spine/head/hands/feet and IK/FK switches. Verify axes, rest pose, bone roll, rotation modes, object transforms and controller constraints with small reversible tests. General human, quadruped, facial and prop rigs need their own original controller keys. The `r6` module is not a universal retargeter or full facial/IK system.

## Authoring
Create an isolated named Action or NLA strip for the shot. Key only intended controllers. Avoid overwriting unrelated animation/constraints. Use `bpy` and native IK/FK when appropriate; inspect current-version API documentation rather than guessing. Blender's slotted Action API changes by version; do not assume all actions expose legacy `.fcurves`. Prefer native keyframe insertion, then inspect the correct slot/layer/channelbag.

Blocking, breakdowns and spline passes must use project-authored poses. Correct tangents and gimbal/quaternion behavior from evaluated results. Contact locks use world-space target constraints or authored compensation, with explicit switch frames. Confirm switching does not pop. Cache simulations deterministically when needed; simulation is secondary support, not ready-made character motion.

## Camera and picture
Stage for the focal action. Start with a locked neutral view; compose the final lens/angle/camera path after the movement reads. Do not mirror a database camera or create arbitrary camera noise. Check action readability, cropping, lighting, shadow contact, motion blur and exposure in the final view. Effects must not conceal defects.

## Time and outputs
Use effective scene fps = `render.fps / render.fps_base`. Document start/end inclusive frames, duration conventions and duplicate loop endpoints. Keep source time, project time and Blender frame numbers distinct. A 60-fps authoring clip may be resampled into a 24-fps scene, but the final result must be watched for aliasing/exposure differences.

Save a versioned editable `.blend`; pack or list external assets deliberately. Render a small preview before final quality. Prefer a frame sequence for recoverable long renders, then encode with FFmpeg if available. Confirm the preview opens, frame count/duration and audio sync when applicable. General rigs may use Blender/FBX/glTF exports subject to their format constraints; this toolkit's `.rbxmx` writer supports canonical R6 only.

If Blender exists locally, use its background Python for reproducible construction/rendering. If Blender MCP exists, discover actual tools and run code in Blender. If neither exists, author a reproducible script and offline R6 checks, but mark Blender execution/rendering unverified. Do not imply a skill grants software, network access or vision tools.
