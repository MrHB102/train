"""Exports the deliverables that make the project reusable once Blender is available, and writes animation-manifest.json:

  out/clips/mrhb.baked.json    r6 clip (every frame keyed, linear) of the player, exactly what was rendered (incl. floor constraint)
  out/clips/dummy.baked.json   same for the dummy
  out/clips/stage.json         per-frame world/root info + impact table + camera track
  animation-manifest.json      brief, tools, reference evidence and its limits, beat sheet, checks with evidence, unresolved findings

In Blender (R6 armatures bound with r6.use): r6.new(...); load the JSON with r6.clip_from_json / r6.build().
"""
import io
import json
import os
import sys
import contextlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import choreo as C
import direction as DR
import direction2
import rig as rg
import r6

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'out')

BEATS = [
    (0, 29, 'Hook', 'Hero shot, name tag pops in, coil for the dash'),
    (30, 54, 'Dash strike', 'Speed-dash with after-images, straight punch (f36), dummy thrown, crash + slide, pop-up'),
    (55, 72, 'Ground combo', 'Jab, cross, left hook, thrust kick, rising uppercut (launch)'),
    (73, 110, 'Air combo', 'Leap, front kick, spin back kick, roundhouse, flip kick, double axe fists, meteor crash (f102)'),
    (111, 123, 'Calm', 'Hero landing, beckon, dummy springs up'),
    (124, 176, 'Kick flurry', 'Slide sweep, front-flip axe kick, side kick, spinning hook kick, cartwheel, double drop-kick'),
    (177, 222, 'Blink steps', 'Six teleporting strikes from six sides, double palm blast'),
    (223, 262, 'Hammer throw', 'Ankle grab, 2.75 revolutions with the dummy attached to the hands, release'),
    (263, 312, 'Helicopter', 'Speed-dash, handstand spin with three leg sweeps, dragon uppercut corkscrew, bicycle kick'),
    (313, 365, 'Rock pillars', 'Calm walk, stomp, three stone pillars launch the dummy'),
    (366, 405, 'Juggle', 'Knee, instep, header, thigh, knee, scooping lob into the sky'),
    (406, 488, 'Flow charge', '540 spin, back-somersault, slide, power pose with aura while the dummy hangs overhead'),
    (489, 541, 'Sky finisher', 'Super-leap, 14-punch barrage, freeze, face grab, dive, head-first slam (impact f541)'),
    (542, 629, 'Aftermath', 'Crater cracks spread, the player rises and walks out; closing stance and title'),
]


def baked(rig_, name):
    """clip with a key on every frame sampled from the rendered pose (floor constraint included)"""
    r6.new(name, C.FPS)
    c = r6.cur()
    for f in range(C.N):
        p = rig_.pose(f)
        r6.put(c, f, 'lin', **{b: v for b, v in p.items()})
    # make sure all bones exist on every key (hrp too)
    return c


def main():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        C.build()
        DR.direct_all()
        direction2.direct_all2()
    contacts_txt = [l for l in buf.getvalue().splitlines() if l.startswith('contact')]
    os.makedirs(os.path.join(OUT, 'clips'), exist_ok=True)
    cp, cd = baked(C.P.rig, 'MrHB'), baked(C.D.rig, 'Dummy')
    for c, fn in ((cp, 'mrhb.baked.json'), (cd, 'dummy.baked.json')):
        d = {'name': c['name'], 'fps': c['fps'], 'loop': False, 'keys': r6.clip_json(c, 3, 4)}
        with open(os.path.join(OUT, 'clips', fn), 'w') as fh:
            json.dump(d, fh, separators=(',', ':'))
    # lint on the AUTHORED clips (keys as written) - strict
    lint = {}
    for nm, a in (('player', C.P), ('dummy', C.D)):
        r6._S['clip'] = a.clip
        lint[nm] = {'keys': len(a.clip['keys']), 'length_s': round(r6.length(a.clip), 3), 'strict_lint_first_30': r6.lint(a.clip, max_lines=30, strict=True)}
    impacts = [{'frame': f, 'kind': k, 'strength': s} for f, k, s in DR.FXL.sfx]
    shots = [{'f0': s.f0, 'f1': s.f1, 'name': s.name} for s in C.CAM.shots]
    hurt_frames = sum(1 for v in DR.DUMMY_HURT if v)
    blink_hidden = sum(1 for v in C.P_VIS if not v)
    manifest = {
        'title': '@Mr_HB vs training dummy - 35 s freestyle fight',
        'brief': {
            'user_request': 'Animation of the Roblox user @Mr_HB fighting a dummy: 18 fps, cohesive, with dashes and effects, fast / exaggerated / strong movement, freestyle, 35 s, in the style and quality of the referenced YouTube Short. '
                           'Blender is not available now: render outside Blender. Remove the old repository content and use the repo for the animation. Later instruction: do not use a custom Mr_HB skin as the rig - use the plain Roblox R6 look.',
            'assumptions': [
                'Output is vertical 1080x1920 (YouTube Shorts format) at a true 18 fps; a frame-doubled 36 fps version is also exported for players that dislike 18 fps.',
                '"Plain Roblox look": the player uses the classic default Roblox colours (yellow head/arms, blue torso, green legs, smiley face); the dummy is a plain grey Studio-style test dummy. The only personalisation is the floating "@Mr_HB" name tag, a small watermark and the closing title.',
                'No Roblox Studio / Moon Animator available: everything is authored as canonical R6 keyframes (skill r6.py DSL) and rendered by an offline three.js renderer.',
            ]},
        'tools': {
            'blender': 'not available (not executed, nothing verified in Blender)',
            'authoring': 'skill r6-animator (r6.py: DSL, FK, sample, lint) + project-side helpers (animation/authoring/*.py)',
            'renderer': 'three.js r186 in headless Chromium (WebGL2 via SwiftShader), 1080x1920, PCF shadow map, ACES tone map',
            'post': 'numpy/OpenCV: bloom, chromatic aberration, vignette, grain, motion/radial blur, hand-drawn style overlays (impact stars, shards, speed lines, glints, manga impact frames)',
            'audio': 'procedural numpy synth (120 BPM bed + SFX at the recorded impact frames)',
        },
        'timebase': {'fps': C.FPS, 'frames': C.N, 'seconds': C.N / C.FPS, 'bpm_grid': '120 BPM = 9 frames per beat; the main beats land on the grid (f36 first hit, f72 launch, f540 slam)'},
        'reference': {
            'url': 'https://youtube.com/shorts/IJJzI5QEWpM',
            'title_from_oembed': 'Roblox Fight Animation Practice - Moon Animator (channel: Drowsy)',
            'access': {
                'video_playback': 'NOT ACCESSIBLE: yt-dlp was refused by YouTube (HTTP 429 / "Sign in to confirm you are not a bot"). Per the skill rules no cookies / auth bypass / alternate-client tricks were used.',
                'inspected': ['public oEmbed metadata (title/author)', '4 static public thumbnails of the Short (1080x1920 key image + three small frames from different moments)'],
                'motion_observed': 'NONE. Timing, rhythm, dash/hit spacing and camera moves of the reference were NOT observed. No claim is made that this animation matches its timeline.',
            },
            'observed_from_stills': [
                'vertical 9:16 framing; Roblox-style character shown in close-ups from a low angle, alternating with a wide shot',
                'blue-grey tiled floor, bright blue sky with soft clouds and sun glare, a large flat distant block',
                'strong bloom/glow on highlights, chromatic fringing on edges, soft vignette',
                'hand-drawn style effects on top of the 3D: white cubes with sketchy black outlines, white shard/slash shapes',
                'a small creator logo in the top-left corner (not reproduced: this project uses its own @Mr_HB stamp)',
            ],
            'inferred': 'Stepped 18 fps exposure, dashes with trails and impact effects come from the USER DESCRIPTION, not from observation. An uploaded .mp4 of the Short is needed for a real motion-reference pass (see README, "Refinar com o vídeo").',
            'transferable_principles_used': ['hold -> snap -> hold timing with 2-4 frame snaps and 1-2 frame hit-stops', 'hand-drawn style overlays on top of a lit 3D scene', 'alternating wide / close low-angle cameras', 'bloom + chromatic aberration lens look'],
        },
        'originality': 'All poses, timings, contacts, cameras and effects are authored for this project. The skill database was only queried for principles (db.py ls/find/style); no database animation, preset or example choreography was loaded, copied or retimed.',
        'beat_sheet': [{'frames': [a, b], 'seconds': [round(a / C.FPS, 2), round((b + 1) / C.FPS, 2)], 'beat': n, 'content': t} for a, b, n, t in BEATS],
        'cameras': shots,
        'impact_and_sfx_table': impacts,
        'contacts_solved': contacts_txt,
        'dummy_hurt_face_frames': hurt_frames,
        'player_blink_hidden_frames': blink_hidden,
        'checks': {
            'lint_strict': lint,
            'contact': 'every strike tip is IK-solved onto its target point on the impact frame (tip-to-target distances in contacts_solved include a deliberate ~0.1 stud drive-through slack); see list.',
            'floor': 'a per-frame floor constraint lifts a character whenever any part would go under y=0 (used for lying/rotating bodies); the baked clips include it.',
            'camera_collision_audit': 'automated audit (camera vs every body part, flagged < 2.2 studs): see run log in README; the only flagged frames before the last revision were the deliberate close push-in.',
            'not_verified': ['Blender import/playback', 'foot sliding in world space during dashes/slides (intentional), planted-foot QA was not declared with qa.py plans', 'continuous playback judged only through contact sheets and the final MP4'],
        },
        'intentional_stylisation': ['R6 rigid limbs (no elbows/knees) with exaggerated torque, wide ranges and stepped 18 fps exposure', 'hit-stops of 1-2 frames, smears via 3D streaks and 2D shards', 'floating/hanging dummy physics (low gravity) for readability', 'manga-style inverted impact frames on the biggest hits (f102, f208, f540)'],
        'unresolved_findings': [
            'The reference video could not be watched, so the style match is by description + stills only.',
            'Some R6 joint overlaps (arms through torso) can occur for 1-3 frames on extreme poses; they are brief and mostly hidden by hit effects.',
            'The lint warns about >120 deg single-segment rotations on flip keys; they are keyed every frame so the rendered motion is correct, but a Blender import using quaternion F-curves should keep the per-frame keys.',
        ],
        'deliverables': ['out/@Mr_HB_fight_18fps.mp4', 'out/@Mr_HB_fight_18fps_silent.mp4', 'out/@Mr_HB_fight_36fps_compat.mp4', 'out/clips/mrhb.baked.json', 'out/clips/dummy.baked.json', 'out/contact_sheet.jpg', 'animation/authoring/*.py (authoring source)', 'animation/render, animation/post, animation/audio'],
    }
    with open(os.path.join(ROOT, 'animation-manifest.json'), 'w') as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    print('manifest written;', len(contacts_txt), 'contacts;', len(impacts), 'sfx/impact entries;', 'hurt frames', hurt_frames, 'blink hidden', blink_hidden)
    for nm in lint:
        print(nm, lint[nm]['keys'], 'keys', lint[nm]['length_s'], 's', len(lint[nm]['strict_lint_first_30']), 'lint lines')
        for l in lint[nm]['strict_lint_first_30'][:12]:
            print('   ', l)


if __name__ == '__main__':
    main()
