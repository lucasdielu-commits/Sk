"""KUMO — pub matcha de cérémonie (marque fictive), encre japonaise (sumi-e), 9:16, 1080x1920, 30 i/s, 26,5 s.

Usage : python3 kumo.py <dossier_polices> <sortie.mp4> [temps,à,prévisualiser]
"""
import json, math, os, subprocess, sys
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

FONTS, OUT = sys.argv[1], sys.argv[2]
W, H, FPS = 1080, 1920, 30
DUR = 26.5
INK = np.array([22, 20, 26], np.float32); MATCHA = np.array([112, 152, 46], np.float32); VERMIL = (196, 46, 36)

def cfont(w, size, it=False): return ImageFont.truetype(os.path.join(FONTS, f"fontsource-cormorant-garamond-5.3.0/files/cormorant-garamond-latin-{w}-{'italic' if it else 'normal'}.woff"), size)
def jfont(w, size): return ImageFont.truetype(os.path.join(FONTS, f"fontsource-jost-5.3.0/files/jost-latin-{w}-normal.woff"), size)
def ease(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3
def ease_in(x): x = min(1, max(0, x)); return x ** 3
def ease_io(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
def back(x, s=1.6): x = min(1, max(0, x)) - 1; return x * x * ((s + 1) * x + s) + 1
def lerp(a, b, x): return a + (b - a) * x
def seg(t, a, b): return (t - a) / (b - a)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

# ------------------------------------------------------------------ papier washi
def washi():
    r = np.random.default_rng(2); base = np.empty((H, W, 3), np.float32); base[:] = (241, 235, 222)
    n = np.asarray(Image.fromarray(r.normal(128, 50, (H // 2, W // 2)).clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1)).resize((W, H)), np.float32)
    base *= (1 + (n[..., None] - 128) / 128 * 0.025)
    fib = Image.new("L", (W, H), 0); d = ImageDraw.Draw(fib)
    for _ in range(900):                                   # longues fibres végétales
        x, y = r.uniform(0, W), r.uniform(0, H); a = r.uniform(0, math.pi); L = r.uniform(30, 160); pts = []
        for k in range(8):
            a += r.normal(0, 0.25); x += math.cos(a) * L / 8; y += math.sin(a) * L / 8; pts.append((x, y))
        d.line(pts, fill=int(r.uniform(30, 90)), width=1)
    f = np.asarray(fib.filter(ImageFilter.GaussianBlur(0.6)), np.float32)[..., None] / 255
    base = base * (1 - f * 0.06) + 255 * f * 0.03
    lowv = np.clip(1.03 - (((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2) * 0.35, 0.85, 1.03)[..., None]
    return base * lowv
PAPER = washi()

def ink_on(canvas, alpha, color=INK, density=1.0):
    """Dépose de l'encre (alpha 0..1) sur la toile float RGB."""
    a = np.clip(alpha * density, 0, 1)[..., None]; return canvas * (1 - a) + color * a

# ------------------------------------------------------------------ coups de pinceau (pré-calculés)
def noise1d(n, seed, k=5):
    r = np.random.default_rng(seed); v = r.random(n)
    for _ in range(k): v = np.convolve(np.r_[v[-3:], v, v[:3]], np.ones(3) / 3, "same")[3:-3] if n > 6 else v
    return (v - v.min()) / (v.max() - v.min() + 1e-6)

class Stroke:
    """Trait de pinceau : carte d'opacité + carte du « moment » où chaque pixel est peint (pour le révéler)."""
    def __init__(self, pts, widths, seed=0, dry=0.45, wet=1.0, bristles=64):
        pts = np.asarray(pts, np.float32); widths = np.asarray(widths, np.float32)
        if len(widths) != len(pts): widths = np.interp(np.linspace(0, 1, len(pts)), np.linspace(0, 1, len(widths)), widths).astype(np.float32)
        # ré-échantillonnage régulier
        seglen = np.hypot(*np.diff(pts, axis=0).T); L = np.r_[0, np.cumsum(seglen)]; tot = L[-1]
        n = max(2, int(tot / max(2.0, widths.mean() / 4)))
        s = np.linspace(0, tot, n); px = np.interp(s, L, pts[:, 0]); py = np.interp(s, L, pts[:, 1]); wr = np.interp(s, L, widths)
        x0 = int(max(0, (px - wr).min() - 4)); x1 = int(min(W, (px + wr).max() + 4)); y0 = int(max(0, (py - wr).min() - 4)); y1 = int(min(H, (py + wr).max() + 4))
        x1 = max(x1, x0 + 2); y1 = max(y1, y0 + 2); x0 = min(x0, W - 2); y0 = min(y0, H - 2); x1 = min(max(x1, x0 + 2), W); y1 = min(max(y1, y0 + 2), H)
        self.box = (x0, y0, x1, y1); A = np.zeros((y1 - y0, x1 - x0), np.float32); U = np.full_like(A, 9.0)
        bri = noise1d(bristles, seed, 2); r = np.random.default_rng(seed)
        for i in range(n):
            u = s[i] / tot; rad = wr[i]
            if rad < 0.6: continue
            dx = px[min(n - 1, i + 1)] - px[max(0, i - 1)]; dy = py[min(n - 1, i + 1)] - py[max(0, i - 1)]; dl = math.hypot(dx, dy) + 1e-6
            nx, ny = -dy / dl, dx / dl
            cx, cy = px[i] - x0, py[i] - y0; ix0, ix1 = int(max(0, cx - rad - 1)), int(min(A.shape[1], cx + rad + 2)); iy0, iy1 = int(max(0, cy - rad - 1)), int(min(A.shape[0], cy + rad + 2))
            if ix1 <= ix0 or iy1 <= iy0: continue
            gy, gx = np.mgrid[iy0:iy1, ix0:ix1].astype(np.float32)
            rr = np.hypot(gx - cx, gy - cy) / rad; nn = ((gx - cx) * nx + (gy - cy) * ny) / rad
            idx = np.clip(((nn + 1) / 2 * (bristles - 1)).astype(int), 0, bristles - 1)
            dryness = dry * u ** 1.6 + 0.08 * r.random()
            hair = (bri[idx] > dryness).astype(np.float32) * (0.75 + 0.25 * bri[idx])
            disc = np.clip((1 - rr) * rad / 1.5, 0, 1) * hair * (wet * (1 - 0.35 * u) + 0.35 * u * 0.7)
            sub = A[iy0:iy1, ix0:ix1]; m = disc > 0.02
            sub[:] = np.maximum(sub, disc); su = U[iy0:iy1, ix0:ix1]; su[m] = np.minimum(su[m], u)
        self.A = np.asarray(Image.fromarray((A * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7)), np.float32) / 255
        self.U = U
    def alpha(self, p, soft=0.02):
        if p <= 0: return None
        return self.A * np.clip((p - self.U) / soft, 0, 1)
    def paint(self, canvas, p, color=INK, density=1.0):
        a = self.alpha(p)
        if a is None: return canvas
        x0, y0, x1, y1 = self.box; canvas[y0:y1, x0:x1] = ink_on(canvas[y0:y1, x0:x1], a, color, density); return canvas

def taper(n, w0, w1=None, peak=0.3, head=0.15):
    u = np.linspace(0, 1, n); w1 = w0 * 0.15 if w1 is None else w1
    return np.where(u < head, w0 * (0.4 + 0.6 * u / head), w0 + (w1 - w0) * ((u - head) / (1 - head)) ** 1.3)
def arc_pts(cx, cy, r, a0, a1, n=200, wob=0.0, seed=0):
    a = np.radians(np.linspace(a0, a1, n)); rr = r * (1 + wob * (noise1d(n, seed, 3) - 0.5))
    return np.c_[cx + rr * np.cos(a), cy + rr * np.sin(a)]

# ensō : cercle zen d'un seul geste, épais au départ, sec à la fin
ENSO_PTS = arc_pts(540, 860, 330, -70, 255, 260, 0.05, 3)
ENSO = Stroke(ENSO_PTS, taper(260, 46, 10, head=0.08), seed=7, dry=0.75)
ENSO_END = Stroke(arc_pts(540, 900, 380, -70, 255, 260, 0.05, 9), taper(260, 52, 12, head=0.08), seed=9, dry=0.75)

# grand coup de pinceau de transition (zigzag qui couvre l'écran)
def big_brush(seed, horizontal=False):
    r = np.random.default_rng(seed); pts = []
    rows = 5
    for k in range(rows):
        y = -80 + k * (H + 160) / (rows - 1)
        xa, xb = (-200, W + 200) if k % 2 == 0 else (W + 200, -200)
        for j in range(12): pts.append((lerp(xa, xb, j / 11), y + r.normal(0, 18) + 140 * math.sin(j / 11 * math.pi) * (1 if k % 2 else -1) * 0.4))
    pts = np.array(pts)
    return Stroke(pts, np.full(len(pts), 300) * (0.9 + 0.1 * noise1d(len(pts), seed)), seed=seed, dry=0.35, bristles=90)
BRUSH_A = big_brush(21); BRUSH_B = big_brush(22)

# ------------------------------------------------------------------ paysage au lavis
def fbm1(x, seed, oct_=5):
    r = np.random.default_rng(seed); v = np.zeros_like(x); a = 1; f = 1
    for o in range(oct_):
        ph = r.uniform(0, 100); v += a * np.sin(x * f * 0.004 + ph) * np.cos(x * f * 0.0027 + ph * 1.3); a *= 0.5; f *= 2.1
    return v
def ridge_alpha(seed, base, amp, fade, strength, width=W + 400):
    x = np.arange(width, dtype=np.float32); ridge = base - amp * (0.5 + 0.5 * fbm1(x, seed)) - amp * 0.4 * np.abs(np.sin(x / 260 + seed))
    y = np.arange(H, dtype=np.float32)[:, None]; d = y - ridge[None, :]
    a = np.where(d > 0, np.exp(-d / fade), 0) * strength
    a *= np.clip(d / 3, 0, 1)                                  # bord net du sommet
    tex = np.asarray(Image.fromarray(np.random.default_rng(seed).normal(128, 60, (H // 4, width // 4)).clip(0, 255).astype(np.uint8)).resize((width, H)), np.float32) / 255
    return (a * (0.8 + 0.4 * tex)).astype(np.float32)
MT = [ridge_alpha(31, 820, 260, 420, 0.42), ridge_alpha(32, 1100, 300, 360, 0.6), ridge_alpha(33, 1400, 260, 300, 0.85)]
def mist(t, k=1.0, scale=1.0, seed=0):
    x = xx[::8, ::8] / 400 * scale; y = yy[::8, ::8] / 400 * scale
    v = np.sin(x * 2.1 + t * 0.12 + seed) * np.cos(y * 3.3 - t * 0.07) + 0.5 * np.sin(x * 5.3 - t * 0.2 + y * 1.7) + 0.25 * np.sin(x * 11 + y * 9 + t * 0.3)
    v = (v - v.min()) / (v.max() - v.min() + 1e-6)
    return np.asarray(Image.fromarray((v * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32) / 255 * k

def bird(cx, cy, s, flap):
    return [Stroke([(cx - s, cy - s * 0.3 * flap), (cx - s * 0.4, cy - s * 0.1), (cx, cy)], [s * 0.05, s * 0.09, s * 0.05], 5, 0.2),
            Stroke([(cx, cy), (cx + s * 0.4, cy - s * 0.12), (cx + s, cy - s * 0.35 * flap)], [s * 0.05, s * 0.09, s * 0.04], 6, 0.2)]

# bambous
def bamboo():
    strokes = []; r = np.random.default_rng(4)
    for k, (x, w, top) in enumerate(((220, 30, -100), (520, 38, -60), (820, 26, 80), (380, 18, 200))):
        y = H + 40; seg_i = 0
        while y > top:
            L = r.uniform(240, 330); y1 = max(top, y - L)
            pts = [(x + r.normal(0, 2), y - 6), (x + r.normal(0, 3), (y + y1) / 2), (x + r.normal(0, 2), y1 + 6)]
            strokes.append(("stem", k, seg_i, Stroke(pts, [w * 1.05, w, w * 1.08], 40 + k * 10 + seg_i, 0.35)))
            strokes.append(("node", k, seg_i, Stroke([(x - w * 0.8, y1 + 4), (x + w * 0.8, y1 + 1)], [4, 6], 70 + seg_i, 0.2)))
            if r.random() < 0.55:                              # feuilles en éventail
                side = 1 if r.random() < 0.5 else -1
                for j in range(3):
                    a = math.radians(side * (25 + j * 22) - 90 * 0 + (10 if side > 0 else 170)); L2 = r.uniform(150, 230)
                    p0 = (x + side * w * 0.5, y1 + 10); pts2 = [p0, (p0[0] + math.cos(a) * L2 * .5, p0[1] + math.sin(a) * L2 * .5 + 30), (p0[0] + math.cos(a) * L2, p0[1] + math.sin(a) * L2 + 70)]
                    strokes.append(("leaf", k, seg_i, Stroke(pts2, [3, 16, 2], 90 + seg_i * 7 + j, 0.25)))
            y = y1 - 10; seg_i += 1
    return strokes
BAMBOO = bamboo()

# bol de thé
BOWL = [Stroke(arc_pts(540, 1060, 300, 5, 175, 120, 0.02, 1), taper(120, 22, 14, head=0.1), 51, 0.5),
        Stroke([(260, 1090), (540, 1060), (820, 1090)], [12, 7, 10], 52, 0.4),
        Stroke(arc_pts(540, 1395, 90, 15, 165, 40, 0.0, 2), [10] * 40, 53, 0.4)]
BOWL_MASK = Image.new("L", (W, H), 0); ImageDraw.Draw(BOWL_MASK).chord((240, 760, 840, 1360), 5, 175, fill=255)
BOWL_MASK = np.asarray(BOWL_MASK.filter(ImageFilter.GaussianBlur(3)), np.float32) / 255
STEAM = [Stroke([(470 + k * 70 + 30 * math.sin(j * 0.9 + k), 1020 - j * 45) for j in range(9)], [2, 4, 5, 5, 4, 3, 2, 1.5, 1], 60 + k, 0.6) for k in range(3)]
WHISK = [Stroke([(380 + j * 40, 1000 + (24 if j % 2 else -24)) for j in range(11)], [3] * 11, 70 + k, 0.5) for k in range(2)]

# boîte de matcha
def tin_strokes():
    out = []
    for k in range(13): out.append(Stroke([(400, 730 + k * 54), (540, 728 + k * 54), (680, 730 + k * 54)], [44, 46, 42], 80 + k, 0.22, bristles=80))
    out.append(Stroke([(380, 712), (540, 706), (700, 712)], [22, 24, 20], 99, 0.5))
    return out
TIN = tin_strokes()
def tin_alpha():
    r = np.random.default_rng(12); m = Image.new("L", (W, H), 0); d = ImageDraw.Draw(m)
    pts = [(392 + r.normal(0, 3), y) for y in range(712, 1420, 20)] + [(688 + r.normal(0, 3), y) for y in range(1420, 712, -20)]
    d.polygon(pts, fill=255); d.ellipse((392, 690, 688, 740), fill=255)
    a = np.asarray(m.filter(ImageFilter.GaussianBlur(1.5)), np.float32) / 255
    streak = np.asarray(Image.fromarray(r.normal(128, 70, (H // 6, 8)).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32) / 255
    return a * (0.86 + 0.16 * streak)
TIN_A = tin_alpha()
TIN_BAND = (390, 960, 690, 1080)

# ------------------------------------------------------------------ textes et sceau
def ink_text(txt, f, track=0):
    ws = [f.getlength(c) for c in txt]; asc, desc = f.getmetrics(); tw = int(sum(ws) + track * (len(txt) - 1))
    m = Image.new("L", (tw + 40, asc + desc + 40), 0); d = ImageDraw.Draw(m); x = 20
    for c, w_ in zip(txt, ws): d.text((x, 20), c, font=f, fill=255); x += w_ + track
    a = np.asarray(m, np.float32) / 255
    tex = np.asarray(Image.fromarray(np.random.default_rng(len(txt)).normal(128, 50, m.size[::-1]).clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1)), np.float32) / 255
    return a * (0.82 + 0.25 * tex)
def put_text(canvas, a, cx, cy, p, color=INK, density=0.92):
    if p <= 0: return canvas
    e = ease(p); h, w = a.shape
    if e < 0.98:      # l'encre « boit » dans le papier : flou qui se résorbe
        a = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur((1 - e) * 8)), np.float32) / 255
    x0 = int(cx - w / 2); y0 = int(cy - h / 2); xs, ys = max(0, x0), max(0, y0); xe, ye = min(W, x0 + w), min(H, y0 + h)
    canvas[ys:ye, xs:xe] = ink_on(canvas[ys:ye, xs:xe], a[ys - y0:ye - y0, xs - x0:xe - x0] * e, color, density); return canvas
TX = {k: ink_text(v, f, tr) for k, v, f, tr in (
    ("instant", "Un instant.", cfont(400, 110, True), 0),
    ("nuage1", "Au-dessus des nuages,", cfont(400, 84, True), 0), ("nuage2", "un thé pousse à l'ombre.", cfont(400, 84, True), 0),
    ("kumo", "KUMO", cfont(500, 190), 40), ("cere", "MATCHA CÉRÉMONIAL", jfont(300, 38), 12),
    ("f1", "Fouetté.", cfont(500, 120, True), 0), ("f2", "Velouté.", cfont(500, 120, True), 0), ("f3", "Vert.", cfont(500, 120, True), 0),
    ("rec", "Première récolte de printemps", cfont(400, 64, True), 0), ("tin", "KUMO", cfont(600, 64), 14),
    ("temps", "Prends le temps.", cfont(400, 96, True), 0), ("handle", "@kumo.matcha", jfont(300, 36), 6))}
def seal_img(s=170):
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((4, 4, s - 4, s - 4), 14, fill=VERMIL + (255,))
    f = cfont(700, int(s * 0.38))
    for ch, (x, y) in zip("KUMO", ((0.27, 0.27), (0.73, 0.27), (0.27, 0.73), (0.73, 0.73))):
        w_ = f.getlength(ch); d.text((s * x - w_ / 2, s * y - s * 0.26), ch, font=f, fill=(244, 236, 222, 255))
    n = (np.random.default_rng(3).random((s, s)) > 0.12).astype(np.uint8) * 255
    a = ImageChops.multiply(im.split()[3], Image.fromarray(n).filter(ImageFilter.GaussianBlur(0.6)))
    im.putalpha(a); return np.asarray(im, np.float32)
SEAL = seal_img(); SEAL_S = seal_img(110)
def put_seal(canvas, cx, cy, p, seal=SEAL):
    if p <= 0: return canvas
    s = back(p, 2.2); im = Image.fromarray(seal.astype(np.uint8)).resize((max(2, int(seal.shape[1] * (1.6 - 0.6 * s))),) * 2)
    a = np.asarray(im, np.float32); h, w = a.shape[:2]; x0, y0 = int(cx - w / 2), int(cy - h / 2)
    al = a[..., 3:4] / 255 * min(1, p * 3) * 0.95; canvas[y0:y0 + h, x0:x0 + w] = canvas[y0:y0 + h, x0:x0 + w] * (1 - al) + a[..., :3] * al; return canvas

# ------------------------------------------------------------------ scènes
def drop_bloom(canvas, cx, cy, R, t, seed=1, dark=1.0):
    ang = np.arctan2(yy - cy, xx - cx); d = np.hypot(xx - cx, yy - cy)
    edge = R * (1 + 0.12 * np.sin(ang * 5 + seed) + 0.07 * np.sin(ang * 11 - seed * 2) + 0.04 * np.sin(ang * 23 + t))
    inside = np.clip((edge - d) / 6, 0, 1); rim = np.exp(-((d - edge * 0.94) / (R * 0.05 + 2)) ** 2) * 0.35
    a = inside * (0.55 + 0.45 * np.clip(d / (edge + 1), 0, 1) ** 3) + rim * inside
    return ink_on(canvas, a, INK, dark)

def s_intro(t):
    c = PAPER.copy()
    if t < 0.75:                                                # la goutte tombe
        y = lerp(-40, 860 - 330 - 0, ease_in(t / 0.75)); r = 12
        c = ink_on(c, np.clip((r - np.hypot(xx - 540 - 330 * math.cos(math.radians(-70)) * 0, yy - y)) / 2, 0, 1), INK)
    else:
        c = drop_bloom(c, 540 + 330 * math.cos(math.radians(-70)), 860 + 330 * math.sin(math.radians(-70)), 34 * ease(seg(t, 0.75, 1.3)), t, 2)
        c = ENSO.paint(c, ease_io(seg(t, 1.0, 2.6)))
    c = put_text(c, TX["instant"], 540, 1340, seg(t, 2.4, 3.2))
    c = put_seal(c, 540, 1520, seg(t, 3.2, 3.5))
    return c

def s_land(t):
    lt = t - 4.0; c = PAPER.copy(); pan = lerp(0, 160, ease_io(seg(lt, 0, 5.5)))
    sun = np.clip((70 - np.hypot(xx - 760, yy - 520 - pan * 0.3)) / 2, 0, 1); c = ink_on(c, sun, np.array(VERMIL, np.float32), 0.85)
    for i, (a, sp) in enumerate(zip(MT, (0.2, 0.45, 0.8))):
        off = int(80 + lt * 12 * sp); sl = a[:, off:off + W]
        sh = int(pan * sp); sl = np.roll(sl, -sh, axis=0) if sh else sl
        if sh: sl[-sh:] = sl[-sh - 1:-sh][0]
        c = ink_on(c, sl, INK, 1.0)
        m = mist(t + i * 7, 0.65, 1 + i * 0.3, i) * np.clip((yy - (860 + i * 260 - pan * sp)) / 300, 0, 1) * np.clip((1250 + i * 260 - pan * sp - yy) / 300, 0, 1)
        c = c * (1 - m[..., None]) + np.array([244, 239, 228]) * m[..., None]
    for k in range(3):
        bx = lerp(-100, W + 100, seg(lt, 0.4 + k * 0.25, 5.4 + k * 0.25)); flap = 0.6 + 0.6 * math.sin(t * 9 + k)
        for st in bird(bx, 420 + k * 50, 34 - k * 6, flap): c = st.paint(c, 1.0)
    c = put_text(c, TX["nuage1"], 540, 260, seg(lt, 0.5, 1.5)); c = put_text(c, TX["nuage2"], 540, 370, seg(lt, 1.1, 2.1))
    return c

def s_bamboo(t):
    lt = t - 9.5; c = PAPER.copy()
    c = c * (1 - 0.25 * mist(t, 1.0, 1.4, 5)[..., None] * 0.4)
    n = len(BAMBOO)
    for i, (kind, k, si, st) in enumerate(BAMBOO):
        t0 = 0.1 + k * 0.25 + si * 0.22 + (0.15 if kind == "leaf" else 0.0); d = 0.35 if kind == "stem" else 0.3
        c = st.paint(c, ease_io(seg(lt, t0, t0 + d)), INK, 0.9 if k != 3 else 0.45)
    c = put_text(c, TX["kumo"], 560, 1520, seg(lt, 1.6, 2.6)); c = put_text(c, TX["cere"], 560, 1660, seg(lt, 2.1, 3.0), INK, 0.8)
    return c

def s_ritual(t):
    lt = t - 14.5; c = PAPER.copy()
    fill = ease(seg(lt, 0.9, 2.0)); lvl = lerp(1360, 1000, fill)
    m = BOWL_MASK * np.clip((yy - lvl) / 8, 0, 1)
    foam = mist(t * 4, 1.0, 6.0, 3)
    green = MATCHA[None, None, :] * (0.85 + 0.25 * foam[..., None]) + np.array([60, 60, 20]) * (yy[..., None] < lvl + 40) * foam[..., None] * 0.6
    c = c * (1 - m[..., None] * 0.95) + green * m[..., None] * 0.95
    for i, st in enumerate(BOWL): c = st.paint(c, ease_io(seg(lt, 0.1 + i * 0.35, 0.9 + i * 0.35)))
    if 1.6 < lt < 3.6:                                         # mouvement du fouet en « M »
        k = (lt * 3) % 1; st = WHISK[int(lt * 3) % 2]; c = st.paint(c, k, np.array([200, 222, 150], np.float32), 0.6)
    for i, st in enumerate(STEAM):
        ph = (lt * 0.5 + i * 0.33) % 1; c = st.paint(c, ease_io(ph * 1.5), INK, 0.35 * math.sin(math.pi * ph))
    for key, y, t0 in (("f1", 330, 0.6), ("f2", 470, 1.4), ("f3", 610, 2.2)):
        c = put_text(c, TX[key], 540, y, seg(lt, t0, t0 + 0.8), MATCHA if key == "f3" else INK)
    return c

def s_tin(t):
    lt = t - 20.0; c = PAPER.copy()
    rv = lerp(690, 1430, ease_io(seg(lt, 0.1, 1.1)))
    c = ink_on(c, TIN_A * np.clip((rv - yy) / 30, 0, 1), INK, 0.95)
    bp = ease(seg(lt, 1.0, 1.5))
    if bp > 0:
        x0, y0, x1, y1 = TIN_BAND; band = np.zeros((H, W), np.float32); band[y0:y1, x0:int(lerp(x0, x1, bp))] = 1
        c = c * (1 - band[..., None]) + MATCHA * band[..., None]
    c = put_text(c, TX["tin"], 540, 1020, seg(lt, 1.4, 2.0), np.array([244, 238, 224], np.float32), 1.0)
    c = put_seal(c, 640, 1380, seg(lt, 1.9, 2.2), SEAL_S)
    c = put_text(c, TX["rec"], 540, 400, seg(lt, 0.5, 1.4))
    return c

def s_end(t):
    lt = t - 23.6; c = PAPER.copy()
    c = ENSO_END.paint(c, ease_io(seg(lt, 0.0, 1.4)))
    c = put_text(c, TX["kumo"], 540, 860, seg(lt, 0.9, 1.8)); c = put_text(c, TX["cere"], 540, 1010, seg(lt, 1.3, 2.0), INK, 0.8)
    c = put_text(c, TX["temps"], 540, 1420, seg(lt, 1.6, 2.4)); c = put_text(c, TX["handle"], 540, 1560, seg(lt, 2.0, 2.6), INK, 0.7)
    c = put_seal(c, 860, 1150, seg(lt, 2.2, 2.5))
    return c

# ------------------------------------------------------------------ transitions encre
def tr_brush(t, fa, fb, t0, t1, brush):
    """Un grand coup de pinceau sec traverse l'écran : la scène suivante apparaît dans la trace."""
    p = seg(t, t0, t1); a = fa(t); b = fb(t)
    m = brush.alpha(ease_io(p) * 1.02, 0.04)
    if m is None: return a
    full = np.zeros((H, W), np.float32); x0, y0, x1, y1 = brush.box; full[y0:y1, x0:x1] = m
    full = np.clip(full * 1.25 + ease_in(seg(p, 0.75, 1.0)), 0, 1)
    out = a * (1 - full[..., None]) + b * full[..., None]
    rim = np.clip(full * (1 - full) * 4, 0, 1) * 0.6
    return ink_on(out, rim, INK, 1.0)

def tr_mist(t, fa, fb, t0, t1):
    p = seg(t, t0, t1); k = math.sin(math.pi * p); base = fa(t) if p < 0.5 else fb(t)
    m = np.clip(mist(t * 3, 1.0, 1.2, 8) * 0.5 + k * 1.1 - 0.2, 0, 1)
    return base * (1 - m[..., None]) + np.array([245, 241, 232]) * m[..., None]

def tr_drop(t, fa, fb, t0, t1):
    """Une goutte d'encre éclot jusqu'à tout recouvrir, puis l'encre se lave et laisse la scène suivante."""
    p = seg(t, t0, t1)
    if p < 0.55:
        return drop_bloom(fa(t), 540, 960, ease_in(p / 0.55) * 1500 + 20, t, 4, 1.0)
    q = ease_io((p - 0.55) / 0.45); b = fb(t)
    dn = np.hypot((xx - 540) / W, (yy - 960) / H) * 1.6
    wash = np.clip((1 - q) * 1.5 - dn * 0.9 + (mist(t, 1.0, 0.7, 11) - 0.5) * 0.35, 0, 1) ** 0.8
    return ink_on(b, wash, INK, 0.97)

def frame(t):
    if t < 3.9: return s_intro(t)
    if t < 4.6: return tr_brush(t, s_intro, s_land, 3.9, 4.6, BRUSH_A)
    if t < 9.1: return s_land(t)
    if t < 9.9: return tr_mist(t, s_land, s_bamboo, 9.1, 9.9)
    if t < 14.2: return s_bamboo(t)
    if t < 15.0: return tr_drop(t, s_bamboo, s_ritual, 14.2, 15.0)
    if t < 19.6: return s_ritual(t)
    if t < 20.3: return tr_brush(t, s_ritual, s_tin, 19.6, 20.3, BRUSH_B)
    if t < 23.2: return s_tin(t)
    if t < 23.9: return tr_mist(t, s_tin, s_end, 23.2, 23.9)
    return s_end(t)

rng_g = np.random.default_rng(0)
GRAIN = [rng_g.normal(0, 2.0, (H // 2, W // 2, 1)).astype(np.float32).repeat(2, 0).repeat(2, 1) for _ in range(4)]
def render(n):
    t = n / FPS; c = frame(t) + GRAIN[n % 4]
    if t < 0.4: c = PAPER * (1 - t / 0.4) + c * (t / 0.4)
    if t > DUR - 0.8: c = c * max(0.0, (DUR - t) / 0.8) + PAPER * (1 - max(0.0, (DUR - t) / 0.8))
    return np.clip(c, 0, 255).astype(np.uint8).tobytes()

TIMES = {"dur": DUR, "drip": 0.75, "enso": [1.0, 2.6], "seal": [3.2, 22.2, 25.8], "brush": [3.9, 19.6], "land": 4.0, "mist": [9.1, 23.2],
         "bamboo": 9.5, "drop": 14.2, "ritual": 14.5, "pour": [15.4, 16.5], "whisk": [16.1, 18.1], "tin": 20.0, "end": 23.6, "ensoend": [23.6, 25.0],
         "texts": [2.4, 4.5, 5.1, 11.1, 15.1, 15.9, 16.7, 20.5, 25.2]}

if __name__ == "__main__":
    wav = OUT.replace(".mp4", ".wav")
    subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "kumo_audio.py"), wav, json.dumps(TIMES)], check=True)
    ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "slow", "-crf", "19",
                           "-maxrate", "8M", "-bufsize", "16M", "-pix_fmt", "yuv420p",
                           "-af", "loudnorm=I=-15:TP=-1:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "256k",
                           "-shortest", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
    sel = [int(float(x) * FPS) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else range(int(DUR * FPS))
    with Pool(4) as pool:
        for i, b in enumerate(pool.imap(render, sel, chunksize=2)):
            ff.stdin.write(b)
            if i % 100 == 0: print(i, flush=True)
    ff.stdin.close(); ff.wait(); os.remove(wav); print("ok", OUT)
