"""ÉCLA — pub soda pétillant (marque fictive), style pop éditorial, 9:16, 1080x1920, 30 i/s, 24,5 s.

Usage : python3 ecla.py <dossier_polices> <sortie.mp4> [temps,à,prévisualiser]
"""
import json, math, os, subprocess, sys
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

FONTS, OUT = sys.argv[1], sys.argv[2]
W, H, FPS = 1080, 1920, 30
DUR = 24.5
CREAM = (255, 244, 226); NAVY = (27, 31, 59); WHITE = (255, 255, 255)
FL = {
    "Y": dict(bg=(255, 206, 58), deep=(236, 150, 18), light=(255, 234, 150), name=("CITRON", "& YUZU"), label="CITRON · YUZU"),
    "P": dict(bg=(255, 96, 140), deep=(208, 38, 92), light=(255, 186, 208), name=("FRAMBOISE", "& LITCHI"), label="FRAMBOISE · LITCHI"),
    "G": dict(bg=(64, 214, 150), deep=(18, 140, 96), light=(186, 244, 212), name=("MENTHE", "& CONCOMBRE"), label="MENTHE · CONCOMBRE"),
}

# ------------------------------------------------------------------ outils
def font(w, size): return ImageFont.truetype(os.path.join(FONTS, f"fontsource-jost-5.3.0/files/jost-latin-{w}-normal.woff"), size)
def text(txt, w, size, color, track=0, pad=20, stroke=0, stroke_color=None):
    f = font(w, size); ws = [f.getlength(c) for c in txt]; asc, desc = f.getmetrics()
    tw = int(sum(ws) + track * (len(txt) - 1))
    im = Image.new("RGBA", (tw + 2 * pad + 2 * stroke, asc + desc + 2 * pad + 2 * stroke), (0, 0, 0, 0)); d = ImageDraw.Draw(im); x = pad + stroke
    for c, w_ in zip(txt, ws):
        if stroke: d.text((x, pad + stroke), c, font=f, fill=(0, 0, 0, 0), stroke_width=stroke, stroke_fill=stroke_color)
        else: d.text((x, pad), c, font=f, fill=color)
        x += w_ + track
    return im

class SSDraw:
    def __init__(self, size, s=3, ox=0, oy=0):
        self.size = (int(size[0]), int(size[1])); self.s, self.ox, self.oy = s, ox, oy
        self.im = Image.new("RGBA", (self.size[0] * s, self.size[1] * s), (0, 0, 0, 0)); self.d = ImageDraw.Draw(self.im)
    def _p(self, xy):
        fl = []
        for v in xy: fl += [v[0], v[1]] if isinstance(v, (tuple, list)) else [v]
        return [((fl[i] - self.ox) * self.s, (fl[i + 1] - self.oy) * self.s) for i in range(0, len(fl), 2)]
    def _b(self, xy): p = self._p(xy); return (p[0][0], p[0][1], p[1][0], p[1][1])
    def ellipse(self, xy, fill=None, outline=None, width=1): self.d.ellipse(self._b(xy), fill=fill, outline=outline, width=int(width * self.s))
    def polygon(self, xy, fill=None, outline=None, width=1): self.d.polygon(self._p(xy), fill=fill, outline=outline, width=int(width * self.s))
    def line(self, xy, fill=None, width=1):
        pts = self._p(xy); w = int(width * self.s); self.d.line(pts, fill=fill, width=w, joint="curve")
        for x, y in (pts[0], pts[-1]): self.d.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=fill)
    def rounded_rectangle(self, xy, r, fill=None, outline=None, width=1):
        self.d.rounded_rectangle(self._b(xy), r * self.s, fill=fill, outline=outline, width=int(width * self.s))
    def result(self): return self.im.resize(self.size, Image.LANCZOS)

def rounded(w, h, r, fill, outline=None, width=0):
    d = SSDraw((w, h)); d.rounded_rectangle((0, 0, w - 1, h - 1), r, fill, outline, width); return d.result()
def alpha(im, a):
    if im is None or a <= 0: return None
    if a >= 0.999: return im
    r, g, b, al = im.split(); return Image.merge("RGBA", (r, g, b, al.point(lambda v: int(v * a))))
def put(fr, im, cx, cy, a=1.0, sx=1.0, sy=None, rot=0.0):
    if im is None or a <= 0: return
    sy = sx if sy is None else sy
    if sx <= 0.01 or sy <= 0.01: return
    if abs(sx - 1) > 0.004 or abs(sy - 1) > 0.004: im = im.resize((max(1, int(im.width * sx)), max(1, int(im.height * sy))), Image.BICUBIC)
    if abs(rot) > 0.1: im = im.rotate(rot, Image.BICUBIC, expand=True)
    im = alpha(im, a)
    if im is not None: fr.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))
def ease(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3
def ease_in(x): x = min(1, max(0, x)); return x ** 3
def ease_io(x): x = min(1, max(0, x)); return x * x * x * (x * (6 * x - 15) + 10)
def back(x, s=1.9): x = min(1, max(0, x)) - 1; return x * x * ((s + 1) * x + s) + 1
def spring(x, f=3.2, d=5.5):          # ressort amorti (rebond naturel), 0 → 1
    x = max(0, x); return 1 - math.exp(-d * x) * math.cos(f * math.pi * x)
def lerp(a, b, x): return a + (b - a) * x
def seg(t, a, b): return (t - a) / (b - a)
def solid(c): return Image.new("RGBA", (W, H), c + (255,))
def shadow_ellipse(w, h, a=0.25):
    d = SSDraw((w * 2, h * 4), 2); d.ellipse((w / 2, h * 1.5, w * 1.5, h * 2.5), fill=(20, 16, 40, int(255 * a)))
    return d.result().filter(ImageFilter.GaussianBlur(h * 0.45))

def reveal(fr, im, cx, cy, p, a=1.0):
    """Révélation par ligne : le texte monte depuis une fente invisible."""
    if p <= 0 or im is None: return
    e = ease(p); h = im.height; off = int((1 - e) * h * 0.9)
    crop = im.crop((0, 0, im.width, max(1, h - off)))
    x = int(cx - im.width / 2); y = int(cy - h / 2) + off
    a_ = alpha(crop, a)
    if a_ is not None: fr.alpha_composite(a_, (x, y))

# ------------------------------------------------------------------ fruits et objets
def lemon_slice(s=220):
    d = SSDraw((s, s)); c = s / 2
    d.ellipse((4, 4, s - 4, s - 4), fill=(255, 214, 40, 255)); d.ellipse((14, 14, s - 14, s - 14), fill=(255, 246, 200, 255))
    d.ellipse((22, 22, s - 22, s - 22), fill=(255, 222, 70, 255))
    for k in range(9):
        a0 = k * 2 * math.pi / 9 + 0.06; a1 = (k + 1) * 2 * math.pi / 9 - 0.06; r0, r1 = 12, c - 30
        pts = [(c + r0 * math.cos((a0 + a1) / 2), c + r0 * math.sin((a0 + a1) / 2))]
        for j in range(7):
            a = lerp(a0, a1, j / 6); pts.append((c + r1 * math.cos(a), c + r1 * math.sin(a)))
        d.polygon(pts, fill=(255, 238, 140, 255))
    d.ellipse((c - 9, c - 9, c + 9, c + 9), fill=(255, 246, 200, 255))
    return d.result()
def raspberry(s=170):
    d = SSDraw((s, s)); rng = np.random.default_rng(3); c = s / 2
    pts = [(c + r * math.cos(a), c + 6 + r * math.sin(a) * 1.1) for r, n in ((0, 1), (26, 6), (50, 11)) for a in np.linspace(0, 2 * math.pi, n, endpoint=False)]
    for x, y in sorted(pts, key=lambda p: p[1]):
        r = 22 + rng.uniform(-2, 2); d.ellipse((x - r, y - r, x + r, y + r), fill=(214, 36, 84, 255))
        d.ellipse((x - r * .75, y - r * .8, x + r * .55, y + r * .45), fill=(244, 70, 118, 255))
        d.ellipse((x - r * .45, y - r * .55, x - r * .05, y - r * .15), fill=(255, 190, 210, 255))
    for k in range(5):
        a = -math.pi / 2 + (k - 2) * 0.5; d.polygon([(c, 18), (c + 46 * math.cos(a - .25), 18 + 30 * math.sin(a - .25) - 4), (c + 46 * math.cos(a), 18 + 30 * math.sin(a) - 14)], fill=(70, 160, 80, 255))
    return d.result()
def mint_leaf(s=220):
    d = SSDraw((s, s)); pts = []
    for k in range(40):
        u = k / 39; y = 14 + u * (s - 28); w = math.sin(math.pi * u) ** 0.8 * s * 0.36 * (1 - 0.25 * u)
        pts.append((s / 2 + w + 4 * math.sin(u * 30), y))
    pts += [(s - x, y) for x, y in reversed(pts)]
    d.polygon(pts, fill=(36, 168, 96, 255))
    d.line([(s / 2, 20), (s / 2, s - 24)], fill=(150, 230, 170, 255), width=5)
    for k in range(4):
        y = 50 + k * 34; d.line([(s / 2, y + 20), (s / 2 + 48 - k * 6, y)], fill=(120, 214, 150, 255), width=3)
        d.line([(s / 2, y + 20), (s / 2 - 48 + k * 6, y)], fill=(120, 214, 150, 255), width=3)
    return d.result()
def cucumber(s=200):
    d = SSDraw((s, s)); c = s / 2
    d.ellipse((4, 4, s - 4, s - 4), fill=(30, 120, 60, 255)); d.ellipse((14, 14, s - 14, s - 14), fill=(196, 240, 170, 255))
    d.ellipse((40, 40, s - 40, s - 40), fill=(170, 226, 140, 255))
    for k in range(10):
        a = k * 2 * math.pi / 10; r = 40; x, y = c + r * math.cos(a), c + r * math.sin(a)
        d.ellipse((x - 6, y - 9, x + 6, y + 9), fill=(250, 255, 230, 255))
    return d.result()
def ice(s=180):
    d = SSDraw((s, s)); d.rounded_rectangle((8, 8, s - 8, s - 8), 34, fill=(235, 248, 255, 150), outline=(255, 255, 255, 230), width=5)
    d.polygon([(30, 40), (70, 26), (60, 80), (26, 96)], fill=(255, 255, 255, 170)); return d.result()
def bubble(s=60):
    d = SSDraw((s, s)); d.ellipse((3, 3, s - 3, s - 3), outline=(255, 255, 255, 230), width=max(2, s // 14))
    d.ellipse((s * .22, s * .2, s * .42, s * .38), fill=(255, 255, 255, 220)); return d.result()
LEMON, RASP, MINT, CUC, ICE = lemon_slice(), raspberry(), mint_leaf(), cucumber(), ice()
BUB = {s: bubble(s) for s in (24, 40, 64, 96)}
FRUITS = {"Y": [LEMON, LEMON.resize((150, 150))], "P": [RASP, RASP.resize((120, 120))], "G": [MINT, CUC]}

# ------------------------------------------------------------------ canette 3D (étiquette cylindrique)
CW, CB = 380, 640                     # diamètre, hauteur de l'étiquette
R_ = CW / 2; LAB = int(2 * math.pi * R_)
_xn = (np.arange(CW) + 0.5 - R_) / R_; _th = np.arcsin(np.clip(_xn, -1, 1)); U0 = _th / (2 * math.pi) * LAB
_shade = (0.42 + 0.58 * np.cos(_th) ** 0.7)
_spec = np.exp(-((_xn + 0.42) / 0.10) ** 2) * 0.55 + np.exp(-((_xn - 0.78) / 0.06) ** 2) * 0.22
def label(k):
    f = FL[k]; im = Image.new("RGBA", (LAB, CB), f["bg"] + (255,)); d = SSDraw((LAB, CB), 2)
    pts = [(x, CB * 0.62 + 18 * math.sin(x / LAB * 2 * math.pi * 3)) for x in range(0, LAB + 20, 20)]
    d.polygon(pts + [(LAB, CB), (0, CB)], fill=f["deep"] + (255,))
    im.alpha_composite(d.result())
    lg = text("écla", "900", 196, WHITE, track=-6); im.alpha_composite(lg, (LAB // 2 - lg.width // 2, 70))
    nm = text(f["label"], "600", 34, NAVY, track=5); im.alpha_composite(nm, (LAB // 2 - nm.width // 2, 330))
    sub = text("SODA PÉTILLANT · 33 CL", "500", 26, WHITE, track=4); im.alpha_composite(sub, (LAB // 2 - sub.width // 2, 470))
    fr = FRUITS[k][0].resize((150, 150))
    for x in (LAB * 0.08, LAB * 0.92): im.alpha_composite(fr, (int(x - 75), 220))
    return np.asarray(im.convert("RGB"), np.float32)
LABELS = {k: label(k) for k in FL}
def metal_band(h, dark=0.35):
    g = np.asarray(Image.linear_gradient("L").resize((1, h)), np.float32)[:, 0] / 255
    col = 150 + 90 * (np.cos(_th) ** 0.6)[None, :] * (1 - dark * g[:, None]) + 80 * _spec[None, :]
    return np.repeat(col[..., None], 3, 2)
TOP_BAND = metal_band(46, 0.2); BOT_BAND = metal_band(36, 0.6)
def can(k, rot=0.0, cond=None):
    """Canette vue légèrement de dessus ; rot en radians."""
    cols = ((U0 + LAB / 2 + rot / (2 * math.pi) * LAB) % LAB).astype(int)
    body = LABELS[k][:, cols] * _shade[None, :, None] + 255 * _spec[None, :, None]
    body = np.clip(body, 0, 255)
    top = TOP_BAND; bot = BOT_BAND
    arr = np.concatenate([top, body, bot], 0).clip(0, 255).astype(np.uint8)
    im = Image.fromarray(arr).convert("RGBA")
    ell = 70; full = Image.new("RGBA", (CW, im.height + ell), (0, 0, 0, 0))
    m = SSDraw((CW, im.height + ell))
    m.rounded_rectangle((0, ell / 2, CW - 1, im.height + ell / 2 - 1), 30, fill=(255, 255, 255, 255))
    m.ellipse((0, 0, CW - 1, ell), fill=(255, 255, 255, 255)); m.ellipse((0, im.height - 10, CW - 1, im.height + ell - 10), fill=(255, 255, 255, 255))
    full.paste(im, (0, ell // 2)); full.putalpha(m.result().split()[3])
    lid = SSDraw((CW, ell + 4))
    lid.ellipse((6, 4, CW - 6, ell - 2), fill=(196, 198, 206, 255)); lid.ellipse((26, 12, CW - 26, ell - 10), fill=(150, 152, 162, 255))
    lid.ellipse((40, 16, CW - 40, ell - 14), fill=(210, 212, 220, 255))
    lid.rounded_rectangle((CW / 2 - 52, 22, CW / 2 + 52, 48), 13, fill=(176, 178, 188, 255), outline=(130, 132, 142, 255), width=3)
    lid.ellipse((CW / 2 - 14, 28, CW / 2 + 14, 42), fill=(120, 122, 132, 255))
    full.alpha_composite(lid.result(), (0, 0))
    if cond is not None: full.alpha_composite(cond)
    return full
CAN_H = TOP_BAND.shape[0] + CB + BOT_BAND.shape[0] + 70
def condensation():
    d = SSDraw((CW, CAN_H)); r = np.random.default_rng(8)
    for _ in range(140):
        x = r.uniform(20, CW - 20); y = r.uniform(90, CAN_H - 60); s = r.uniform(3, 11) * (0.4 + 0.6 * math.cos(math.asin((x - R_) / R_)))
        d.ellipse((x - s, y - s * 1.2, x + s, y + s * 1.2), fill=(255, 255, 255, 70), outline=(255, 255, 255, 140), width=1.2)
        d.ellipse((x - s * .5, y - s * .8, x - s * .1, y - s * .3), fill=(255, 255, 255, 220))
    return d.result()
COND = condensation()
SHADOW = shadow_ellipse(CW, 60, 0.28)

def put_can(fr, k, cx, cy, sc=1.0, rot=0.0, squash=0.0, tilt=0.0, cond=False, shadow=True, sh_y=None):
    im = can(k, rot, COND if cond else None)
    sx, sy = sc * (1 + squash * 0.5), sc * (1 - squash)
    if shadow:
        put(fr, SHADOW, cx, (sh_y if sh_y is not None else cy + im.height * sy / 2) , 0.9, sc * (1 + squash * 0.3), sc)
    put(fr, im, cx, cy, 1, sx, sy, tilt)

# ------------------------------------------------------------------ typographie
def big(txt, color, size=200, w="900", track=-6): return text(txt, w, size, color, track)
def outline(txt, color, size=300, stroke=4): return text(txt, "900", size, None, -4, 10, stroke, color + (255,))
HOOK = [("T'AS", 700), ("SOIF ?", 900)]
HOOK_COL = [FL["Y"]["deep"], FL["P"]["bg"], FL["G"]["deep"], NAVY]
HOOK_L = [[text(c, "900", 230, HOOK_COL[(i + j) % 4], 0, 10) for j, c in enumerate(w)] for i, (w, _) in enumerate(HOOK)]
PSSHT = text("pssht !", "800", 80, NAVY)
MARQ = {k: [outline(f["name"][0] + "  ", f["light"], 330, 5), outline(f["name"][0] + "  ", f["deep"], 330, 5)] for k, f in FL.items()}
TITLE = {k: (big(f["name"][0], NAVY if k != "P" else WHITE, 150), big(f["name"][1], WHITE if k != "P" else NAVY, 96, "700", -3)) for k, f in FL.items()}
L1 = big("3 PARFUMS.", NAVY, 136); L2 = big("0 SUCRE AJOUTÉ.", FL["P"]["deep"], 104, "900", -4)
CHIPS = []
for k in "YPG":
    t_ = text(FL[k]["label"].title(), "700", 40, NAVY)
    c = rounded(t_.width + 30, 84, 42, FL[k]["light"] + (255,)); c.alpha_composite(t_, (15, 42 - t_.height // 2)); CHIPS.append(c)
G1, G2, G3 = big("Glacé.", NAVY, 170), big("Pétillant.", NAVY, 170), big("Vrai.", FL["P"]["deep"], 170)
def sticker():
    d = SSDraw((300, 300)); pts = [(150 + (140 if k % 2 == 0 else 122) * math.cos(k * math.pi / 12), 150 + (140 if k % 2 == 0 else 122) * math.sin(k * math.pi / 12)) for k in range(24)]
    d.polygon(pts, fill=FL["Y"]["bg"] + (255,)); im = d.result()
    a = text("33 cl", "900", 76, NAVY); b = text("45 kcal", "600", 40, NAVY)
    im.alpha_composite(a, (150 - a.width // 2, 82)); im.alpha_composite(b, (150 - b.width // 2, 166)); return im
STICK = sticker()
LOGO = text("écla", "900", 300, NAVY, -10, 10)
TAG = text("Le soda qui pétille pour de vrai.", "500", 50, NAVY)
HANDLE = text("@ecla.soda", "700", 44, FL["P"]["deep"])
def pill():
    t_ = text("BIENTÔT PRÈS DE CHEZ TOI", "700", 34, WHITE, 3); c = rounded(t_.width + 70, 96, 48, NAVY + (255,))
    c.alpha_composite(t_, (35, 48 - t_.height // 2)); return c
PILL = pill()

# ------------------------------------------------------------------ bulles montantes (décor)
rngb = np.random.default_rng(5)
RISE = [(rngb.uniform(0, W), rngb.uniform(0, H), rngb.choice([24, 40, 64]), rngb.uniform(120, 360), rngb.uniform(0, 6)) for _ in range(26)]
def rising(fr, t, a=0.8):
    for x, y, s, v, ph in RISE:
        yy = (y - t * v) % (H + 200) - 100; xx = x + 20 * math.sin(t * 2 + ph)
        put(fr, BUB[s], xx, yy, a)

# ------------------------------------------------------------------ scènes
def scene_hook(t):
    fr = solid(CREAM)
    for i, (letters, (_, y)) in enumerate(zip(HOOK_L, HOOK)):
        widths = [l.width - 20 for l in letters]; x = W / 2 - sum(widths) / 2
        for j, im in enumerate(letters):
            t0 = 0.12 + (i * 4 + j) * 0.075; p = seg(t, t0, t0 + 0.6)
            if p > 0:
                yy = y - (1 - spring(p, 2.4, 6)) * 260; rot = (1 - ease(p * 1.4)) * (18 if j % 2 else -18)
                out = ease_in(seg(t, 2.05, 2.35))
                put(fr, im, x + widths[j] / 2, yy - out * 120, 1 - out * 0, 1 + out * 0.15, None, rot)
            x += widths[j]
    # la canette tombe, s'écrase, rebondit
    p = seg(t, 1.05, 1.45); land = 1420
    if t >= 1.05:
        if p < 1: y = lerp(-500, land, ease_in(p)); sq = -0.12 * p
        else: q = t - 1.45; y = land - 60 * abs(math.sin(q * 7)) * math.exp(-q * 6); sq = 0.16 * math.exp(-q * 9) * math.cos(q * 26)
        put_can(fr, "Y", W / 2, y, 0.78, 0.2 + t * 0.6, sq, sh_y=land + CAN_H * 0.78 / 2 - 10)
    ps = seg(t, 1.8, 2.25)
    if 0 < ps < 1:
        put(fr, PSSHT, W / 2 + 230, 1060 - ps * 60, math.sin(math.pi * ps), back(ps * 2), None, -10)
        r = np.random.default_rng(1)
        for k in range(22):
            a = r.uniform(-2.4, -0.7); sp = r.uniform(300, 900)
            put(fr, BUB[24], W / 2 + math.cos(a) * sp * ps, 1150 + math.sin(a) * sp * ps + 400 * ps ** 2, 1 - ps)
    return fr

def scene_flavor(t, k, t0):
    f = FL[k]; fr = solid(f["bg"]); lt = t - t0
    for row, (y, dirx, sp) in enumerate(((330, -1, 260), (720, 1, 200), (1110, -1, 300))):
        m = MARQ[k][row % 2]; off = (lt * sp * dirx) % m.width
        for x in (-off, -off + m.width, -off - m.width): fr.alpha_composite(m, (int(x), y - m.height // 2)) if -m.width < x < W else None
    rising(fr, t, 0.7)
    cx, cy = W / 2, 960 + 22 * math.sin(lt * 2.1)
    fruits = FRUITS[k]; items = []
    for i in range(5):
        a = lt * 1.3 + i * 2 * math.pi / 5; z = math.sin(a)
        items.append((z, fruits[i % 2], cx + math.cos(a) * 400, cy + 120 + z * 110 - 160 + i % 2 * 40, 0.75 + 0.35 * z, lt * 60 * (1 if i % 2 else -1)))
    for z, im, x, y, s, r in sorted(items):
        if z < 0: put(fr, im, x, y, 1, s, None, r)
    put_can(fr, k, cx, cy, 1.0, lt * 1.7 + 0.4, 0, -4 * math.sin(lt * 1.6), sh_y=cy + CAN_H / 2 - 10)
    for z, im, x, y, s, r in sorted(items):
        if z >= 0: put(fr, im, x, y, 1, s, None, r)
    a_, b_ = TITLE[k]
    reveal(fr, a_, W / 2, 1530, seg(lt, 0.35, 0.8)); reveal(fr, b_, W / 2, 1660, seg(lt, 0.55, 1.0))
    return fr

def scene_lineup(t):
    fr = solid(CREAM); lt = t - 14.0
    reveal(fr, L1, W / 2, 300, seg(lt, 0.5, 0.95)); reveal(fr, L2, W / 2, 430, seg(lt, 0.75, 1.2))
    for i, k in enumerate("YPG"):
        x = W / 2 + (i - 1) * 330; t0 = 0.05 + i * 0.15; p = seg(lt, t0, t0 + 0.38); land = 1080
        if p <= 0: continue
        hop = seg(lt, 2.5 + i * 0.09, 3.0 + i * 0.09)
        if p < 1: y = lerp(-500, land, ease_in(p)); sq = -0.1 * p
        else:
            q = lt - t0 - 0.38; y = land - 40 * abs(math.sin(q * 8)) * math.exp(-q * 7); sq = 0.15 * math.exp(-q * 9) * math.cos(q * 26)
        if 0 < hop < 1: y -= 220 * math.sin(math.pi * hop); sq += -0.08 * math.sin(math.pi * hop)
        put_can(fr, k, x, y, 0.72, lt * 1.2 + i, sq, (i - 1) * -3, sh_y=land + CAN_H * 0.72 / 2 - 8)
        cp = back(seg(lt, 1.4 + i * 0.1, 1.75 + i * 0.1))
        if cp > 0: put(fr, CHIPS[i], x, 1430 + (i % 2) * 90, 1, cp * 0.92)
    return fr

ICES = [(np.random.default_rng(i).uniform(80, W - 80), np.random.default_rng(i + 9).uniform(900, 1850), np.random.default_rng(i).uniform(0.6, 1.1), i) for i in range(7)]
def scene_close(t):
    lt = t - 18.2
    g = np.linspace(0, 1, H)[:, None, None]
    fr = Image.fromarray((np.array([206, 236, 255]) * (1 - g) + np.array([120, 182, 240]) * g).astype(np.uint8).repeat(W, 1)).convert("RGBA")
    rising(fr, t * 1.3, 0.9)
    for x, y, s, i in ICES:
        if i % 2: put(fr, ICE, x + 30 * math.sin(lt + i), y - lt * 40, 0.9, s, None, lt * 30 * (1 if i % 3 else -1) + i * 20)
    put_can(fr, "P", W / 2 + 120, 1200 + 16 * math.sin(lt * 2), 1.18, lt * 0.9 + 2.6, 0, 8, cond=True, shadow=False)
    for x, y, s, i in ICES:
        if not i % 2: put(fr, ICE, x + 30 * math.sin(lt + i), y - lt * 50, 1, s, None, lt * 40 + i * 30)
    for im, y, t0 in ((G1, 280, 0.35), (G2, 450, 0.6), (G3, 620, 0.85)):
        reveal(fr, im, im.width / 2 + 60, y, seg(lt, t0, t0 + 0.4))
    sp = back(seg(lt, 2.0, 2.35))
    if sp > 0: put(fr, STICK, 250, 1180, 1, sp, None, -12 + 6 * math.sin(lt * 3))
    return fr

def scene_end(t):
    fr = solid(CREAM); lt = t - 21.8
    lp = seg(lt, 0.15, 0.75)
    if lp > 0:
        s = spring(lp, 2.2, 5); put(fr, LOGO, W / 2, 640, 1, 0.6 + 0.4 * s)
        for i, k in enumerate("YPG"):            # trois bulles de couleur autour du logo
            p = back(seg(lt, 0.45 + i * 0.08, 0.8 + i * 0.08))
            d = SSDraw((60, 60)); d.ellipse((0, 0, 59, 59), fill=FL[k]["bg"] + (255,))
            put(fr, d.result(), W / 2 + 290 + i * 20, 480 + i * 70 + 8 * math.sin(lt * 3 + i), 1, p * (1 - 0.25 * i))
    reveal(fr, TAG, W / 2, 870, seg(lt, 0.6, 1.0))
    for i, k in enumerate("YPG"):
        p = seg(lt, 0.9 + i * 0.1, 1.3 + i * 0.1); land = 1300
        if p > 0:
            if p < 1: y = lerp(1900, land, ease(p)); sq = 0
            else: q = lt - 1.3 - i * 0.1; y = land; sq = 0.12 * math.exp(-q * 9) * math.cos(q * 26)
            put_can(fr, k, W / 2 + (i - 1) * 230, y, 0.46, lt * 1.4 + i, sq, sh_y=land + CAN_H * 0.46 / 2 - 6)
    put(fr, PILL, W / 2, 1610, 1, back(seg(lt, 1.4, 1.75)))
    reveal(fr, HANDLE, W / 2, 1740, seg(lt, 1.6, 2.0))
    return fr

# ------------------------------------------------------------------ transitions (masques)
def composite(a, b, mask):
    return Image.composite(b.convert("RGB"), a.convert("RGB"), mask)

def tr_bubbles(t, a, b, t0, t1, cx, cy, seed=4, grow_from="center"):
    """Éclatement de bulles : des disques grandissent et révèlent la scène suivante."""
    p = seg(t, t0, t1); r = np.random.default_rng(seed); d = SSDraw((W // 2, H // 2), 2, 0, 0)
    for k in range(46):
        ang = r.uniform(0, 2 * math.pi); dist = r.uniform(0, 1.0) ** 0.6; delay = dist * 0.45 + r.uniform(0, 0.12)
        q = ease(seg(p, delay, delay + 0.55)); rad = q * r.uniform(260, 520)
        x = cx + math.cos(ang) * dist * 1300; y = cy + math.sin(ang) * dist * 1600
        if rad > 0: d.ellipse(((x - rad) / 2, (y - rad) / 2, (x + rad) / 2, (y + rad) / 2), fill=(255, 255, 255, 255))
    full = ease(seg(p, 0.75, 1.0)) * 2400
    if full > 0: d.ellipse(((cx - full) / 2, (cy - full) / 2, (cx + full) / 2, (cy + full) / 2), fill=(255, 255, 255, 255))
    m = d.result().split()[3].resize((W, H), Image.BICUBIC)
    out = composite(a, b, m).convert("RGBA")
    # liseré de bulles blanches au bord du masque
    edge = ImageChops.subtract(m.filter(ImageFilter.MaxFilter(9)), m).point(lambda v: min(255, v * 2))
    out.alpha_composite(Image.merge("RGBA", (Image.new("L", (W, H), 255),) * 3 + (edge,)))
    return out

def tr_liquid(t, a, b, t0, t1, color):
    p = ease_io(seg(t, t0, t1)); lvl = lerp(H + 160, -260, p); x = np.arange(W)
    wave = lvl + 46 * np.sin(x / 140 + t * 9) + 22 * np.sin(x / 61 - t * 13) + 60 * math.sin(p * math.pi) * np.sin(x / 330 + 1)
    yy = np.arange(H)[:, None]; m = Image.fromarray(((yy > wave[None, :]) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
    out = composite(a, b, m).convert("RGBA")
    foam = SSDraw((W, H), 1); pts = [(xi, wave[xi]) for xi in range(0, W, 12)] + [(W, wave[-1])]
    foam.line(pts, fill=WHITE + (235,), width=14)
    out.alpha_composite(foam.result())
    r = np.random.default_rng(int(t * 30))
    for k in range(18):
        xx = r.uniform(0, W); yy_ = wave[int(xx)] + r.uniform(30, 520)
        if yy_ < H: put(out, BUB[r.choice([24, 40])], xx, yy_, 0.8)
    return out

def tr_iris(t, a, b, t0, t1, cx, cy):
    p = ease_io(seg(t, t0, t1)); rad = p * 2300; d = SSDraw((W // 2, H // 2), 2)
    d.ellipse(((cx - rad) / 2, (cy - rad) / 2, (cx + rad) / 2, (cy + rad) / 2), fill=(255, 255, 255, 255))
    m = d.result().split()[3].resize((W, H), Image.BICUBIC); out = composite(a, b, m).convert("RGBA")
    ring = SSDraw((W, H), 1); r2 = rad + 24; ring.ellipse((cx - r2, cy - r2, cx + r2, cy + r2), outline=WHITE + (230,), width=16)
    out.alpha_composite(ring.result()); return out

def tr_shutters(t, a, b, t0, t1):
    p = seg(t, t0, t1); fr = (a if p < 0.5 else b).copy().convert("RGBA")
    cols = [FL["Y"]["bg"], FL["P"]["bg"], FL["G"]["bg"]]; bw = H / 3 + 260
    for i, c in enumerate(cols):
        q = seg(p, i * 0.1, 0.62 + i * 0.1); x = lerp(-W - 900, W + 900, ease_io(q)) if q > 0 else -W - 900
        y0 = i * H / 3 - 130; d = SSDraw((W, H), 1)
        sk = 420
        d.polygon([(x - 900, y0 + bw), (x - 900 + sk, y0), (x + 900 + sk, y0), (x + 900, y0 + bw)], fill=c + (255,))
        fr.alpha_composite(d.result())
    return fr

def tr_textzoom(t, a, b, t0, t1):
    """Le mot « écla » grandit et la scène suivante apparaît à travers ses lettres."""
    p = seg(t, t0, t1); fr = a.copy().convert("RGBA")
    if p < 0.25:
        put(fr, LOGO, W / 2, H / 2, 1, back(p / 0.25) * 1.0); return fr
    z = math.exp(ease_in((p - 0.25) / 0.75) * math.log(40))
    lw, lh = int(LOGO.width * z), int(LOGO.height * z)
    fx, fy = 0.555, 0.52                             # point d'ancrage dans le jambage du « l »
    big_ = LOGO.resize((max(1, lw), max(1, lh)), Image.BICUBIC) if z < 12 else None
    m = Image.new("L", (W, H), 0)
    if big_ is not None:
        m.paste(big_.split()[3], (int(W / 2 - lw * fx), int(H / 2 - lh * fy)))
    else:
        box = ((lw * fx - W / 2) / z, (lh * fy - H / 2) / z, (lw * fx + W / 2) / z, (lh * fy + H / 2) / z)
        m = LOGO.split()[3].resize((W, H), Image.BICUBIC, box=box)
    return composite(fr, b, m).convert("RGBA")

def tr_rise(t, a, b, t0, t1):
    p = seg(t, t0, t1); r = np.random.default_rng(11); d = SSDraw((W // 2, H // 2), 2)
    for k in range(60):
        x = r.uniform(-60, W + 60); delay = r.uniform(0, 0.45); q = ease(seg(p, delay, delay + 0.55))
        y = lerp(H + 300, r.uniform(-200, H), q); rad = q * r.uniform(220, 420)
        if rad > 0: d.ellipse(((x - rad) / 2, (y - rad) / 2, (x + rad) / 2, (y + rad) / 2), fill=(255, 255, 255, 255))
    if p > 0.7:
        h_ = ease((p - 0.7) / 0.3) * H; d.polygon([(0, H / 2), (W / 2, H / 2), (W / 2, (H - h_) / 2), (0, (H - h_) / 2)], fill=(255, 255, 255, 255))
    m = d.result().split()[3].resize((W, H), Image.BICUBIC); return composite(a, b, m).convert("RGBA")

# ------------------------------------------------------------------ montage
def Y(t): return scene_flavor(t, "Y", 2.3)
def P(t): return scene_flavor(t, "P", 6.0)
def G(t): return scene_flavor(t, "G", 9.8)
def frame(t):
    if t < 2.05: return scene_hook(t)
    if t < 2.55: return tr_bubbles(t, scene_hook(t), Y(t), 2.05, 2.55, W / 2, 1150)
    if t < 5.85: return Y(t)
    if t < 6.45: return tr_liquid(t, Y(t), P(t), 5.85, 6.45, FL["P"]["bg"])
    if t < 9.65: return P(t)
    if t < 10.15: return tr_iris(t, P(t), G(t), 9.65, 10.15, W / 2, 960)
    if t < 13.55: return G(t)
    if t < 14.2: return tr_shutters(t, G(t), scene_lineup(t), 13.55, 14.2)
    if t < 17.55: return scene_lineup(t)
    if t < 18.4: return tr_textzoom(t, scene_lineup(t), scene_close(t), 17.55, 18.4)
    if t < 21.35: return scene_close(t)
    if t < 21.95: return tr_rise(t, scene_close(t), scene_end(t), 21.35, 21.95)
    return scene_end(t)

FAST = [(1.0, 1.6), (2.05, 2.55), (5.85, 6.45), (9.65, 10.15), (13.55, 14.6), (17.9, 18.4), (21.35, 21.95), (22.6, 23.3)]
rng_g = np.random.default_rng(0)
GRAIN = [rng_g.normal(0, 2.4, (H // 2, W // 2, 1)).astype(np.float32).repeat(2, 0).repeat(2, 1) for _ in range(6)]
def render(n):
    t = n / FPS; k = 7 if any(a <= t < b for a, b in FAST) else 3
    acc = sum(np.asarray(frame(min(DUR - 0.001, max(0, t + (i / (k - 1) - 0.5) * 0.55 / FPS))).convert("RGB"), np.float32) for i in range(k)) / k
    acc += GRAIN[n % 6]
    if t > DUR - 0.25: acc *= max(0, (DUR - t) / 0.25) * 0 + 1      # pas de fondu au noir : on garde l'image finale
    return np.clip(acc, 0, 255).astype(np.uint8).tobytes()

SECTIONS = {"intro_end": 2.4, "stop1": (13.55, 14.05), "chill": (18.25, 21.4), "riser": (17.4, 18.25), "outro": 21.8}
EV = {
    "letter": [0.12 + i * 0.075 + 0.12 for i in range(8)],
    "fall": [1.05], "land": [1.45], "open": [1.8], "fizz": [[1.82, 2.8], [18.3, 21.3]],
    "bubbles": [[2.05, 2.55], [21.35, 21.95]], "gloop": [5.85], "iris": [9.65],
    "swish3": [13.55], "lands3": [14.43, 14.58, 14.73], "hop": [16.5, 16.59, 16.68],
    "pop": [15.4, 15.5, 15.6, 20.2, 22.25, 22.33, 22.41, 23.2],
    "tick": [2.65, 2.85, 6.35, 6.55, 10.15, 10.35, 14.5, 14.75, 18.55, 18.8, 19.05, 22.4, 23.4],
    "zoom": [17.8], "logo": [21.95], "chime": [22.2], "clink": [18.6, 19.3, 19.9, 20.7, 21.1],
    "minilands": [22.75, 22.85, 22.95],
}

if __name__ == "__main__":
    wav = OUT.replace(".mp4", ".wav")
    subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ecla_audio.py"),
                    wav, json.dumps({"dur": DUR, "sections": SECTIONS, "events": EV})], check=True)
    ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "slow", "-crf", "19",
                           "-maxrate", "8M", "-bufsize", "16M", "-pix_fmt", "yuv420p",
                           "-af", "loudnorm=I=-13:TP=-1:LRA=9", "-ar", "48000", "-c:a", "aac", "-b:a", "256k",
                           "-shortest", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
    sel = [int(float(x) * FPS) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else range(int(DUR * FPS))
    with Pool(4) as pool:
        for i, b in enumerate(pool.imap(render, sel, chunksize=2)):
            ff.stdin.write(b)
            if i % 100 == 0: print(i, flush=True)
    ff.stdin.close(); ff.wait(); os.remove(wav); print("ok", OUT)
