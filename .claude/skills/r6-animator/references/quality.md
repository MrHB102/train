# Quality and honest completion

Use hard gates plus artistic review. Numerical success is not a quality percentage.

| Gate | Required evidence |
|---|---|
| Brief | Correct action, style, length, characters, loop/root and requested format |
| Original authorship | Project-authored script/beat decisions; no external motion preset or database key data |
| Reference analysis | Inspected media with timestamps; observations separated from inference; access limits stated |
| Technical | Finite channels, expected range/timebase, correct rig/action/slot, no missing assets or broken constraints |
| Contact/weight | Support windows checked for world-space slide and floor penetration; impacts/grabs evaluated at exact times |
| Motion | Readable silhouettes, intentional timing, smooth or intentionally stepped arcs, purposeful overlap and recovery |
| Loop | Pose AND velocity seam, root policy, actual frame-range playback across multiple repetitions |
| Visual | Contact sheet from multiple views plus normal-speed playback and important in-betweens |
| Delivery | Saved editable file, reproducible authoring source, playable preview and requested exports |

For R6, `qa.py clip.json --plan plan.json` checks invalid channels, duration, per-frame floor penetration, declared planted-foot drift and seam metrics. `plan.json` may contain `duration_s`, `grounded: [[start_s,end_s]]`, `plants: [{bone: "rl", start_s: ..., end_s: ..., tolerance: 0.05}]`, `ground_tolerance`, `loop_pose_tolerance_deg`, `loop_pose_tolerance_studs`, `loop_velocity_tolerance_deg_s` and `loop_velocity_tolerance_studs_s`. Values use seconds and studs/degrees for canonical R6. Choose tolerances for the shot scale; do not relax them simply to pass. Root-travel cycles require in-place extraction or a separate world-space seam check; this checker assumes closed root channels. Inspect the returned strict lint separately even when the sampled checks pass.

Floor check = lowest leg-box corner; planted-foot point = local sole center. This is an offline approximation. It does not validate arbitrary Blender constraints, two-rig contact or final quaternion curve evaluation. If no ground/plant intervals were declared, those checks are **not assessed**, not silently passed. Fix the plan rather than inventing coverage. Run technical checks after polishing and export.

Use an unresolved findings list. A minor intentional style exception can ship when documented; a failed major gate requires revision or a clear partial-delivery statement. Never report “watched”, “rendered”, “verified in Blender”, “100% better” or “professional” merely because a script exists or a tool returned a path.
