# 0008 — Recoil is a spring on the value, plus an impulse on Jiggle

**Status**: accepted

**Context.** In character creators, dragging a size slider makes the body pop past the target and settle, which feels alive. Applying Trait values directly looks like a snap.

**Decision.** Every Trait and Dial has a displayed value that follows its target through a damped spring (frequency and damping per Region: light Bust, heavier Hips). The Body is rebuilt from displayed values each frame while anything moves (about 6 ms). The change in effective values also kicks the Jiggle joints of the Region, so the flesh lags and wobbles on top of the shape overshoot. Extended Range limits are widened by a slack proportional to Recoil strength so the overshoot is not clipped at the maximum.

**Consequences.** The sliders show targets, never the overshoot. Strength 0 is critically damped (no overshoot). Dependent systems (skirt, apron) retarget their rest shape without resetting, so cloth follows the growing body instead of popping.
