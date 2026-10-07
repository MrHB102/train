# 0010 — Footwear is procedural

**Status**: accepted; the toe box and the sole thickness are superseded by [0012](0012-toe-box-hull-and-sole.md)

**Context.** The CC0 MakeHuman shoes are flat men's and sports shoes; there is no high heel. Shoes must also fit any foot size and Heel Height, and keep Ground Contact.

**Decision.** Shoes are an upper and a sole cut from the foot (two Shells, the sole with its own color), a toe box that pushes the toe vertices radially to a smooth envelope so five toes merge into one rounded tip, and a stiletto post rigid on the foot bone. The post is tilted by the same angle the animator uses to pitch the foot for the Heel Height, so it stands vertical on the floor.

**Consequences.** Any foot shape fits. Heel Height comes from the shoe when one is worn. The toe tip is a stylized volume, not a modeled last.
