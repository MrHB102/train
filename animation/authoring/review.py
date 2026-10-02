"""Blocking review: render chosen frames with the real 3D renderer (low res) and build a labelled contact sheet."""
import json
import math
import os
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
RENDER = os.path.abspath(os.path.join(HERE, '..', 'render'))
OUT = os.path.abspath(os.path.join(HERE, '..', 'out'))


def render_frames(shot_path, frames, outdir, scale=0.3, exposure=1.0):
    os.makedirs(outdir, exist_ok=True)
    for f in os.listdir(outdir):
        if f.endswith('.png'): os.remove(os.path.join(outdir, f))
    cmd = ['node', 'render.mjs', '--shot', shot_path, '--out', outdir, '--scale', str(scale), '--list', ','.join(str(int(f)) for f in frames), '--exposure', str(exposure)]
    p = subprocess.run(cmd, cwd=RENDER, capture_output=True, text=True)
    if p.returncode: raise RuntimeError(p.stderr[-2000:] + p.stdout[-1000:])
    return outdir


def contact_sheet(outdir, frames, out_png, cols=6, labels=None, fps=18):
    ims = []
    for f in frames:
        im = Image.open(os.path.join(outdir, 'f%04d.png' % f)).convert('RGB'); ims.append((f, im))
    w, h = ims[0][1].size
    rows = math.ceil(len(ims) / cols)
    sheet = Image.new('RGB', (cols * w, rows * h), (12, 14, 18))
    d = ImageDraw.Draw(sheet)
    try: font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', max(12, w // 16))
    except Exception: font = ImageFont.load_default()
    for i, (f, im) in enumerate(ims):
        x, y = (i % cols) * w, (i // cols) * h
        sheet.paste(im, (x, y))
        lab = 'f%d  %.2fs' % (f, f / fps) + ((' ' + labels[i]) if labels else '')
        d.rectangle((x, y, x + w, y + max(14, w // 14) + 4), fill=(0, 0, 0))
        d.text((x + 4, y + 2), lab, fill=(255, 255, 255), font=font)
    sheet.save(out_png)
    return out_png


def apply_post(outdir, frames, shot_path, scale):
    sys.path.insert(0, os.path.join(HERE, '..', 'post'))
    import numpy as np, cv2
    from post import Post
    fx2d = os.path.join(OUT, 'fx2d.json')
    W, H = int(round(1080 * scale)), int(round(1920 * scale))
    P = Post(shot_path, fx2d, W, H)
    for f in frames:
        pth = os.path.join(outdir, 'f%04d.png' % f)
        im = cv2.cvtColor(cv2.imread(pth), cv2.COLOR_BGR2RGB)
        out = P.process(f, im)
        cv2.imwrite(pth, cv2.cvtColor(out, cv2.COLOR_RGB2BGR))


def review(shot_path, frames, name, scale=0.3, cols=6, exposure=1.0, post=True):
    od = os.path.join(OUT, 'review', name + '_frames')
    render_frames(shot_path, frames, od, scale, exposure)
    if post: apply_post(od, frames, shot_path, scale)
    png = os.path.join(OUT, 'review', name + '.png')
    contact_sheet(od, frames, png, cols)
    return png
