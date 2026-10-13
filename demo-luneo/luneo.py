"""LUNÉO — pub train de nuit (marque fictive), papier découpé façon stop-motion, 9:16, 1080x1920, 30 i/s, 25,5 s.

Usage : python3 luneo.py <dossier_polices> <sortie.mp4> [temps,à,prévisualiser]
"""
import json, math, os, subprocess, sys
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

FONTS, OUT = sys.argv[1], sys.argv[2]
W, H, FPS, STEP = 1080, 1920, 30, 12           # STEP : cadence « image par image »
DUR = 25.5
CREAM = (246, 238, 222); DESK = (232, 218, 192); NAVY = (34, 44, 86); NIGHT = (24, 30, 62); DEEP = (18, 22, 46)
MUST = (240, 182, 58); CORAL = (236, 104, 84); MINT = (118, 198, 168); TEAL = (38, 128, 150); BLUE = (52, 78, 140)
FOREST = (38, 104, 82); PEACH = (250, 204, 164); WHITE = (255, 252, 244); INK = (40, 30, 34)

def font(w, size): return ImageFont.truetype(os.path.join(FONTS, f"fontsource-jost-5.3.0/files/jost-latin-{w}-normal.woff"), size)
def ease(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3
def ease_in(x): x = min(1, max(0, x)); return x ** 3
def ease_io(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
def back(x, s=2.0): x = min(1, max(0, x)) - 1; return x * x * ((s + 1) * x + s) + 1
def lerp(a, b, x): return a + (b - a) * x
def seg(t, a, b): return (t - a) / (b - a)
def step(t): return math.floor(t * STEP) / STEP          # temps « stop-motion »
def boil(t, seed, amp=1.6):                              # frémissement des découpes à chaque pose
    r = np.random.default_rng(int(step(t) * STEP) * 131 + seed); return r.uniform(-amp, amp), r.uniform(-amp, amp)

# ------------------------------------------------------------------ papier
_r = np.random.default_rng(1)
_fib = Image.fromarray(_r.normal(128, 40, (H // 2, W // 2)).clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
_fib2 = Image.fromarray(_r.normal(128, 40, (H // 8, W // 32)).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
TEX = (np.asarray(_fib.resize((W, H), Image.BICUBIC), np.float32) - 128) / 128 * 0.05 + (np.asarray(_fib2, np.float32) - 128) / 128 * 0.03 + 1.0
TEXL = Image.fromarray(((TEX - 0.85) / 0.3 * 255).clip(0, 255).astype(np.uint8))

def jag(pts, seed=0, amp=2.2, step_=14):
    """Densifie un polygone et rend ses bords irréguliers (papier découpé aux ciseaux)."""
    r = np.random.default_rng(seed); out = []
    for i in range(len(pts)):
        (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % len(pts)]
        L = math.hypot(x1 - x0, y1 - y0); n = max(1, int(L / step_)); nx, ny = (-(y1 - y0) / (L + 1e-6), (x1 - x0) / (L + 1e-6))
        for k in range(n):
            u = k / n; j = r.uniform(-amp, amp); out.append((x0 + (x1 - x0) * u + nx * j, y0 + (y1 - y0) * u + ny * j))
    return out

def paper(size, shapes, shadow=(7, 9), blur=7, sh_a=0.32, tex_off=(0, 0)):
    """shapes : liste de (type, données, couleur). Rend une découpe texturée avec ombre portée."""
    w, h = int(size[0]), int(size[1]); s = 2
    big = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0)); d = ImageDraw.Draw(big)
    for kind, data, col in shapes:
        if kind == "poly": d.polygon([(x * s, y * s) for x, y in data], fill=col + (255,))
        elif kind == "ell": x0, y0, x1, y1 = data; d.ellipse((x0 * s, y0 * s, x1 * s, y1 * s), fill=col + (255,))
        elif kind == "rect": x0, y0, x1, y1 = data; d.rectangle((x0 * s, y0 * s, x1 * s, y1 * s), fill=col + (255,))
        elif kind == "rrect": x0, y0, x1, y1, rr = data; d.rounded_rectangle((x0 * s, y0 * s, x1 * s, y1 * s), rr * s, fill=col + (255,))
        elif kind == "img": im, (x, y) = data; big.alpha_composite(im.resize((im.width * s, im.height * s)), (int(x * s), int(y * s)))
    im = big.resize((w, h), Image.LANCZOS)
    a = np.asarray(im, np.float32); ox, oy = tex_off
    tx = TEX[np.arange(h)[:, None] % H, (np.arange(w)[None, :] + ox) % W]
    a[..., :3] *= tx[..., None]
    im = Image.fromarray(a.clip(0, 255).astype(np.uint8))
    if shadow is None: return im
    out = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    sh = im.split()[3].filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * sh_a))
    out.paste(Image.new("RGBA", (w, h), (20, 14, 30, 255)), (20 + shadow[0], 20 + shadow[1]), sh)
    out.alpha_composite(im, (20, 20)); return out

def place(fr, im, x, y, t=None, seed=0, amp=1.6, rot=0.0, scale=1.0, a=1.0):
    """Pose une découpe (coin haut-gauche + 20 px de marge d'ombre) avec frémissement."""
    if im is None or a <= 0: return
    if t is not None: dx, dy = boil(t, seed, amp)
    else: dx = dy = 0
    if scale != 1: im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if abs(rot) > 0.1: im = im.rotate(rot, Image.BICUBIC, expand=True)
    if a < 1:
        r, g, b, al = im.split(); im = Image.merge("RGBA", (r, g, b, al.point(lambda v: int(v * a))))
    fr.alpha_composite(im, (int(x - 20 + dx), int(y - 20 + dy)))

def centered(fr, im, cx, cy, t=None, seed=0, rot=0.0, scale=1.0, a=1.0):
    if im is None: return
    w = im.width * scale; h = im.height * scale
    if abs(rot) > 0.1:
        rr = math.radians(rot); w2 = abs(w * math.cos(rr)) + abs(h * math.sin(rr)); h2 = abs(w * math.sin(rr)) + abs(h * math.cos(rr)); w, h = w2, h2
    place(fr, im, cx - w / 2 + 20, cy - h / 2 + 20, t, seed, 1.6, rot, scale, a)

def bg(color):
    a = np.empty((H, W, 3), np.float32); a[:] = color; a *= TEX[..., None]
    return Image.fromarray(a.clip(0, 255).astype(np.uint8)).convert("RGBA")

# ------------------------------------------------------------------ étiquettes et lettres découpées
def tag(txt, size=64, w="800", fg=NAVY, bgc=WHITE, padx=40, pady=22, seed=3):
    f = font(w, size); tw = int(f.getlength(txt)); asc, desc = f.getmetrics()
    W_, H_ = tw + 2 * padx, asc + desc + 2 * pady
    t = Image.new("RGBA", (W_, H_), (0, 0, 0, 0)); ImageDraw.Draw(t).text((padx, pady), txt, font=f, fill=fg + (255,))
    return paper((W_, H_), [("poly", jag([(0, 0), (W_, 0), (W_, H_), (0, H_)], seed, 2.5), bgc), ("img", (t, (0, 0)), None)], (5, 7), 5)

def cut_letters(txt, size, colors, w="900", seed=5):
    """Chaque lettre découpée dans du papier de couleur, avec un bord blanc."""
    f = font(w, size); out = []
    for i, ch in enumerate(txt):
        if ch == " ": out.append(None); continue
        bw = int(f.getlength(ch)) + 50; asc, desc = f.getmetrics(); bh = asc + desc + 30
        m = Image.new("L", (bw, bh), 0); ImageDraw.Draw(m).text((25, 10), ch, font=f, fill=255)
        rim = m.filter(ImageFilter.MaxFilter(17)).filter(ImageFilter.GaussianBlur(1)).point(lambda v: 255 if v > 90 else 0)
        col = colors[i % len(colors)]
        base = Image.new("RGBA", (bw, bh), (0, 0, 0, 0)); base.paste(Image.new("RGBA", (bw, bh), WHITE + (255,)), (0, 0), rim)
        base.paste(Image.new("RGBA", (bw, bh), col + (255,)), (0, 0), m)
        out.append(paper((bw, bh), [("img", (base, (0, 0)), None)], (6, 8), 6))
    return out

def draw_letters(fr, letters, cx, cy, t, t0, gap=0.07, spacing=0.78, seed=40):
    ws = [(l.width - 40) * spacing if l is not None else 40 for l in letters]; x = cx - sum(ws) / 2
    for i, l in enumerate(letters):
        if l is not None:
            p = seg(step(t), t0 + i * gap, t0 + i * gap + 0.25)
            if p > 0:
                r = np.random.default_rng(seed + i).uniform(-7, 7)
                centered(fr, l, x + ws[i] / 2, cy + (1 - back(p)) * 40, t, seed + i, r, back(p) * 1.0)
        x += ws[i]

# ------------------------------------------------------------------ éléments
def star(cx, cy, r): return [(cx + (r if k % 2 == 0 else r * 0.45) * math.cos(-math.pi / 2 + k * math.pi / 5), cy + (r if k % 2 == 0 else r * 0.45) * math.sin(-math.pi / 2 + k * math.pi / 5)) for k in range(10)]
STAR = paper((60, 60), [("poly", star(30, 30, 26), MUST)], (3, 4), 3, 0.25)
rs = np.random.default_rng(9); STARS = [(rs.uniform(40, W - 40), rs.uniform(150, 900), rs.uniform(0.4, 1.0), i) for i in range(26)]
def stars(fr, t, a=1.0):
    for x, y, s, i in STARS:
        tw = 0.75 + 0.25 * math.sin(step(t) * 3 + i)
        centered(fr, STAR, x, y, t, 300 + i, i * 13, s * tw, a)

def moon(r=150):
    s = 2 * r + 20; sh = [("ell", (10, 10, s - 10, s - 10), CREAM)]
    for cx, cy, cr in ((0.35, 0.4, 0.13), (0.62, 0.62, 0.09), (0.6, 0.3, 0.06)):
        sh.append(("ell", (s * cx - s * cr, s * cy - s * cr, s * cx + s * cr, s * cy + s * cr), (226, 216, 196)))
    return paper((s, s), sh, (8, 10), 10, 0.35)
MOON = moon()

def ridge(seed, y0, amp, n, width, peaks=False, snow=None):
    r = np.random.default_rng(seed); xs = np.linspace(0, width, n); pts = [(0, H)]
    ys = []
    for i, x in enumerate(xs):
        y = y0 - (r.uniform(0.3, 1.0) * amp if (i % 2 == 1 or not peaks) else r.uniform(0, 0.25) * amp); ys.append(y); pts.append((x, y))
    pts.append((width, H)); return pts, list(zip(xs, ys))
def mountains(seed, y0, amp, width, col, snow=True):
    pts, top = ridge(seed, y0, amp, 9, width, True)
    shapes = [("poly", jag(pts, seed, 2.5, 18), col)]
    if snow:
        for i in range(1, len(top) - 1, 2):
            x, y = top[i]; xl, yl = top[i - 1]; xr, yr = top[i + 1]; k = 0.28
            shapes.append(("poly", jag([(x, y), (lerp(x, xr, k), lerp(y, yr, k)), (lerp(x, xr, k * .6), lerp(y, yr, k) + 10), (x, lerp(y, yr, k * .5) + 14),
                                        (lerp(x, xl, k * .6), lerp(y, yl, k) + 8), (lerp(x, xl, k), lerp(y, yl, k))], seed + i, 1.6, 10), CREAM))
    return paper((width, H), shapes, (6, 8), 8, 0.35)

def buildings(seed, base, hmin, hmax, width, col, win=None):
    r = np.random.default_rng(seed); x = 0; shapes = []; wins = []
    while x < width:
        bw = r.uniform(90, 190); bh = r.uniform(hmin, hmax); y = base - bh
        shapes.append(("poly", jag([(x, y), (x + bw, y), (x + bw, H), (x, H)], seed + int(x), 1.8, 16), col))
        if r.random() < 0.4: shapes.append(("poly", jag([(x + bw * .2, y), (x + bw * .5, y - 50), (x + bw * .8, y)], int(x), 1.2, 10), col))
        if win:
            for wy in np.arange(y + 30, base - 20, 46):
                for wx in np.arange(x + 18, x + bw - 30, 36):
                    if r.random() < 0.35: wins.append(("rect", (wx, wy, wx + 16, wy + 24), win))
        x += bw - 4
    return paper((width, H), shapes + wins, (6, 8), 7, 0.4)

def tower():
    w, h = 300, 900; cx = w / 2; sh = []
    sh.append(("poly", jag([(cx - 8, 0), (cx + 8, 0), (cx + 60, 380), (cx + 140, h), (cx + 80, h), (cx, 600), (cx - 80, h), (cx - 140, h), (cx - 60, 380)], 77, 1.4, 12), DEEP))
    sh.append(("rect", (cx - 76, 380, cx + 76, 400), DEEP)); sh.append(("rect", (cx - 116, 640, cx + 116, 662), DEEP))
    sh.append(("ell", (cx - 6, 140, cx + 6, 152), MUST))
    return paper((w, h), sh, (6, 8), 6, 0.35)
TOWER = tower()

def train(cars=4, body=CORAL, roof=WHITE, seed=11):
    cw, ch = 380, 150; w = cars * (cw + 18) + 220; h = ch + 70; sh = []
    # locomotive arrondie
    sh.append(("poly", jag([(0, 30), (120, 10), (220, 10), (220, ch + 20), (0, ch + 20)], seed, 1.5, 12), body))
    sh.append(("poly", jag([(20, 40), (110, 26), (110, 80), (20, 84)], seed + 1, 1, 8), MUST))
    sh.append(("rect", (0, ch - 6, 220, ch + 4), roof))
    for k in range(cars):
        x = 236 + k * (cw + 18)
        sh.append(("rrect", (x, 14, x + cw, ch + 20, 16), body)); sh.append(("rect", (x, 14, x + cw, 34), roof))
        for j in range(4): sh.append(("rect", (x + 26 + j * 88, 56, x + 86 + j * 88, 100), MUST))
        sh.append(("rect", (x, ch - 6, x + cw, ch + 4), roof))
    for k in range(cars * 2 + 2):
        x = 60 + k * ((w - 120) / (cars * 2 + 1)); sh.append(("ell", (x - 22, ch + 8, x + 22, ch + 52), INK))
    return paper((w, h), sh, (6, 9), 7, 0.4)
TRAIN = train(); TRAIN_S = train(3)

def wave_layer(seed, y0, amp, col, width=W + 200):
    pts = [(0, H)] + [(x, y0 + amp * math.sin(x / 70 + seed) + amp * 0.5 * math.sin(x / 29 + seed * 2)) for x in np.linspace(0, width, 60)] + [(width, H)]
    return paper((width, H - y0 + 120), [("poly", [(x, y - y0 + 100) for x, y in jag(pts, seed, 1.5, 20)], col)], (5, 7), 7, 0.35)

def cloud(seed, w=360):
    r = np.random.default_rng(seed); sh = []
    for k in range(5):
        cx = 60 + k * (w - 120) / 4; rr = r.uniform(50, 90); sh.append(("ell", (cx - rr, 110 - rr * (0.9 if k % 2 else 1.2), cx + rr, 110 + rr * 0.6), WHITE))
    sh.append(("rect", (40, 110, w - 40, 160), WHITE)); return paper((w, 200), sh, (5, 7), 6, 0.25)
CLOUDS = [cloud(i, 300 + i * 40) for i in range(3)]
def gull():
    return paper((90, 40), [("poly", jag([(0, 18), (22, 4), (45, 22), (68, 4), (90, 18), (68, 12), (45, 32), (22, 12)], 2, 0.8, 8), INK)], (3, 4), 3, 0.2)
GULL = gull()

def ticket():
    w, h = 900, 440; sh = [("poly", jag([(0, 0), (w, 0), (w, h), (0, h)], 21, 2.5), NAVY)]
    for y in range(30, h, 52): sh.append(("ell", (-14, y - 12, 14, y + 12), DESK))
    sh.append(("rect", (650, 30, 654, h - 30), (70, 84, 140)))
    im = paper((w, h), sh, (8, 10), 9, 0.35)
    for txt, wt, sz, col, x, y in (("BILLET DE NUIT", "600", 34, MUST, 70, 50), ("PARIS", "900", 120, WHITE, 66, 110), ("?", "900", 120, CORAL, 300, 240),
                                   ("DÉPART", "500", 28, (170, 180, 220), 690, 70), ("21:30", "800", 64, WHITE, 690, 104), ("VOIT. 7", "500", 28, (170, 180, 220), 690, 250),
                                   ("COUCH. 42", "800", 36, WHITE, 690, 288)):
        ImageDraw.Draw(im).text((x + 20, y + 20), txt, font=font(wt, sz), fill=col + (255,))
    d = ImageDraw.Draw(im); ax, ay = 110, 340
    d.polygon([(ax, ay - 12), (ax + 150, ay - 12), (ax + 150, ay - 36), (ax + 200, ay), (ax + 150, ay + 36), (ax + 150, ay + 12), (ax, ay + 12)], fill=CORAL + (255,))
    return im
TICKET = ticket()
def stamp():
    s = 340; m = Image.new("L", (s, s), 0); d = ImageDraw.Draw(m)
    d.ellipse((10, 10, s - 10, s - 10), outline=255, width=14); d.ellipse((40, 40, s - 40, s - 40), outline=255, width=5)
    f = font("900", 66); tw = f.getlength("CE SOIR"); d.text(((s - tw) / 2, 128), "CE SOIR", font=f, fill=255)
    noise = Image.fromarray((np.random.default_rng(4).random((s, s)) > 0.18).astype(np.uint8) * 255)
    m = ImageChops.multiply(m, noise).filter(ImageFilter.GaussianBlur(0.7))
    im = Image.new("RGBA", (s, s), CORAL + (0,)); im.putalpha(m.point(lambda v: int(v * 0.9))); return im
STAMP = stamp()

# ------------------------------------------------------------------ textes
L_HOOK1 = cut_letters("Et si tu", 120, [CORAL, MUST, MINT, NAVY], seed=1)
L_HOOK2 = cut_letters("partais ?", 150, [NAVY, CORAL, MUST, MINT], seed=2)
TG_CITY = tag("Ce soir, 21:30.", 70); TG_DEP = tag("QUAI 7 · DÉPART", 34, "700", WHITE, CORAL, seed=8)
TG_MT1 = tag("Tu t'endors à Paris…", 66)
TG_SEA = tag("…tu te réveilles", 66, seed=4); TG_SEA2 = tag("face à la mer.", 76, "900", WHITE, TEAL, seed=6)
TG_MAP = tag("12 destinations", 76); TG_CAB = tag("Draps frais.", 70); TG_CAB2 = tag("Café au réveil.", 70, "800", WHITE, CORAL, seed=9)
L_LOGO = cut_letters("Lunéo", 230, [MUST, CORAL, MINT, (110, 150, 226), MUST], seed=7)
TG_END = tag("Le train de nuit, réinventé.", 50, "600"); TG_CTA = tag("RÉSERVER MA NUIT", 46, "800", WHITE, CORAL, seed=12)
TG_HANDLE = tag("@luneo.train", 40, "600", WHITE, NAVY, seed=13)
def price_sticker():
    s = 280; sh = [("poly", jag([(s / 2 + (130 if k % 2 == 0 else 112) * math.cos(k * math.pi / 14), s / 2 + (130 if k % 2 == 0 else 112) * math.sin(k * math.pi / 14)) for k in range(28)], 3, 1.2, 10), MUST)]
    im = paper((s, s), sh, (6, 8), 6)
    d = ImageDraw.Draw(im); f1, f2 = font("600", 38), font("900", 92)
    d.text((s / 2 + 20 - f1.getlength("dès") / 2, 70), "dès", font=f1, fill=NAVY + (255,)); d.text((s / 2 + 20 - f2.getlength("39 €") / 2, 110), "39 €", font=f2, fill=NAVY + (255,))
    return im
PRICE = price_sticker()

# ------------------------------------------------------------------ couches pré-rendues
CITY_FAR = buildings(31, 1250, 200, 420, W + 400, (42, 56, 108), (90, 104, 160))
CITY_MID = buildings(32, 1380, 160, 360, W + 400, (30, 38, 80), MUST)
PLATFORM = paper((W + 200, 520), [("poly", jag([(0, 60), (W + 200, 60), (W + 200, 520), (0, 520)], 33, 2), (26, 24, 40)), ("rect", (0, 40, W + 200, 66), CORAL)], (0, -8), 8, 0.4)
MT_FAR = mountains(41, 1050, 420, W + 500, (58, 80, 146), True)
MT_MID = mountains(42, 1280, 380, W + 500, (40, 58, 116), True)
MT_NEAR = paper((W + 300, 700), [("poly", jag([(0, 300), (W + 300, 240), (W + 300, 700), (0, 700)], 43, 3, 20), (22, 40, 70))], (6, 8), 8, 0.4)
def bridge():
    w, h = W + 300, 300; sh = [("rect", (0, 0, w, 34), (120, 70, 60))]
    for k in range(7):
        x = k * (w / 6.5); sh.append(("poly", jag([(x, 34), (x + 120, 34), (x + 100, h), (x + 20, h)], 60 + k, 1.4, 12), (120, 70, 60)))
    return paper((w, h), sh, (6, 8), 6, 0.35)
BRIDGE = bridge()
SEA = [wave_layer(1, 1250, 22, (90, 170, 190)), wave_layer(2, 1400, 26, TEAL), wave_layer(3, 1560, 30, (28, 96, 124))]
CLIFF = paper((W + 300, 500), [("poly", jag([(0, 120), (W * 0.5, 90), (W + 300, 150), (W + 300, 500), (0, 500)], 51, 3, 18), (196, 130, 86)), ("rect", (0, 100, W + 300, 120), (120, 160, 90))], (6, 8), 8, 0.35)
SUN = paper((300, 300), [("ell", (10, 10, 290, 290), MUST)], (6, 8), 10, 0.25)

def land_map():
    sh = [("poly", jag([(60, 260), (430, 180), (700, 300), (900, 260), (1000, 600), (880, 1000), (980, 1300), (700, 1500), (420, 1380), (300, 1100), (120, 1000), (40, 640)], 71, 4, 22), MINT)]
    sh.append(("poly", jag([(560, 1080), (700, 1050), (760, 1240), (640, 1320)], 72, 3, 14), (150, 210, 180)))
    return paper((W, 1600), sh, (6, 8), 8, 0.3)
MAP = land_map()
def pin(col=CORAL):
    sh = [("poly", jag([(50, 140)] + [(50 + 46 * math.cos(a), 50 + 46 * math.sin(a)) for a in np.linspace(math.pi * 0.85, math.pi * 2.15, 20)], 5, 1, 8), col), ("ell", (32, 32, 68, 68), WHITE)]
    return paper((100, 150), sh, (5, 7), 5)
PIN = pin(); PIN_HOME = pin(NAVY)
DEST = [("Nice", (720, 1180)), ("Vienne", (880, 560)), ("Rome", (820, 1420)), ("Barcelone", (300, 1300))]
HOME = (430, 560)
DEST_TAGS = [tag(n, 44, "800", NAVY, WHITE, 26, 14, seed=20 + i) for i, (n, _) in enumerate(DEST)]
HOME_TAG = tag("Paris", 44, "800", WHITE, NAVY, 26, 14, seed=30)

def cabin_layers():
    wall = paper((W, H), [("rect", (0, 0, W, H), (250, 214, 150)), ("rect", (0, 1180, W, H), (214, 120, 84))], None)
    win = [("rrect", (150, 300, 930, 900, 70), (120, 80, 60))]
    frame = paper((W, 1000), win, (8, 10), 10, 0.4)
    hole = Image.new("L", frame.size, 255); ImageDraw.Draw(hole).rounded_rectangle((210, 360, 910, 880), 50, fill=0)
    frame.putalpha(ImageChops.multiply(frame.split()[3], hole))
    bunk = paper((W + 40, 700), [("rrect", (-20, 80, W + 20, 380, 30), WHITE), ("rrect", (60, 40, 420, 180, 50), (236, 236, 246)),
                                ("rect", (-20, 360, W + 20, 700), (120, 80, 60)), ("rrect", (-20, 200, W + 20, 400, 20), (110, 150, 210))], (6, 8), 8, 0.35)
    cup = paper((220, 220), [("rrect", (30, 70, 170, 210, 26), WHITE), ("ell", (150, 100, 210, 170), WHITE), ("ell", (165, 115, 195, 155), (250, 214, 150)), ("rect", (44, 70, 156, 90), (120, 70, 40))], (5, 7), 6)
    return wall, frame, bunk, cup
WALL, WFRAME, BUNK, CUP = cabin_layers()
WIN_MASK = Image.new("L", (W, H), 0); ImageDraw.Draw(WIN_MASK).rounded_rectangle((190, 340, 890, 860), 50, fill=255)

# ------------------------------------------------------------------ scènes
def scene_ticket(t):
    fr = bg(DESK); ts = step(t)
    p = ease(seg(ts, 0.2, 0.75))
    centered(fr, TICKET, lerp(-500, W / 2, p), 1180, t, 1, lerp(-14, -3, p))
    sp = seg(ts, 1.15, 1.35)
    if sp > 0:
        sc = 1.6 - 0.6 * back(sp, 3.0); sx, sy = (np.random.default_rng(int(ts * 12)).uniform(-6, 6, 2) if sp < 1.4 else (0, 0))
        st = STAMP.resize((int(STAMP.width * sc), int(STAMP.height * sc))).rotate(-14, Image.BICUBIC, expand=True)
        fr.alpha_composite(st, (int(W / 2 + 150 - st.width / 2 + sx), int(1280 - st.height / 2 + sy)))
    draw_letters(fr, L_HOOK1, W / 2, 470, t, 1.5, 0.06)
    draw_letters(fr, L_HOOK2, W / 2, 660, t, 1.95, 0.06)
    return fr

def scene_city(t):
    fr = bg(NIGHT); ts = step(t); lt = ts - 3.6; cam = lt * 20
    stars(fr, t)
    centered(fr, MOON, 760, lerp(1100, 470, ease(seg(lt, 0, 2.5))), t, 2)
    place(fr, CITY_FAR, -100 - cam * 0.4, 0, t, 3); place(fr, TOWER, 260 - cam * 0.6, 1380 - TOWER.height + 20, t, 4)
    place(fr, CITY_MID, -150 - cam * 0.7, 0, t, 5)
    tx = lerp(W + 100, -260, ease(seg(lt, 0.4, 2.6)))
    place(fr, TRAIN, tx, 1300, t, 6, 1.2)
    place(fr, PLATFORM, -60 - cam, 1440, t, 7)
    centered(fr, TG_CITY, W / 2, 300, t, 8, -3, back(seg(lt, 0.3, 0.6)))
    centered(fr, TG_DEP, 260, 1580, t, 9, 4, back(seg(lt, 1.6, 1.9)))
    return fr

def scene_mount(t):
    fr = bg((30, 40, 92)); ts = step(t); lt = ts - 7.6; cam = lt * 40
    stars(fr, t, 0.9); centered(fr, MOON, 300, 420, t, 10, 0, 0.7)
    place(fr, MT_FAR, -200 - cam * 0.3, 0, t, 11); place(fr, MT_MID, -250 - cam * 0.55, 0, t, 12)
    place(fr, BRIDGE, -150 - cam * 0.8, 1380, t, 13)
    place(fr, TRAIN_S, lerp(-1300, W + 200, seg(lt, 0.2, 3.6)), 1236, t, 14, 1.0)
    place(fr, MT_NEAR, -150 - cam * 1.1, 1480, t, 15)
    centered(fr, TG_MT1, W / 2, 330, t, 16, -2, back(seg(lt, 0.4, 0.7)))
    return fr

def scene_sea(t):
    fr = bg(PEACH); ts = step(t); lt = ts - 11.7
    centered(fr, SUN, 560, lerp(1300, 760, ease(seg(lt, 0, 2.6))), t, 20)
    for i, c in enumerate(CLOUDS): place(fr, c, (i * 420 + lt * 30 * (i + 1)) % (W + 400) - 300, 380 + i * 130, t, 21 + i)
    for i in range(4):
        x = (lt * 120 + i * 260) % (W + 300) - 150; y = 640 + i * 60 + 20 * math.sin(lt * 4 + i)
        centered(fr, GULL, x, y, t, 25 + i, 0, 0.8 if step(t * 2) % 0.5 < 0.25 else 0.7)
    place(fr, CLIFF, -150, 1060, t, 30)
    place(fr, TRAIN_S, lerp(W + 100, -1500, seg(lt, 0.2, 3.6)), 1005, t, 31, 1.0)
    for i, layer in enumerate(SEA):
        bob = 14 * math.sin(lt * 2.4 + i * 1.3); place(fr, layer, -100 + 40 * math.sin(lt + i), [1250, 1400, 1560][i] - 100 + bob, t, 32 + i)
    centered(fr, TG_SEA, W / 2, 260, t, 36, 2, back(seg(lt, 0.3, 0.6)))
    centered(fr, TG_SEA2, W / 2 + 40, 390, t, 37, -3, back(seg(lt, 0.7, 1.0)))
    return fr

def scene_map(t):
    fr = bg(CREAM); ts = step(t); lt = ts - 15.5
    sea = bg((170, 214, 226)); fr = sea
    place(fr, MAP, 0, 180, t, 40)
    dots = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(dots)
    for i, (n, (x, y)) in enumerate(DEST):
        p = ease_io(seg(lt, 0.4 + i * 0.35, 1.1 + i * 0.35))
        if p <= 0: continue
        hx, hy = HOME; cx_, cy_ = (hx + x) / 2 + (y - hy) * 0.18, (hy + y) / 2 - (x - hx) * 0.18
        for k in range(int(28 * p)):
            u = k / 28; px = (1 - u) ** 2 * hx + 2 * (1 - u) * u * cx_ + u * u * x; py = (1 - u) ** 2 * hy + 2 * (1 - u) * u * cy_ + u * u * y
            d.ellipse((px - 6, py - 6, px + 6, py + 6), fill=NAVY + (255,))
    fr.alpha_composite(dots)
    centered(fr, PIN_HOME, HOME[0], HOME[1] - 60, t, 41, 0, back(seg(lt, 0.1, 0.35)))
    centered(fr, HOME_TAG, HOME[0], HOME[1] + 40, t, 42, -3, back(seg(lt, 0.2, 0.45)))
    for i, (n, (x, y)) in enumerate(DEST):
        b = back(seg(lt, 1.05 + i * 0.35, 1.3 + i * 0.35))
        if b > 0:
            centered(fr, PIN, x, y - 60 * b, t, 43 + i, 0, b)
            centered(fr, DEST_TAGS[i], x, y + 40, t, 50 + i, (-1) ** i * 4, b)
    centered(fr, TG_MAP, W / 2, 260, t, 55, -2, back(seg(lt, 0.2, 0.5)))
    centered(fr, PRICE, 860, 1640, t, 56, 12, back(seg(lt, 2.3, 2.6)))
    return fr

def scene_cabin(t):
    ts = step(t); lt = ts - 19.4; fr = WALL.copy()
    view = bg((40, 60, 120)); cam = lt * 420
    place(view, MT_FAR, -((cam * 0.5) % 600) - 200, -250, t, 60); place(view, MT_MID, -((cam * 0.9) % 600) - 250, -320, t, 61)
    centered(view, MOON, 700, 520, t, 62, 0, 0.5)
    fr.paste(view, (0, 0), WIN_MASK)
    place(fr, WFRAME, 0, 0, t, 63)
    place(fr, BUNK, -20, 1150, t, 64)
    centered(fr, CUP, 820, 1080, t, 65)
    for k in range(3):                                     # vapeur en volutes de papier
        y = 980 - ((lt * 60 + k * 40) % 120); centered(fr, paper((60, 90), [("poly", jag([(30, 0), (50, 30), (30, 60), (40, 90), (20, 90), (10, 60), (30, 30), (10, 0)], k, 1, 8), WHITE)], None), 800 + k * 18, y, t, 70 + k, k * 10, 0.6, 0.7)
    centered(fr, TG_CAB, W / 2 - 60, 1000, t, 66, -3, back(seg(lt, 0.3, 0.6)))
    centered(fr, TG_CAB2, W / 2 + 40, 1120, t, 67, 3, back(seg(lt, 0.7, 1.0)))
    return fr

def scene_end(t):
    fr = bg(NIGHT); ts = step(t); lt = ts - 22.6
    stars(fr, t); centered(fr, MOON, 820, 420, t, 80, 0, 0.8)
    draw_letters(fr, L_LOGO, W / 2, 860, t, 22.75, 0.08, 0.94, 90)
    centered(fr, TG_END, W / 2, 1110, t, 81, -2, back(seg(lt, 0.7, 1.0)))
    centered(fr, TG_CTA, W / 2, 1300, t, 82, 2, back(seg(lt, 1.1, 1.4)))
    centered(fr, TG_HANDLE, W / 2, 1450, t, 83, -2, back(seg(lt, 1.4, 1.7)))
    place(fr, TRAIN_S, lerp(W + 50, -1600, seg(lt, 0.3, 2.9)), 1580, t, 84, 1.0)
    return fr

# ------------------------------------------------------------------ transitions papier
def tear_line(seed, n=40, vertical=True):
    r = np.random.default_rng(seed); pts = []; x = 0
    for k in range(n + 1):
        x += r.uniform(-28, 28); x = max(-120, min(120, x)); pts.append((x, k / n))
    return pts
TEAR = tear_line(5)
def tr_tear(t, a, b, t0, t1, seed=5):
    """Papier déchiré : la moitié gauche de A se détache, la droite part dans l'autre sens."""
    p = ease_in(seg(step(t), t0, t1)); fr = b.copy()
    line = [(W / 2 + x, y * H) for x, y in TEAR]
    for side in (-1, 1):
        poly = ([(-50, -50)] + line + [(-50, H + 50)]) if side < 0 else ([(W + 50, -50)] + line + [(W + 50, H + 50)])
        m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).polygon(poly, fill=255)
        rim = m.filter(ImageFilter.MaxFilter(13)); fib = ImageChops.multiply(ImageChops.subtract(rim, m), TEXL)
        piece = Image.new("RGBA", (W, H), (0, 0, 0, 0)); piece.paste(Image.new("RGBA", (W, H), WHITE + (255,)), (0, 0), rim); piece.paste(a, (0, 0), m)
        piece.putalpha(ImageChops.lighter(m, fib.point(lambda v: 255 if v > 40 else 0)))
        dx = side * p * W * 0.85; rot = side * p * 9
        pc = piece.rotate(rot, Image.BICUBIC, center=(W / 2, H)) if rot else piece
        sh = pc.split()[3].filter(ImageFilter.GaussianBlur(12)).point(lambda v: v // 3)
        fr.paste(Image.new("RGBA", (W, H), (20, 14, 30, 255)), (int(dx + 12), 16), sh)
        fr.alpha_composite(pc, (int(dx), int(p * 60)))
    return fr

def tr_page(t, a, b, t0, t1):
    """Page tournée : A pivote sur sa gauche comme une page de livre, B est dessous."""
    p = ease_io(seg(step(t), t0, t1)); fr = b.copy(); ang = p * math.pi
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    grad = np.clip(1 - np.arange(W) / (W * (0.2 + 0.8 * (1 - p))), 0, 1) * 120 * math.sin(ang)
    sh.putalpha(Image.fromarray(np.repeat(grad[None, :], H, 0).astype(np.uint8))); fr.alpha_composite(sh)
    w = int(abs(math.cos(ang)) * W)
    if w > 4:
        if ang < math.pi / 2:
            pg = a.resize((w, H), Image.BICUBIC)
            shade = int(150 * (1 - math.cos(ang))); pg = Image.blend(pg, Image.new("RGBA", (w, H), (20, 14, 30, 255)), shade / 400)
            fr.alpha_composite(pg, (0, 0))
    return fr

def tr_fold(t, a, b, t0, t1):
    """Pliage en accordéon : le haut de A se replie, puis le bas de B se déplie."""
    p = ease_io(seg(step(t), t0, t1)); fr = Image.new("RGBA", (W, H), DEEP + (255,)); m = H // 2
    if p < 0.5:
        q = p / 0.5; fr.paste(b.crop((0, 0, W, m)), (0, 0)); fr.paste(a.crop((0, m, W, H)), (0, m))
        h = int(m * math.cos(q * math.pi / 2))
        if h > 2:
            flap = a.crop((0, 0, W, m)).resize((W, h), Image.BICUBIC); flap = Image.blend(flap, Image.new("RGBA", flap.size, (20, 14, 30, 255)), q * 0.55)
            fr.alpha_composite(flap, (0, m - h))
    else:
        q = (p - 0.5) / 0.5; fr.paste(b.crop((0, 0, W, m)), (0, 0)); fr.paste(a.crop((0, m, W, H)), (0, m))
        h = int(m * math.sin(q * math.pi / 2))
        if h > 2:
            flap = b.crop((0, m, W, H)).resize((W, h), Image.BICUBIC); flap = Image.blend(flap, Image.new("RGBA", flap.size, (20, 14, 30, 255)), (1 - q) * 0.55)
            fr.alpha_composite(flap, (0, m))
    d = ImageDraw.Draw(fr); d.line((0, m, W, m), fill=(255, 255, 255, int(120 * math.sin(p * math.pi))), width=3)
    return fr

def tr_strips(t, a, b, t0, t1, n=5):
    p = seg(step(t), t0, t1); fr = b.copy(); sh_ = H // n
    for i in range(n):
        q = ease_in(seg(p, i * 0.08, 0.6 + i * 0.08)); dx = (1 if i % 2 else -1) * q * (W + 100)
        strip = a.crop((0, i * sh_, W, (i + 1) * sh_ + 2))
        m = Image.new("L", strip.size, 255); s2 = Image.new("RGBA", (W + 40, strip.height + 40), (0, 0, 0, 0))
        s2.paste(Image.new("RGBA", strip.size, (20, 14, 30, 255)), (26, 30), m.point(lambda v: 90)); s2 = s2.filter(ImageFilter.GaussianBlur(8))
        fr.alpha_composite(s2, (int(dx - 20), i * sh_ - 20)); fr.alpha_composite(strip, (int(dx), i * sh_))
    return fr

def tr_circle(t, a, b, t0, t1, cx=W / 2, cy=H / 2):
    p = ease_io(seg(step(t), t0, t1)); r = p * 1250; fr = a.copy()
    pts = [(cx + (r + np.random.default_rng(k).uniform(-6, 6)) * math.cos(k * 2 * math.pi / 90), cy + (r + np.random.default_rng(k + 99).uniform(-6, 6)) * math.sin(k * 2 * math.pi / 90)) for k in range(90)]
    m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).polygon(pts, fill=255)
    rim = m.filter(ImageFilter.MaxFilter(15))
    fr.paste(Image.new("RGBA", (W, H), (20, 14, 30, 255)), (8, 10), rim.filter(ImageFilter.GaussianBlur(10)).point(lambda v: v // 3))
    fr.paste(Image.new("RGBA", (W, H), WHITE + (255,)), (0, 0), rim); fr.paste(b, (0, 0), m)
    return fr

# ------------------------------------------------------------------ montage
def frame(t):
    if t < 3.0: return scene_ticket(t)
    if t < 3.8: return tr_tear(t, scene_ticket(t), scene_city(t), 3.0, 3.8)
    if t < 7.0: return scene_city(t)
    if t < 7.8: return tr_page(t, scene_city(t), scene_mount(t), 7.0, 7.8)
    if t < 11.0: return scene_mount(t)
    if t < 11.9: return tr_fold(t, scene_mount(t), scene_sea(t), 11.0, 11.9)
    if t < 15.0: return scene_sea(t)
    if t < 15.7: return tr_strips(t, scene_sea(t), scene_map(t), 15.0, 15.7)
    if t < 18.8: return scene_map(t)
    if t < 19.6: return tr_circle(t, scene_map(t), scene_cabin(t), 18.8, 19.6, 540, 600)
    if t < 22.0: return scene_cabin(t)
    if t < 22.8: return tr_tear(t, scene_cabin(t), scene_end(t), 22.0, 22.8)
    return scene_end(t)

def render(n):
    t = n / FPS
    img = frame(t).convert("RGB")
    a = np.asarray(img, np.float32)
    # léger vignettage et lumière chaude « table de tournage »
    a *= VIG[..., None]
    if t < 0.3: a *= t / 0.3
    if t > DUR - 0.4: a *= max(0, (DUR - t) / 0.4)
    return a.clip(0, 255).astype(np.uint8).tobytes()
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = np.clip(1.06 - (((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2) * 0.55, 0.72, 1.06)

TIMES = {"dur": DUR, "ticket": 0.2, "stamp": 1.2, "letters": [1.5 + i * 0.06 for i in range(8)] + [1.95 + i * 0.06 for i in range(9)],
         "tears": [3.0, 22.0], "train": [4.0, 7.8, 11.9, 22.9], "horn": [4.4, 23.4], "page": 7.0, "fold": 11.0, "sea": [11.7, 15.0],
         "strips": 15.0, "pins": [15.6, 15.7, 16.55, 16.9, 17.25, 17.6], "dots": [15.9, 18.0], "price": 17.8, "circle": 18.8,
         "cabin": [19.4, 22.0], "tags": [3.9, 5.2, 8.0, 12.0, 12.4, 15.7, 19.7, 20.1, 23.3, 23.7, 24.0], "logo": [22.75 + i * 0.08 for i in range(5)]}

if __name__ == "__main__":
    wav = OUT.replace(".mp4", ".wav")
    subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "luneo_audio.py"), wav, json.dumps(TIMES)], check=True)
    ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "slow", "-crf", "19",
                           "-maxrate", "8M", "-bufsize", "16M", "-pix_fmt", "yuv420p",
                           "-af", "loudnorm=I=-14:TP=-1:LRA=10", "-ar", "48000", "-c:a", "aac", "-b:a", "256k",
                           "-shortest", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
    sel = [int(float(x) * FPS) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else range(int(DUR * FPS))
    with Pool(4) as pool:
        for i, b in enumerate(pool.imap(render, sel, chunksize=2)):
            ff.stdin.write(b)
            if i % 100 == 0: print(i, flush=True)
    ff.stdin.close(); ff.wait(); os.remove(wav); print("ok", OUT)
