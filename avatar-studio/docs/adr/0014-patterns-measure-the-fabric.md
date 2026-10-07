# 0014 — Patterns are measured over the fabric

**Status**: accepted

**Context.** Pattern coordinates were an angle around a vertical axis times a fixed radius, so polka dots grew over the Bust, shrank at the waist and stretched along a flared skirt (whose circumference is the same at every row in those coordinates).

**Decision.** Torso Garments use `torsoUv`: u is the arc length over the reference surface from the front centre line, measured on rings every 1 cm with rays from the centre of each section, v is the height, and the seam sits at the back with the ring's circumference as its period. The skirt cloth uses the arc at the radius of its own row and the slanted distance along the cloth. Tartan is a real sett (wide band, two thin threads, darker crossings, twill). Pleats are a displacement of the render mesh only.

**Consequences.** Dots and checks keep their size on the reference Body; on a morphed Body the cloth stretches with it, like printed elastic fabric. The rings are computed once, on the first torso Garment (about 0.1–0.3 s).
