"""ARCADIUM 84 — pub bar d'arcade (marque fictive), synthwave / VHS années 80, 9:16, 1080x1920, 30 i/s, 24,5 s.

Usage : python3 arcadium.py <dossier_polices> <sortie.mp4> [temps,à,prévisualiser]
"""
import json, math, os, subprocess, sys
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

FONTS, OUT = sys.argv[1], sys.argv[2]
W, H, FPS = 1080, 1920, 30
DUR = 24.5
HOR = 1120                                   # ligne d'horizon
PINK = (255, 46, 170); CYAN = (40, 230, 255); PURPLE = (120, 40, 220); YEL = (255, 214, 70); WHITE = (255, 255, 255)

def font(w, size): return ImageFont.truetype(os.path.join(FONTS, f"fontsource-jost-5.3.0/files/jost-latin-{w}-normal.woff"), size)
def cfont(w, size, it=True): return ImageFont.truetype(os.path.join(FONTS, f"fontsource-cormorant-garamond-5.3.0/files/cormorant-garamond-latin-{w}-{'italic' if it else 'normal'}.woff"), size)
def ease(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3
def ease_in(x): x = min(1, max(0, x)); return x ** 3
def ease_io(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
def back(x, s=1.8): x = min(1, max(0, x)) - 1; return x * x * ((s + 1) * x + s) + 1
def lerp(a, b, x): return a + (b - a) * x
def seg(t, a, b): return (t - a) / (b - a)

def mask_text(txt, f, track=0, pad=40, skew=0.0, stroke=0):
    ws = [f.getlength(c) for c in txt]; asc, desc = f.getmetrics(); tw = int(sum(ws) + track * (len(txt) - 1))
    m = Image.new("L", (tw + 2 * pad, asc + desc + 2 * pad), 0); d = ImageDraw.Draw(m); x = pad
    for c, w_ in zip(txt, ws):
        d.text((x, pad), c, font=f, fill=255, stroke_width=stroke, stroke_fill=255); x += w_ + track
    if skew:
        ext = int(m.height * abs(skew)) + 4
        m = m.transform((m.width + ext, m.height), Image.AFFINE, (1, skew, -ext if skew < 0 else 0, 0, 1, 0), Image.BICUBIC)
    return m

def colorize(m, col):
    return Image.merge("RGBA", (*[Image.new("L", m.size, c) for c in col], m))

def glow(im, r=18, k=1.0, col=None):
    a = im.split()[3]; pad = r * 3
    big = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0)); big.alpha_composite(im, (pad, pad))
    ga = big.split()[3].filter(ImageFilter.GaussianBlur(r)).point(lambda v: min(255, int(v * k)))
    if col is None: rgb = big.convert("RGB").filter(ImageFilter.GaussianBlur(r)); g = Image.merge("RGBA", (*rgb.split(), ga))
    else: g = colorize(ga, col)
    g.alpha_composite(big); return g

def put(fr, im, cx, cy, a=1.0, sc=1.0):
    if im is None or a <= 0 or sc <= 0.01: return
    if abs(sc - 1) > 0.004: im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BICUBIC)
    if a < 1:
        r, g, b, al = im.split(); im = Image.merge("RGBA", (r, g, b, al.point(lambda v: int(v * a))))
    fr.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

# ------------------------------------------------------------------ paysage synthwave
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
def sky():
    g = np.clip(yy / HOR, 0, 1)[..., None]
    c = np.array([14, 4, 34]) * (1 - g) + np.array([150, 24, 120]) * g ** 2.2 + np.array([40, 10, 70]) * g * (1 - g)
    c[yy >= HOR] = (10, 2, 22)
    return Image.fromarray(c.clip(0, 255).astype(np.uint8))
SKY = sky()
rs = np.random.default_rng(3); STARS = [(rs.uniform(0, W), rs.uniform(0, HOR - 300), rs.uniform(1, 3.2), rs.uniform(0, 6)) for _ in range(120)]
def sun_img(r=360):
    s = 2 * r; y = np.arange(s)[:, None]; x = np.arange(s)[None, :]
    inside = ((x - r) ** 2 + (y - r) ** 2) < r * r
    g = (y / s)[..., None]; col = np.array([255, 226, 80]) * (1 - g) + np.array([255, 40, 150]) * g
    cut = np.ones((s, s), bool); yn = y[:, 0] / s
    for k in range(9):
        y0 = 0.52 + k * 0.055; hgt = 0.006 + k * 0.0045; cut[(yn > y0) & (yn < y0 + hgt), :] = False
    a = (inside & cut).astype(np.uint8) * 255
    im = Image.fromarray(np.dstack([col.repeat(s, 1).clip(0, 255), a[..., None]]).astype(np.uint8))
    return glow(im, 50, 0.7, (255, 80, 150))
SUN = sun_img()
def mountains():
    r = np.random.default_rng(8); pts = [(0, HOR)]
    for k, x in enumerate(np.linspace(0, W, 13)): pts.append((x, HOR - (r.uniform(120, 300) if k % 2 else r.uniform(30, 90))))
    pts.append((W, HOR)); im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.polygon(pts, fill=(18, 6, 42, 255)); d.line(pts[1:-1], fill=CYAN + (255,), width=4)
    for i in range(1, len(pts) - 2, 2):                  # arêtes en fil de fer
        x, y = pts[i + 1]; d.line((x, y, x + r.uniform(-60, 60), HOR), fill=CYAN + (90,), width=2)
    return glow(im, 10, 0.6, CYAN).crop((30, 30, W + 30, H + 30))
MOUNT = mountains()

def grid(t, speed=1.0, col=PINK):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im); vx = W / 2
    off = (t * speed * 1.6) % 1.0
    for k in range(0, 26):
        z = k + 1 - off; y = HOR + 900 / z
        if HOR < y < H + 10: d.line((0, y, W, y), fill=col + (int(255 * min(1, 1.6 / z ** 0.5)),), width=max(2, int(7 / z ** 0.4)))
    for k in range(-16, 17):
        x1 = vx + k * 230; d.line((vx + k * 12, HOR, x1, H), fill=col + (220,), width=3)
    d.line((0, HOR, W, HOR), fill=(255, 140, 220, 255), width=4)
    g = im.filter(ImageFilter.GaussianBlur(9)); g.alpha_composite(im); return g

def landscape(t, sun_y=0, speed=1.0, logo=None):
    fr = SKY.convert("RGBA"); ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for x, y, s, ph in STARS:
        a = int(200 * (0.5 + 0.5 * math.sin(t * 3 + ph))); d.ellipse((x - s, y - s, x + s, y + s), fill=(255, 220, 255, a))
    fr.alpha_composite(ov)
    put(fr, SUN, W / 2, HOR - 150 + sun_y)
    fr.alpha_composite(MOUNT)
    fr.paste((10, 2, 22, 255), (0, HOR + 2, W, H))
    fr.alpha_composite(grid(t, speed))
    return fr

# ------------------------------------------------------------------ titres chromés et néons
def chrome(txt, size, skew=-0.18, track=0):
    m = mask_text(txt, font("900", size), track, 40, skew)
    h = m.height; y = np.linspace(0, 1, h)[:, None]
    top = np.array([90, 170, 255]); mid = np.array([255, 255, 255]); dark = np.array([40, 20, 60]); bot = np.array([255, 150, 60])
    c = np.where(y < 0.5, (top * (1 - y / 0.5) + mid * (y / 0.5)), np.where(y < 0.53, dark, dark * (1 - (y - 0.53) / 0.47) + bot * ((y - 0.53) / 0.47)))
    col = np.repeat(c[:, None, :], m.width, 1)
    im = Image.fromarray(np.dstack([col.clip(0, 255), np.asarray(m)[..., None]]).astype(np.uint8))
    edge = colorize(ImageChops.subtract(m.filter(ImageFilter.MaxFilter(7)), m), (255, 230, 255))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0)); out.alpha_composite(edge); out.alpha_composite(im)
    return glow(out, 22, 0.9, PINK)
def neon(txt, f, col, track=0, core=4, skew=0.0):
    m = mask_text(txt, f, track, 60, skew)
    edge = ImageChops.subtract(m.filter(ImageFilter.MaxFilter(core * 2 + 1)), m.filter(ImageFilter.MinFilter(3)))
    tube = colorize(edge.filter(ImageFilter.GaussianBlur(1)), (255, 240, 250))
    g = colorize(edge.filter(ImageFilter.GaussianBlur(14)).point(lambda v: min(255, v * 3)), col)
    g2 = colorize(edge.filter(ImageFilter.GaussianBlur(40)).point(lambda v: min(255, v * 2)), col)
    out = Image.new("RGBA", m.size, (0, 0, 0, 0)); out.alpha_composite(g2); out.alpha_composite(g); out.alpha_composite(tube); return out
LOGO = chrome("ARCADIUM", 148, -0.2, 2)
LOGO84 = neon("84", cfont(700, 260), PINK, 0, 5)
SUB = neon("BAR  ARCADE", font("500", 54), CYAN, 14, 3)
INSERT = neon("INSERT COIN", font("700", 110), YEL, 6, 4)
T60 = chrome("60 BORNES", 140, -0.15); TJEUX = neon("JEUX ILLIMITÉS", font("600", 64), CYAN, 6, 3)
HAPPY = neon("HAPPY HOUR", font("800", 104), PINK, 6, 4); HH = neon("18H — 20H", font("600", 72), CYAN, 8, 3)
VEN1 = chrome("CE VENDREDI", 112, -0.18); VEN2 = neon("Soirée 80's", cfont(700, 170), PINK, 0, 5)
END1 = neon("@arcadium84", font("500", 50), CYAN, 4, 3); END2 = neon("LYON", font("600", 46), PINK, 22, 3)

def flicker(t, t0, seed=1):
    """Néon qui s'allume en grésillant puis reste allumé (petits ratés aléatoires)."""
    lt = t - t0
    if lt < 0: return 0.0
    if lt < 0.6:
        r = np.random.default_rng(int(lt * 30) + seed * 100); return float(r.random() > 0.45) * (0.4 + 0.6 * lt / 0.6)
    r = np.random.default_rng(int(t * 30) + seed); return 0.25 if r.random() < 0.03 else 1.0

# ------------------------------------------------------------------ pixel art (sprites originaux)
PX = 10; PW, PH = W // PX, H // PX
def sprite(rows, col):
    h = len(rows); w = len(rows[0]); a = np.zeros((h, w, 4), np.uint8)
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch == "#": a[y, x] = col + (255,)
    return Image.fromarray(a)
ALIEN_A = [["..#....#..", "...####...", "..######..", ".##.##.##.", "##########", "#.######.#", "#.#....#.#", "...#..#..."],
           ["..#....#..", "#..####..#", "#.######.#", "###.##.###", "##########", "..######..", ".#......#.", "#........#"]]
ALIEN_B = [["...####...", ".########.", "##.####.##", "##########", "..##..##..", ".##.##.##.", "##......##"],
           ["...####...", ".########.", "##.####.##", "##########", ".##.##.##.", "##......##", ".##....##."]]
SHIP = ["....##....", "...####...", "...####...", ".########.", "##########", "###.##.###", "##......##"]
SA = [sprite(f, (255, 80, 200)) for f in ALIEN_A]; SB = [sprite(f, (80, 240, 255)) for f in ALIEN_B]; SS = sprite(SHIP, (255, 230, 90))
def pixel_text(txt, size, col):
    f = font("700", size); m = Image.new("L", (int(f.getlength(txt)) + 4, size + 6), 0); ImageDraw.Draw(m).text((2, 0), txt, font=f, fill=255)
    return colorize(m.point(lambda v: 255 if v > 110 else 0), col)
def game(t, w=PW, h=PH, score_base=0):
    """Mini-jeu de tir rétro rendu en basse résolution."""
    im = Image.new("RGBA", (w, h), (6, 2, 18, 255)); d = ImageDraw.Draw(im); fr_ = int(t * 4) % 2
    r = np.random.default_rng(5)
    for k in range(40):
        x = int(r.uniform(0, w)); y = int((r.uniform(0, h) + t * 18 * (1 + k % 3)) % h); d.point((x, y), fill=(140, 120, 200, 255))
    ox = int(6 + 6 * math.sin(t * 1.6)); dead = set()
    shots = [(k * 0.55 + 0.2) for k in range(30)]
    for s in shots:
        if t > s + 0.7: dead.add(int(s / 0.55) % 18)
    for row in range(3):
        for col in range(6 if w > 60 else 4):
            idx = row * 6 + col
            if idx in dead: continue
            spr = (SA if row != 1 else SB)[fr_]; im.alpha_composite(spr, (ox + 4 + col * 15, (30 if h > 100 else 26) + row * 12))
    sx = int(w / 2 - 5 + 30 * math.sin(t * 2.1)); im.alpha_composite(SS, (sx, h - 30))
    for s in shots:
        lt = t - s
        if 0 < lt < 0.7: by = int(h - 32 - lt * 160); d.line((sx + 5, by, sx + 5, by + 3), fill=(255, 255, 160, 255))
        if 0.6 < lt < 0.9:
            idx = int(s / 0.55) % 18; cx = ox + 9 + (idx % 6) * 15; cy = 34 + (idx // 6) * 14; rr = int((lt - 0.6) * 30)
            for a in range(8): d.point((cx + int(rr * math.cos(a * 0.785)), cy + int(rr * math.sin(a * 0.785))), fill=(255, 200, 80, 255))
    sc = score_base + int(len([s for s in shots if t > s + 0.7]) * 150)
    im.alpha_composite(pixel_text(f"SCORE {sc:06d}", 9, (255, 255, 255)), (4, 4)); im.alpha_composite(pixel_text("HI 099990", 9, (255, 80, 200)), (4, 15))
    return im

# ------------------------------------------------------------------ borne d'arcade
def cabinet():
    w, h = 720, 1300; im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    body = [(80, 0), (640, 0), (660, 160), (620, 560), (700, 760), (700, 1300), (20, 1300), (20, 760), (100, 560), (60, 160)]
    d.polygon(body, fill=(28, 10, 54, 255)); d.line(body + [body[0]], fill=PINK + (255,), width=6)
    d.rectangle((90, 20, 630, 150), fill=(255, 40, 160, 255)); d.rounded_rectangle((120, 190, 600, 560), 26, fill=(4, 2, 10, 255), outline=CYAN + (255,), width=6)
    d.polygon([(100, 600), (620, 600), (690, 760), (30, 760)], fill=(48, 18, 84, 255), outline=CYAN + (255,))
    d.ellipse((150, 640, 230, 700), fill=(10, 10, 10, 255)); d.line((190, 670, 190, 610), fill=(220, 220, 230, 255), width=14); d.ellipse((170, 590, 210, 630), fill=(255, 40, 60, 255))
    for k, c in enumerate([(255, 220, 60), (40, 230, 255), (255, 46, 170)]): d.ellipse((380 + k * 90, 650, 440 + k * 90, 700), fill=c + (255,))
    d.rounded_rectangle((300, 900, 420, 1060), 14, fill=(10, 4, 20, 255), outline=YEL + (255,), width=5); d.rectangle((345, 930, 375, 1020), fill=(255, 200, 40, 255))
    m = mask_text("ARCADIUM", font("900", 76), 4, 0, -0.15); im.alpha_composite(colorize(m, (255, 240, 250)), (360 - m.width // 2, 40))
    return glow(im, 16, 0.5, PINK)
CAB = cabinet()
def coin(s=110):
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im); d.ellipse((4, 4, s - 4, s - 4), fill=(255, 210, 60, 255), outline=(255, 250, 200, 255), width=6)
    d.ellipse((24, 24, s - 24, s - 24), outline=(220, 150, 20, 255), width=5); return glow(im, 12, 0.7, YEL)
COIN = coin()

# ------------------------------------------------------------------ dessins au néon
def neon_path(fr, pts, p, col, width=8):
    if p <= 0: return
    pts = np.array(pts, float); L = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]); q = pts[L <= p * L[-1]]
    if len(q) < 2: return
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov); d.line([tuple(x) for x in q], fill=col + (255,), width=width * 3, joint="curve")
    g = ov.filter(ImageFilter.GaussianBlur(26)); g2 = ov.filter(ImageFilter.GaussianBlur(8))
    core = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(core).line([tuple(x) for x in q], fill=(255, 245, 250, 255), width=width, joint="curve")
    fr.alpha_composite(g); fr.alpha_composite(g2); fr.alpha_composite(core)
GLASS = [[(330, 640), (750, 640), (540, 940), (330, 640)], [(540, 940), (540, 1200)], [(420, 1210), (660, 1210)],
         [(640, 520), (580, 760)], list(zip(470 + 30 * np.cos(np.linspace(0, 6.3, 40)), 720 + 30 * np.sin(np.linspace(0, 6.3, 40))))]
GCOL = [PINK, PINK, PINK, CYAN, YEL]
JOY = [[(780, 1500), (980, 1500), (980, 1560), (780, 1560), (780, 1500)], [(880, 1500), (880, 1400)], list(zip(880 + 34 * np.cos(np.linspace(0, 6.3, 40)), 1380 + 34 * np.sin(np.linspace(0, 6.3, 40))))]

# ------------------------------------------------------------------ OSD magnétoscope
def osd(fr, label, t, show_tc=True, sym="play"):
    d = ImageDraw.Draw(fr); f = font("500", 46)
    for dx, dy, c in ((3, 3, (0, 0, 0, 160)), (0, 0, (240, 255, 240, 255))):
        d.text((90 + dx, 120 + dy), label, font=f, fill=c)
        if show_tc:
            s = int(t); d.text((90 + dx, 180 + dy), f"0:{s // 60:02d}:{s % 60:02d}", font=f, fill=c)
        d.text((640 + dx, 1700 + dy), "OCT.14 1984", font=font("500", 40), fill=c)
    x0 = 90 + f.getlength(label) + 20
    if sym == "play": d.polygon([(x0, 128), (x0 + 34, 148), (x0, 168)], fill=(240, 255, 240, 255))
    elif sym == "rew":
        for k in range(2): d.polygon([(x0 + 34 + k * 34, 128), (x0 + k * 34, 148), (x0 + 34 + k * 34, 168)], fill=(240, 255, 240, 255))
    elif sym == "stop": d.rectangle((x0, 128, x0 + 38, 166), fill=(240, 255, 240, 255))

# ------------------------------------------------------------------ scènes
def s_intro(t):                                # 0–2,6 : neige, allumage, puis paysage + logo
    fr = landscape(t, lerp(220, 0, ease(seg(t, 0.8, 2.6))), 1.0)
    k = ease(seg(t, 1.4, 2.4)); z = lerp(0.05, 1.0, k)
    if k > 0:
        put(fr, LOGO, W / 2, lerp(HOR - 200, 640, k), min(1, k * 2), z)
        put(fr, LOGO84, W / 2 + 270, 800, flicker(t, 2.3, 2), 1.0)
        put(fr, SUB, W / 2, 930, flicker(t, 2.7, 3))
    return fr
def s_logo(t): return s_intro(t)
def s_coin(t):                                 # 6,8–10,4 : borne + néon INSERT COIN + pièce
    lt = t - 6.8; fr = Image.new("RGBA", (W, H), (8, 2, 20, 255))
    fr.alpha_composite(grid(t, 0.3, PURPLE).transpose(Image.FLIP_TOP_BOTTOM).point(lambda v: v // 2))
    cab = CAB.copy(); g = game(lt + 0.3, 96, 74).resize((480, 370), Image.NEAREST); cab.alpha_composite(g, (CAB.width // 2 - 240, 214 + 16))
    put(fr, cab, W / 2, 1180, 1, lerp(0.86, 0.95, ease(seg(lt, 0, 3.6))))
    put(fr, INSERT, W / 2, 330, flicker(t, 7.1, 5))
    cp = seg(lt, 1.4, 2.2)
    if 0 < cp < 1:
        y = lerp(-80, 1180 + 300, ease_in(cp)); s_ = abs(math.cos(lt * 14)); c = COIN.resize((max(4, int(COIN.width * s_)), COIN.height))
        put(fr, c, W / 2 - 4, y)
    return fr
def s_game(t):                                 # 10,7–14,5 : jeu plein écran
    lt = t - 10.7; fr = game(lt, PW, PH, 4200).resize((W, H), Image.NEAREST)
    put(fr, T60, W / 2, 760, ease(seg(lt, 0.6, 1.0)), lerp(1.4, 1, ease(seg(lt, 0.6, 1.0))))
    put(fr, TJEUX, W / 2, 920, flicker(t, 11.6, 7))
    return fr
def s_bar(t):                                  # 14,7–18,5 : néons cocktail + joystick
    lt = t - 14.7; fr = Image.new("RGBA", (W, H), (10, 2, 18, 255))
    wall = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(wall)
    for k in range(0, H, 90): d.line((0, k, W, k), fill=(40, 16, 60, 255), width=3)
    fr.alpha_composite(wall)
    for i, (pts, c) in enumerate(zip(GLASS, GCOL)):
        on = flicker(t, 14.8 + i * 0.15, 20 + i); neon_path(fr, pts, ease_io(seg(lt, 0.1 + i * 0.15, 0.9 + i * 0.15)) * on, c)
    for i, pts in enumerate(JOY): neon_path(fr, pts, ease_io(seg(lt, 1.2 + i * 0.12, 1.8 + i * 0.12)) * flicker(t, 15.9, 30 + i), CYAN, 6)
    put(fr, HAPPY, W / 2, 280, flicker(t, 15.4, 9)); put(fr, HH, W / 2, 420, flicker(t, 15.9, 10))
    return fr
def s_friday(t):                               # 18,7–21,5 : retour au paysage, annonce
    lt = t - 18.7; fr = landscape(t, 0, 2.2)
    put(fr, VEN1, W / 2, 520, ease(seg(lt, 0.2, 0.6)), lerp(2.0, 1.0, ease(seg(lt, 0.2, 0.6))))
    put(fr, VEN2, W / 2, 720, flicker(t, 19.2, 11))
    return fr
def s_end(t):
    lt = t - 21.9; fr = landscape(t, 30, 0.8)
    dk = Image.new("RGBA", (W, H), (0, 0, 0, 110)); fr.alpha_composite(dk)
    put(fr, LOGO, W / 2, 620, ease(seg(lt, 0.0, 0.4)), lerp(1.3, 1, ease(seg(lt, 0, 0.4))))
    put(fr, LOGO84, W / 2 + 270, 780, flicker(t, 22.2, 12)); put(fr, SUB, W / 2, 920, flicker(t, 22.5, 13))
    put(fr, END2, W / 2, 1030, flicker(t, 22.8, 14)); put(fr, END1, W / 2, 1490, flicker(t, 23.0, 15))
    if int(t * 2.5) % 2 == 0 and lt > 0.8:
        pt = pixel_text("INSERT COIN TO CONTINUE", 9, YEL).resize((int(pixel_text("INSERT COIN TO CONTINUE", 9, YEL).width * 6), 15 * 6), Image.NEAREST)
        put(fr, pt, W / 2, 1640)
    return fr

# ------------------------------------------------------------------ transitions télé / VHS
def static(seed, strength=1.0):
    r = np.random.default_rng(seed); n = r.integers(0, 255, (H // 3, W // 3), dtype=np.uint8)
    im = Image.fromarray(n).resize((W, H), Image.NEAREST).convert("RGB"); return im
def crt_on(t, img, t0, t1):
    p = seg(t, t0, t1); fr = Image.new("RGB", (W, H), (0, 0, 0))
    if p < 0.35:
        fr = Image.blend(fr, static(int(t * 60)), 0.6)
        return fr
    q = ease((p - 0.35) / 0.65); h = max(4, int(H * q)); w = int(W * min(1, 0.02 + q * 3))
    sq = img.convert("RGB").resize((w, h), Image.BILINEAR); fr.paste(sq, ((W - w) // 2, (H - h) // 2))
    return Image.blend(fr, Image.new("RGB", (W, H), (255, 255, 255)), max(0, 0.6 - q))
def crt_off(t, img, t0, t1):
    p = seg(t, t0, t1); fr = Image.new("RGB", (W, H), (0, 0, 0))
    if p < 0.55:
        q = ease_in(p / 0.55); h = max(6, int(H * (1 - q))); sq = img.convert("RGB").resize((W, h)); fr.paste(sq, (0, (H - h) // 2))
        return Image.blend(fr, Image.new("RGB", (W, H), (255, 255, 255)), q * 0.5)
    q = ease_in((p - 0.55) / 0.45); w = max(6, int(W * (1 - q))); d = ImageDraw.Draw(fr)
    d.rectangle(((W - w) / 2, H / 2 - 3, (W + w) / 2, H / 2 + 3), fill=(255, 255, 255))
    if q > 0.7: d.ellipse((W / 2 - 14, H / 2 - 14, W / 2 + 14, H / 2 + 14), fill=(255, 255, 255))
    return fr.filter(ImageFilter.GaussianBlur(2))
def rewind(t, a, b, t0, t1):
    """Rembobinage VHS : défilement vertical rapide, bandes de suivi, couleurs qui bavent."""
    p = seg(t, t0, t1); img = (a if p < 0.5 else b).convert("RGB"); arr = np.asarray(img)
    off = int((p * 7 % 1) * H); arr = np.roll(arr, off, 0).copy()
    r = np.random.default_rng(int(t * 90))
    for k in range(5):
        y = r.integers(0, H - 80); hh = r.integers(20, 90); arr[y:y + hh] = np.clip(arr[y:y + hh].astype(int) + r.integers(60, 140), 0, 255)
        arr[y:y + hh] = np.roll(arr[y:y + hh], r.integers(-120, 120), 1)
    out = Image.fromarray(arr); rr, gg, bb = out.split(); out = Image.merge("RGB", (ImageChops.offset(rr, 14, 0), gg, ImageChops.offset(bb, -14, 0)))
    fr = out.convert("RGBA"); osd(fr, "REW", t, False, "rew"); return fr.convert("RGB")
def channel(t, a, b, t0, t1):
    p = seg(t, t0, t1)
    if 0.25 < p < 0.6: return static(int(t * 90))
    img = (a if p <= 0.25 else b).convert("RGB")
    if p >= 0.6:
        q = ease((p - 0.6) / 0.4); img = ImageChops.offset(img, 0, int((1 - q) * H * 0.4))
    return img
def pixel_zoom(t, a, b, t0, t1):
    p = seg(t, t0, t1)
    if p < 0.6:
        q = ease_in(p / 0.6); z = 1 + q * 25; img = a.convert("RGB"); w = W / z; h = H / z
        cy = min(max(H * 0.3, h / 2), H - h / 2)
        return img.resize((W, H), Image.NEAREST, box=(W / 2 - w / 2, cy - h / 2, W / 2 + w / 2, cy + h / 2))
    q = (p - 0.6) / 0.4; return Image.blend(Image.new("RGB", (W, H), (255, 255, 255)), b.convert("RGB"), ease(q))
def glitch(t, a, b, t0, t1):
    p = seg(t, t0, t1); img = np.asarray((a if p < 0.5 else b).convert("RGB")).copy(); r = np.random.default_rng(int(t * 120))
    k = math.sin(math.pi * p)
    for _ in range(int(10 + 30 * k)):
        y = r.integers(0, H - 60); x = r.integers(0, W - 100); hh = r.integers(10, 120); ww = r.integers(80, 600)
        img[y:y + hh, x:x + ww] = np.roll(img[y:y + hh, x:x + ww], r.integers(-200, 200), 1)
        if r.random() < 0.3: img[y:y + hh, x:x + ww, r.integers(0, 3)] = 255
    out = Image.fromarray(img); rr, gg, bb = out.split()
    return Image.merge("RGB", (ImageChops.offset(rr, int(22 * k), 0), gg, ImageChops.offset(bb, -int(22 * k), 0)))

# ------------------------------------------------------------------ montage
def frame(t):
    if t < 1.3: return crt_on(t, s_intro(max(t, 0.9)), 0.0, 1.3)
    if t < 6.4: return s_intro(t).convert("RGB")
    if t < 6.95: return rewind(t, s_intro(t), s_coin(t), 6.4, 6.95)
    if t < 10.4: return s_coin(t).convert("RGB")
    if t < 10.85: return channel(t, s_coin(t), s_game(t), 10.4, 10.85)
    if t < 14.4: return s_game(t).convert("RGB")
    if t < 14.95: return pixel_zoom(t, s_game(t), s_bar(t), 14.4, 14.95)
    if t < 18.45: return s_bar(t).convert("RGB")
    if t < 18.85: return glitch(t, s_bar(t), s_friday(t), 18.45, 18.85)
    if t < 21.2: return s_friday(t).convert("RGB")
    if t < 21.75: return crt_off(t, s_friday(t), 21.2, 21.75)
    if t < 22.4: return crt_on(t, s_end(t), 21.75, 22.4)
    return s_end(t).convert("RGB")

def vhs(img, n, t):
    """Couche magnétoscope : flou horizontal, bavure des couleurs, tremblement de bande, lignes, bruit."""
    a = np.asarray(img.resize((W // 2, H), Image.BILINEAR).resize((W, H), Image.BILINEAR)).astype(np.float32)
    r = np.random.default_rng(n)
    wob = (np.sin(np.arange(H) / 37 + t * 5) * 1.5 + np.sin(np.arange(H) / 11 - t * 13) * 0.8).astype(int)
    ii = (np.arange(W)[None, :] - wob[:, None]) % W; a = a[np.arange(H)[:, None], ii]
    a[..., 0] = np.roll(a[..., 0], 4, 1); a[..., 2] = np.roll(a[..., 2], -3, 1)
    a[::3] *= 0.82                                               # lignes de balayage
    a += r.normal(0, 7, (H // 2, W // 2, 1)).repeat(2, 0).repeat(2, 1)
    yb = int((t * 260) % (H + 400)) - 200                         # bande de suivi qui remonte
    if 0 < yb < H - 40: a[yb:yb + 26] = a[yb:yb + 26] * 0.6 + r.uniform(60, 160, (26, W, 1))
    a *= np.clip(1.05 - (((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2) * 0.9, 0.55, 1.05)[..., None]
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))

def render(n):
    t = n / FPS; img = frame(t)
    # halo des néons
    sm = img.resize((W // 6, H // 6), Image.BILINEAR); hi = np.clip(np.asarray(sm, np.float32) - 140, 0, 255) * 1.5
    bl = Image.fromarray(hi.clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6)).resize((W, H), Image.BICUBIC)
    img = ImageChops.add(img, bl.point(lambda v: int(v * 0.6)))
    fr = vhs(img, n, t).convert("RGBA")
    if 1.3 < t < 6.4: osd(fr, "PLAY", t)
    elif t >= 22.6: osd(fr, "STOP", t, False, "stop")
    return np.asarray(fr.convert("RGB")).tobytes()

TIMES = {"dur": DUR, "static": [0.0, 0.45], "crt_on": [0.45, 21.75], "logo": 1.4, "neon": [2.3, 2.7, 7.1, 11.6, 15.4, 15.9, 19.2, 22.2, 22.5, 22.8, 23.0],
         "rewind": 6.4, "coin": 8.2, "coin_drop": 9.0, "blips": [k * 0.55 + 0.2 for k in range(40)], "channel": 10.4, "game": [10.7, 14.4],
         "slam": [11.3, 19.0, 21.9], "zoom": 14.4, "glass": [14.8 + i * 0.15 for i in range(5)] + [15.9, 16.0, 16.1], "glitch": 18.45,
         "crt_off": 21.2, "end": 21.9}

if __name__ == "__main__":
    wav = OUT.replace(".mp4", ".wav")
    subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "arcadium_audio.py"), wav, json.dumps(TIMES)], check=True)
    ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "slow", "-crf", "22",
                           "-maxrate", "8M", "-bufsize", "16M", "-pix_fmt", "yuv420p",
                           "-af", "loudnorm=I=-13:TP=-1:LRA=9", "-ar", "48000", "-c:a", "aac", "-b:a", "256k",
                           "-shortest", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
    sel = [int(float(x) * FPS) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else range(int(DUR * FPS))
    with Pool(4) as pool:
        for i, b in enumerate(pool.imap(render, sel, chunksize=2)):
            ff.stdin.write(b)
            if i % 100 == 0: print(i, flush=True)
    ff.stdin.close(); ff.wait(); os.remove(wav); print("ok", OUT)
