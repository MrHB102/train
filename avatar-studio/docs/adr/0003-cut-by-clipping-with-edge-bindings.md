# The Cut clips triangles; new vertices ride on base-mesh edges

The Cut is made by clipping triangles against the cutting plane. Each new vertex is stored as a point on a base-mesh edge (A, B, t) instead of deleting whole vertices or pre-baking a cut mesh.

A cut that deleted vertices would be jagged at mesh resolution, and a pre-baked mesh could not follow Morph Targets. With edge bindings the Cut stays clean for every Trait value and every Pose, and Shells reuse the same mechanism to get smooth necklines and leg openings.
