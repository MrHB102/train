---
name: r6-animator
description: Author original professional Blender animations, especially Roblox R6/Motor6D characters, fights, cycles and cutscenes. Use for creating, editing, polishing, previewing or exporting animation, or when a user supplies a YouTube, X/Twitter, TikTok or other video as motion/style reference for Blender. Analyze visible motion before authoring; use the bundled database only for inspiration, never reusable animation. Supports Claude and Codex with Blender MCP or local Blender Python.
---

# R6 Animator — original animation production

Create the animation yourself from the user's brief. Own the choreography, poses, timing, spacing, curves, contact, camera and polish. Treat `<BASE>` as the directory containing this SKILL.md; use absolute paths for tools. Respond in the user's language.

## Non-negotiable behavior

- **Database = inspiration only.** Study descriptions, phases and aggregate metrics. Never copy, load, retarget, reconstruct, mirror, retime or slightly alter a database clip. The bundled database contains no pose/keyframe arrays; CLI/MCP key/raw access is blocked. Do not obtain a replacement clip elsewhere to evade this rule.
- **No ready-made animation.** Do not use motion packs, canned fights, generated presets or example choreography as the answer. Reuse math, rigging, rendering and validation utilities. Reuse animation segments only if authored for this user's current project. User-supplied actions may be edited when requested; identify that as editing rather than new authorship.
- **Video links require visual evidence.** Open/watch the actual media or extract and inspect timestamped frames plus a temporal sequence. Search results, titles and transcripts cannot establish motion/style. Never claim to have watched inaccessible video. Read [video-reference.md](references/video-reference.md) whenever a video/link is supplied.
- **User style wins.** The historical R6 database is one action style, not universal law. Do not impose anime snaps, detached joints, low guards, overshoot or extreme ranges on realistic/subtle briefs. Deliberate rig deformation requires a visual reason.
- **Execute when tools exist.** Inspect the scene, write and run original Blender Python or use Blender MCP, save the editable result and verify it. Do not stop at instructions or code for the user to paste when execution is available. Read source/docstrings when needed; author `bpy` directly when R6 helpers do not fit.
- **Evidence before “done”.** Numeric checks, contact sheets AND normal-speed playback are required for a verified animation. If Blender/playback/vision is unavailable, deliver the usable parts and state exactly which checks remain. Do not claim professional quality, successful export or a quality percentage without evidence.

## Load only what the task needs

| Need | Read |
|---|---|
| New animation or polish | [craft.md](references/craft.md), [quality.md](references/quality.md) |
| Any supplied video, including social links | [video-reference.md](references/video-reference.md) |
| Execution, editing, export, remote Blender | [workflow.md](references/workflow.md) |
| Human/animal/prop rig, camera, render production | [blender-production.md](references/blender-production.md) |
| Two or more characters / combat | [fight.md](references/fight.md) |
| Claude/Codex setup and capability limits | [clients.md](references/clients.md) |
| Reference database | [database.md](references/database.md) |
| R6 axes/Motor6D or rig debugging | [conventions.md](references/conventions.md) |

## Production loop

1. **Inspect and define.** Check Blender version, tools, scene, rigs, scale, frame rate, NLA/constraints, actions and output location. Use existing characters. Do not clear the scene. Define intent, duration, loop/root behavior and deliverables; choose reasonable defaults when the brief permits.
2. **Analyze references.** For video, inspect the requested interval, cut boundaries, key extremes and adjacent frames. Record timestamps, observations, uncertainties, transferable principles and elements to change. For the database, use `python <BASE>/scripts/db.py find WORDS`, `show ID`, or `style` only if relevant. Create an original beat sheet without source poses in it.
3. **Block.** Author new storytelling poses and action/reaction beats. Establish weight shifts and contacts first. Use stepped keys to check clarity before refining; choose continuous, stepped or mixed timing to fit the brief.
4. **Refine.** Design breakdowns/arcs, change spacing, offset the body chain where appropriate, maintain support, add follow-through and resolve contacts. Polish the camera after the action reads from a neutral view. Use project-authored segments only.
5. **Verify and iterate.** Run lint and [quality.md](references/quality.md). Inspect multiple views, fast in-betweens and full-speed playback; fix the largest visible defect and repeat. Do not stop after an arbitrary number of attempts while a material defect remains.
6. **Deliver.** Save a versioned `.blend`, original authoring script and preview; export `.rbxmx` only for R6 when requested. Record provenance and QA evidence in the project manifest. Report results and any real tool/access limitation concisely.

## R6 implementation

Use helpers for R6 only. Other rigs require a rig-specific controller map and original `bpy` code; do not claim automatic retargeting.

Boot in Blender (MCP `execute_blender_code` or Blender's Python console):
```python
import sys
sys.path.insert(0, r"<BASE>/scripts")
import r6
# Inspect/select the intended rig first. Do not silently create a replacement.
print(r6.use("YourR6Armature", build_if_missing=False))
```

Author a new clip with `r6.new(name, fps, loop)` and brief-specific `key/table/track` calls. There are deliberately no reusable pose tables here. Run `r6.plant(skip=airborne_frames)` only on appropriate grounded keys; it adjusts height, **does not lock feet in world space**. Run `r6.check(strict=True)`; explain justified stylized exceptions. Run `r6.build(set_range=False)`, verify duration against the actual scene fps/fps_base, then set the shot range deliberately. `r6.read()` edits an existing action. Use `r6.sheet(...)`/`show()` and view the resulting image; a printed path alone is not an inspection.

Bones: `t` Torso, `h` Head, `ra/la` arms, `rl/ll` legs, `hrp` root. Cell: `pitch,yaw,roll,right,up,fwd` (degrees/studs); bare number = pitch, `-` = unkeyed. Rotation signs are semantic: same L/R rotation values mirror; translations use the same character +X on both sides. Easing shapes key → next: `lin step in out io bo bi bio eo ei eio`. Choose rather than mechanically applying a house default.

Use `scripts/qa.py` for sampled R6 checks and planted-foot intervals; MCP `r6_qa` accepts an authored table. Math/DSL checks complement Blender playback and do not prove Blender interpolation, contact or visual quality. See workflow for export fidelity and quaternion spins.

## Project record

Write a small `animation-manifest.json` beside the outputs: brief/assumptions, version/tool capabilities, fps and seconds, authored script, reference URLs/IDs and inspected intervals, observed style principles, original beat decisions, contact/airborne windows, intentional stylization, checks performed with evidence paths, unresolved findings and deliverables. Keep `observed` separate from `inferred`. Update this record after revisions; do not mark unperformed checks as passed.
