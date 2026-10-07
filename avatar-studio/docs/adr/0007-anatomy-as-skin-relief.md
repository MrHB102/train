# 0007 — Anatomy is skin relief, not geometry

**Status**: accepted

**Context.** The base mesh is smooth: no collarbones, neck tendons, ribs, hip bones or abdominal line, so the torso read as a plastic tube. Real anatomy at that scale (a 2 mm ridge, 8 mm wide) is finer than the mesh (about 5 mm edges after subdivision), so morph targets cannot carry it.

**Decision.** Anatomy is a height-and-cavity field evaluated in the skin shader from landmarks (collarbone lines, sternal notch, tendon lines, costal arches, navel, inguinal lines, spine) snapped to the reference surface and stored in reference space. Bump and a warm cavity shade come from that field; a per-vertex cavity attribute (how far a vertex sits below its neighbours) adds the same cue to every fold of the mesh for free.

**Consequences.** Details stay sharp at any resolution and follow every morph because landmarks live in reference space. Silhouettes do not change (a collarbone does not show in profile). Each group has its own Skin parameter; abdominal definition follows Muscle Tone and ribs follow leanness.
