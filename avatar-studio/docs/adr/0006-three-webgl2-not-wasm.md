# Render with three.js on WebGL2; no WebAssembly, no WebGPU

The owner left the choice to us. We render with three.js's WebGL2 renderer and custom GLSL, and write all simulation in plain JavaScript.

WebGL2 runs in every current browser including phones. The heavy parts (blending about 50k sparse Morph Target entries, a handful of spring joints, about ten thousand cloth particles) cost far less than a frame, so a WebAssembly core would add a toolchain and copying overhead without removing a bottleneck, and WebGPU is not yet universal. Revisit if cloth particle counts grow tenfold.
