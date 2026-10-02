"""Procedural sound for the fight (numpy only): a 120 BPM beat that lines up with the 9-frame grid (1 beat = 0.5 s), plus SFX for every
impact / whoosh / blink / boom recorded by the effects authoring (fx2d.json 'sfx').  Output: 44.1 kHz stereo WAV.

Structure (frames @18 fps): intro pulse -> full beat from the first hit (f36) -> riser during the energy charge (f440-488) ->
barrage hats/snare roll (f498-526) -> hard drop = near silence for the freeze (f527-532) -> boom at the slam (f541) -> pad and sting."""
import json
import math
import os
import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter

SR = 44100
FPS = 18
rng = np.random.RandomState(7)


def fr(f):
    return int(round(f / FPS * SR))


def env(n, a=0.002, d=0.1):
    t = np.arange(n) / SR
    e = np.minimum(1.0, t / max(a, 1e-4)) * np.exp(-t / max(d, 1e-4))
    return e


def lp(x, fc, order=2):
    b, a = butter(order, fc / (SR / 2), 'low'); return lfilter(b, a, x)


def hp(x, fc, order=2):
    b, a = butter(order, fc / (SR / 2), 'high'); return lfilter(b, a, x)


def bp(x, lo, hi, order=2):
    b, a = butter(order, [lo / (SR / 2), hi / (SR / 2)], 'band'); return lfilter(b, a, x)


def add(buf, start, sig, gain=1.0, pan=0.0):
    i = max(0, start)
    if i >= len(buf): return
    sig = sig[: len(buf) - i]
    l = gain * (1 - max(0, pan)); r = gain * (1 + min(0, pan))
    buf[i:i + len(sig), 0] += sig * l
    buf[i:i + len(sig), 1] += sig * r


def kick(g=1.0):
    n = int(0.42 * SR); t = np.arange(n) / SR
    f = 46 + 130 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) * env(n, 0.001, 0.13) + 0.25 * np.sin(2 * ph) * env(n, 0.001, 0.05)) * g


def snare(g=1.0):
    n = int(0.3 * SR); t = np.arange(n) / SR
    noise = bp(rng.randn(n), 1200, 7500) * env(n, 0.001, 0.07)
    tone = np.sin(2 * np.pi * 190 * t) * env(n, 0.001, 0.05)
    return (0.9 * noise + 0.5 * tone) * g


def hat(g=1.0, open_=False):
    n = int((0.16 if open_ else 0.05) * SR)
    return hp(rng.randn(n), 7000) * env(n, 0.0005, 0.06 if open_ else 0.015) * g


def bass(freq, dur, g=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * 2 * freq * t) + 0.18 * np.sign(np.sin(2 * np.pi * freq * t))
    return lp(s, 380) * np.minimum(1, t / 0.01) * np.minimum(1, (dur - t) / 0.03) * g


def pluck(freq, g=1.0, dur=0.28):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sign(np.sin(2 * np.pi * freq * t)) * 0.5 + np.sin(2 * np.pi * freq * 2.01 * t) * 0.3
    return lp(s, 2600) * env(n, 0.002, 0.11) * g


def pad(freqs, dur, g=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * t + i) for i, f in enumerate(freqs)) / len(freqs)
    s += 0.4 * sum(np.sin(2 * np.pi * f * 1.004 * t) for f in freqs) / len(freqs)
    return lp(s, 1800) * np.minimum(1, t / 0.8) * np.minimum(1, (dur - t) / 1.5) * g


# ------------------------------------------------------------------ sfx
def sfx_hit(s):
    n = int(0.4 * SR); t = np.arange(n) / SR
    thump = np.sin(2 * np.pi * (70 + 60 * np.exp(-t / 0.03)) * t) * env(n, 0.001, 0.09)
    crack = bp(rng.randn(n), 800, 6500) * env(n, 0.0008, 0.035 + 0.01 * s)
    return (thump * (0.5 + 0.2 * s) + crack * (0.5 + 0.12 * s)) * (0.5 + 0.18 * s)


def sfx_whoosh(s):
    dur = 0.28 + 0.06 * s; n = int(dur * SR); t = np.arange(n) / SR
    x = rng.randn(n)
    # sweep a band-pass up then down by crossfading a few static filters
    out = np.zeros(n)
    centres = np.linspace(500, 3800, 7)
    for i, c in enumerate(centres):
        w = np.exp(-((t / dur - (i + 0.5) / 7) ** 2) / 0.02)
        out += bp(x, c * 0.7, c * 1.3) * w
    return out * np.sin(np.pi * np.minimum(1, t / dur)) * 0.55


def sfx_crash(s):
    n = int(1.1 * SR); t = np.arange(n) / SR
    boom = np.sin(2 * np.pi * (48 + 40 * np.exp(-t / 0.12)) * t) * env(n, 0.001, 0.35)
    debris = lp(rng.randn(n), 3500) * env(n, 0.001, 0.22)
    return (0.8 * boom + 0.45 * debris) * (0.5 + 0.2 * s)


def sfx_boom(s):
    n = int(2.6 * SR); t = np.arange(n) / SR
    boom = np.sin(2 * np.pi * (36 + 90 * np.exp(-t / 0.18)) * t) * env(n, 0.001, 0.9)
    rumble = lp(rng.randn(n), 260) * env(n, 0.005, 0.8)
    air = hp(rng.randn(n), 3000) * env(n, 0.001, 0.15) * 0.5
    return (1.0 * boom + 0.9 * rumble + air) * (0.45 + 0.17 * s)


def sfx_blink():
    n = int(0.16 * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * (2400 - 6000 * t) * t) * env(n, 0.001, 0.05) + 0.4 * hp(rng.randn(n), 5000) * env(n, 0.001, 0.03)) * 0.5


def sfx_charge(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 80 * (1 + 7 * (t / dur) ** 2)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.5 * np.sign(np.sin(2 * np.pi * np.cumsum(f * 1.5) / SR))
    sh = hp(rng.randn(n), 4000) * (t / dur) ** 2 * 0.5
    w = (t / dur) ** 2
    tone = lp(s, 1500) * (1 - w) + lp(s, 7000) * w          # the filter opens as the charge builds
    return (tone * 0.5 + sh) * np.minimum(1, t / 0.5) * (0.3 + 0.7 * (t / dur))


def build(fx2d_path, out_wav, total_frames=630):
    d = json.load(open(fx2d_path))
    sfx = d['sfx']
    N = fr(total_frames) + SR
    buf = np.zeros((N, 2))
    beat = 9
    # ---------------- music bed
    A = 55.0
    bass_notes = [A, A, A * 1.1892, A * 0.8909]       # A, A, C, G  (per bar of 4 beats)
    arp = [A * 4, A * 4 * 1.1892, A * 4 * 1.3348, A * 4 * 1.4983, A * 4 * 1.7818, A * 4 * 1.4983, A * 4 * 1.3348, A * 4 * 1.1892]
    for b in range(0, total_frames // beat + 1):
        f = b * beat
        bar = b // 4
        pos = b % 4
        in_main = 36 <= f < 526 or 541 <= f < 612
        calm = 441 <= f < 489
        if f < 36:
            if pos in (0, 2): add(buf, fr(f), kick(0.45))
            continue
        if f >= 527 and f < 541:
            continue                                      # the drop (freeze/grab/dive)
        if f >= 541:
            if f < 560:
                add(buf, fr(f), bass(A, 0.45, 0.5))
            continue
        full = in_main and not calm
        if pos in (0, 2) or calm:
            add(buf, fr(f), kick(0.9 if not calm else 0.7))
        if pos in (1, 3) and full:
            add(buf, fr(f), snare(0.8))
        if full or calm:
            add(buf, fr(f), bass(bass_notes[bar % 4], beat / FPS * 0.9, 0.55))
            add(buf, fr(f + 4.5), hat(0.45))
            add(buf, fr(f), hat(0.3))
        if full and f > 70:
            for k in range(2):
                add(buf, fr(f + k * 4.5), pluck(arp[(b * 2 + k) % len(arp)], 0.16), pan=0.3 * (1 if k else -1))
    # barrage: 16th hats and an accelerating snare roll
    for k in range(28):
        add(buf, fr(498 + k), hat(0.5))
    for k in range(7):
        add(buf, fr(512 + k * 2 + (k * k) * 0.1), snare(0.7))
    # closing pad
    add(buf, fr(556), pad([A, A * 1.5, A * 1.1892 * 2], (630 - 556) / FPS + 1.0, 0.26))
    # ---------------- sfx
    for f, kind, s in sfx:
        t0 = fr(f)
        if kind == 'hit': add(buf, t0, sfx_hit(s), 0.9)
        elif kind in ('whoosh',): add(buf, t0, sfx_whoosh(s), 0.8)
        elif kind == 'crash': add(buf, t0, sfx_crash(s), 0.9)
        elif kind == 'boom': add(buf, t0, sfx_boom(s), 1.0)
        elif kind == 'blink': add(buf, t0, sfx_blink(), 0.7)
        elif kind == 'charge': add(buf, t0, sfx_charge(2.6 if f < 500 else 0.35), 0.8)
    add(buf, fr(612), sfx_boom(2), 0.6)                    # title sting
    # master: gentle glue + normalise
    peak = np.max(np.abs(buf)) + 1e-9
    buf = np.tanh(buf / peak * 1.6) / np.tanh(1.6)
    buf *= 0.89
    buf = buf[: fr(total_frames)]
    # tiny fade out
    nfade = int(0.25 * SR); buf[-nfade:] *= np.linspace(1, 0, nfade)[:, None]
    wavfile.write(out_wav, SR, (buf * 32767).astype(np.int16))
    return out_wav


if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.abspath(os.path.join(here, '..', 'out'))
    print(build(os.path.join(out, 'fx2d.json'), os.path.join(out, 'audio.wav')))
