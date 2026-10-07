# 0009 — Thin garment parts are Ribbons, not clipped Shells

**Status**: accepted

**Context.** Shells are cut from the Body mesh with a scalar field. A part narrower than about two triangles (a 4 mm bikini string, a 2 cm strap) breaks into fragments or disappears because clipping only keeps triangles with a vertex inside.

**Decision.** Thin parts are Ribbons: a path of samples, each bound to a Body triangle by barycentric weights (found by raycasting the reference mesh), swept into a flat strip or a round cord with its own width. Skin weights are blended from the bound triangle, so a Ribbon deforms and wobbles with the Body exactly like a Shell.

**Consequences.** Strings, straps and ties can be any width, follow every morph and never fragment. A Ribbon covers nothing, so it never hides Body or Shell triangles beneath it.
