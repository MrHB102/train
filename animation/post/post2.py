"""v2 2D post for the 120 fps timeline.

Lens:   depth of field (from the renderer's depth pass and the camera's focus distance / aperture), bloom with a warm halo
        and a horizontal anamorphic streak on very bright spots, chromatic aberration (pulses on impacts), shock-wave
        refraction ripples on the heaviest hits, grade, vignette, grain.
Overlay: hand-drawn style impact stars, shards, speed lines, glints, manga impact frames, titles.  Shapes animate
        continuously in their own clock (story or real) and their outline 'boils' (redrawn with jitter) at 24 Hz like
        drawn-over effects, regardless of the 120 fps output.
"""
import json
import math
import os

import cv2
import numpy as np

AA = cv2.LINE_AA


def _interp(arr, x):
    x = max(0.0, x)
    i = int(math.floor(x)); t = x - i
    if i >= len(arr) - 1: return arr[-1]
    return arr[i] + (arr[i + 1] - arr[i]) * t


class Post:
    def __init__(self, shot_path, fx2d_path, W, H):
        shot = json.load(open(shot_path))
        fx = json.load(open(fx2d_path))
        self.cam = shot['cam']
        self.W, self.H = W, H
        self.fps = shot['fps']; self.sfps = shot['story_fps']; self.BASE = self.fps / self.sfps
        self.frames = shot['frames']
        self.tau = shot['tau']
        self.cuts = set(shot.get('cuts', []))
        self.ev = fx['events']
        self.chars = fx['chars']
        self.tags_vis = shot.get('tags', {}).get('P', {}).get('vis')
        self.head_P = shot['chars']['P']['parts']['Head']
        self.s = W / 1080.0
        self.yy, self.xx = np.mgrid[0:H, 0:W].astype(np.float32)
        # output-frame range of each event
        self.by_frame = {}
        nodes = fx['warp_nodes']

        def out_of(af):
            if af <= 0: return af * self.BASE
            if af >= len(nodes) - 1: return nodes[-1] + (af - (len(nodes) - 1)) * self.BASE
            i = int(math.floor(af)); return nodes[i] + (nodes[i + 1] - nodes[i]) * (af - i)
        self.out_of = out_of
        for k, e in enumerate(self.ev):
            f0 = e['f0']; f1 = e.get('f1', f0) + 1
            if e.get('clk') == 'real':
                n0 = e['n0']; n1 = n0 + (f1 - f0) * self.BASE
            else:
                n0 = out_of(f0); n1 = out_of(f1)
            for n in range(max(0, int(math.floor(n0))), min(self.frames, int(math.ceil(n1)) + 1)):
                self.by_frame.setdefault(n, []).append(e)

    def feff(self, e, n):
        return e['f0'] + (n - e['n0']) / self.BASE if e.get('clk') == 'real' else self.tau[n]

    def active(self, e, n):
        f = self.feff(e, n)
        return e['f0'] - 1e-6 <= f < e.get('f1', e['f0']) + 1, f

    # ------------------------------------------------------------------ projection (mirrors three.js lookAt + rotateZ roll)
    def project(self, n, p):
        c = self.cam[min(n, len(self.cam) - 1)]
        pos = np.array(c[0:3]); tgt = np.array(c[3:6]); fov = c[6]; roll = math.radians(c[7])
        fwd = tgt - pos; fwd /= np.linalg.norm(fwd)
        right = np.cross(fwd, [0, 1, 0]); right /= np.linalg.norm(right)
        up = np.cross(right, fwd)
        x = right * math.cos(roll) + up * math.sin(roll)
        y = -right * math.sin(roll) + up * math.cos(roll)
        d = np.array(p) - pos
        cx, cy, depth = d @ x, d @ y, d @ fwd
        if depth < 0.05: return None
        t = math.tan(math.radians(fov) / 2)
        asp = self.W / self.H
        px = (cx / (depth * t * asp) + 1) / 2 * self.W
        py = (1 - cy / (depth * t)) / 2 * self.H
        return px, py, depth, (self.H / 2) / (t * depth)

    def screen_motion(self, n, who, k=4):
        a = self.project(n, self.chars[who]['torso'][max(n - k, 0)]); b = self.project(n, self.chars[who]['torso'][n])
        if not a or not b: return np.array([1.0, 0.0]), 0.0
        v = np.array([b[0] - a[0], b[1] - a[1]]); m = np.linalg.norm(v)
        return ((v / m) if m > 1e-3 else np.array([1.0, 0.0])), m

    # ------------------------------------------------------------------ main
    def process(self, n, img, depth=None):
        W, H = self.W, self.H
        im = img.astype(np.float32) / 255.0
        evs = []
        for e in self.by_frame.get(n, []):
            ok, f = self.active(e, n)
            if ok: evs.append((e, f))
        if depth is not None:
            im = self.dof(im, n, depth)
        for e, f in evs:
            if e['t'] == 'mblur': im = self.motion_blur(im, n, f, e)
        for e, f in evs:
            if e['t'] == 'rblur': im = self.radial_blur(im, n, f, e)
        for e, f in evs:
            if e['t'] == 'star' and e['r'] >= 1.3: im = self.shock_ripple(im, n, f, e)
        im = self.bloom(im)
        ca = 1.0 * self.s + sum(e['amt'] * self.s * max(0.0, 1 - (f - e['f0']) / max(e['f1'] - e['f0'] + 1, 1)) ** 1.5 for e, f in evs if e['t'] == 'ca')
        im = self.chroma(im, ca)
        im = self.grade(im, self.grade_params(n))
        rng = np.random.RandomState(n * 7 + 3)
        im += rng.normal(0, 0.009, im.shape[:2])[..., None].astype(np.float32)
        im = np.clip(im, 0, 1)
        ov = np.zeros((H, W, 4), np.float32); used = False
        for e, f in evs:
            t = e['t']
            if t == 'star': self.star(ov, n, f, e); used = True
            elif t == 'shards': self.shards(ov, n, f, e); used = True
            elif t == 'lines': self.lines(ov, n, f, e); used = True
            elif t == 'sparkle': self.sparkle(ov, n, f, e); used = True
        if used:
            a = ov[..., 3:4]
            im = im * (1 - a) + ov[..., :3] * a
        for e, f in evs:
            if e['t'] == 'flash': im = self.flash(im, n, f, e)
        for e, f in evs:
            if e['t'] == 'text': im = self.text(im, n, f, e)
        im = self.watermark(im)
        return (np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)

    # ------------------------------------------------------------------ lens
    def dof(self, im, n, depth):
        """gather-free layered DOF: blur levels mixed by circle of confusion from the log depth (0.3..600 studs)"""
        c = self.cam[n]
        focus, ap = (c[8], c[9]) if len(c) > 9 else (10.0, 0.0)
        if ap <= 0.02: return im
        dz = depth.astype(np.float32) / 255.0
        z = 0.3 * np.exp(dz * math.log(2000.0))
        coc = ap * 15.0 * self.s * np.abs(1.0 - focus / np.maximum(z, 0.3))       # pixels (radius)
        coc = np.minimum(coc, 16.0 * self.s)
        # the floating name tag is a sprite (not in the depth pass): keep its rectangle in focus
        tv = self.tags_vis[n] if self.tags_vis else 0.0
        if tv > 0.01:
            h = self.head_P[n][:3]; cpos = np.array(c[0:3])
            k = max(0.5, float(np.linalg.norm(np.array(h) - cpos)) * 0.085) * tv
            pr = self.project(n, (h[0], h[1] + 1.55 + 0.25 * k, h[2]))
            if pr:
                hw, hh = 2.2 * k * pr[3], 0.65 * k * pr[3]
                m = np.exp(-np.maximum(np.abs(self.xx - pr[0]) / max(hw, 1) - 1, 0) * 6) * np.exp(-np.maximum(np.abs(self.yy - pr[1]) / max(hh, 1) - 1, 0) * 6)
                coc = coc * (1 - m)
        coc = cv2.GaussianBlur(coc, (0, 0), 2.0 * self.s)                         # soften the transitions at silhouettes
        levels = [0.0, 2.5, 5.0, 9.0, 16.0]
        H, W = im.shape[:2]
        half = cv2.resize(im, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
        stack = [im, cv2.GaussianBlur(im, (0, 0), (2.5 * self.s) / 1.6)] + \
                [cv2.resize(cv2.GaussianBlur(half, (0, 0), (r * self.s) / 3.2), (W, H), interpolation=cv2.INTER_LINEAR) for r in levels[2:]]
        out = np.zeros_like(im)
        cs = coc / self.s
        for i in range(len(levels)):
            lo = levels[i - 1] if i > 0 else None; c0 = levels[i]; hi = levels[i + 1] if i + 1 < len(levels) else None
            w = np.zeros_like(cs)
            if lo is not None:
                m = (cs >= lo) & (cs < c0); w[m] = (cs[m] - lo) / (c0 - lo)
            if hi is not None:
                m = (cs >= c0) & (cs < hi); w[m] = (hi - cs[m]) / (hi - c0)
            else:
                w[cs >= c0] = 1.0
            if lo is None: w[cs < c0] = 1.0
            out += stack[i] * w[..., None]
        return out

    def bloom(self, im):
        lum = im.max(axis=2, keepdims=True)
        br = np.clip(im - 0.8, 0, None) * np.clip(lum * 1.6, 0, 1.6)
        s = self.s
        H, W = im.shape[:2]
        h2 = cv2.resize(br, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
        h4 = cv2.resize(h2, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        up = lambda a: cv2.resize(a, (W, H), interpolation=cv2.INTER_LINEAR)
        acc = up(cv2.GaussianBlur(h2, (0, 0), 3 * s)) * 0.55 + up(cv2.GaussianBlur(h4, (0, 0), 5 * s)) * 0.45 + up(cv2.GaussianBlur(h4, (0, 0), 14.5 * s)) * 0.4
        # anamorphic streak only on small, very hot spots (impact cores, sun glints), never on large bright areas
        hot = np.clip(im.max(axis=2) - 0.96, 0, None)
        if hot.max() > 0.01:
            local = hot - cv2.blur(hot, (int(41 * s) | 1, int(41 * s) | 1))
            local = np.clip(local, 0, None).astype(np.float32)
            k = int(220 * s) | 1
            acc += cv2.blur(local, (k, max(1, int(3 * s))))[..., None] * 9.0 * np.array([0.55, 0.75, 1.0], np.float32)
        return im + acc * 0.2 * np.array([1.0, 0.97, 0.9], np.float32)

    def chroma(self, im, px):
        if px < 0.3: return im
        H, W = im.shape[:2]
        k = px / (W / 2)
        out = im.copy()
        cx, cy = W / 2, H / 2
        for ch, sc in ((0, 1 + k), (2, 1 - k)):
            M = np.array([[sc, 0, cx - sc * cx], [0, sc, cy - sc * cy]], np.float32)
            out[..., ch] = cv2.warpAffine(im[..., ch], M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        return out

    def grade_params(self, n):
        g = dict(sat=1.1, contrast=1.1, exposure=1.0, vig=0.34, tint=(1.0, 1.0, 1.0))
        f = self.tau[n]
        for e in self.ev:
            if e['t'] != 'grade' or not (e['f0'] <= f <= e['f1'] + 1): continue
            ramp = max(e.get('ramp', 6), 1)
            w = min(1.0, (f - e['f0'] + 1) / ramp, (e['f1'] + 1 - f) / ramp)
            w = max(0.0, w)
            for k in ('sat', 'contrast', 'exposure', 'vig'):
                if k in e: g[k] += (e[k] - g[k]) * w
            if 'tint' in e: g['tint'] = tuple(a + (b - a) * w for a, b in zip(g['tint'], e['tint']))
        return g

    def grade(self, im, g):
        H, W = im.shape[:2]
        im = im * g['exposure'] * np.array(g['tint'], np.float32)
        im = (im - 0.5) * g['contrast'] + 0.5
        lum = (im * np.array([0.299, 0.587, 0.114], np.float32)).sum(axis=2, keepdims=True)
        im = lum + (im - lum) * g['sat']
        r2 = ((self.xx - W / 2) / (W / 2)) ** 2 * 0.8 + ((self.yy - H / 2) / (H / 2)) ** 2 * 0.65
        return im * (1 - g['vig'] * np.clip(r2 - 0.25, 0, 1.2) ** 1.2)[..., None]

    # ------------------------------------------------------------------ blurs / distortion
    def motion_blur(self, im, n, f, e):
        who = e.get('who', 'P')
        d, _ = self.screen_motion(n, who)
        L = max(3, int(e.get('len', 12) * 0.8 * self.s))
        k = np.zeros((L, L), np.float32)
        cv2.line(k, (0, L // 2), (L - 1, L // 2), 1.0, 1)
        M = cv2.getRotationMatrix2D((L / 2 - 0.5, L / 2 - 0.5), math.degrees(math.atan2(d[1], d[0])), 1.0)
        k = cv2.warpAffine(k, M, (L, L)); k /= max(k.sum(), 1e-6)
        bl = cv2.filter2D(im, -1, k, borderType=cv2.BORDER_REPLICATE)
        pr = self.project(n, self.chars[who]['torso'][n])
        if pr:
            sx, sy = 2.4 * pr[3], 3.4 * pr[3]
            m = np.exp(-(((self.xx - pr[0]) / sx) ** 2 + ((self.yy - pr[1]) / sy) ** 2))[..., None]
            return bl * (1 - 0.8 * m) + im * (0.8 * m)
        return bl

    def radial_blur(self, im, n, f, e):
        H, W = im.shape[:2]
        pr = self.project(n, e['p'])
        cx, cy = (pr[0], pr[1]) if pr else (W / 2, H / 2)
        amt = 0.6 * e.get('amt', 0.05) * max(0.0, 1 - (f - e['f0']) / max(e['f1'] - e['f0'] + 1, 1)) ** 1.6
        if amt < 0.002: return im
        acc = np.zeros_like(im); N = 7
        for i in range(N):
            sc = 1 + amt * i / (N - 1)
            M = np.array([[sc, 0, cx - sc * cx], [0, sc, cy - sc * cy]], np.float32)
            acc += cv2.warpAffine(im, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        acc /= N
        m = np.clip(np.sqrt(((self.xx - cx) / W) ** 2 + ((self.yy - cy) / H) ** 2) * 2.2, 0, 1)[..., None]
        return im * (1 - m) + acc * m

    def shock_ripple(self, im, n, f, e):
        """refraction ring expanding from a heavy impact (real time, ~0.25 s)"""
        pr = self.project(n, e['p'])
        if not pr: return im
        age = (f - e['f0']) / self.sfps
        if age > 0.3: return im
        R = (0.15 + 2.6 * age) * self.W * (0.6 + 0.2 * e['r'])
        width = 0.05 * self.W
        dx, dy = self.xx - pr[0], self.yy - pr[1]
        r = np.sqrt(dx * dx + dy * dy) + 1e-3
        amp = 14.0 * self.s * (1 - age / 0.3) ** 1.5
        k = amp * np.exp(-((r - R) / width) ** 2) * np.sin((r - R) / width * 2.4)
        mx = (self.xx + dx / r * k).astype(np.float32); my = (self.yy + dy / r * k).astype(np.float32)
        return cv2.remap(im, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

    # ------------------------------------------------------------------ hand-drawn effects
    def _rng(self, n, e, k=0):
        return np.random.RandomState((e.get('seed', 1) * 977 + (n // 5) * 131 + k) % (2 ** 31))     # boil at 24 Hz

    def _poly(self, ov, pts, fill, outline, thick, alpha=1.0):
        pts = np.round(np.array(pts) * 4).astype(np.int32).reshape(-1, 1, 2)      # sub-pixel (shift=2) for smooth motion
        if outline is not None:
            cv2.fillPoly(ov, [pts], (*outline, alpha), lineType=AA, shift=2)
            cv2.polylines(ov, [pts], True, (*outline, alpha), max(1, int(thick)), AA, shift=2)
        cv2.fillPoly(ov, [pts], (*fill, alpha), lineType=AA, shift=2)

    def star(self, ov, n, f, e):
        pr = self.project(n, e['p'])
        if not pr: return
        age = f - e['f0']; life = max(e['f1'] - e['f0'] + 1, 1)
        grow = _interp([0.35, 1.08, 0.9, 0.7, 0.5, 0.4], age * 1.0)
        R = e['r'] * pr[3] * grow
        R = min(R, self.W * (0.27 if e['r'] > 1.8 else 0.15))
        rng = self._rng(n, e)
        rays = e.get('rays', 12)
        pts = []
        for i in range(2 * rays):
            a = i * math.pi / rays + rng.uniform(-0.05, 0.05)
            r = R * (rng.uniform(0.82, 1.12) if i % 2 == 0 else rng.uniform(0.35, 0.46))
            pts.append((pr[0] + math.cos(a) * r, pr[1] + math.sin(a) * r))
        th = max(2, 5 * self.s)
        alpha = 1.0 if age < life * 0.75 else max(0.0, 1 - (age - life * 0.75) / (life * 0.25 + 0.5))
        self._poly(ov, pts, (1, 1, 1), (0.04, 0.04, 0.06), th * 1.6, alpha)
        core = [(pr[0] + (x - pr[0]) * 0.5, pr[1] + (y - pr[1]) * 0.5) for x, y in pts]
        self._poly(ov, core, (1.0, 0.93, 0.62), None, 0, alpha)

    def shards(self, ov, n, f, e):
        pr = self.project(n, e['p'])
        if not pr: return
        age = f - e['f0']; life = max(e['f1'] - e['f0'] + 1, 1)
        rng = self._rng(n, e, 1)
        base = np.random.RandomState(e.get('seed', 1) * 31)
        R = min(e['r'] * pr[3], self.W * 0.24)
        fade = max(0.0, 1 - max(0.0, age - life * 0.6) / (life * 0.4 + 0.3))
        for i in range(e['n']):
            ang = base.uniform(0, 2 * math.pi); dist0 = base.uniform(0.35, 0.8); ln = base.uniform(0.25, 0.55); wd = base.uniform(0.05, 0.1)
            d = R * (dist0 + 0.26 * age) + rng.uniform(-2, 2) * self.s
            L = R * ln * max(0.0, 1 - age / (life + 1.6)); Wd = R * wd
            ca, sa = math.cos(ang), math.sin(ang)
            cx, cy = pr[0] + ca * d, pr[1] + sa * d
            tip = (cx + ca * L, cy + sa * L); tail = (cx - ca * L * 0.25, cy - sa * L * 0.25)
            l1 = (cx - sa * Wd, cy + ca * Wd); l2 = (cx + sa * Wd, cy - ca * Wd)
            self._poly(ov, [tail, l1, tip, l2], (1, 1, 1), (0.04, 0.04, 0.06), 3 * self.s, fade)

    def lines(self, ov, n, f, e):
        W, H = self.W, self.H
        rng = self._rng(n, e, 2)
        cnt = e.get('n', 24); a0 = e.get('a', 0.8)
        life = max(e.get('f1', e['f0']) - e['f0'] + 1, 1); age = f - e['f0']
        env = min(1.0, age / 0.6 + 0.2) * min(1.0, (life - age) / 0.8 + 0.1)
        col = (1, 1, 1)
        if e.get('mode') == 'radial':
            pr = self.project(n, e['p']) if e.get('p') else None
            cx, cy = (pr[0], pr[1]) if pr else (W / 2, H / 2)
            inner = e.get('inner', 0.18) * W
            for i in range(cnt):
                ang = rng.uniform(0, 2 * math.pi); r0 = inner * rng.uniform(0.9, 1.9); r1 = max(W, H) * rng.uniform(0.6, 1.1); wd = rng.uniform(2, 9) * self.s
                ca, sa = math.cos(ang), math.sin(ang)
                p1 = (cx + ca * r1, cy + sa * r1)
                l = (cx + ca * r0 - sa * wd, cy + sa * r0 + ca * wd); r = (cx + ca * r0 + sa * wd, cy + sa * r0 - ca * wd)
                self._poly(ov, [l, p1, r], col, None, 0, a0 * env)
            return
        who = e.get('who', 'P')
        d, _ = self.screen_motion(n, who)
        ang = math.radians(e['ang']) if e.get('ang') is not None else math.atan2(d[1], d[0])
        ca, sa = math.cos(ang), math.sin(ang)
        px, py = -sa, ca
        span = abs(W * ca) + abs(H * sa)
        drift = ((n % 5) / 5.0) * 0.08 * span          # lines slide along the motion between boils
        for i in range(cnt):
            off = rng.uniform(-0.5, 0.5) * (abs(W * px) + abs(H * py))
            ln = rng.uniform(0.18, 0.55) * span; st = rng.uniform(-0.5, 0.5) * span - drift
            wd = rng.uniform(1.5, 5.5) * self.s
            cx, cy = W / 2 + px * off + ca * st, H / 2 + py * off + sa * st
            b = (cx + ca * ln / 2, cy + sa * ln / 2)
            l = (cx - ca * ln / 2 + px * wd, cy - sa * ln / 2 + py * wd); r = (cx - ca * ln / 2 - px * wd, cy - sa * ln / 2 - py * wd)
            self._poly(ov, [l, b, r], col, None, 0, a0 * env * rng.uniform(0.5, 1.0))

    def sparkle(self, ov, n, f, e):
        pr = self.project(n, e['p'])
        if not pr: return
        age = f - e['f0']
        s = _interp([0.3, 1.0, 0.8, 0.5, 0.25, 0.0], age) * e.get('r', 0.5) * pr[3] * 2.2
        if s < 0.5: return
        cx, cy = pr[0], pr[1]
        rot = age * 0.4
        pts = []
        for k in range(8):
            a = rot + k * math.pi / 4; r = s * (1.6 if k % 2 == 0 else 0.23)
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
        self._poly(ov, pts, (1, 1, 1), None, 0, 0.95)
        cv2.circle(ov, (int(cx), int(cy)), max(2, int(s * 0.35)), (1, 1, 1, 1.0), -1, AA)

    # ------------------------------------------------------------------ screen-wide
    def flash(self, im, n, f, e):
        age = f - e['f0']; kind = e.get('kind', 'white'); a = e.get('a', 1.0)
        life = max(e['f1'] - e['f0'] + 1, 1)
        if kind == 'white':
            k = 0.8 * a * math.exp(-age / (0.35 * life + 0.25))
            return im * (1 - k) + k
        if kind == 'black':
            k = a * max(0.0, 1 - age / life)
            return im * (1 - k)
        if kind in ('invert', 'impact'):
            if age > life: return im
            g = im.mean(axis=2)
            g = 1 - np.clip((g - 0.35) * 2.6, 0, 1)
            out = np.stack([g, g, g], axis=2) * 0.92 + 0.04
            ov = np.zeros((self.H, self.W, 4), np.float32)
            ee = dict(mode='radial', n=44, a=1.0, inner=0.16, seed=e.get('seed', 5), f0=e['f0'], f1=e['f1'])
            if e.get('p'): ee['p'] = e['p']
            self.lines(ov, n, e['f0'] + 0.5, ee)
            out = np.where(ov[..., 3:4] > 0.2, 1 - out, out)
            return out * a + im * (1 - a)
        return im

    def _put_text(self, im, txt, x, y, scale, th, col, outline, alpha=1.0, font=cv2.FONT_HERSHEY_DUPLEX):
        H, W = im.shape[:2]
        m_out = np.zeros((H, W), np.uint8); m_in = np.zeros((H, W), np.uint8)
        cv2.putText(m_out, txt, (x, y), font, scale, 255, th + outline, AA)
        cv2.putText(m_in, txt, (x, y), font, scale, 255, th, AA)
        a_out = (m_out.astype(np.float32) / 255)[..., None] * alpha
        a_in = (m_in.astype(np.float32) / 255)[..., None] * alpha
        im = im * (1 - a_out) + np.array([0.02, 0.02, 0.03], np.float32) * a_out
        return im * (1 - a_in) + np.array(col, np.float32) * a_in

    def text(self, im, n, f, e):
        age = f - e['f0']; life = e['f1'] - e['f0'] + 1
        W, H = self.W, self.H
        txt = e['text']
        size = e.get('size', 0.1) * W
        sc = _interp([0.2, 1.25, 1.1, 1.0], age) if e.get('anim', 'pop') == 'pop' else 1.0
        alpha = max(0.0, (life - age) / 3.0) if age > life - 3 else 1.0
        font = cv2.FONT_HERSHEY_DUPLEX
        (tw0, th0), _ = cv2.getTextSize(txt, font, 1.0, 2)
        scale = size * sc / max(th0, 1) / 1.15
        th = max(2, int(scale * 2.0))
        (tw, tht), _ = cv2.getTextSize(txt, font, scale, th)
        x = int(e['pos'][0] * W - tw / 2); y = int(e['pos'][1] * H + tht / 2)
        col = tuple(int(e.get('col', '#ffffff').lstrip('#')[i:i + 2], 16) / 255 for i in (0, 2, 4))
        return self._put_text(im, txt, x, y, scale, th, col, max(4, int(10 * self.s * sc)), alpha)

    def watermark(self, im):
        scale = 1.15 * self.s; th = max(1, int(2 * self.s))
        x, y = int(34 * self.s), int(84 * self.s)
        im = self._put_text(im, '@Mr_HB', x, y, scale, th, (0.95, 0.96, 1.0), int(7 * self.s), 0.85)
        x0, y0 = x, y + int(16 * self.s)
        a = np.zeros(im.shape[:2], np.uint8); cv2.line(a, (x0, y0), (x0 + int(150 * self.s), y0), 255, max(2, int(5 * self.s)), AA)
        a = (a.astype(np.float32) / 255)[..., None] * 0.85
        return im * (1 - a) + np.array([0.83, 0.13, 0.18], np.float32) * a


def overlay_rgba(P, n, scale=0.5, watermark=False):
    """the 2D layer alone, as straight-alpha RGBA (for the .blend's VSE): hand-drawn shapes, white flashes, titles, watermark.
    Manga impact frames (inverted image) and lens effects are not representable as an overlay and are left out."""
    W, H = P.W, P.H
    ov = np.zeros((H, W, 4), np.float32)
    evs = []
    for e in P.by_frame.get(n, []):
        ok, f = P.active(e, n)
        if ok: evs.append((e, f))
    for e, f in evs:
        t = e['t']
        if t == 'star': P.star(ov, n, f, e)
        elif t == 'shards': P.shards(ov, n, f, e)
        elif t == 'lines': P.lines(ov, n, f, e)
        elif t == 'sparkle': P.sparkle(ov, n, f, e)
    # white flashes: white over everything with the flash strength as alpha
    for e, f in evs:
        if e['t'] == 'flash' and e.get('kind', 'white') == 'white':
            age = f - e['f0']; life = max(e['f1'] - e['f0'] + 1, 1)
            k = 0.8 * e.get('a', 1.0) * math.exp(-age / (0.35 * life + 0.25))
            ov[..., :3] = ov[..., :3] * ov[..., 3:4] + (1 - ov[..., 3:4]) * 1.0
            ov[..., 3] = ov[..., 3] + (1 - ov[..., 3]) * k
    # titles + watermark: draw on a black and a white canvas, recover colour and alpha
    blk = np.zeros((H, W, 3), np.float32); wht = np.ones((H, W, 3), np.float32)
    for e, f in evs:
        if e['t'] == 'text':
            blk = P.text(blk, n, f, e); wht = P.text(wht, n, f, e)
    if watermark:
        blk = P.watermark(blk); wht = P.watermark(wht)
    a = np.clip(1 - (wht - blk).mean(axis=2), 0, 1)
    col = np.where(a[..., None] > 1e-3, blk / np.maximum(a[..., None], 1e-3), 0)
    ov[..., :3] = ov[..., :3] * ov[..., 3:4] * (1 - a[..., None]) + col * a[..., None]
    ov[..., 3] = ov[..., 3] + (1 - ov[..., 3]) * a
    ov[..., :3] = np.where(ov[..., 3:4] > 1e-4, ov[..., :3] / np.maximum(ov[..., 3:4], 1e-4), 0)
    out = (np.clip(ov, 0, 1) * 255 + 0.5).astype(np.uint8)
    if scale != 1.0:
        out = cv2.resize(out, (int(W * scale), int(H * scale)), interpolation=cv2.INTER_AREA)
    return out


def has_overlay(P, n):
    return any(P.active(e, n)[0] and e['t'] in ('star', 'shards', 'lines', 'sparkle', 'flash', 'text') for e in P.by_frame.get(n, []))
