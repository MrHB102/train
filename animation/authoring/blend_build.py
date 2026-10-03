"""Builds animation/blender/MrHB_fight_v2.blend (Blender 5.x; saved with bpy 5.0, opens in 5.2).

    python blend_build.py            (runs the whole v2 build first, then assembles and saves the .blend)

Scene "Fight3D" (120 fps, 1080x1920, EEVEE):
  * MrHB / Dummy        canonical R6 armatures (bones exactly as the r6-animator skill builds them, 1 unit = 1 stud) with
                        Roblox-look rounded parts; pose-bone Euler orders ZYX (limbs) / ZXY (centre) so the F-curves are the
                        canonical R6 channels.  Their actions ARE the v2 motion: the same Bezier F-curves (interpolation,
                        easing, handles) that were evaluated to render the video.  The player's blink frames are keyed
                        hide_render / hide_viewport; the dummy's hurt face is a keyed mix in its head material.
  * CAM_Cinematic       the v2 camera, keyed per frame (location, rotation, focal length, focus distance, f-stop); cuts are
                        CONSTANT keys and timeline markers carry the shot names
  * environment         tiled floor, gradient sky world, key sun + warm back light, distant blocks, arena rim
  * FX                  3D effects as objects: impact / ground rings, shock walls, ground cracks, rock pillars, after-image
                        rigs (NLA time-offset copies of the actions), energy aura shells, kick arcs, debris / dust / spark
                        particle systems, impact flash lights, the floating @Mr_HB name tag
  * compositor          bloom (glare), slight chromatic dispersion, vignette
Scene "Edit" (VSE): the Fight3D scene strip + the soundtrack (out/v2/audio.wav, packed).
Not reproduced in Blender (they are 2D post effects in the video): hand-drawn stars / shards / speed lines / manga impact
frames, motion / radial blur, titles - see README.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy        # noqa: E402
import bmesh      # noqa: E402
from mathutils import Matrix, Vector, Euler  # noqa: E402

import rig as _rig  # noqa: E402,F401  (puts the skill scripts on sys.path)
import r6         # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, '..'))
BLEND_DIR = os.path.join(ROOT, 'blender')
FPS = 120
S_R2B = Matrix(((-1, 0, 0), (0, 0, 1), (0, 1, 0)))       # Roblox / r6 world (x right, y up, z back) -> Blender (z up)


def V(p):
    return S_R2B @ Vector((p[0], p[1], p[2]))


def hexcol(h, a=1.0):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c) + (a,)


# ------------------------------------------------------------------------------------------------ action helpers
def new_action(name, id_type='OBJECT'):
    act = bpy.data.actions.new(name)
    slot = act.slots.new(id_type=id_type, name=name)
    strip = act.layers.new('Layer').strips.new(type='KEYFRAME')
    return act, slot, strip.channelbag(slot, ensure=True)


def assign(idblock, act, slot):
    ad = idblock.animation_data_create()
    ad.action = act
    ad.action_slot = slot


def fcurve_keys(cb, path, index, xs, ys, interp='LINEAR', group=None, constant_at=()):
    fc = cb.fcurves.new(path, index=index, group_name=group or path)
    kp = fc.keyframe_points
    kp.add(len(xs))
    co = [0.0] * (2 * len(xs))
    co[0::2] = xs; co[1::2] = ys
    kp.foreach_set('co', co)
    ip = {'LINEAR': 1, 'CONSTANT': 0, 'BEZIER': 2}[interp]
    kp.foreach_set('interpolation', [ip] * len(xs))
    for i in constant_at:
        if 0 <= i < len(kp): kp[i].interpolation = 'CONSTANT'
    fc.update()
    return fc


# ------------------------------------------------------------------------------------------------ materials
def principled(name, color, rough=0.6, emit=None, emit_strength=0.0):
    m = bpy.data.materials.new(name)
    nt = m.node_tree if m.node_tree else None
    if nt is None:
        m.use_nodes = True; nt = m.node_tree
    b = nt.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = color
    b.inputs['Roughness'].default_value = rough
    if emit:
        b.inputs['Emission Color'].default_value = emit
        b.inputs['Emission Strength'].default_value = emit_strength
    return m


def fx_material(name, additive=True, gradient=None):
    """emissive effect material: colour and alpha come from the object's colour (Object Info), so one material serves every
    effect object and the effect is animated by keying object.color"""
    m = bpy.data.materials.new(name)
    if not m.node_tree: m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; Lk = nt.links
    for n in list(N): N.remove(n)
    out = N.new('ShaderNodeOutputMaterial')
    info = N.new('ShaderNodeObjectInfo')
    em = N.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = 3.0
    tr = N.new('ShaderNodeBsdfTransparent')
    mix = N.new('ShaderNodeMixShader')
    Lk.new(info.outputs['Color'], em.inputs['Color'])
    alpha = info.outputs['Alpha']
    if gradient == 'z':                      # shock walls: fade toward the top
        tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); mr = N.new('ShaderNodeMapRange')
        mr.inputs['From Min'].default_value = 0.0; mr.inputs['From Max'].default_value = 1.0
        mr.inputs['To Min'].default_value = 1.0; mr.inputs['To Max'].default_value = 0.0
        mul = N.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'
        Lk.new(tc.outputs['Generated'], sep.inputs[0]); Lk.new(sep.outputs['Z'], mr.inputs['Value'])
        Lk.new(mr.outputs['Result'], mul.inputs[0]); Lk.new(alpha, mul.inputs[1]); alpha = mul.outputs[0]
    Lk.new(alpha, mix.inputs['Fac'])
    Lk.new(tr.outputs[0], mix.inputs[1]); Lk.new(em.outputs[0], mix.inputs[2])
    if additive:
        add = N.new('ShaderNodeAddShader')
        Lk.new(tr.outputs[0], add.inputs[0]); Lk.new(em.outputs[0], add.inputs[1])
        mix2 = N.new('ShaderNodeMixShader')
        Lk.new(alpha, mix2.inputs['Fac']); Lk.new(tr.outputs[0], mix2.inputs[1]); Lk.new(add.outputs[0], mix2.inputs[2])
        Lk.new(mix2.outputs[0], out.inputs['Surface'])
    else:
        Lk.new(mix.outputs[0], out.inputs['Surface'])
    m.blend_method = 'BLEND' if hasattr(m, 'blend_method') else None
    if hasattr(m, 'surface_render_method'): m.surface_render_method = 'BLENDED'
    m.use_backface_culling = False
    return m


def face_image(name, hurt, base):
    """face decal (the classic smile, or the knocked-silly face) drawn with PIL, packed into the .blend"""
    from PIL import Image, ImageDraw
    S = 512
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    ink = (20, 22, 28, 255)
    if not hurt:
        d.ellipse((154, 204, 198, 272), fill=ink); d.ellipse((314, 204, 358, 272), fill=ink)
        d.arc((150, 230, 362, 430), 20, 160, fill=ink, width=16)
    else:
        for cx in (170, 342):
            d.line((cx - 34, 206, cx + 34, 272), fill=ink, width=18); d.line((cx + 34, 206, cx - 34, 272), fill=ink, width=18)
        d.ellipse((204, 332, 308, 412), fill=ink); d.ellipse((222, 366, 290, 406), fill=(192, 57, 43, 255))
    path = os.path.join(BLEND_DIR, 'tex', name + '.png')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path)
    img = bpy.data.images.load(path); img.pack(); img.name = name
    return img


def head_material(name, skin, faces, hurt_keys=None):
    m = principled(name, skin)
    nt = m.node_tree; N = nt.nodes; Lk = nt.links
    b = N.get('Principled BSDF')
    uv = N.new('ShaderNodeUVMap')
    t0 = N.new('ShaderNodeTexImage'); t0.image = faces[0]; t0.extension = 'CLIP'
    Lk.new(uv.outputs['UV'], t0.inputs['Vector'])
    col = N.new('ShaderNodeMix'); col.data_type = 'RGBA'
    col.inputs['A'].default_value = skin
    Lk.new(t0.outputs['Color'], col.inputs['B'])
    a = t0.outputs['Alpha']
    if len(faces) > 1:
        t1 = N.new('ShaderNodeTexImage'); t1.image = faces[1]; t1.extension = 'CLIP'
        Lk.new(uv.outputs['UV'], t1.inputs['Vector'])
        sw = N.new('ShaderNodeValue'); sw.name = 'HurtFace'; sw.label = 'hurt face (keyed)'
        cm = N.new('ShaderNodeMix'); cm.data_type = 'RGBA'
        Lk.new(sw.outputs[0], cm.inputs['Factor']); Lk.new(t0.outputs['Color'], cm.inputs['A']); Lk.new(t1.outputs['Color'], cm.inputs['B'])
        am = N.new('ShaderNodeMix'); am.data_type = 'FLOAT'
        Lk.new(sw.outputs[0], am.inputs['Factor']); Lk.new(t0.outputs['Alpha'], am.inputs['A']); Lk.new(t1.outputs['Alpha'], am.inputs['B'])
        Lk.new(cm.outputs['Result'], col.inputs['B']); a = am.outputs['Result']
    Lk.new(a, col.inputs['Factor'])
    Lk.new(col.outputs['Result'], b.inputs['Base Color'])
    return m


# ------------------------------------------------------------------------------------------------ R6 rig
LOOKS = {'player': {'Head': '#f5cd30', 'Torso': '#0d69ac', 'Arm': '#f5cd30', 'Leg': '#4b974b'},
         'dummy': {'Head': '#a3a2a5', 'Torso': '#a3a2a5', 'Arm': '#a3a2a5', 'Leg': '#8f8e92'}}
SIZE = {'Torso': (2, 2, 1), 'Head': (1.25, 1.25, 1.25), 'Left Arm': (1, 2, 1), 'Right Arm': (1, 2, 1), 'Left Leg': (1, 2, 1), 'Right Leg': (1, 2, 1)}


def box_mesh(name, size, center, front_uv=False):
    """box in the r6 rest frame (mapped to Blender), optional [0,1] UVs on the front (-Z r6 = -Y Blender) face"""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    uvl = bm.loops.layers.uv.new('UVMap')
    for v in bm.verts:
        p = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))      # r6 local
        v.co = S_R2B @ (p + Vector(center))
    bm.normal_update()
    for f in bm.faces:
        n = f.normal
        for l in f.loops:
            if front_uv and n.y < -0.9:
                lv = S_R2B.inverted() @ l.vert.co - Vector(center)
                l[uvl].uv = (0.5 - lv.x / size[0], 0.5 + lv.y / size[1])
            else:
                l[uvl].uv = (0.001, 0.001)
    bm.to_mesh(me); bm.free()
    return me


def build_rig(name, kind, coll, faces):
    arm = bpy.data.armatures.new(name); ob = bpy.data.objects.new(name, arm); coll.objects.link(ob)
    vl = bpy.context.view_layer
    vl.objects.active = ob; ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    cen = {b: p[0] for b, p in r6.fk({}).items()}; jp = {}
    for b in r6.BONES:
        par = r6.J[b][0]; jp[b] = cen[b] if par is None else tuple(cen[par][i] + r6.J[b][1][i] for i in range(3))
    for b in r6.BONES:
        eb = arm.edit_bones.new(b); eb.head = S_R2B @ Vector(jp[b]); eb.tail = eb.head + Vector((0, 0, 0.25))
    for b in r6.BONES:
        if r6.J[b][0]: arm.edit_bones[b].parent = arm.edit_bones[r6.J[b][0]]
    bpy.ops.object.mode_set(mode='OBJECT')
    import bl_map
    for pb in ob.pose.bones:
        pb.rotation_mode = bl_map.MODE[pb.name]
    L = LOOKS[kind]
    mats = {}
    for part in ('Torso', 'Arm', 'Leg'):
        mats[part] = principled('%s_%s' % (name, part), hexcol(L[part]), 0.62)
    mats['Head'] = head_material('%s_Head' % name, hexcol(L['Head']), faces)
    meshes = {}
    for b in r6.BONES[1:]:
        me = box_mesh('%s.%s' % (name, b), SIZE[b], cen[b], front_uv=(b == 'Head'))
        part = 'Head' if b == 'Head' else ('Torso' if b == 'Torso' else ('Arm' if 'Arm' in b else 'Leg'))
        me.materials.append(mats[part])
        mo = bpy.data.objects.new('%s.%s' % (name, b), me); coll.objects.link(mo)
        vg = mo.vertex_groups.new(name=b); vg.add(list(range(len(me.vertices))), 1.0, 'REPLACE')
        bev = mo.modifiers.new('Bevel', 'BEVEL'); bev.width = 0.26 if b == 'Head' else 0.07; bev.segments = 4 if b == 'Head' else 2
        bev.limit_method = 'NONE'
        md = mo.modifiers.new('Armature', 'ARMATURE'); md.object = ob
        mo.parent = ob
        meshes[b] = mo
    ob.select_set(False)
    return ob, meshes, cen


# ------------------------------------------------------------------------------------------------ build
def build_scene(S, verbose=True):
    import choreo as C
    import timeline as TL
    import export2
    warp = S.warp; n_out = warp.n_total
    sc = bpy.context.scene
    sc.name = 'Fight3D'
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.fps = FPS; sc.render.fps_base = 1.0
    sc.render.resolution_x, sc.render.resolution_y = 1080, 1920
    sc.frame_start, sc.frame_end = 0, n_out - 1
    sc.view_settings.view_transform = 'AgX'
    try: sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception: pass
    sc.unit_settings.system = 'NONE'
    root = sc.collection
    colls = {}
    for nm in ('Characters', 'Camera', 'Environment', 'FX', 'FX_Ghosts', 'Lights'):
        c = bpy.data.collections.new(nm); root.children.link(c); colls[nm] = c

    # ---- characters
    smile = face_image('face_smile', False, None); hurt = face_image('face_hurt', True, None)
    rigs = {}
    for cid, nm, kind, faces in (('P', 'MrHB', 'player', [smile]), ('D', 'Dummy', 'dummy', [smile, hurt])):
        ob, meshes, cen = build_rig(nm, kind, colls['Characters'], faces)
        act, slot = S.act[cid]
        assign(ob, act, slot)
        rigs[cid] = (ob, meshes)
    # player blink visibility (keyed on the part meshes)
    vis = [1 if export2.sample_story(C.P_VIS, warp.af(n)) else 0 for n in range(n_out)]
    changes = [0] + [n for n in range(1, n_out) if vis[n] != vis[n - 1]]
    for b, mo in rigs['P'][1].items():
        act, slot, cb = new_action('vis_' + mo.name)
        xs = [float(n) for n in changes]; ys = [0.0 if vis[n] else 1.0 for n in changes]
        fcurve_keys(cb, 'hide_render', 0, xs, ys, 'CONSTANT'); fcurve_keys(cb, 'hide_viewport', 0, xs, ys, 'CONSTANT')
        assign(mo, act, slot)
    # dummy hurt face
    hurtv = [1.0 if export2.sample_story(S.DR.DUMMY_HURT, warp.af(n)) else 0.0 for n in range(n_out)]
    ch = [0] + [n for n in range(1, n_out) if hurtv[n] != hurtv[n - 1]]
    hm = bpy.data.materials['Dummy_Head']
    act, slot, cb = new_action('HurtFace', 'NODETREE')
    fcurve_keys(cb, 'nodes["HurtFace"].outputs[0].default_value', 0, [float(n) for n in ch], [hurtv[n] for n in ch], 'CONSTANT')
    assign(hm.node_tree, act, slot)

    # ---- camera
    cam_d = bpy.data.cameras.new('CAM_Cinematic'); cam = bpy.data.objects.new('CAM_Cinematic', cam_d); colls['Camera'].objects.link(cam)
    sc.camera = cam
    cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 24.0; cam_d.clip_start = 0.1; cam_d.clip_end = 2000
    cam_d.dof.use_dof = True
    loc = [[], [], []]; rot = [[], [], []]; lens = []; fdist = []; fstop = []
    prev = None
    for n, c in enumerate(S.cam):
        P = V(c[0:3]); L = V(c[3:6]); fov = c[6]; roll = math.radians(c[7])
        fwd = (L - P).normalized(); right = fwd.cross(Vector((0, 0, 1))).normalized(); up = right.cross(fwd)
        x = right * math.cos(roll) + up * math.sin(roll); y = -right * math.sin(roll) + up * math.cos(roll)
        M = Matrix((x, y, -fwd)).transposed()
        e = M.to_euler('XYZ', prev) if prev is not None else M.to_euler('XYZ')
        prev = e
        for i in range(3): loc[i].append(P[i]); rot[i].append(e[i])
        lens.append(12.0 / math.tan(math.radians(fov) / 2))
        fdist.append(max(0.2, c[8] if len(c) > 8 else 10.0))
        ap = c[9] if len(c) > 9 else 0.0
        fstop.append(16.0 - (16.0 - 1.8) * min(1.0, ap))
    xs = [float(n) for n in range(n_out)]
    cuts = [n - 1 for n in S.cuts if n > 0]
    act, slot, cb = new_action('CAM_Cinematic')
    for i in range(3):
        fcurve_keys(cb, 'location', i, xs, loc[i], 'LINEAR', 'Camera', cuts)
        fcurve_keys(cb, 'rotation_euler', i, xs, rot[i], 'LINEAR', 'Camera', cuts)
    assign(cam, act, slot)
    act, slot, cb = new_action('CAM_Lens', 'CAMERA')
    fcurve_keys(cb, 'lens', 0, xs, lens, 'LINEAR', 'Lens', cuts)
    fcurve_keys(cb, 'dof.focus_distance', 0, xs, fdist, 'LINEAR', 'Lens', cuts)
    fcurve_keys(cb, 'dof.aperture_fstop', 0, xs, fstop, 'LINEAR', 'Lens', cuts)
    assign(cam_d, act, slot)
    for n in S.cuts:
        s = None
        af = warp.af(n)
        for sh in C.CAM.shots:
            if sh.f0 <= af < sh.f1: s = sh
        sc.timeline_markers.new(s.name if s else 'cut', frame=n)

    # ---- environment
    env = colls['Environment']
    me = bpy.data.meshes.new('Floor'); bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=500); bm.to_mesh(me); bm.free()
    floor = bpy.data.objects.new('Floor', me); env.objects.link(floor)
    fm = principled('Floor_Tiles', hexcol('#1d2a3f'), 0.4)
    nt = fm.node_tree; N = nt.nodes; Lk = nt.links
    br = N.new('ShaderNodeTexBrick'); br.offset = 0.0; br.squash = 1.0
    br.inputs['Scale'].default_value = 1.0 / 5.55; br.inputs['Mortar Size'].default_value = 0.02
    br.inputs['Brick Width'].default_value = 1.0; br.inputs['Row Height'].default_value = 1.0
    br.inputs['Color1'].default_value = hexcol('#2b3d5c'); br.inputs['Color2'].default_value = hexcol('#223250'); br.inputs['Mortar'].default_value = hexcol('#0b1018')
    tc = N.new('ShaderNodeTexCoord'); Lk.new(tc.outputs['Object'], br.inputs['Vector'])
    Lk.new(br.outputs['Color'], N['Principled BSDF'].inputs['Base Color'])
    me.materials.append(fm)
    bm_ = principled('Block_Light', hexcol('#dfe8f3'), 0.9); bd_ = principled('Block_Dark', hexcol('#1b2433'), 0.7)
    for i, (x, z, w, h, d) in enumerate([[-70, -120, 40, 26, 6], [-30, -160, 56, 40, 6], [60, -140, 30, 60, 8], [110, -90, 24, 34, 6], [-120, -60, 20, 30, 20], [150, -170, 70, 50, 10], [10, -210, 90, 30, 12]]):
        me = box_mesh('Block%d' % i, (w, h, d), (x, h / 2, z)); me.materials.append(bm_ if (x + z) % 2 else bd_)
        o = bpy.data.objects.new('Block%d' % i, me); env.objects.link(o)
    bpy.ops.mesh.primitive_torus_add(major_radius=34.3, minor_radius=0.12, location=(0, 0, 0.03))
    rim = bpy.context.active_object; rim.name = 'ArenaRim'
    for c in rim.users_collection: c.objects.unlink(rim)
    env.objects.link(rim)
    rim.data.materials.append(principled('Rim_Glow', hexcol('#9fd2ff'), 0.5, hexcol('#9fd2ff'), 2.0))
    # world: gradient sky (zenith / mid / horizon of the video's sky)
    w = bpy.data.worlds.new('Sky'); sc.world = w
    if not w.node_tree: w.use_nodes = True
    N = w.node_tree.nodes; Lk = w.node_tree.links
    bg = N.get('Background'); tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); ramp = N.new('ShaderNodeValToRGB')
    nrm = N.new('ShaderNodeVectorMath'); nrm.operation = 'NORMALIZE'
    Lk.new(tc.outputs['Generated'], nrm.inputs[0]); Lk.new(nrm.outputs[0], sep.inputs[0]); Lk.new(sep.outputs['Z'], ramp.inputs['Fac'])
    ramp.color_ramp.elements[0].position = 0.0; ramp.color_ramp.elements[0].color = (0.62, 0.78, 0.95, 1)
    ramp.color_ramp.elements[1].position = 0.9; ramp.color_ramp.elements[1].color = (0.07, 0.24, 0.66, 1)
    e = ramp.color_ramp.elements.new(0.25); e.color = (0.24, 0.52, 0.90, 1)
    Lk.new(ramp.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = 1.0
    # lights
    lc = colls['Lights']
    for nm, d, col, en in (('Sun_Key', (-0.55, 0.78, 0.62), (1.0, 0.95, 0.86), 4.0), ('Sun_Back', (-0.45, 0.62, -0.65), (1.0, 0.89, 0.72), 2.2), ('Fill_Cool', (0.55, 0.4, 0.75), (0.62, 0.78, 1.0), 0.8)):
        ld = bpy.data.lights.new(nm, 'SUN'); ld.energy = en; ld.color = col; ld.angle = math.radians(2.0)
        lo = bpy.data.objects.new(nm, ld); lc.objects.link(lo)
        dv = V(d).normalized()
        lo.rotation_euler = dv.to_track_quat('Z', 'Y').to_euler()

    # ---- name tag (bone-parented to the head, faces the camera)
    cu = bpy.data.curves.new('NameTag', 'FONT'); cu.body = '@Mr_HB'; cu.align_x = 'CENTER'; cu.size = 0.8; cu.extrude = 0.02
    cu.offset = 0.0
    tag = bpy.data.objects.new('NameTag_@Mr_HB', cu); colls['Characters'].objects.link(tag)
    tag.data.materials.append(principled('NameTag', (1, 1, 1, 1), 0.5, (1, 1, 1, 1), 1.5))
    tag.parent = rigs['P'][0]; tag.parent_type = 'BONE'; tag.parent_bone = 'Head'
    tag.location = (0, 1.4, 0)
    con = tag.constraints.new('DAMPED_TRACK'); con.target = cam; con.track_axis = 'TRACK_Z'
    tv = [export2.sample_story(S.DR.TAG_VIS, warp.af(n), True) for n in range(n_out)]
    act, slot, cb = new_action('NameTag')
    keyn = [n for n in range(n_out) if n == 0 or abs(tv[n] - tv[n - 1]) > 1e-4 or (n + 1 < n_out and abs(tv[n + 1] - tv[n]) > 1e-4)]
    for i in range(3):
        fcurve_keys(cb, 'scale', i, [float(n) for n in keyn], [max(0.0, tv[n]) for n in keyn], 'LINEAR', 'Tag')
    assign(tag, act, slot)

    n_fx = build_fx(S, colls, rigs, warp, cam)
    # ---- compositor: bloom + dispersion + vignette
    try:
        ng = bpy.data.node_groups.new('Fight_Comp', 'CompositorNodeTree')
        sc.compositing_node_group = ng
        N = ng.nodes; Lk = ng.links
        rl = N.new('CompositorNodeRLayers')
        gl = N.new('CompositorNodeGlare')
        try: gl.glare_type = 'BLOOM'
        except Exception: pass
        ld = N.new('CompositorNodeLensdist')
        el = N.new('CompositorNodeEllipseMask')
        mixv = N.new('ShaderNodeMix') if False else N.new('CompositorNodeMixRGB') if hasattr(bpy.types, 'CompositorNodeMixRGB') else None
        out = N.new('NodeGroupOutput')
        ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
        Lk.new(rl.outputs['Image'], gl.inputs[0])
        Lk.new(gl.outputs[0], ld.inputs[0])
        try: ld.inputs['Dispersion'].default_value = 0.012
        except Exception: pass
        Lk.new(ld.outputs[0], out.inputs[0])
    except Exception as ex:
        print('compositor setup skipped:', ex)

    # ---- Edit scene: VSE with the 3D scene strip and the soundtrack
    ed = bpy.data.scenes.new('Edit')
    ed.render.fps = FPS; ed.render.resolution_x, ed.render.resolution_y = 1080, 1920
    ed.frame_start, ed.frame_end = 0, n_out - 1
    se = ed.sequence_editor_create()
    strips = se.strips if hasattr(se, 'strips') else se.sequences
    st = strips.new_scene('Fight3D', sc, channel=1, frame_start=0)
    # 2D effect layer (half-resolution RGBA image runs, rendered by post2.overlay_rgba) + the @Mr_HB stamp
    od = os.path.join(BLEND_DIR, 'overlay')
    nruns = 0
    if os.path.isdir(od):
        fr = sorted(int(f[1:5]) for f in os.listdir(od) if f.startswith('o') and f.endswith('.png'))
        runs = []
        for f in fr:
            if runs and f == runs[-1][1] + 1: runs[-1][1] = f
            else: runs.append([f, f])
        for a, b in runs:
            im = strips.new_image('fx2d_%04d' % a, os.path.join(od, 'o%04d.png' % a), channel=2, frame_start=a, fit_method='FIT')
            for f in range(a + 1, b + 1): im.elements.append('o%04d.png' % f)
            im.blend_type = 'ALPHA_OVER'
            nruns += 1
        wm = os.path.join(od, 'watermark.png')
        if os.path.exists(wm):
            st_wm = strips.new_image('watermark', wm, channel=3, frame_start=0, fit_method='FIT')
            st_wm.frame_final_end = n_out
            st_wm.blend_type = 'ALPHA_OVER'
    wav = os.path.join(ROOT, 'out', 'v2', 'audio.wav')
    if os.path.exists(wav):
        snd = strips.new_sound('Soundtrack', wav, channel=4, frame_start=0)
        try: snd.sound.pack()
        except Exception: pass
    for sc_ in (sc, ed):
        try:
            if hasattr(sc_.render.image_settings, 'media_type'): sc_.render.image_settings.media_type = 'VIDEO'
            sc_.render.image_settings.file_format = 'FFMPEG'
            sc_.render.ffmpeg.format = 'MPEG4'; sc_.render.ffmpeg.codec = 'H264'; sc_.render.ffmpeg.audio_codec = 'AAC'
        except Exception:
            sc_.render.image_settings.file_format = 'PNG'     # this bpy build has no FFmpeg: PNG sequence (switch to FFmpeg in Blender)
        sc_.render.filepath = '//render/' + sc_.name + '_'
    if verbose: print('blend: Edit scene with %d 2D-effect image runs' % nruns)
    bpy.context.window_manager  # noqa
    if verbose: print('blend: scene built (%d FX objects)' % n_fx)
    return sc


# ------------------------------------------------------------------------------------------------ FX
def _vis_keys(ob, n0, n1, cb=None):
    act, slot, cb = new_action('fx_' + ob.name)
    xs = [0.0, float(max(0, n0)), float(n1)]
    ys = [1.0, 0.0, 1.0]
    fcurve_keys(cb, 'hide_render', 0, xs, ys, 'CONSTANT', 'vis'); fcurve_keys(cb, 'hide_viewport', 0, xs, ys, 'CONSTANT', 'vis')
    return act, slot, cb


def _ease_keys(cb, path, idx, n0, n1, v0, v1, ease='EASE_OUT', ip='CUBIC', group='fx'):
    fc = cb.fcurves.new(path, index=idx, group_name=group)
    kp = fc.keyframe_points; kp.add(2)
    kp[0].co = (n0, v0); kp[1].co = (n1, v1)
    kp[0].interpolation = ip; kp[0].easing = ease
    fc.update()
    return fc


def build_fx(S, colls, rigs, warp, cam):
    import choreo as C
    fxc = colls['FX']; gc = colls['FX_Ghosts']
    BASE = warp.n_total and (120.0 / 18.0)
    mat_add = fx_material('FX_Additive', True)
    mat_wall = fx_material('FX_Wall', True, 'z')
    crack_imgs = {}
    count = 0

    def span(e):
        f0 = e['f0']; f1 = e.get('f1', f0) + 1
        if e.get('clk') == 'real':
            n0 = int(round(warp.out(f0))); return n0, n0 + (f1 - f0) * BASE
        return warp.out(f0), warp.out(f1)

    # ring mesh (annulus) and open cylinder, shared
    me_ring = bpy.data.meshes.new('fx_ring'); bm = bmesh.new()
    segs = 72; vs_o = []; vs_i = []
    for k in range(segs):
        a = 2 * math.pi * k / segs
        vs_o.append(bm.verts.new((math.cos(a), math.sin(a), 0))); vs_i.append(bm.verts.new((0.86 * math.cos(a), 0.86 * math.sin(a), 0)))
    for k in range(segs):
        bm.faces.new((vs_o[k], vs_o[(k + 1) % segs], vs_i[(k + 1) % segs], vs_i[k]))
    bm.to_mesh(me_ring); bm.free(); me_ring.materials.append(mat_add)
    me_wall = bpy.data.meshes.new('fx_wall'); bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=56, radius1=1.0, radius2=1.0, depth=1.0)
    for v in bm.verts: v.co.z += 0.5
    bm.to_mesh(me_wall); bm.free(); me_wall.materials.append(mat_wall)
    me_pillar = box_mesh('fx_pillar', (1, 1, 1), (0, 0.5, 0)); me_pillar.materials.append(principled('Pillar_Rock', hexcol('#8e98ac'), 0.92))
    # debris / dust / spark instance objects (hidden from render themselves)
    inst = bpy.data.collections.new('FX_Instances'); colls['FX'].children.link(inst)
    inst.hide_render = True
    def inst_obj(nm, me):
        o = bpy.data.objects.new(nm, me); inst.objects.link(o); return o
    deb = inst_obj('inst_debris', box_mesh('debris_cube', (1, 1, 1), (0, 0, 0))); deb.data.materials.append(principled('Debris', hexcol('#f2f4f8'), 0.85))
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.0)
    ds = bpy.context.active_object; ds.name = 'inst_dust'
    for c in ds.users_collection: c.objects.unlink(ds)
    inst.objects.link(ds)
    dm = principled('Dust', hexcol('#cfd6df', 1.0), 1.0)
    try:
        dm.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 0.28
        dm.surface_render_method = 'BLENDED'
    except Exception: pass
    ds.data.materials.append(dm)
    sp = inst_obj('inst_spark', box_mesh('spark', (0.06, 0.06, 0.5), (0, 0, 0))); sp.data.materials.append(principled('Spark', (1, 0.9, 0.7, 1), 0.3, (1, 0.9, 0.7, 1), 25.0))

    for e in S.paths_fx3 if hasattr(S, 'paths_fx3') else []:
        pass
    import json
    shot = json.load(open(S.paths[0]))
    for k, e in enumerate(shot['fx']):
        t = e['t']; n0, n1 = span(e)
        if t in ('ring', 'wall'):
            ob = bpy.data.objects.new('fx_%s_%04d' % (t, k), me_ring if t == 'ring' else me_wall); fxc.objects.link(ob)
            ob.location = V(e['p'])
            if t == 'ring':
                nrm = V(e.get('n', [0, 1, 0])).normalized()
                ob.rotation_euler = nrm.to_track_quat('Z', 'Y').to_euler()
            act, slot, cb = _vis_keys(ob, n0, n1)
            r0, r1 = e['r0'], e['r1']
            for i in range(2 if t == 'wall' else 3):
                _ease_keys(cb, 'scale', i, n0, n1, r0, r1)
            if t == 'wall':
                _ease_keys(cb, 'scale', 2, n0, n1, e.get('h0', 0.5), e.get('h1', 1.5))
            col = hexcol(e.get('col', '#ffffff'))
            for i in range(3):
                fc = cb.fcurves.new('color', index=i, group_name='fx'); kp = fc.keyframe_points; kp.add(1); kp[0].co = (n0, col[i])
            _ease_keys(cb, 'color', 3, n0, n1, e.get('a0', 0.9), e.get('a1', 0.0), 'EASE_IN')
            assign(ob, act, slot); count += 1
        elif t == 'pillar':
            ob = bpy.data.objects.new('fx_pillar_%04d' % k, me_pillar); fxc.objects.link(ob)
            ob.location = V((e['p'][0], -0.05, e['p'][2])); ob.rotation_euler = (math.radians(e.get('tilt', 0)), 0, -math.radians(e.get('rot', 0)))
            act, slot, cb = _vis_keys(ob, n0, n1)
            _ease_keys(cb, 'scale', 0, n0, n0 + 2 * BASE, e['w'], e['w']); _ease_keys(cb, 'scale', 1, n0, n0 + 2 * BASE, e['w'] * e.get('d', 1), e['w'] * e.get('d', 1))
            _ease_keys(cb, 'scale', 2, n0, warp.out(e['f0'] + 2), 0.01, e['h'])
            assign(ob, act, slot); count += 1
        elif t in ('debris', 'dust', 'sparks'):
            me = bpy.data.meshes.new('emit'); bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.2); bm.to_mesh(me); bm.free()
            ob = bpy.data.objects.new('fx_%s_%04d' % (t, k), me); fxc.objects.link(ob)
            ob.location = V(e['p']); ob.hide_render = False
            ps = ob.modifiers.new('ps', 'PARTICLE_SYSTEM').particle_system; pst = ps.settings
            pst.frame_start = n0; pst.frame_end = n0 + 1
            pst.count = int(e.get('n', 10)) * (2 if t == 'dust' else 1)
            pst.lifetime = (e.get('life', 0.9) if t != 'dust' else 0.9) * 120
            pst.normal_factor = {'debris': e.get('speed', 10) * 0.6, 'dust': 1.2, 'sparks': e.get('speed', 18) * 0.6}[t]
            pst.factor_random = {'debris': e.get('speed', 10) * 0.5, 'dust': 1.0, 'sparks': e.get('speed', 18) * 0.5}[t]
            pst.render_type = 'OBJECT'
            pst.instance_object = {'debris': deb, 'dust': ds, 'sparks': sp}[t]
            sz = e.get('size', 1.0)
            pst.particle_size = {'debris': (sz[0] + sz[1]) / 2 if isinstance(sz, list) else 0.2,
                                 'dust': (sz if not isinstance(sz, list) else 1.0) * 0.6, 'sparks': 1.0}[t]
            pst.size_random = 0.6
            pst.effector_weights.gravity = {'debris': 3.5, 'dust': -0.05, 'sparks': 2.6}[t]
            pst.use_rotations = t != 'dust'; pst.angular_velocity_factor = 6.0 if t == 'debris' else 0.0
            if t == 'sparks': pst.use_rotations = True; pst.rotation_mode = 'VEL'
            pst.drag_factor = 0.5 if t == 'dust' else 0.05
            ob.show_instancer_for_render = False; ob.show_instancer_for_viewport = False
            count += 1
        elif t == 'crack':
            seed = e.get('seed', 1) % 4
            if seed not in crack_imgs:
                crack_imgs[seed] = crack_material(seed)
            me = bpy.data.meshes.new('crack'); bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
            uvl = bm.loops.layers.uv.new('UVMap')
            for f_ in bm.faces:
                for l in f_.loops: l[uvl].uv = (l.vert.co.x + 0.5, l.vert.co.y + 0.5)
            bm.to_mesh(me); bm.free(); me.materials.append(crack_imgs[seed])
            ob = bpy.data.objects.new('fx_crack_%04d' % k, me); fxc.objects.link(ob)
            ob.location = V((e['p'][0], 0.03, e['p'][2])); ob.rotation_euler = (0, 0, -e.get('rot', 0))
            end = warp.out(e['fadeAt'] + 14) if e.get('fadeAt') else (n1 if not e.get('keep') else warp.n_total)
            act, slot, cb = _vis_keys(ob, n0, end)
            for i in range(2): _ease_keys(cb, 'scale', i, n0, warp.out(e['f0'] + 2), e['s'] * 0.35, e['s'])
            assign(ob, act, slot); count += 1
        elif t == 'slash':
            ob = slash_object(k, e, mat_add, fxc)
            act, slot, cb = _vis_keys(ob, n0, n1)
            col = hexcol(e.get('col', '#ffffff'))
            for i in range(3):
                fc = cb.fcurves.new('color', index=i, group_name='fx'); kp = fc.keyframe_points; kp.add(1); kp[0].co = (n0, col[i])
            _ease_keys(cb, 'color', 3, n0, n1, 1.0, 0.0, 'EASE_IN')
            assign(ob, act, slot); count += 1
        elif t == 'glow' and e.get('light'):
            ld = bpy.data.lights.new('fx_flash_%04d' % k, 'POINT'); ld.color = hexcol(e.get('col', '#fff2d6'))[:3]; ld.shadow_soft_size = 0.5
            ob = bpy.data.objects.new('fx_flash_%04d' % k, ld); colls['Lights'].objects.link(ob); ob.location = V(e['p'])
            act, slot, cb = new_action('fx_flash_%04d' % k, 'LIGHT')
            fc = cb.fcurves.new('energy', index=0, group_name='fx'); kp = fc.keyframe_points; kp.add(3)
            peak = 4000.0 * e['light']
            kp[0].co = (n0 - 1, 0.0); kp[1].co = (n0, peak); kp[2].co = (n1, 0.0)
            kp[1].interpolation = 'EXPO'; kp[1].easing = 'EASE_OUT'
            fc.update(); assign(ld, act, slot); count += 1
    count += build_ghosts_and_aura(S, shot, colls, rigs, warp)
    return count


def crack_material(seed):
    from PIL import Image, ImageDraw
    import random
    r = random.Random(seed * 13 + 5)
    im = Image.new('RGBA', (512, 512), (0, 0, 0, 0)); d = ImageDraw.Draw(im)

    def branch(x, y, a, ln, wd, depth):
        segs = 5 + r.randint(0, 2); px, py = x, y
        for i in range(segs):
            a += (r.random() - 0.5) * 0.7; l = ln / segs * (0.7 + r.random() * 0.6)
            nx, ny = px + math.cos(a) * l, py + math.sin(a) * l
            d.line((px, py, nx, ny), fill=(190, 225, 255, 140), width=int(wd + 5))
            d.line((px, py, nx, ny), fill=(4, 6, 10, 245), width=max(1, int(wd)))
            if depth < 2 and r.random() < 0.45: branch(nx, ny, a + (1 if r.random() < .5 else -1) * (0.5 + r.random() * 0.7), ln * 0.45, wd * 0.6, depth + 1)
            px, py = nx, ny; wd *= 0.86
    n = 7 + r.randint(0, 3)
    for i in range(n): branch(256, 256, i / n * 2 * math.pi + r.random() * 0.5, 120 + r.random() * 120, 9, 0)
    path = os.path.join(BLEND_DIR, 'tex', 'crack_%d.png' % seed); im.save(path)
    img = bpy.data.images.load(path); img.pack()
    m = bpy.data.materials.new('Crack_%d' % seed)
    if not m.node_tree: m.use_nodes = True
    N = m.node_tree.nodes; Lk = m.node_tree.links
    b = N['Principled BSDF']; tx = N.new('ShaderNodeTexImage'); tx.image = img
    Lk.new(tx.outputs['Color'], b.inputs['Base Color']); Lk.new(tx.outputs['Alpha'], b.inputs['Alpha'])
    if hasattr(m, 'surface_render_method'): m.surface_render_method = 'BLENDED'
    return m


def slash_object(k, e, mat, coll):
    """kick arc: partial annulus in the (u, v) plane around p, tapered"""
    me = bpy.data.meshes.new('slash'); bm = bmesh.new()
    U = V(e['u']).normalized(); W = V(e['v']).normalized()
    R = e['r']; rin = e.get('rin', 0.78); th = e.get('th', 0.22)
    a0, a1 = e['a0'], e['a1']; segs = 40
    outer = []; inner = []
    for i in range(segs + 1):
        t = i / segs; a = a0 + (a1 - a0) * t
        taper = math.sin(math.pi * t ** 0.7)
        ro = (rin + th * taper) * R; ri = (rin - th * 0.12 * taper) * R
        dirv = U * math.cos(a) + W * math.sin(a)
        outer.append(bm.verts.new(dirv * ro)); inner.append(bm.verts.new(dirv * ri))
    for i in range(segs):
        bm.faces.new((outer[i], outer[i + 1], inner[i + 1], inner[i]))
    bm.to_mesh(me); bm.free(); me.materials.append(mat)
    ob = bpy.data.objects.new('fx_slash_%04d' % k, me); coll.objects.link(ob); ob.location = V(e['p'])
    return ob


def build_ghosts_and_aura(S, shot, colls, rigs, warp):
    """after-images: per character, one translucent rig copy per story-frame lag, playing the same action through an NLA
    strip shifted by the lag; their visibility / strength are keyed from the ghost events.  Aura: emissive shells on the
    player's own armature, keyed from the aura events."""
    import choreo as C
    count = 0
    BASE = 120.0 / 18.0
    gm = fx_material('FX_Ghost', True)
    ghosts = {'P': {}, 'D': {}}
    for e in shot['fx']:
        if e['t'] == 'ghost':
            for lag in e.get('lags', [2, 4, 6]):
                if abs(lag - round(lag)) < 1e-6:
                    ghosts[e['c']].setdefault(int(round(lag)), []).append(e)
    for cid, lags in ghosts.items():
        ob, meshes = rigs[cid]
        act, slot = S.act[cid]
        for lag, evs in sorted(lags.items()):
            arm = ob.data.copy(); g = bpy.data.objects.new('%s_ghost_lag%d' % (ob.name, lag), arm); colls['FX_Ghosts'].objects.link(g)
            bpy.context.view_layer.update()
            for pb in g.pose.bones: pb.rotation_mode = ob.pose.bones[pb.name].rotation_mode
            ad = g.animation_data_create()
            tr = ad.nla_tracks.new(); st = tr.strips.new('lag%d' % lag, 0, act)
            try: st.action_slot = slot
            except Exception: pass
            st.frame_start_ui = lag * BASE if hasattr(st, 'frame_start_ui') else lag * BASE
            for b, mo in meshes.items():
                gmo = bpy.data.objects.new('%s_ghost%d.%s' % (ob.name, lag, b), mo.data.copy()); colls['FX_Ghosts'].objects.link(gmo)
                gmo.data.materials.clear(); gmo.data.materials.append(gm)
                vg = gmo.vertex_groups.new(name=b); vg.add(list(range(len(gmo.data.vertices))), 1.0, 'REPLACE')
                bev = gmo.modifiers.new('Bevel', 'BEVEL'); bev.width = 0.07; bev.segments = 2
                md = gmo.modifiers.new('Armature', 'ARMATURE'); md.object = g; gmo.parent = g
                # visibility / alpha from the events using this lag
                a2, s2, cb = new_action('ghostvis_%s' % gmo.name)
                xs = [0.0]; ys = [1.0]; ax = []; ay = []
                for e in sorted(evs, key=lambda e: e['f0']):
                    n0, n1 = warp.out(e['f0']), warp.out(e.get('f1', e['f0']) + 1)
                    xs += [n0, n1]; ys += [0.0, 1.0]
                    i = sorted(e['lags']).index(lag)
                    a = 0.8 * e.get('a', 0.5) * e.get('decay', 0.7) ** i
                    ax += [n0, n1]; ay += [a, a * (0.35 if e.get('fade') else 1.0)]
                order = sorted(range(len(xs)), key=lambda i: xs[i]); xs = [xs[i] for i in order]; ys = [ys[i] for i in order]
                fcurve_keys(cb, 'hide_render', 0, xs, ys, 'CONSTANT', 'vis'); fcurve_keys(cb, 'hide_viewport', 0, xs, ys, 'CONSTANT', 'vis')
                col = hexcol(evs[0].get('col', '#9fd0ff'))
                for i in range(3):
                    fc = cb.fcurves.new('color', index=i, group_name='fx'); kp = fc.keyframe_points; kp.add(1); kp[0].co = (0, col[i])
                if ax:
                    o2 = sorted(range(len(ax)), key=lambda i: ax[i])
                    fcurve_keys(cb, 'color', 3, [ax[i] for i in o2], [ay[i] for i in o2], 'LINEAR', 'fx')
                assign(gmo, a2, s2); count += 1
    # aura shells on the player
    auras = [e for e in shot['fx'] if e['t'] == 'aura' and e['c'] == 'P']
    if auras:
        am = fx_material('FX_Aura', True)
        ob, meshes = rigs['P']
        for b, mo in meshes.items():
            amo = bpy.data.objects.new('MrHB_aura.%s' % b, mo.data.copy()); colls['FX'].objects.link(amo)
            amo.data.materials.clear(); amo.data.materials.append(am)
            vg = amo.vertex_groups.new(name=b); vg.add(list(range(len(amo.data.vertices))), 1.0, 'REPLACE')
            sol = amo.modifiers.new('Shell', 'DISPLACE'); sol.strength = 0.22
            md = amo.modifiers.new('Armature', 'ARMATURE'); md.object = ob; amo.parent = ob
            a2, s2, cb = new_action('auravis_%s' % amo.name)
            xs = [0.0]; ys = [1.0]
            for e in auras:
                xs += [warp.out(e['f0']), warp.out(e['f1'] + 1)]; ys += [0.0, 1.0]
            fcurve_keys(cb, 'hide_render', 0, xs, ys, 'CONSTANT', 'vis'); fcurve_keys(cb, 'hide_viewport', 0, xs, ys, 'CONSTANT', 'vis')
            col = hexcol(auras[0].get('col', '#ff4050'))
            for i in range(3):
                fc = cb.fcurves.new('color', index=i, group_name='fx'); kp = fc.keyframe_points; kp.add(1); kp[0].co = (0, col[i])
            fc = cb.fcurves.new('color', index=3, group_name='fx'); kp = fc.keyframe_points; kp.add(1); kp[0].co = (0, auras[0].get('a', 0.5))
            assign(amo, a2, s2); count += 1
    return count


def verify(S, samples=40):
    """evaluate the saved scene with Blender's depsgraph and compare every part centre with the baked 120 fps motion"""
    import choreo as C
    import numpy as np
    sc = bpy.data.scenes['Fight3D']
    worst = 0.0
    n_out = S.warp.n_total
    frames = [int(i * (n_out - 1) / (samples - 1)) for i in range(samples)]
    import rig as rg
    for n in frames:
        sc.frame_set(n)
        dg = bpy.context.evaluated_depsgraph_get()
        for cid, nm in (('P', 'MrHB'), ('D', 'Dummy')):
            arm = bpy.data.objects[nm]
            for j, b in enumerate(rg.PARTS):
                pb = arm.pose.bones[b]
                # part centre = bone (joint) frame applied to the rest offset joint->centre
                rest_head = arm.data.bones[b].head_local
                cen_rest = S_R2B @ Vector(r6.fk({})[b][0])
                M = arm.matrix_world @ pb.matrix @ arm.data.bones[b].matrix_local.inverted()
                c = M @ cen_rest
                ref = V(S.bake.parts[cid][n, j, :3])
                worst = max(worst, (c - ref).length)
    return worst


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import make2
    S = make2.build(export=False, allow_solve=False)     # the solver forks workers: never run it inside the Blender session
    import v2
    v2.S.floor_lift = True
    v2.build_curves()                     # same curves + the floor-lift F-curve (object Z) in each action
    print('floor lift keyed:', v2.S.lift_info)
    build_scene(S)
    err = verify(S)
    print('verify: max part-centre difference between the .blend (depsgraph) and the rendered motion: %.5f studs' % err)
    for sc_ in bpy.data.scenes:
        sc_.frame_set(0)
    os.makedirs(BLEND_DIR, exist_ok=True)
    path = os.path.join(BLEND_DIR, 'MrHB_fight_v2.blend')
    bpy.context.window_manager  # noqa
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
    bpy.ops.file.make_paths_relative()            # overlay image runs: //overlay/... (works wherever the folder is copied)
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
    print('saved', path, os.path.getsize(path) // 1024, 'KB')
    return S, err


if __name__ == '__main__':
    main()
