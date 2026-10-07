# 0012 — The toe box is a hull, and the sole lifts the Avatar

**Status**: accepted (supersedes the toe box of [0010](0010-procedural-footwear.md))

**Context.** 0010 pushed the toe vertices of the foot mesh out to a smooth envelope. The mesh has five separate toes, so clipping and inflating them left a ragged, torn tip and a toe that sank into the floor.

**Decision.** The Shells (upper and sole) stop just behind the ball of the foot. From there a `ToeBox` — one closed hull made of rings — takes over: its sections come from the foot mesh itself (lateral extent and instep height per slice, expanded and never shrunk, plus a margin) and close in a round tip beyond the longest toe. It has two materials (upper, sole), is weighted to the foot bone and a toe bone so it flexes at the ball, and follows the current Body by remapping to the ankle and the foot length. The sole has its own thickness; `Body.setGroundLift` raises the Avatar by it and the stiletto post grows by the same amount, so the sole meets the floor.

**Consequences.** The tip is clean at any foot size and in any Motion. The toe box is a stylized last, not the shape of the toes inside it, and there is a visible seam where it meets the upper (it reads as a vamp panel). `validate-garments` checks that no foot vertex falls outside the hull.
