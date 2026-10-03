"""v2 manifest: animation-manifest.json (keeps the v1 brief / reference sections, adds the v2 request and everything that was
measured for v2).  Called by run_all2.py --stage manifest with the results of the other stages."""
import json
import os

import choreo as C
import timeline as TL
import qa2
import spacing

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def collision_summary(B):
    runs = qa2.collisions(B, spacing.allowed_rules())
    frames = sum(r['n1'] - r['n0'] + 1 for r in runs)
    deep = [r for r in runs if r['max'] > 0.6]
    return {'runs': len(runs), 'frames': frames, 'percent_of_frames': round(100.0 * frames / B.n, 2),
            'runs_deeper_than_0.6_studs': [{'story_frames': [round(r['af0'], 2), round(r['af1'], 2)], 'output_frames': [r['n0'], r['n1']],
                                             'max_depth_studs': round(r['max'], 2), 'pairs_player_x_dummy': sorted(map(list, r['pairs']))[:6]} for r in deep]}


def write(S, results):
    path = os.path.join(ROOT, 'animation-manifest.json')
    old = json.load(open(path)) if os.path.exists(path) else {}
    w = S.warp
    m = {
        'title': '@Mr_HB vs training dummy - freestyle fight, v2 (120 fps / 60 fps, Blender curves, cinematic camera)',
        'version': 2,
        'brief_v2': {
            'user_request': 'Use Blender-style Bezier curves and easing, make the animation 120 fps and much smoother, fix the moments '
                            'where one rig goes inside the other, fix the preparation timing (e.g. drawing a sword: the pull is fast '
                            'but reaching for the hilt takes longer -> slow preparation, fast action), and put everything into a .blend. '
                            'Answers: Blender 5.2; keep whatever duration is needed for cohesion; deliver both 60 fps and 120 fps; the '
                            'avatar will be swapped in Roblox Studio (not Blender) -> Roblox-importable animations; 2D overlays may stay '
                            'as rendered images but the effects must have quality; make the camera more immersive / cinematic.',
            'assumptions': [
                'The v1 choreography (poses, contacts, beat order) is kept; v2 re-times it, re-interpolates it with Blender curves, '
                'repairs interpenetrations and re-shoots / re-lights / re-effects it.',
                'Roblox export: one KeyframeSequence per rig with the root motion folded into the RootJoint (both rigs anchored at the same '
                'origin); 60 keyframes per second baked from the same curves.',
                'The .blend is saved with Blender 5.0.1 (bpy module available here); Blender opens files from older versions, so it opens in 5.2. '
                'Blender 5.2 itself was not available to test.'],
        },
        'timing_v2': {
            'story_grid': '18 fps authoring frames (unchanged poses / contacts)',
            'output': '120 fps; %d output frames = %.2f s (v1: 630 frames = 35.0 s)' % (w.n_total, w.seconds()),
            'warp': 'piecewise-linear story-frame -> output-frame map; every story frame lands on an integer output frame',
            'rules': {
                'wind_up': 'interval before each strike chamber key x%.2f (capped +%.0f story frames): the preparation is slow and readable' % (TL.WIND, TL.WIND_CAP),
                'strike': 'chamber -> contact x%.2f and eased in (QUART/CUBIC EASE_IN): fastest at the contact' % TL.STRIKE,
                'hit_stop': {('strength_%d' % k): 'x%.1f on [hit, hit+1]' % v for k, v in TL.HITSTOP.items()},
                'no_wind_up_or_stop': 'barrage and blink strikes keep their rhythm',
            },
            'slow_motion': [{'story_frames': [a, b], 'factor': k, 'what': t} for a, b, k, ri, ro, t in TL.SLOWMO],
            'preparations': [{'story_frames': [a, b], 'factor': k, 'what': t} for a, b, k, t in TL.PREP],
            'tightened': [{'story_frames': [a, b], 'factor': k, 'what': t} for a, b, k, t in TL.TIGHTEN],
            'per_strike_report': S.rep,
        },
        'curves_v2': {
            'source': 'Blender 5 layered Actions (one slot, one keyframe strip) built with bpy 5.0.1; channels = canonical R6 pose-bone Euler '
                      '(limbs ZYX, centre bones ZXY) + location; evaluated with FCurve.evaluate for the render, QA, camera and Roblox bake',
            'interpolation': {
                'default': 'BEZIER, AUTO_CLAMPED handles (Blender default ease)',
                'attacker into contact': 'QUART / CUBIC EASE_IN on the striking limb, torso and root; flat incoming handle at the chamber (moving hold)',
                'target before contact': 'CONSTANT on pose channels (root keeps moving unless standing still): no reaction before the touch',
                'target after contact': 'BACK EASE_OUT on head / limbs (whip and settle)',
                'teleports (blink)': 'CONSTANT across the hidden frames, flat handles on both sides',
                'floor constraint': 'object-level location Z F-curve (FloorLift) in the same action, linear per frame where active',
            },
            'mapping_check': 'semantic pose <-> Blender channels verified against r6.fk: max error 1.1e-6 studs',
        },
        'interpenetration_v2': {
            'method': ['pose solver (Powell on exact box SAT depths) on overlapping key frames: dummy root / torso / head / limb rotations, '
                       'player non-striking limbs, head, torso line and small step; strike tips kept on their targets',
                       'smooth dummy push (analytic SAT push along the player->dummy line or upward when airborne, 0.2 s ramps) outside impact windows',
                       'keys inserted at overlapping in-betweens of impact windows; quarter-frame keys in the hammer spin so the orbit follows the circle',
                       'authoring fix: player one stud further back for the slide sweep'],
            'before': results.get('collisions_before', 'v1 timing evaluated at 120 fps: about 2,400 output frames, depths up to 1.6 studs (torso in torso, head in head)'),
            'after': results.get('collisions_after'),
            'allowed_on_purpose': 'striking limb sinking up to ~0.6 stud into the struck part for ~0.2 story frames around the contact; grabs (hammer throw, face grab)',
            'solver_log_tail': (S.solve_log or [])[-12:],
        },
        'camera_v2': ['framing a little tighter and lower than v1; every shot creeps (orbit drift + push-in), faster in slow motion (bullet-time orbit)',
                      'exact framing smoothed non-causally (~0.07 s) then critically-damped springs on aim point, orbit direction and distance (real time)',
                      'frame guard keeps the subject inside ~85 % of the frame (rate-limited, never snaps)',
                      'handheld multi-sine drift; impact shakes as damped 9-17 Hz sinusoids; FOV punch that springs back',
                      'depth of field: focus at the harmonic middle of the subject depth range, aperture from the lens capped so both fighters stay sharp',
                      'camera kept >= 0.9 stud above the floor and out of the bodies'],
        'effects_v2': ['two clocks: story-clock effects follow slow motion / hit-stops, real-clock effects (flashes, stars, sparks, impact glow and rings) always play at speed',
                       'continuous limb trails (ribbons rebuilt every frame from the real limb path), denser after-images with fresnel rim and colour gradient',
                       'impact: glow core with a flash point light, spark bursts, shards / stars that animate continuously and boil at 24 Hz',
                       'energy aura: flowing flame-noise shell + rising embers; billowing lit dust puffs',
                       'post: depth of field from a depth pass, bloom (pyramid), anamorphic streak on small hot spots only, shock-wave refraction ripple on heavy hits, chromatic aberration pulses, grade, grain'],
        'deliverables_v2': results.get('deliverables', []),
        'checks_v2': results.get('checks', {}),
        'unresolved_v2': results.get('unresolved', []),
        'v1': {k: old[k] for k in ('brief', 'tools', 'reference', 'originality', 'beat_sheet') if k in old},
    }
    with open(path, 'w') as fh:
        json.dump(m, fh, indent=2, ensure_ascii=False)
    return path
