"""v2 sound for the 120 fps timeline (numpy only).  Same instruments and SFX as synth.py, re-timed in output seconds:

  * tempo ~120 BPM, nudged so that both the first hit and the final slam land exactly on a beat
  * sections follow the story (intro pulse, full beat from the first hit, calm + riser during the charge, barrage roll,
    the drop before the slam, closing pad and sting) at their warped times
  * slow motion: the music bed is low-passed and ducked while the story runs slower than ~60 %, SFX stay full
  * every impact / whoosh / blink / boom of the effect table plays at its output time
"""
import importlib.util
import json
import math
import os

import numpy as np
from scipy.io import wavfile

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location('synth1', os.path.join(HERE, 'synth.py'))
S1 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(S1)
SR = S1.SR


def build(fx2d_path, out_wav):
    d = json.load(open(fx2d_path))
    nodes = d['warp_nodes']; fps = d['fps']; base = fps / d['story_fps']

    def t_of(af):            # story frame -> output seconds
        if af <= 0: return af * base / fps
        if af >= len(nodes) - 1: return (nodes[-1] + (af - len(nodes) + 1) * base) / fps
        i = int(math.floor(af)); return (nodes[i] + (nodes[i + 1] - nodes[i]) * (af - i)) / fps

    T = d['frames'] / fps
    N = int(T * SR) + SR
    bed = np.zeros((N, 2)); fxb = np.zeros((N, 2))
    sm = lambda t: int(round(t * SR))
    t_first, t_slam = t_of(36), t_of(540)
    k = max(1, round((t_slam - t_first) / 0.5))
    beat = (t_slam - t_first) / k                       # seconds per beat (~0.5)
    A = 55.0
    bass_notes = [A, A, A * 1.1892, A * 0.8909]
    arp = [A * 4, A * 4 * 1.1892, A * 4 * 1.3348, A * 4 * 1.4983, A * 4 * 1.7818, A * 4 * 1.4983, A * 4 * 1.3348, A * 4 * 1.1892]
    t_calm0, t_calm1 = t_of(441), t_of(489)
    t_bar0, t_bar1 = t_of(498), t_of(526)
    t_drop0 = t_of(527)
    t_end_beat = t_of(612)
    b0 = -int(math.ceil(t_first / beat))
    b = b0
    while True:
        t = t_first + b * beat
        if t > T: break
        if t < 0: b += 1; continue
        pos = (b - b0) % 4; bar = (b - b0) // 4
        if t < t_first - 1e-6:
            if pos in (0, 2): S1.add(bed, sm(t), S1.kick(0.45))
        elif t_drop0 <= t < t_slam - 1e-6:
            pass                                          # the drop: freeze, grab, dive
        elif t >= t_slam - 1e-6:
            if t < t_slam + 2.2: S1.add(bed, sm(t), S1.bass(A, 0.45, 0.5))
        else:
            calm = t_calm0 <= t < t_calm1
            full = not calm and not (t_bar0 <= t < t_bar1 and False)
            if pos in (0, 2) or calm: S1.add(bed, sm(t), S1.kick(0.9 if not calm else 0.7))
            if pos in (1, 3) and full: S1.add(bed, sm(t), S1.snare(0.8))
            S1.add(bed, sm(t), S1.bass(bass_notes[bar % 4], beat * 0.9, 0.55))
            S1.add(bed, sm(t + beat / 2), S1.hat(0.45)); S1.add(bed, sm(t), S1.hat(0.3))
            if full and t > t_of(70):
                for j in range(2):
                    S1.add(bed, sm(t + j * beat / 2), S1.pluck(arp[(b * 2 + j) % len(arp)], 0.16), pan=0.3 * (1 if j else -1))
        b += 1
    # barrage: 16th hats and an accelerating snare roll (follows the punches in story time)
    for j in range(28):
        S1.add(bed, sm(t_of(498 + j)), S1.hat(0.5))
    for j in range(7):
        S1.add(bed, sm(t_of(512 + j * 2 + (j * j) * 0.1)), S1.snare(0.7))
    t_pad = t_of(556)
    S1.add(bed, sm(t_pad), S1.pad([A, A * 1.5, A * 1.1892 * 2], T - t_pad + 1.0, 0.26))
    # ---- slow motion: duck + low-pass the bed where the story runs slower than ~60 %
    speed = np.ones(N)
    for i in range(len(nodes) - 1):
        a, c = sm(nodes[i] / fps), sm(nodes[i + 1] / fps)
        if c > a: speed[a:min(c, N)] = base / (nodes[i + 1] - nodes[i])
    w = np.clip((0.62 - speed) / 0.25, 0, 1)
    ker = np.ones(int(0.08 * SR)) / int(0.08 * SR)
    w = np.convolve(w, ker, mode='same')
    low = np.stack([S1.lp(bed[:, 0], 700), S1.lp(bed[:, 1], 700)], axis=1)
    bed = bed * (1 - w[:, None]) + low * 0.7 * w[:, None]
    # ---- sfx
    for t, kind, s in d['sfx']:
        t0 = sm(t)
        if kind == 'hit': S1.add(fxb, t0, S1.sfx_hit(s), 0.9)
        elif kind == 'whoosh': S1.add(fxb, t0, S1.sfx_whoosh(s), 0.8)
        elif kind == 'crash': S1.add(fxb, t0, S1.sfx_crash(s), 0.9)
        elif kind == 'boom': S1.add(fxb, t0, S1.sfx_boom(s), 1.0)
        elif kind == 'blink': S1.add(fxb, t0, S1.sfx_blink(), 0.7)
        elif kind == 'charge': S1.add(fxb, t0, S1.sfx_charge(2.9 if t < t_of(500) else 0.45), 0.8)
    S1.add(fxb, sm(t_end_beat), S1.sfx_boom(2), 0.6)
    buf = bed + fxb
    peak = np.max(np.abs(buf)) + 1e-9
    buf = np.tanh(buf / peak * 1.6) / np.tanh(1.6) * 0.89
    buf = buf[: int(T * SR)]
    nf = int(0.25 * SR); buf[-nf:] *= np.linspace(1, 0, nf)[:, None]
    wavfile.write(out_wav, SR, (buf * 32767).astype(np.int16))
    return out_wav, round(60.0 / beat, 2)


if __name__ == '__main__':
    out = os.path.abspath(os.path.join(HERE, '..', 'out', 'v2'))
    print(build(os.path.join(out, 'fx2d.json'), os.path.join(out, 'audio.wav')))
