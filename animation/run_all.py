#!/usr/bin/env python3
"""Full production run (no Blender needed):

    python run_all.py                    # everything
    python run_all.py --stage make       # choreography -> shot.json + fx2d.json  (+ QA report)
    python run_all.py --stage render --from 0 --to 630 --workers 4
    python run_all.py --stage post
    python run_all.py --stage audio
    python run_all.py --stage encode

Outputs (animation/out): frames/ (raw 3D), frames_post/ (final stills), @Mr_HB_fight_18fps.mp4 (native 18 fps, with audio),
@Mr_HB_fight_18fps_silent.mp4, @Mr_HB_fight_36fps_compat.mp4 (each frame shown twice, for players/platforms that dislike 18 fps).
"""
import argparse
import concurrent.futures as cf
import glob
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
RENDER = os.path.join(HERE, 'render')
sys.path.insert(0, os.path.join(HERE, 'authoring'))
sys.path.insert(0, os.path.join(HERE, 'post'))
N = 630
FPS = 18
W, H = 1080, 1920


def stage_make():
    import make
    shot, n = make.build()
    print('shot', shot, n)


def _render_range(a, b, scale):
    cmd = ['node', 'render.mjs', '--shot', os.path.join(OUT, 'shot.json'), '--out', os.path.join(OUT, 'frames'), '--from', str(a), '--to', str(b), '--scale', str(scale)]
    p = subprocess.run(cmd, cwd=RENDER, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr[-1500:])
    return (a, b, p.stdout.strip().splitlines()[-1] if p.stdout.strip() else '')


def stage_render(f0, f1, workers, scale):
    os.makedirs(os.path.join(OUT, 'frames'), exist_ok=True)
    # interleave small chunks over the workers so the heavy beats are spread evenly
    chunk = 21
    jobs = [(a, min(a + chunk, f1)) for a in range(f0, f1, chunk)]
    t0 = time.time()
    with cf.ThreadPoolExecutor(workers) as ex:
        futs = [ex.submit(_render_range, a, b, scale) for a, b in jobs]
        for i, fu in enumerate(cf.as_completed(futs)):
            a, b, msg = fu.result()
            print('chunk %d-%d done (%d/%d) %.0fs  %s' % (a, b, i + 1, len(jobs), time.time() - t0, msg), flush=True)


def _post_one(args):
    f, scale = args
    import cv2
    from post import Post
    global _POST
    try:
        _POST
    except NameError:
        _POST = Post(os.path.join(OUT, 'shot.json'), os.path.join(OUT, 'fx2d.json'), int(round(W * scale)), int(round(H * scale)))
    im = cv2.cvtColor(cv2.imread(os.path.join(OUT, 'frames', 'f%04d.png' % f)), cv2.COLOR_BGR2RGB)
    out = _POST.process(f, im)
    cv2.imwrite(os.path.join(OUT, 'frames_post', 'f%04d.png' % f), cv2.cvtColor(out, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_PNG_COMPRESSION, 3])
    return f


def stage_post(f0, f1, workers, scale):
    os.makedirs(os.path.join(OUT, 'frames_post'), exist_ok=True)
    t0 = time.time()
    with cf.ProcessPoolExecutor(workers) as ex:
        for i, f in enumerate(ex.map(_post_one, [(f, scale) for f in range(f0, f1)], chunksize=4)):
            if i % 60 == 0: print('post %d/%d %.0fs' % (i, f1 - f0, time.time() - t0), flush=True)


def stage_audio():
    import importlib.util
    spec = importlib.util.spec_from_file_location('synth', os.path.join(HERE, 'audio', 'synth.py'))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    print(m.build(os.path.join(OUT, 'fx2d.json'), os.path.join(OUT, 'audio.wav')))


def stage_encode():
    src = os.path.join(OUT, 'frames_post', 'f%04d.png')
    aud = os.path.join(OUT, 'audio.wav')
    main = os.path.join(OUT, '@Mr_HB_fight_18fps.mp4')
    silent = os.path.join(OUT, '@Mr_HB_fight_18fps_silent.mp4')
    compat = os.path.join(OUT, '@Mr_HB_fight_36fps_compat.mp4')
    vflags = ['-c:v', 'libx264', '-preset', 'slow', '-crf', '15', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-profile:v', 'high']
    subprocess.check_call(['ffmpeg', '-y', '-v', 'error', '-framerate', str(FPS), '-i', src, '-i', aud, '-map', '0:v', '-map', '1:a', *vflags,
                           '-c:a', 'aac', '-b:a', '192k', '-shortest', main])
    subprocess.check_call(['ffmpeg', '-y', '-v', 'error', '-framerate', str(FPS), '-i', src, *vflags, silent])
    subprocess.check_call(['ffmpeg', '-y', '-v', 'error', '-framerate', str(FPS), '-i', src, '-i', aud, '-map', '0:v', '-map', '1:a', '-vf', 'fps=36', *vflags,
                           '-c:a', 'aac', '-b:a', '192k', '-shortest', compat])
    for f in (main, silent, compat):
        p = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,width,height,r_frame_rate,nb_frames,duration', '-of', 'json', f]))
        print(os.path.basename(f), os.path.getsize(f) // 1024, 'KB', [(s.get('codec_type'), s.get('width'), s.get('height'), s.get('r_frame_rate'), s.get('nb_frames'), s.get('duration')) for s in p['streams']])


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', default='all')
    ap.add_argument('--from', dest='f0', type=int, default=0)
    ap.add_argument('--to', dest='f1', type=int, default=N)
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--scale', type=float, default=1.0)
    a = ap.parse_args()
    st = a.stage
    if st in ('all', 'make'): stage_make()
    if st in ('all', 'audio'): stage_audio()
    if st in ('all', 'render'): stage_render(a.f0, a.f1, a.workers, a.scale)
    if st in ('all', 'post'): stage_post(a.f0, a.f1, a.workers, a.scale)
    if st in ('all', 'encode'): stage_encode()
