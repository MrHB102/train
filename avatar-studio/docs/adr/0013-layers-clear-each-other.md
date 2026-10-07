# 0013 — Outer Garments clear the ones under them

**Status**: accepted

**Context.** Garments are Shells at a fixed height above the Body. With Padding a bodice stands up to 7 mm over the Bust, taller than the 5.2 mm of an apron bib above it, so the bodice showed through and the edge between them became a staircase of triangles. The apron panel and the skirt are two separate simulated cloths, and on large bodies the skirt came through the panel; the waist ring also had cliffs where a big Bust overhangs the waist.

**Decision.** `Dresser.underOffset(layer, v)` returns the thickness of the tallest opaque piece below a layer at a vertex; the apron's bib, waistband and straps use `max(own, under + 1.4 mm)` and are refreshed whenever the Outfit changes. The apron panel gets a layer constraint on its cloth (`Cloth.layer`): after collisions its particles are pushed outside the skirt's visible surface (`SkirtSurface`, read from the render mesh). The skirt's body envelope is dilated one column and blurred so cliffs become ramps. Ribbons carry no Trim.

**Consequences.** An apron sits correctly over any bodice and any Body, and `validate-garments` checks bib clearance, panel-over-skirt gap on three bodies and the absence of sharp folds. The clearance is a rule of the Dresser, not of each recipe.
