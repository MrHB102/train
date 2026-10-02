"""2D post: lens look (bloom, chromatic aberration, vignette, grain), blurs, and the hand-drawn style effects
(impact stars, shards, speed lines, glints, impact frames, titles) that are drawn on top of the 3D render.

Hand-drawn effects are re-drawn every 2nd frame (on twos) with jitter, like drawn-over effects on an 18 fps animation.
"""
import json
import math
import os

import cv2
import numpy as np

AA = cv2.LINE_AA


class Post:
    def __init__(self, shot_path, fx2d_path, W, H, fps=18):
        shot = json.load(open(shot_path))
        fx = json.load(open(fx2d_path))
        self.cam = shot['cam']
        self.W, self.H, self.fps = W, H, fps
        self.frames = shot['frames']
        self.ev = fx['events']
        self.chars = fx['chars']
        self.s = W / 1080.0
        self.by_frame = {}
        for e in self.ev:
            for f in range(e['f0'], e.get('f1', e['f0']) + 1):
                self.by_frame.setdefault(f, []).append(e)

    # ------------------------------------------------------------------ projection (mirrors three.js camera + rotateZ roll)
    def project(self, f, p):
        c = self.cam[min(f, len(self.cam) - 1)]
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
        scale = (self.H / 2) / (t * depth)            # pixels per stud at that depth
        return px, py, depth, scale

    def screen_motion(self, f, who):
        a = self.project(f, self.chars[who]['torso'][max(f - 1, 0)]); b = self.project(f, self.chars[who]['torso'][f])
        if not a or not b: return (1.0, 0.0), 0.0
        v = np.array([b[0] - a[0], b[1] - a[1]]); n = np.linalg.norm(v)
        return ((v / n) if n > 1e-3 else np.array([1.0, 0.0])), n

    # ------------------------------------------------------------------ main
    def process(self, f, img, final=True):
        """img: uint8 RGB (H,W,3) from the renderer -> uint8 RGB"""
        W, H = self.W, self.H
        im = img.astype(np.float32) / 255.0
        evs = self.by_frame.get(f, [])
        # --- blurs
        for e in evs:
            if e['t'] == 'mblur': im = self.motion_blur(im, f, e)
        for e in evs:
            if e['t'] == 'rblur': im = self.radial_blur(im, f, e)
        # --- lens look
        im = self.bloom(im, 0.2)
        ca = 1.1 * self.s + sum(e['amt'] * self.s * max(0.0, 1 - (f - e['f0']) / max(e['f1'] - e['f0'] + 1, 1)) for e in evs if e['t'] == 'ca')
        im = self.chroma(im, ca)
        g = self.grade_params(f)
        im = self.grade(im, g)
        rng = np.random.RandomState(f * 7 + 3)
        im += rng.normal(0, 0.010, im.shape[:2])[..., None].astype(np.float32)
        im = np.clip(im, 0, 1)
        # --- hand-drawn overlay (crisp, after the lens look)
        ov = np.zeros((H, W, 4), np.float32)
        used = False
        for e in evs:
            t = e['t']
            if t == 'star': self.star(ov, f, e); used = True
            elif t == 'shards': self.shards(ov, f, e); used = True
            elif t == 'lines': self.lines(ov, f, e); used = True
            elif t == 'sparkle': self.sparkle(ov, f, e); used = True
        if used:
            a = ov[..., 3:4]
            im = im * (1 - a) + ov[..., :3] * a
        # --- flashes / impact frames / titles
        for e in evs:
            if e['t'] == 'flash': im = self.flash(im, f, e)
        for e in evs:
            if e['t'] == 'text': im = self.text(im, f, e)
        if final:
            im = self.watermark(im, f)
        return (np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)

    # ------------------------------------------------------------------ lens
    def bloom(self, im, k):
        lum = im.max(axis=2, keepdims=True)
        br = np.clip(im - 0.78, 0, None) * np.clip(lum * 1.6, 0, 1.6)
        s = self.s
        acc = cv2.GaussianBlur(br, (0, 0), 7 * s) * 0.55 + cv2.GaussianBlur(br, (0, 0), 22 * s) * 0.45 + cv2.GaussianBlur(br, (0, 0), 62 * s) * 0.40
        return im + acc * k * np.array([1.0, 0.97, 0.90], np.float32)

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

    def grade_params(self, f):
        g = dict(sat=1.1, contrast=1.1, exposure=1.0, vig=0.32, tint=(1.0, 1.0, 1.0))
        for e in self.ev:
            if e['t'] != 'grade' or not (e['f0'] <= f <= e['f1']): continue
            ramp = max(e.get('ramp', 6), 1)
            w = min(1.0, (f - e['f0'] + 1) / ramp, (e['f1'] - f + 1) / ramp)
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
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r2 = ((xx - W / 2) / (W / 2)) ** 2 * 0.8 + ((yy - H / 2) / (H / 2)) ** 2 * 0.65
        im = im * (1 - g['vig'] * np.clip(r2 - 0.25, 0, 1.2) ** 1.2)[..., None]
        return im

    # ------------------------------------------------------------------ blurs
    def motion_blur(self, im, f, e):
        who = e.get('who', 'P')
        d, n = self.screen_motion(f, who)
        L = max(3, int(e.get('len', 12) * self.s))
        k = np.zeros((L, L), np.float32)
        cv2.line(k, (0, L // 2), (L - 1, L // 2), 1.0, 1)
        ang = math.degrees(math.atan2(d[1], d[0]))
        M = cv2.getRotationMatrix2D((L / 2 - 0.5, L / 2 - 0.5), ang, 1.0)
        k = cv2.warpAffine(k, M, (L, L)); k /= max(k.sum(), 1e-6)
        bl = cv2.filter2D(im, -1, k, borderType=cv2.BORDER_REPLICATE)
        # keep the subject sharper: elliptical mask at the subject's screen position
        pr = self.project(f, self.chars[who]['torso'][f])
        if pr:
            H, W = im.shape[:2]
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            sx, sy = 2.4 * pr[3], 3.4 * pr[3]
            m = np.exp(-(((xx - pr[0]) / sx) ** 2 + ((yy - pr[1]) / sy) ** 2))[..., None]
            return bl * (1 - 0.8 * m) + im * (0.8 * m)
        return bl

    def radial_blur(self, im, f, e):
        H, W = im.shape[:2]
        pr = self.project(f, e['p'])
        cx, cy = (pr[0], pr[1]) if pr else (W / 2, H / 2)
        age = f - e['f0']
        amt = e.get('amt', 0.05) * max(0.0, 1 - age / max(e['f1'] - e['f0'] + 1, 1))
        acc = np.zeros_like(im)
        N = 7
        for i in range(N):
            sc = 1 + amt * i / (N - 1)
            M = np.array([[sc, 0, cx - sc * cx], [0, sc, cy - sc * cy]], np.float32)
            acc += cv2.warpAffine(im, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        acc /= N
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        m = np.clip(np.sqrt(((xx - cx) / W) ** 2 + ((yy - cy) / H) ** 2) * 2.2, 0, 1)[..., None]
        return im * (1 - m) + acc * m

    # ------------------------------------------------------------------ hand-drawn effects
    def _rng(self, f, e, k=0):
        return np.random.RandomState((e.get('seed', 1) * 977 + (f // 2) * 131 + k) % (2 ** 31))

    def _poly(self, ov, pts, fill, outline, thick, alpha=1.0):
        pts = np.round(np.array(pts)).astype(np.int32).reshape(-1, 1, 2)
        if outline is not None:
            cv2.fillPoly(ov, [pts], (*outline, alpha), lineType=AA)
            cv2.polylines(ov, [pts], True, (*outline, alpha), max(1, int(thick)), AA)
        cv2.fillPoly(ov, [pts], (*fill, alpha), lineType=AA)

    def star(self, ov, f, e):
        pr = self.project(f, e['p'])
        if not pr: return
        age = f - e['f0']; life = max(e['f1'] - e['f0'], 1)
        grow = [0.55, 1.0, 0.85, 0.65, 0.5][min(age, 4)]
        R = e['r'] * pr[3] * grow
        R = min(R, self.W * (0.27 if e['r'] > 1.8 else 0.15))
        rng = self._rng(f, e)
        n = e.get('rays', 12)
        pts = []
        for i in range(2 * n):
            a = i * math.pi / n + rng.uniform(-0.06, 0.06)
            r = R * (rng.uniform(0.8, 1.15) if i % 2 == 0 else rng.uniform(0.34, 0.46))
            pts.append((pr[0] + math.cos(a) * r, pr[1] + math.sin(a) * r))
        th = max(2, 5 * self.s)
        alpha = 1.0 if age < life else 0.8
        self._poly(ov, pts, (1, 1, 1), (0.04, 0.04, 0.06), th * 1.6, alpha)
        core = [((pr[0] + (x - pr[0]) * 0.5), (pr[1] + (y - pr[1]) * 0.5)) for x, y in pts]
        self._poly(ov, core, (1.0, 0.93, 0.62), None, 0, alpha)

    def shards(self, ov, f, e):
        pr = self.project(f, e['p'])
        if not pr: return
        age = f - e['f0']; life = max(e['f1'] - e['f0'], 1)
        rng = self._rng(f, e, 1)
        base = np.random.RandomState(e.get('seed', 1) * 31)
        R = min(e['r'] * pr[3], self.W * 0.24)
        for i in range(e['n']):
            ang = base.uniform(0, 2 * math.pi); dist0 = base.uniform(0.35, 0.8); ln = base.uniform(0.25, 0.55); wd = base.uniform(0.05, 0.1)
            d = R * (dist0 + 0.22 * age) + rng.uniform(-3, 3) * self.s
            L = R * ln * (1 - age / (life + 1.6)); Wd = R * wd
            ca, sa = math.cos(ang), math.sin(ang)
            cx, cy = pr[0] + ca * d, pr[1] + sa * d
            tip = (cx + ca * L, cy + sa * L); tail = (cx - ca * L * 0.25, cy - sa * L * 0.25)
            l1 = (cx - sa * Wd, cy + ca * Wd); l2 = (cx + sa * Wd, cy - ca * Wd)
            self._poly(ov, [tail, l1, tip, l2], (1, 1, 1), (0.04, 0.04, 0.06), 3 * self.s, 1.0)

    def lines(self, ov, f, e):
        W, H = self.W, self.H
        rng = self._rng(f, e, 2)
        n = e.get('n', 24); a0 = e.get('a', 0.8)
        col = (1, 1, 1)
        if e.get('mode') == 'radial':
            pr = self.project(f, e['p']) if e.get('p') else None
            cx, cy = (pr[0], pr[1]) if pr else (W / 2, H / 2)
            inner = e.get('inner', 0.18) * W
            for i in range(n):
                ang = rng.uniform(0, 2 * math.pi); r0 = inner * rng.uniform(0.9, 1.9); r1 = max(W, H) * rng.uniform(0.6, 1.1); wd = rng.uniform(2, 9) * self.s
                ca, sa = math.cos(ang), math.sin(ang)
                p0 = (cx + ca * r0, cy + sa * r0); p1 = (cx + ca * r1, cy + sa * r1)
                l = (cx + ca * r0 - sa * wd, cy + sa * r0 + ca * wd); r = (cx + ca * r0 + sa * wd, cy + sa * r0 - ca * wd)
                self._poly(ov, [l, p1, r], col, None, 0, a0)
            return
        who = e.get('who', 'P')
        d, mv = self.screen_motion(f, who)
        if e.get('ang') is not None:
            ang = math.radians(e['ang'])
        else:
            ang = math.atan2(d[1], d[0])
        ca, sa = math.cos(ang), math.sin(ang)
        px, py = -sa, ca
        span = abs(W * ca) + abs(H * sa)
        for i in range(n):
            off = rng.uniform(-0.5, 0.5) * (abs(W * px) + abs(H * py))
            ln = rng.uniform(0.18, 0.55) * span; st = rng.uniform(-0.5, 0.5) * span
            wd = rng.uniform(1.5, 5.5) * self.s
            cx, cy = W / 2 + px * off + ca * st, H / 2 + py * off + sa * st
            a = (cx - ca * ln / 2, cy - sa * ln / 2); b = (cx + ca * ln / 2, cy + sa * ln / 2)
            l = (cx - ca * ln / 2 + px * wd, cy - sa * ln / 2 + py * wd); r = (cx - ca * ln / 2 - px * wd, cy - sa * ln / 2 - py * wd)
            self._poly(ov, [l, b, r], col, None, 0, a0 * rng.uniform(0.5, 1.0))

    def sparkle(self, ov, f, e):
        pr = self.project(f, e['p'])
        if not pr: return
        age = f - e['f0']
        s = [0.5, 1.0, 0.8, 0.5, 0.3][min(age, 4)] * e.get('r', 0.5) * pr[3] * 2.2
        cx, cy = pr[0], pr[1]
        pts = [(cx, cy - s * 1.6), (cx + s * 0.16, cy - s * 0.16), (cx + s * 1.6, cy), (cx + s * 0.16, cy + s * 0.16), (cx, cy + s * 1.6), (cx - s * 0.16, cy + s * 0.16), (cx - s * 1.6, cy), (cx - s * 0.16, cy - s * 0.16)]
        self._poly(ov, pts, (1, 1, 1), None, 0, 0.95)
        cv2.circle(ov, (int(cx), int(cy)), max(2, int(s * 0.35)), (1, 1, 1, 1.0), -1, AA)

    # ------------------------------------------------------------------ screen-wide
    def flash(self, im, f, e):
        age = f - e['f0']; kind = e.get('kind', 'white'); a = e.get('a', 1.0)
        life = max(e['f1'] - e['f0'] + 1, 1)
        if kind == 'white':
            k = a * max(0.0, 1 - age / (life + 1.5))
            return im * (1 - k) + k
        if kind == 'black':
            k = a * max(0.0, 1 - age / life)
            return im * (1 - k)
        if kind in ('invert', 'impact'):
            # manga-style impact frame: inverted, hard-thresholded two-tone with radial burst lines
            g = im.mean(axis=2)
            g = 1 - np.clip((g - 0.35) * 2.6, 0, 1)
            out = np.stack([g, g, g], axis=2)
            out = out * 0.92 + 0.04
            ov = np.zeros((self.H, self.W, 4), np.float32)
            ee = dict(mode='radial', n=44, a=1.0, inner=0.16, seed=e.get('seed', 5))
            if e.get('p'): ee['p'] = e['p']
            self.lines(ov, f, ee)
            a_ = ov[..., 3:4]
            out = out * (1 - a_ * 0.0) + (1 - out) * a_ * 0.0 + a_ * (1 - out) * 0.0
            out = np.where(a_ > 0.2, 1 - out, out)
            return out * a + im * (1 - a)
        return im

    def _put_text(self, im, txt, x, y, scale, th, col, outline, alpha=1.0, font=cv2.FONT_HERSHEY_DUPLEX, underline=None):
        H, W = im.shape[:2]
        m_out = np.zeros((H, W), np.uint8); m_in = np.zeros((H, W), np.uint8)
        cv2.putText(m_out, txt, (x, y), font, scale, 255, th + outline, AA)
        cv2.putText(m_in, txt, (x, y), font, scale, 255, th, AA)
        a_out = (m_out.astype(np.float32) / 255)[..., None] * alpha
        a_in = (m_in.astype(np.float32) / 255)[..., None] * alpha
        im = im * (1 - a_out) + np.array([0.02, 0.02, 0.03], np.float32) * a_out
        im = im * (1 - a_in) + np.array(col, np.float32) * a_in
        return im

    def text(self, im, f, e):
        age = f - e['f0']; life = e['f1'] - e['f0']
        W, H = self.W, self.H
        txt = e['text']
        size = e.get('size', 0.1) * W
        sc = [0.2, 1.25, 1.1, 1.0][min(age, 3)] if e.get('anim', 'pop') == 'pop' else 1.0
        alpha = max(0.0, (life - age) / 3.0) if age > life - 3 else 1.0
        font = cv2.FONT_HERSHEY_DUPLEX
        (tw0, th0), _ = cv2.getTextSize(txt, font, 1.0, 2)
        scale = size * sc / max(th0, 1) / 1.15
        th = max(2, int(scale * 2.0))
        (tw, tht), _ = cv2.getTextSize(txt, font, scale, th)
        x = int(e['pos'][0] * W - tw / 2); y = int(e['pos'][1] * H + tht / 2)
        col = tuple(int(e.get('col', '#ffffff').lstrip('#')[i:i + 2], 16) / 255 for i in (0, 2, 4))
        return self._put_text(im, txt, x, y, scale, th, col, max(4, int(10 * self.s * sc)), alpha)

    def watermark(self, im, f):
        """small @Mr_HB stamp, top-left (own design)"""
        scale = 1.15 * self.s; th = max(1, int(2 * self.s))
        x, y = int(34 * self.s), int(84 * self.s)
        im = self._put_text(im, '@Mr_HB', x, y, scale, th, (0.95, 0.96, 1.0), int(7 * self.s), 0.85)
        x0, y0 = x, y + int(16 * self.s)
        cv2.line(im, (x0, y0), (x0 + int(150 * self.s), y0), (0.83, 0.13, 0.18), max(2, int(5 * self.s)), AA) if im.dtype == np.uint8 else None
        a = np.zeros(im.shape[:2], np.uint8); cv2.line(a, (x0, y0), (x0 + int(150 * self.s), y0), 255, max(2, int(5 * self.s)), AA)
        a = (a.astype(np.float32) / 255)[..., None] * 0.85
        return im * (1 - a) + np.array([0.83, 0.13, 0.18], np.float32) * a
