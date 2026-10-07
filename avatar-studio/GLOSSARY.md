# Avatar Studio

A browser customizer for an adult female figure shown from the neck down to the feet and without arms. People shape the figure, dress it, set its skin and watch it move; the figure is built to look anatomically faithful.

## Language

### The figure

**Avatar**:
The complete customizable figure on the Stage: a Body together with its Skin, an Outfit, a Pose or Motion, and Dynamics.
_Avoid_: model, character, doll

**Body**:
The anatomically faithful adult female shape of the Avatar, covering torso and legs only. It is never shown without a Base Layer.
_Avoid_: mesh, model, figure, skin

**Cut**:
The flat section where the Body ends, once at the neck and once at each shoulder.
_Avoid_: crop, truncation, clip

**Cap**:
The finishing piece that closes a Cut so the Body reads as a deliberate display form rather than a broken figure.
_Avoid_: plug, lid, stump

**Design**:
The complete, serializable description of an Avatar: every Trait value, Outfit choice, color, Pose and Dynamics setting. It is what gets saved, shared and restored.
_Avoid_: config, profile, save file, state

**Preset**:
A named Body setup (Trait and Dial values) that ships with the app, from Natural to Giant. Applying one animates the Body there and leaves Skin and Outfit alone.
_Avoid_: template, default avatar

### Shaping the Body

**Trait**:
A named, bounded characteristic of the Body that a person can adjust, such as Bust Size or Waist Width.
_Avoid_: slider, parameter, modifier, morph

**Neutral**:
The value of a Trait that leaves the Body unchanged. All Neutrals together give the reference Body: an adult woman of average build.
_Avoid_: default, zero, base

**Natural Range**:
The span of a Trait's values that stays anatomically plausible.
_Avoid_: normal range, limits

**Extended Range**:
The wider span of a Trait that allows stylized or exaggerated proportions. Sliders cover it by default and mark where the Natural Range ends; the Body can briefly pass beyond it during a Recoil.
_Avoid_: extreme mode, cheat range

**Macro Trait**:
A Trait whose effect depends on the other Macro Traits, so their influences combine rather than add (Age, Weight, Muscle, Height, Proportions, Ancestry, Bust Size, Bust Firmness).
_Avoid_: global slider, main slider

**Detail Trait**:
A Trait that reshapes one Region on its own and adds on top of the Macro Traits.
_Avoid_: fine-tune, local slider

**Morph Target**:
A stored displacement of the Body's surface that Traits blend to produce a Body.
_Avoid_: shape key, blend shape, target file

**Dial**:
A single control that moves several Traits together toward a named look, such as Curves, Muscle Tone or Thigh Thickness. A Design stores the Dial's position apart from the Traits it drives.
_Avoid_: shortcut, combo slider, master slider

**Lift**:
The vertical carriage of a Soft Tissue Region, from perky (high and firm) to relaxed (fuller and lower). Relaxed is a soft, attractive shape and never the sagging of an aged body; only Age ages the Body.
_Avoid_: sag, droop

**Silhouette**:
One of the named overall outline families (Hourglass, Pear, Apple, Rectangle, Inverted Triangle, Diamond, Column) that can be blended into the Body.
_Avoid_: body type, body shape

**Region**:
A named anatomical area of the Body: Neck, Shoulders, Torso, Bust, Waist, Belly, Hips, Glutes, Thighs, Knees, Calves, Ankles, Feet.
_Avoid_: part, zone, area, body part

**Age**:
A Macro Trait stating how many years old the Body appears. It is always an adult age, 25 to 80.
_Avoid_: maturity, life stage

**Ancestry**:
The blend of three reference morphologies (African, Asian, Caucasian) that shapes the Body. It does not decide Skin Tone.
_Avoid_: race, ethnicity

**Measurement**:
A dimension of the current Body in centimeters (Height, Bust, Underbust, Waist, Hips, Thigh, Calf). It is read from the Body, never set directly.
_Avoid_: size, dimension, stat

### Movement

**Rig**:
The articulated skeleton that poses the Body, including the virtual joints that carry Jiggle.
_Avoid_: armature, bones

**Pose**:
A still arrangement of the Rig, such as Standing, Contrapposto or Hip Pop.
_Avoid_: stance, position

**Motion**:
A looping animation of the Rig, such as Idle, Walk, Strut or Dance.
_Avoid_: animation clip, action

**Ground Contact**:
The rule that the lowest point of the Avatar always rests on the Stage floor, whatever the Traits, Heel Height or Pose.
_Avoid_: grounding, floor snap

**Recoil**:
The springy overshoot with which the Body reaches a new Trait or Dial value: it grows past the target, settles back and sets off a Jiggle in the Soft Tissue. Its strength is a Dynamics setting; at zero the Body goes straight to the value.
_Avoid_: bounce animation, easing, tween

**Contact**:
The rule that two masses of the Body meet without crossing: the breasts press together into a cleavage and the thighs touch along their length.
_Avoid_: collision, clipping

**Soft Tissue**:
The Regions whose flesh visibly moves with the Avatar: Bust, Glutes, Thighs and Belly.
_Avoid_: jiggle zone, physics region

**Jiggle**:
The secondary motion of Soft Tissue as it lags behind and rebounds from the Avatar's movement.
_Avoid_: bounce, wobble, soft-body

**Softness**:
How far a Soft Tissue Region swings in a Jiggle.
_Avoid_: bounciness, amplitude

**Firmness**:
How strongly a Soft Tissue Region resists deformation, both at rest (its shape) and in motion (its Jiggle).
_Avoid_: stiffness, tightness

**Dynamics**:
The adjustable settings of all secondary motion: Jiggle per Region, Drape behavior and wind.
_Avoid_: physics settings, simulation options

### Dressing

**Outfit**:
A themed set of Garments worn together, such as the Bunny Suit or the Maid Dress.
_Avoid_: costume, look, set

**Garment**:
A single piece of clothing: a leotard, stockings, a skirt, an apron, shoes.
_Avoid_: clothes, item, piece

**Base Layer**:
The bikini (a triangle or bandeau top and a bikini or boyshort bottom) that is always worn beneath everything else, so the Body is never shown bare. It tucks itself inside any Garment that covers the same area.
_Avoid_: underwear, default clothes

**Shell**:
A Garment that clings to the Body's surface and deforms with it, such as a leotard, tights or stockings.
_Avoid_: skin-tight clothing, overlay

**Drape**:
A Garment or Accessory that hangs free and moves under simulated cloth physics, such as a skirt, an apron, a ribbon or a tail.
_Avoid_: cloth, loose garment, soft garment

**Ribbon**:
A thin Garment part that follows the Body's surface along a path: the strings of a bikini, a strap, a tie. It can be finer than the Body's mesh because it is built from the path, not cut from the surface.
_Avoid_: string, cord, line

**Accessory**:
An addition that is not clothing: a tail, a collar bow, a ribbon, an anklet.
_Avoid_: prop, add-on

**Padding**:
The extra thickness under a Shell that smooths the Body's contour over the Bust. At zero, thin fabric traces the form (the "tent").
_Avoid_: cup, lining

**Fabric**:
The material look of a Garment: satin, latex, cotton, lace, fishnet, velvet.
_Avoid_: texture, material

**Trim**:
A decorative edge or seam detail on a Garment, such as a lace edge, binding or piping.
_Avoid_: border, decoration

**Heel Height**:
How high shoes lift the heel; it tilts the feet and lifts the Avatar while Ground Contact still holds.
_Avoid_: shoe size, platform

### Skin and presentation

**Skin**:
The surface appearance of the Body: tone, undertone, fine detail, Marks and Sheen.
_Avoid_: texture, material

**Skin Tone**:
The overall color of the Skin, chosen independently of Ancestry.
_Avoid_: complexion, race color

**Mark**:
A small natural feature on the Skin, such as a freckle or a mole.
_Avoid_: spot, blemish

**Imperfection**:
Any natural irregularity of the Skin: pores, mottling, redness, veins and Marks. Each one can be dialed down to zero, and all together give flawless skin.
_Avoid_: defect, texture detail, noise

**Anatomy**:
The relief and shading of bones, tendons and muscles on the Skin: collarbones, neck tendons, breastbone, ribs, abdominal line, navel, hip bones, spine and lower-back dimples. It never changes the Body's geometry, and each group can be dialed from nothing to pronounced.
_Avoid_: bone detail, normal map, bump

**Sheen**:
The glossy or shimmering finish of the Skin.
_Avoid_: shine, glow

**Stage**:
The environment around the Avatar: floor, backdrop, lighting and camera.
_Avoid_: scene, studio, viewport

**Focus**:
A camera framing of one Region or of the whole Avatar.
_Avoid_: zoom preset, view
