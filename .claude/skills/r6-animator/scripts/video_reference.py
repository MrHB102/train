#!/usr/bin/env python3
"""Prepare actual media for visual inspection; never infer animation from metadata.
Requires ffmpeg/ffprobe/Pillow; yt-dlp is optional for public URLs.
"""
import argparse
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import urlsplit


def run(args, timeout=90):
    try:
        p = subprocess.run([str(a) for a in args], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f'{Path(str(args[0])).name} timed out; retry a shorter/local clip') from None
    if p.returncode:
        # Do not echo signed media URLs, authentication material or remote metadata.
        raise RuntimeError(f'{Path(str(args[0])).name} failed (exit {p.returncode}); media may be inaccessible or unsupported')
    return p.stdout


def acquire(source, out):
    u = urlsplit(source)
    if u.scheme in ('http', 'https'):
        if not u.hostname or u.username or u.password:
            raise ValueError('Use a public HTTP(S) URL without credentials')
        exe = shutil.which('yt-dlp')
        if not exe:
            raise RuntimeError('URL preparation requires yt-dlp; use an uploaded/local video if unavailable')
        dest = out / 'download'
        dest.mkdir()
        run([exe, '--ignore-config', '--no-playlist', '--no-progress', '--no-warnings',
             '--max-filesize', '250M', '--socket-timeout', '20', '--retries', '1',
             '-f', 'bv*[height<=720]+ba/b[height<=720]/b', '--merge-output-format', 'mp4',
             '-o', str(dest / 'source.%(ext)s'), '--', source], timeout=180)
        media = [p for p in dest.glob('source.*') if p.suffix.lower() in ('.mp4', '.mkv', '.webm', '.mov', '.m4v')]
        if len(media) != 1:
            raise RuntimeError('Expected one downloaded video; use a supported local clip')
        return media[0]
    p = Path(source).expanduser().resolve()
    if not p.is_file():
        raise ValueError('Local video does not exist (or URL scheme is unsupported)')
    return p


def probe(path):
    d = json.loads(run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', path]))
    streams = [s for s in d.get('streams', []) if s.get('codec_type') == 'video']
    if not streams:
        raise ValueError('No video stream')
    s = streams[0]
    duration = float(d.get('format', {}).get('duration') or s.get('duration') or 0)
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('Cannot determine a finite positive media duration')
    return {'duration_s': duration, 'width': s.get('width'), 'height': s.get('height'),
            'avg_frame_rate': s.get('avg_frame_rate'), 'time_base': s.get('time_base'),
            'note': 'Container timing; does not establish original animation exposure or speed.'}


def prepare(source, output, start=0.0, duration=10.0, frames=12, times=None):
    if not (math.isfinite(start) and start >= 0 and math.isfinite(duration) and 0 < duration <= 120):
        raise ValueError('start must be >=0; duration must be >0 and <=120 seconds')
    if not 2 <= frames <= 64:
        raise ValueError('frames must be between 2 and 64')
    for exe in ('ffmpeg', 'ffprobe'):
        if not shutil.which(exe):
            raise RuntimeError(f'{exe} is required')
    from PIL import Image, ImageDraw, ImageOps
    out = Path(output).expanduser().resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('Output directory must be empty; choose a new directory to preserve earlier evidence')
    out.mkdir(parents=True, exist_ok=True)
    media = acquire(source, out)
    meta = probe(media)
    if start >= meta['duration_s']:
        raise ValueError('start is outside the video')
    length = min(duration, meta['duration_s'] - start)
    # Keep last sample safely within duration even on low-fps media.
    rate = meta['avg_frame_rate'] or '0/1'
    num, den = (float(x) for x in rate.split('/'))
    frame_dt = den / num if num > 0 and den > 0 else 0.1
    last = max(start, start + length - min(frame_dt, length / 2))
    ts = list(times) if times is not None else [start + (last - start) * i / (frames - 1) for i in range(frames)]
    if not ts or len(ts) > 64 or any(not math.isfinite(t) or t < start or t >= start + length for t in ts):
        raise ValueError('times must contain 1–64 absolute source seconds within the selected interval')
    ts = sorted(set(ts))
    files = []
    for i, t in enumerate(ts):
        path = out / f'frame-{i:03d}.jpg'
        run(['ffmpeg', '-nostdin', '-v', 'error', '-ss', f'{t:.6f}', '-i', media,
             '-map', '0:v:0', '-frames:v', '1', '-vf', 'scale=640:-2', '-y', path])
        if not path.is_file():
            raise RuntimeError(f'No decoded frame at requested time {t:.4f}s')
        with Image.open(path) as im:
            im = im.convert('RGB')
            draw = ImageDraw.Draw(im)
            draw.rectangle((0, 0, 300, 25), fill='black')
            draw.text((8, 6), f'source ~{t:.4f}s | clip {t-start:.4f}s', fill='white')
            im.save(path, quality=92)
        files.append({'path': str(path), 'requested_source_s': round(t, 6), 'clip_s': round(t-start, 6),
                      'timestamp_kind': 'requested decoder seek; approximate nearest decoded image'})
    cols = min(4, len(files)); tile_w, tile_h = 320, 220
    sheet = Image.new('RGB', (cols * tile_w, math.ceil(len(files) / cols) * tile_h), '#15171c')
    for i, f in enumerate(files):
        with Image.open(f['path']) as im:
            thumb = ImageOps.contain(im.convert('RGB'), (tile_w, tile_h - 25))
            x, y = (i % cols) * tile_w, (i // cols) * tile_h
            sheet.paste(thumb, (x + (tile_w-thumb.width)//2, y))
            ImageDraw.Draw(sheet).text((x+8, y+tile_h-20), f"~{f['requested_source_s']:.4f}s", fill='white')
    sheet_path = out / 'contact-sheet.jpg'; sheet.save(sheet_path, quality=92)
    proxy = out / 'proxy.mp4'
    run(['ffmpeg', '-nostdin', '-v', 'error', '-ss', str(start), '-i', media, '-t', str(length),
         '-map', '0:v:0', '-an', '-vf', 'scale=640:-2', '-c:v', 'libx264', '-preset', 'veryfast',
         '-crf', '23', '-movflags', '+faststart', '-y', proxy])
    result = {'schema': 1, 'source': source, 'media': str(media), 'metadata': meta,
              'interval_source_s': [start, start+length], 'frames': files,
              'contact_sheet': str(sheet_path), 'proxy': str(proxy),
              'status': 'prepared-not-analyzed', 'visual_inspection_performed': False,
              'observations': [], 'instructions': 'Open images and inspect motion over time; write timestamped observations separately. No poses are extracted.'}
    manifest = out / 'reference-manifest.json'
    manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    result['manifest'] = str(manifest)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source'); ap.add_argument('--out', required=True)
    ap.add_argument('--start', type=float, default=0); ap.add_argument('--duration', type=float, default=10)
    ap.add_argument('--frames', type=int, default=12); ap.add_argument('--times', help='comma-separated absolute source seconds')
    a = ap.parse_args()
    try:
        r = prepare(a.source, a.out, a.start, a.duration, a.frames,
                    [float(t) for t in a.times.split(',')] if a.times else None)
        print(json.dumps(r, ensure_ascii=False, indent=2))
    except (ValueError, RuntimeError, subprocess.TimeoutExpired, ImportError, OSError) as e:
        print(f'{type(e).__name__}: {e}', file=sys.stderr); return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
