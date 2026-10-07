# Jiggle is carried by virtual joints in the Rig

Soft Tissue moves through spring-damper virtual joints that are skinned like any other joint: the two Bust joints that come with the source Rig, plus Glutes, Thighs and Belly joints that we add. We chose this over vertex-shader displacement and over a soft-body simulation.

The same skinning then carries the Base Layer, Shells and Caps along with the flesh at no extra cost, and there is one code path for every Region. The price is that the motion is a translation in the parent joint's frame and volume is only approximated by the weights, so Extended Range sizes need clamped excursions.

## Considered Options

- Vertex-shader displacement: rejected, because Garments would not follow the flesh.
- Finite-element soft body: rejected for cost and tuning effort that nothing here justifies.
