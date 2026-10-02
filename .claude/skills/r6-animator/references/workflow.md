# Execution, editing and export

## New project
Inspect tools/rig first. Analyze requested media, design new beats, then author a project-local Python script. For R6, import `r6` from `<BASE>/scripts` and use new/key/table/track/build; tables must be freshly authored. For other rigs, use an inspected control map and `bpy`. Preserve the existing scene. Save intermediate blocking and final versions when useful.

R6 bind: `r6.use("ArmatureName", build_if_missing=False)`. Explicit new proxy request only: `r6.rig("NewR6")`. `r6.build(set_range=False)` creates a separate action, retaining the previous action. It does not copy NLA layering/constraints into the offline clip; inspect their evaluated effect in Blender.

## Existing action
User-requested editing may use `r6.read(action="Name")` → change authored keys → `r6.build()`. Keep the source action and record this as an edit. The reader handles R6 quaternion/location channels, not arbitrary rig controls. Euler reconstruction can lose winding information; verify spins and add intermediate keys deliberately. Other channels remain in the old action, not automatically merged into the new one.

## Grounding
`r6.plant(skip=[airborne_key_frames])` adjusts root height on selected keys. It is not a world-space foot lock and does not fix in-between penetration or sliding. Declare grounded and support windows; use `qa.py` for offline samples and inspect evaluated Blender contact. Use root/leg compensation or native rig IK for stable support.

## Visual preview
`r6.sheet(fr=[...], views=("front","side"), path=...)` renders selected keys/in-betweens in a temporary scene. Open the resulting PNG through available vision tools or show it in Blender's Image Editor and capture it. Also render/play a timed preview. A contact sheet alone cannot verify rhythm.

Offline: `python <BASE>/scripts/preview.py /project/authored-clip.json /project/sheet.png`. The file uses `name/fps/loop/keys` from `r6.dump()`, not a database record. Offline box previews validate canonical R6 math only. Database IDs are intentionally rejected.

## Roblox export
`r6.export('/project/Name.rbxmx', bake=True)` writes canonical R6 KeyframeSequence XML. `.rbxmx` contains the editable sequence, not an uploaded Roblox animation ID. Import through Roblox Studio's available import workflow; publishing is a separate step. Verify the import rather than assuming identical interpolation.

The helper's sample interpolation and Blender's quaternion F-curves can differ. Export sampling from the helper alone does not guarantee final evaluated Blender motion. For exact evaluated motion, inspect/bake from Blender at the output timebase and compare poses/markers against the export; account for constraints, NLA, object transforms and root policy. Keep rotations below shortcut angles between samples. Confirm priority/loop/origin on the imported sequence.

## Project segments
`stash/add` can sequence only motion authored for the current project. Keep ownership/source names in the manifest. Do not fill the library from database IDs, bundled examples or purchased presets. Verify segment joins, velocities, root accumulation and contact after sequencing.

## Remote Blender
Blender's Python process must see the same absolute `scripts` path, or a copied matching version of `r6.py/rbx.py`. The companion MCP runs outside Blender and cannot execute Blender commands. Use the active client's actual Blender connection, not guessed tool names. Avoid silent changes to external configurations.

## Troubleshooting
Wrong axes: inspect bones/rest/roll and conventions. Short-way spin: subdivide rotation path and verify playback. Invisible action: inspect correct object/action/slot/NLA influence and frame range. Feet sliding: correct support windows and root travel, not just plant height. Missing tools: deliver runnable source and state the missing execution/inspection. See clients for setup.
