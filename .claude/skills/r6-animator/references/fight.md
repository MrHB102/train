# Original combat and multiple characters

Author choreography for this brief. No bundled fight script, pose library or preset sequence is available. Use original character controllers and project-authored clips. Do not reproduce a database exchange.

1. Define geography, screen direction, capabilities, intent and duration. Divide the scene into escalation/reversal/consequence beats suited to the story; do not impose a fixed number of blows or a standard 30-second fight.
2. Block both participants on the same timebase. Every attack needs target, preparation, commitment, contact/whiff, reaction and recovery. Record impact times and target body regions. Intentional misses must be explicit.
3. Work from a neutral camera. Check world-space strike-tip distance, facing, opponent spacing, torso overlap and foot support. Pair reaction timing with physical contact. Do not solve missed punches by camera shake.
4. Design grounded steps and airborne arcs. Keep momentum and believable landings. Throw/grab interactions require shared attachment/contact windows; prevent attachment pops. Choose recovery behavior from the story rather than forcing a kip-up.
5. Apply hit-stop, smears, stepped exposure and exaggerated reactions only if the chosen style calls for them. Count the time of pauses in the duration budget. Do not automatically add effects to every blow.
6. Polish the camera after choreography reads. Preserve screen direction unless a visible reorientation justifies a change. Avoid cuts concealing the contact being validated.
7. Inspect exact impacts and frames on either side, wide and close views, then watch the whole fight at speed. Export synchronized per-character clips when requested, with shared fps/origin policy and documented stage transforms.

For general Blender rigs, evaluate constraints and IK in the dependency graph. R6 `r6.fk()` checks only canonical local rig math, not the final world placement of two armatures. Verify final evaluated world-space geometry in Blender. Keep the impact table and visual evidence in the manifest.
