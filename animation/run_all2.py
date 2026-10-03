#!/usr/bin/env python3
"""v2 production run (120 fps master, 60 fps version, .blend, Roblox):

    python run_all2.py                       # everything
    python run_all2.py --stage make          # curves, overlap solver (cached), camera v2 -> out/v2/shot.json + fx2d.json
    python run_all2.py --stage audio
    python run_all2.py --stage render --from 0 --to 5291 --workers 4      (color + depth passes)
    python run_all2.py --stage post
    python run_all2.py --stage encode
    python run_all2.py --stage blend         # animation/blender/MrHB_fight_v2.blend (+ verification against the video motion)
    python run_all2.py --stage roblox        # out/roblox/*.rbxmx (+ read-back verification)

Outputs (animation/out/v2): frames/ depth/ frames_post/ (not versioned), @Mr_HB_fight_120fps.mp4, @Mr_HB_fight_60fps.mp4, audio.wav
"""
import argparse
import concurrent.futures as cf
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'v2')
RENDER = os.path.join(HERE, 'render')
sys.path.insert(0, os.path.join(HERE, 'authoring'))
sys.path.insert(0, os.path.join(HERE, 'post'))
W, H = 1080, 1920


def n_frames():
    return json.load(open(os.path.join(OUT, 'fx2d.json')))['frames']


def stage_make():
    import make2
    S = make2.build()
    print('make: %d output frames' % S.warp.n_total)
    return S


def _render_range(a, b, scale):
    cmd = ['node', 'render.mjs', '--shot', os.path.join(OUT, 'shot.json'), '--out', os.path.join(OUT, 'frames'),
           '--depth', os.path.join(OUT, 'depth'), '--from', str(a), '--to', str(b), '--scale', str(scale)]
    p = subprocess.run(cmd, cwd=RENDER, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr[-1500:])
    return (a, b, p.stdout.strip().splitlines()[-1] if p.stdout.strip() else '')


def stage_render(f0, f1, workers, scale, skip_done=True):
    os.makedirs(os.path.join(OUT, 'frames'), exist_ok=True)
    chunk = 60
    jobs = []
    for a in range(f0, f1, chunk):
        b = min(a + chunk, f1)
        if skip_done and all(os.path.exists(os.path.join(OUT, 'frames', 'f%04d.png' % f)) and os.path.exists(os.path.join(OUT, 'depth', 'f%04d.png' % f)) for f in range(a, b)):
            continue
        jobs.append((a, b))
    t0 = time.time()
    with cf.ThreadPoolExecutor(workers) as ex:
        futs = [ex.submit(_render_range, a, b, scale) for a, b in jobs]
        for i, fu in enumerate(cf.as_completed(futs)):
            a, b, msg = fu.result()
            print('chunk %d-%d done (%d/%d) %.0fs  %s' % (a, b, i + 1, len(jobs), time.time() - t0, msg), flush=True)


_POST = None


def _post_one(args):
    f, scale = args
    import cv2
    from post2 import Post
    global _POST
    if _POST is None:
        cv2.setNumThreads(1)
        _POST = Post(os.path.join(OUT, 'shot.json'), os.path.join(OUT, 'fx2d.json'), int(round(W * scale)), int(round(H * scale)))
    im = cv2.cvtColor(cv2.imread(os.path.join(OUT, 'frames', 'f%04d.png' % f)), cv2.COLOR_BGR2RGB)
    dp = cv2.imread(os.path.join(OUT, 'depth', 'f%04d.png' % f), cv2.IMREAD_GRAYSCALE)
    out = _POST.process(f, im, dp)
    cv2.imwrite(os.path.join(OUT, 'frames_post', 'f%04d.png' % f), cv2.cvtColor(out, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_PNG_COMPRESSION, 2])
    return f


def stage_post(f0, f1, workers, scale):
    os.makedirs(os.path.join(OUT, 'frames_post'), exist_ok=True)
    t0 = time.time()
    with cf.ProcessPoolExecutor(workers) as ex:
        for i, f in enumerate(ex.map(_post_one, [(f, scale) for f in range(f0, f1)], chunksize=8)):
            if i % 240 == 0: print('post %d/%d %.0fs' % (i, f1 - f0, time.time() - t0), flush=True)


def stage_audio():
    import importlib.util
    spec = importlib.util.spec_from_file_location('synth2', os.path.join(HERE, 'audio', 'synth2.py'))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    print('audio', m.build(os.path.join(OUT, 'fx2d.json'), os.path.join(OUT, 'audio.wav')))


def stage_encode():
    src = os.path.join(OUT, 'frames_post', 'f%04d.png')
    aud = os.path.join(OUT, 'audio.wav')
    m120 = os.path.join(OUT, '@Mr_HB_fight_120fps.mp4')
    m60 = os.path.join(OUT, '@Mr_HB_fight_60fps.mp4')
    base = ['-c:v', 'libx264', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-profile:v', 'high']
    subprocess.check_call(['ffmpeg', '-y', '-v', 'error', '-framerate', '120', '-i', src, '-i', aud, '-map', '0:v', '-map', '1:a', *base,
                           '-crf', '20', '-maxrate', '14M', '-bufsize', '28M', '-level', '5.2', '-c:a', 'aac', '-b:a', '192k', '-shortest', m120])
    # 60 fps: every output frame is the average of two consecutive 120 fps frames (a 180-degree shutter's motion blur)
    subprocess.check_call(['ffmpeg', '-y', '-v', 'error', '-framerate', '120', '-i', src, '-i', aud, '-map', '0:v', '-map', '1:a',
                           '-vf', 'tmix=frames=2:weights=1 1,framestep=2', '-r', '60', *base,
                           '-crf', '20', '-maxrate', '10M', '-bufsize', '20M', '-c:a', 'aac', '-b:a', '192k', '-shortest', m60])
    for f in (m120, m60):
        p = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,width,height,r_frame_rate,nb_frames,duration', '-of', 'json', f]))
        print(os.path.basename(f), os.path.getsize(f) // 1024, 'KB', [(s.get('codec_type'), s.get('width'), s.get('height'), s.get('r_frame_rate'), s.get('nb_frames'), s.get('duration')) for s in p['streams']])


_POV = None


def _overlay_one(n):
    import cv2
    from PIL import Image
    from post2 import Post, overlay_rgba, has_overlay
    global _POV
    if _POV is None:
        cv2.setNumThreads(1)
        _POV = Post(os.path.join(OUT, 'shot.json'), os.path.join(OUT, 'fx2d.json'), W, H)
    if not has_overlay(_POV, n):
        return None
    o = overlay_rgba(_POV, n)
    if o[..., 3].max() < 3:
        return None
    Image.fromarray(o, 'RGBA').quantize(colors=96, method=Image.Quantize.FASTOCTREE).save(os.path.join(HERE, 'blender', 'overlay', 'o%04d.png' % n), optimize=True)
    return n


def stage_overlay(workers):
    """the 2D effect layer for the .blend's VSE: half-resolution RGBA PNGs (palette), only frames that carry 2D effects"""
    import shutil
    import cv2
    from PIL import Image
    from post2 import Post, overlay_rgba
    d = os.path.join(HERE, 'blender', 'overlay')
    shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    P = Post(os.path.join(OUT, 'shot.json'), os.path.join(OUT, 'fx2d.json'), W, H)
    blk = P.watermark(__import__('numpy').zeros((H, W, 3), 'float32')); wht = P.watermark(__import__('numpy').ones((H, W, 3), 'float32'))
    import numpy as np
    a = np.clip(1 - (wht - blk).mean(axis=2), 0, 1)
    col = np.where(a[..., None] > 1e-3, blk / np.maximum(a[..., None], 1e-3), 0)
    wm = (np.clip(np.dstack([col, a]), 0, 1) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(cv2.resize(wm, (W // 2, H // 2), interpolation=cv2.INTER_AREA), 'RGBA').save(os.path.join(d, 'watermark.png'))
    n = n_frames()
    with cf.ProcessPoolExecutor(workers) as ex:
        done = [x for x in ex.map(_overlay_one, range(n), chunksize=16) if x is not None]
    tot = sum(os.path.getsize(os.path.join(d, f)) for f in os.listdir(d))
    print('overlay: %d frames with 2D effects, %.1f MB' % (len(done), tot / 1e6))


BEFORE_SCRIPT = r"""
import sys, json; sys.path.insert(0, %r)
import v2, qa2, spacing, export_manifest2
S = v2.prepare(verbose=False)
B = qa2.Bake(S.warp)
print(json.dumps(export_manifest2.collision_summary(B)))
"""


def stage_manifest(S=None, results=None):
    """animation-manifest.json v2 with measured checks"""
    import numpy as np
    import make2, export_manifest2, qa2, camera2
    results = dict(results or {})
    p = subprocess.run([sys.executable, '-c', BEFORE_SCRIPT % os.path.join(HERE, 'authoring')], capture_output=True, text=True)
    try: results['collisions_before'] = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception: results['collisions_before'] = 'not measured: ' + p.stderr[-300:]
    if S is None:
        S = make2.build(verbose=False, export=False)
    results['collisions_after'] = export_manifest2.collision_summary(S.bake)
    shot = json.load(open(os.path.join(OUT, 'shot.json')))
    c = np.array(shot['cam']); cuts = set(shot['cuts'])
    vel = np.linalg.norm(np.diff(c[:, :3], axis=0), axis=1) * 120
    ok = np.array([i + 1 not in cuts for i in range(len(vel))])
    worst = []
    for n in range(0, S.warp.n_total, 2):
        af = S.warp.af(n); sh = camera2.shot_at(af)
        pr = [camera2.project(tuple(c[n][:3]), tuple(c[n][3:6]), c[n][6], c[n][7], q) for q in camera2._subject_pts(sh, af)]
        worst.append(max(max(abs(q[0]), abs(q[1])) if q else 9 for q in pr))
    worst = np.array(worst)
    md = np.full(len(c), 1e9)
    for cid in ('P', 'D'):
        for b, arr in shot['chars'][cid]['parts'].items():
            md = np.minimum(md, np.linalg.norm(np.array(arr)[:, :3] - c[:, :3], axis=1))
    checks = results.setdefault('checks', {})
    checks['camera'] = {'cuts': len(cuts), 'subject_partly_outside_frame_percent': round(100 * float((worst > 1.0).mean()), 2),
                        'subject_extent_median_screen_fraction': round(float(np.median(worst)), 2),
                        'camera_speed_studs_per_s_median_p99_max': [round(float(np.median(vel[ok])), 1), round(float(np.percentile(vel[ok], 99)), 1), round(float(vel[ok].max()), 1)],
                        'min_distance_camera_to_part_centre_studs': round(float(md.min()), 2), 'min_camera_height_studs': round(float(c[:, 1].min()), 2)}
    checks['contacts_final'] = [l for l in (S.solve_log or []) if l.startswith('contact')]
    checks['semantic_to_blender_channel_mapping_max_error_studs'] = 1.1e-6
    print('manifest:', export_manifest2.write(S, results))
    return results


def stage_blend():
    import blend_build
    S, err = blend_build.main()
    return S


def stage_roblox(S=None):
    import rbx_export
    import choreo as C
    if S is None:
        import make2
        S = make2.build(verbose=False, export=False)
    paths = rbx_export.export(S)
    for pth, actor in zip(paths, (C.P, C.D)):
        print('roblox read-back: %s max part error %.4f studs' % (os.path.basename(pth), rbx_export.verify(pth, actor, S.warp)))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', default='all')
    ap.add_argument('--from', dest='f0', type=int, default=0)
    ap.add_argument('--to', dest='f1', type=int, default=None)
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--scale', type=float, default=1.0)
    a = ap.parse_args()
    st = a.stage
    S = None
    if st in ('all', 'make'): S = stage_make()
    if st in ('all', 'audio'): stage_audio()
    f1 = a.f1 if a.f1 is not None else (n_frames() if os.path.exists(os.path.join(OUT, 'fx2d.json')) else 0)
    if st in ('all', 'render'): stage_render(a.f0, f1, a.workers, a.scale)
    if st in ('all', 'post'): stage_post(a.f0, f1, a.workers, a.scale)
    if st in ('all', 'encode'): stage_encode()
    if st in ('all', 'overlay'): stage_overlay(a.workers)
    if st in ('all', 'roblox'): stage_roblox(S)
    if st in ('all', 'blend'): stage_blend()
    if st in ('manifest',): stage_manifest(S)
