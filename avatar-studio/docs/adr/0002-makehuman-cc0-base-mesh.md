# The Body is built on MakeHuman's CC0 base mesh and Morph Targets

We start from MakeHuman's `hm08` base mesh, its Morph Targets, its default Rig and its skin weights instead of sculpting a body or generating one procedurally. They are released under CC0, are anatomically faithful, and already provide hundreds of validated Morph Targets for the Bust, Hips, Glutes, Thighs and Silhouettes.

The topology is therefore fixed (about 13k quads before the Cut) and the Rig layout is MakeHuman's, not ours. This is hard to reverse because every Trait, weight and Garment binding refers to this mesh.

## Considered Options

- A procedural body from smoothly blended implicit shapes: rejected, because matching real anatomy and producing Rig weights would cost far more than the whole app.
- Ready-made game-avatar formats: rejected, because their licenses restrict redistribution and they ship no body Morph Targets.
