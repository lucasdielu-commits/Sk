"""AURÈLE — film publicitaire parfum de luxe (marque fictive), noir et or, 9:16, 1080x1920, 30 i/s, 26,5 s.

Usage : python3 aurele.py <dossier_polices> <sortie.mp4> [temps,à,prévisualiser]
"""
import json, math, os, subprocess, sys
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

FONTS, OUT = sys.argv[1], sys.argv[2]
W, H, FPS = 1080, 1920, 30
DUR = 26.5
GOLD = (226, 184, 110); GOLD_HI = (255, 236, 190); GOLD_LO = (120, 78, 28); BLACK = (6, 5, 4)

# ------------------------------------------------------------------ outils
def cfont(w, size, it=False):
    return ImageFont.truetype(os.path.join(FONTS, f"fontsource-cormorant-garamond-5.3.0/files/cormorant-garamond-latin-{w}-{'italic' if it else 'normal'}.woff"), size)
def jfont(w, size): return ImageFont.truetype(os.path.join(FONTS, f"fontsource-jost-5.3.0/files/jost-latin-{w}-normal.woff"), size)
def ease(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3
def ease_in(x): x = min(1, max(0, x)); return x ** 3
def ease_io(x): x = min(1, max(0, x)); return x * x * x * (x * (6 * x - 15) + 10)
def lerp(a, b, x): return a + (b - a) * x
def seg(t, a, b): return (t - a) / (b - a)
def clamp(x): return min(1, max(0, x))

def gold_fill(mask, shimmer=None):
    """Remplit un masque L avec un dégradé or vertical (+ reflet mobile)."""
    w, h = mask.size; y = np.linspace(0, 1, h)[:, None]
    c = (np.array(GOLD_HI)[None, None] * np.clip(1 - y * 2.2, 0, 1)[..., None]
         + np.array(GOLD)[None, None] * (1 - np.abs(y * 2.2 - 1).clip(0, 1))[..., None] * (y < 0.9)[..., None]
         + np.array(GOLD_LO)[None, None] * np.clip(y * 2 - 1, 0, 1)[..., None])
    c = np.repeat(c, w, 1)
    if shimmer is not None:
        x = np.linspace(0, 1, w)[None, :]; band = np.exp(-((x - shimmer - y * 0.3) / 0.06) ** 2)
        c = c + band[..., None] * 90
    im = Image.fromarray(c.clip(0, 255).astype(np.uint8)).convert("RGBA"); im.putalpha(mask); return im

def text_mask(txt, f, track=0, pad=30):
    ws = [f.getlength(ch) for ch in txt]; asc, desc = f.getmetrics(); tw = int(sum(ws) + track * (len(txt) - 1))
    m = Image.new("L", (tw + 2 * pad, asc + desc + 2 * pad), 0); d = ImageDraw.Draw(m); x = pad; pos = []
    for ch, w_ in zip(txt, ws): d.text((x, pad), ch, font=f, fill=255); pos.append((x, w_)); x += w_ + track
    return m, pos

class Letters:
    """Texte or, révélé lettre par lettre (fondu + flou + légère montée)."""
    def __init__(self, txt, f, track=0, color=None):
        self.m, self.pos = text_mask(txt, f, track)
        self.img = gold_fill(self.m) if color is None else Image.merge("RGBA", (*[Image.new("L", self.m.size, c) for c in color], self.m))
    def draw(self, fr, cx, cy, p, stagger=0.06, dur=0.5, out=0.0, shimmer=None):
        if p <= 0: return
        img = self.img if shimmer is None else gold_fill(self.m, shimmer)
        n = len(self.pos); x0 = int(cx - img.width / 2); y0 = int(cy - img.height / 2)
        tot = stagger * (n - 1) + dur
        for i, (x, w_) in enumerate(self.pos):
            q = ease(seg(p * tot, i * stagger, i * stagger + dur)) * (1 - out)
            if q <= 0.01: continue
            piece = img.crop((int(x) - 6, 0, int(x + w_) + 6, img.height))
            if q < 0.97: piece = piece.filter(ImageFilter.GaussianBlur((1 - q) * 6))
            r, g, b, a = piece.split(); piece = Image.merge("RGBA", (r, g, b, a.point(lambda v: int(v * q))))
            fr.alpha_composite(piece, (x0 + int(x) - 6, y0 + int((1 - q) * 18)))

def glow_add(fr_rgb, layer_rgb, k=1.0):
    return ImageChops.add(fr_rgb, layer_rgb.point(lambda v: int(v * k)) if k != 1 else layer_rgb)

# ------------------------------------------------------------------ or liquide (bruit déformé, éclairage spéculaire)
LW, LH = 270, 480
_gy, _gx = np.mgrid[0:LH, 0:LW].astype(np.float32) / LH
def fbm(x, y, t):
    v = np.zeros_like(x); a = 1.0; f = 1.0
    for o in range(5):
        v += a * np.sin(x * f * 3.4 + np.sin(y * f * 2.6 + t * 0.7 + o) * 1.6 + t * (0.3 + o * 0.11)) * np.cos(y * f * 3.0 - t * 0.4 + o * 1.7)
        a *= 0.45; f *= 2.05
    return v
def liquid_gold(t, zoom=1.0, cx=0.5, cy=0.5):
    x = (_gx - cx * LW / LH) / zoom; y = (_gy - cy) / zoom
    wx = fbm(x + 3.1, y, t * 0.6); wy = fbm(x, y + 7.7, t * 0.6)
    h = fbm(x + wx * 0.35, y + wy * 0.35, t)
    gyv, gxv = np.gradient(h)
    n = np.dstack([-gxv * 14, -gyv * 14, np.ones_like(h)]); n /= np.linalg.norm(n, axis=2, keepdims=True)
    L = np.array([-0.4, -0.6, 0.7]); L /= np.linalg.norm(L)
    diff = np.clip((n * L).sum(2), 0, 1); hv = (L + np.array([0, 0, 1])); hv /= np.linalg.norm(hv)
    spec = np.clip((n * hv).sum(2), 0, 1) ** 60
    base = np.clip(0.5 + h * 0.25, 0, 1)[..., None]
    col = (np.array([30, 16, 4]) * (1 - diff[..., None]) + np.array([205, 140, 48]) * diff[..., None]) * (0.55 + 0.6 * base)
    col += spec[..., None] * np.array([255, 240, 200]) * 1.3
    im = Image.fromarray(col.clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
    return im.filter(ImageFilter.GaussianBlur(1.2))

def smoke_noise(t, scale=1.0):
    x, y = _gx * scale, _gy * scale
    v = fbm(x * 0.8 + 11, y * 0.8 - t * 0.15, t * 0.3)
    return (v - v.min()) / (v.max() - v.min() + 1e-6)

# ------------------------------------------------------------------ poussière d'or (bokeh en profondeur)
def bokeh_sprite(r, blur):
    s = int(r * 2 + blur * 4 + 6); im = Image.new("L", (s, s), 0)
    ImageDraw.Draw(im).ellipse((s / 2 - r, s / 2 - r, s / 2 + r, s / 2 + r), fill=255)
    return im.filter(ImageFilter.GaussianBlur(blur))
SPR = {}
def sprite(r, blur):
    k = (int(r), int(blur))
    if k not in SPR: SPR[k] = bokeh_sprite(*k)
    return SPR[k]
rngd = np.random.default_rng(7)
DUST = [dict(x=rngd.uniform(-100, W + 100), y=rngd.uniform(-100, H + 100), z=rngd.uniform(0, 1), ph=rngd.uniform(0, 6),
             vx=rngd.uniform(-10, 10), vy=rngd.uniform(-28, -6)) for _ in range(90)]
GOLDL = Image.new("RGB", (400, 400), (255, 214, 140))
def dust(fr, t, focus=0.5, amount=1.0, push=0.0):
    """focus : profondeur nette (0 = loin, 1 = près). push : avance de caméra."""
    for p in DUST:
        z = (p["z"] + push) % 1.0; s = 0.4 + z * 2.6
        x = (p["x"] + p["vx"] * t + 30 * math.sin(t * 0.5 + p["ph"]) - W / 2) * (0.6 + z * 0.8) + W / 2
        y = ((p["y"] + p["vy"] * t * (0.5 + z)) % (H + 200)) - 100
        blur = 0.5 + abs(z - focus) * 26; r = 2 + s * 3 + abs(z - focus) * 14
        a = amount * (0.25 + 0.75 * math.sin(t * 1.3 + p["ph"]) ** 2) * (0.5 + 0.5 * z) * (1 - min(1, abs(z - focus) * 1.1)) ** 0.5
        if a < 0.02: continue
        sp = sprite(r, blur).point(lambda v, a=a: int(v * a))
        fr.paste(GOLDL.crop((0, 0, sp.width, sp.height)), (int(x - sp.width / 2), int(y - sp.height / 2)),
                 ImageChops.lighter(sp, Image.new("L", sp.size, 0)))

# ------------------------------------------------------------------ rayons de lumière
def rays_img():
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im); r = np.random.default_rng(3); ox, oy = W * 0.15, -200
    for k in range(9):
        a = math.radians(r.uniform(48, 78)); w = r.uniform(0.02, 0.07); L = 2600
        p = [(ox, oy), (ox + L * math.cos(a - w), oy + L * math.sin(a - w)), (ox + L * math.cos(a + w), oy + L * math.sin(a + w))]
        d.polygon(p, fill=int(r.uniform(40, 110)))
    im = im.filter(ImageFilter.GaussianBlur(40))
    yy = np.linspace(1, 0.15, H)[:, None]
    return Image.fromarray((np.asarray(im, np.float32) * yy).astype(np.uint8))
RAYS = rays_img()
def rays(fr_rgb, t, k=1.0, color=(255, 200, 130)):
    fl = 0.75 + 0.25 * math.sin(t * 1.7) * math.sin(t * 0.63 + 1)
    layer = Image.merge("RGB", [RAYS.point(lambda v, c=c: int(v * c / 255 * k * fl)) for c in color])
    return ImageChops.add(fr_rgb, layer)

# ------------------------------------------------------------------ flacon
BW, BH = 440, 600; CAPW, CAPH = 250, 230
def ss(size, s=3): im = Image.new("RGBA", (size[0] * s, size[1] * s), (0, 0, 0, 0)); return im, ImageDraw.Draw(im), s
def bottle_img():
    tw, th = BW + 40, BH + CAPH + 60
    im, d, s = ss((tw, th)); ox = 20; by = CAPH + 50       # haut du corps
    # corps de verre
    d.rounded_rectangle((ox * s, by * s, (ox + BW) * s, (by + BH) * s), 46 * s, fill=(30, 18, 8, 235))
    # parfum ambré
    d.rounded_rectangle(((ox + 26) * s, (by + 70) * s, (ox + BW - 26) * s, (by + BH - 60) * s), 26 * s, fill=(176, 102, 26, 255))
    # fond épais
    d.rounded_rectangle(((ox + 20) * s, (by + BH - 64) * s, (ox + BW - 20) * s, (by + BH - 18) * s), 20 * s, fill=(90, 54, 20, 255))
    # col doré
    d.rectangle(((tw / 2 - 70) * s, (by - 40) * s, (tw / 2 + 70) * s, (by + 6) * s), fill=(150, 108, 46, 255))
    body = im.resize((tw, th), Image.LANCZOS)
    a = np.asarray(body, np.float32)
    # dégradé vertical du parfum (plus clair en haut) + ombrage latéral du verre
    x = (np.arange(tw) - tw / 2) / (BW / 2); y = np.arange(th)[:, None]
    lat = (0.55 + 0.45 * np.cos(np.clip(x, -1, 1) * 1.35)) [None, :]
    vert = np.clip(1.25 - (y - by) / BH * 0.6, 0.6, 1.3)
    a[..., :3] *= (lat * vert)[..., None]
    # reflets verticaux du verre
    hl = np.exp(-((x + 0.62) / 0.07) ** 2) * 0.9 + np.exp(-((x - 0.8) / 0.03) ** 2) * 0.6 + np.exp(-((x + 0.25) / 0.16) ** 2) * 0.12
    mask_body = (y >= by) & (y <= by + BH)
    a[..., :3] += (hl[None, :] * 255 * mask_body)[..., None] * np.array([1.0, 0.9, 0.75])
    out = Image.fromarray(a.clip(0, 255).astype(np.uint8))
    # bouchon : cylindre or
    cap, cd, s2 = ss((CAPW, CAPH)); cd.rounded_rectangle((0, 0, CAPW * s2, CAPH * s2), 22 * s2, fill=(255, 255, 255, 255))
    cap = cap.resize((CAPW, CAPH), Image.LANCZOS); cx = (np.arange(CAPW) - CAPW / 2) / (CAPW / 2)
    sh = (0.35 + 0.65 * np.cos(np.clip(cx, -1, 1) * 1.4) ** 0.8) + np.exp(-((cx + 0.45) / 0.08) ** 2) * 0.8
    col = np.array(GOLD, np.float32)[None, None] * sh[None, :, None] * np.linspace(1.15, 0.75, CAPH)[:, None, None]
    for k in range(6): col[int(CAPH * 0.15 + k * CAPH * 0.13)] *= 0.72
    capc = Image.fromarray(col.clip(0, 255).astype(np.uint8)).convert("RGBA"); capc.putalpha(cap.split()[3])
    out.alpha_composite(capc, (tw // 2 - CAPW // 2, 10))
    # plaque gravée
    pl = Image.new("RGBA", (300, 150), (0, 0, 0, 0)); pd = ImageDraw.Draw(pl)
    pd.rectangle((0, 0, 299, 149), outline=GOLD + (220,), width=2); pd.rectangle((8, 8, 291, 141), outline=GOLD + (120,), width=1)
    m, _ = text_mask("AURÈLE", cfont(500, 54), 10, 0); g = gold_fill(m); pl.alpha_composite(g, (150 - g.width // 2, 30))
    m2, _ = text_mask("EAU DE PARFUM", jfont(400, 18), 6, 0); g2 = gold_fill(m2); pl.alpha_composite(g2, (150 - g2.width // 2, 104))
    out.alpha_composite(pl, (tw // 2 - 150, by + BH // 2 - 70))
    return out
BOTTLE = bottle_img()
BMASK = BOTTLE.split()[3]
RIM = ImageChops.subtract(BMASK, BMASK.filter(ImageFilter.MinFilter(7))).filter(ImageFilter.GaussianBlur(2))
def reflection(img):
    r = img.transpose(Image.FLIP_TOP_BOTTOM); a = np.asarray(r.split()[3], np.float32)
    fade = np.linspace(0.32, 0, r.height)[:, None] ** 1.5 * 3.0
    r.putalpha(Image.fromarray((a * np.clip(fade, 0, 1)).astype(np.uint8))); return r.filter(ImageFilter.GaussianBlur(3))
REFL = reflection(BOTTLE)
def sweep_band(w, h, k, width=160):
    x = np.arange(w)[None, :]; y = np.arange(h)[:, None]
    c = lerp(-w * 0.6, w * 1.6, k); band = np.exp(-((x + y * 0.45 - c) / width) ** 2)
    return Image.fromarray((band * 255).astype(np.uint8))

def draw_bottle(fr, cx, cy, sc=1.0, reveal=1.0, rim=1.0, sweep=None, refl=True):
    """reveal : 0 = silhouette seulement éclairée par le liseré, 1 = flacon entier."""
    b = BOTTLE
    if reveal < 1:
        r_, g_, b_, a_ = b.split(); b = Image.merge("RGBA", (r_, g_, b_, a_.point(lambda v: int(v * reveal))))
    if sweep is not None and 0 < sweep < 1:
        band = ImageChops.multiply(sweep_band(b.width, b.height, sweep), BMASK).point(lambda v: v * 150 // 255)
        b = b.copy(); b.alpha_composite(Image.merge("RGBA", (*[Image.new("L", b.size, c) for c in (255, 240, 210)], band)))
    if sc != 1: b = b.resize((int(b.width * sc), int(b.height * sc)), Image.BICUBIC)
    x = int(cx - b.width / 2); y = int(cy - b.height / 2)
    if refl:
        rf = REFL if sc == 1 else REFL.resize(b.size, Image.BICUBIC)
        if reveal < 1: rf = Image.merge("RGBA", (*rf.split()[:3], rf.split()[3].point(lambda v: int(v * reveal))))
        fr.alpha_composite(rf, (x, y + b.height - 4))
    fr.alpha_composite(b, (x, y))
    if rim > 0:
        rm = RIM if sc == 1 else RIM.resize(b.size, Image.BICUBIC)
        layer = Image.merge("RGBA", (*[Image.new("L", rm.size, c) for c in GOLD_HI], rm.point(lambda v: int(min(255, v * 1.6 * rim)))))
        fr.alpha_composite(layer, (x, y)); fr.alpha_composite(layer.filter(ImageFilter.GaussianBlur(10)), (x, y))

# ------------------------------------------------------------------ dessins au trait (révélation progressive)
def path_len(pts): return np.concatenate([[0], np.cumsum(np.hypot(np.diff(pts[:, 0]), np.diff(pts[:, 1])))])
def draw_path(d, pts, p, width, color, s=3, ox=0, oy=0):
    if p <= 0: return
    L = path_len(pts); keep = L <= p * L[-1]
    q = pts[keep]
    if len(q) < 2: return
    d.line([((x - ox) * s, (y - oy) * s) for x, y in q], fill=color, width=int(width * s), joint="curve")
def circle_pts(cx, cy, r, a0=-90, n=240): a = np.radians(np.linspace(a0, a0 + 360, n)); return np.c_[cx + r * np.cos(a), cy + r * np.sin(a)]
def drop_pts(cx, cy, s):
    th = np.linspace(0, 2 * np.pi, 220); x = s * 0.6 * np.sin(th) * np.sin(th / 2) ** 1.0; y = -s * np.cos(th / 2) * 0.95
    return np.c_[cx + x, cy + y * 1.0 + s * 0.2]
def flower_pts(cx, cy, s):
    th = np.linspace(0, 2 * np.pi, 600); r = s * (0.35 + 0.65 * np.abs(np.cos(2.5 * th)) ** 0.8)
    return np.c_[cx + r * np.cos(th), cy + r * np.sin(th)]
def grain_paths(cx, cy, s):
    out = []
    for k in range(6):
        th = np.linspace(0, 2 * np.pi, 260); r = s * (0.18 + k * 0.15) * (1 + 0.08 * np.sin(th * 3 + k) + 0.04 * np.sin(th * 7))
        out.append(np.c_[cx + r * np.cos(th) * 1.15, cy + r * np.sin(th)])
    return out
NOTES = [("Ambre", "chaud · lumineux", lambda: [drop_pts(540, 860, 230), drop_pts(540, 880, 120)]),
         ("Vanille noire", "profonde · veloutée", lambda: [flower_pts(540, 860, 230), circle_pts(540, 860, 40)]),
         ("Bois de santal", "crémeux · boisé", lambda: grain_paths(540, 860, 240))]
NOTE_TXT = [(Letters(n, cfont(400, 110, True)), Letters(sub.upper(), jfont(300, 30), 8)) for n, sub, _ in NOTES]
NOTE_PATHS = [f() for _, _, f in NOTES]
FRAME_RING = circle_pts(540, 860, 330)
def scene_note(t, i, t0):
    lt = t - t0; fr = Image.new("RGB", (W, H), BLACK); fr = rays(fr, t, 0.35)
    fr = fr.convert("RGBA"); dust(fr, t, 0.3, 0.6)
    ov, d, s = ss((W, H), 2)
    draw_path(d, FRAME_RING, ease_io(seg(lt, 0.0, 1.0)), 2.2, GOLD + (200,), s)
    for k, pts in enumerate(NOTE_PATHS[i]):
        draw_path(d, pts, ease_io(seg(lt, 0.2 + k * 0.12, 1.4 + k * 0.12)), 3.2, GOLD_HI + (255,), s)
    ov = ov.resize((W, H), Image.LANCZOS); fr.alpha_composite(ov.filter(ImageFilter.GaussianBlur(8))); fr.alpha_composite(ov)
    a, b = NOTE_TXT[i]; out = ease(seg(lt, 2.85, 3.2))
    num = Letters(f"0{i + 1}", jfont(300, 34), 6); num.draw(fr, W / 2, 380, seg(lt, 0.1, 0.6), out=out)
    a.draw(fr, W / 2, 1330, seg(lt, 0.6, 1.6), out=out); b.draw(fr, W / 2, 1440, seg(lt, 1.0, 1.8), 0.02, out=out)
    return fr

# ------------------------------------------------------------------ textes
T_INTRO1 = Letters("Il existe une heure", cfont(300, 92, True)); T_INTRO2 = Letters("où tout devient or.", cfont(300, 92, True))
T_NUIT = Letters("Nuit d'ambre", cfont(400, 130, True))
T_LOGO = Letters("AURÈLE", cfont(400, 150), 26); T_EDP = Letters("EAU DE PARFUM", jfont(300, 32), 14)
T_SOIR1 = Letters("Le soir", cfont(300, 120, True)); T_SOIR2 = Letters("t'appartient.", cfont(300, 120, True))
T_END1 = Letters("AURÈLE", cfont(400, 180), 34); T_PARIS = Letters("P A R I S", jfont(300, 30), 10)
T_INFO = Letters("Eau de parfum  ·  50 ml", cfont(400, 50, True)); T_CTA = Letters("DÉCOUVRIR LA COLLECTION", jfont(400, 28), 8)
T_HANDLE = Letters("@aurele.paris", jfont(300, 30), 4)

def letterbox(fr, k=1.0):
    h = int(130 * k)
    if h > 0:
        d = ImageDraw.Draw(fr); d.rectangle((0, 0, W, h), fill=(0, 0, 0)); d.rectangle((0, H - h, W, H), fill=(0, 0, 0))

# ------------------------------------------------------------------ scènes
def scene_intro(t):
    fr = Image.new("RGB", (W, H), BLACK).convert("RGBA"); dust(fr, t, 0.55, ease(t / 1.2) * 0.9)
    # trait d'or qui se dessine
    p = ease_io(seg(t, 0.3, 1.6)); ov, d, s = ss((W, H), 2)
    if p > 0:
        w = 820 * p; d.line(((W / 2 - w / 2) * s, 1010 * s, (W / 2 + w / 2) * s, 1010 * s), fill=GOLD_HI + (255,), width=2 * s)
        ov = ov.resize((W, H), Image.LANCZOS); fr.alpha_composite(ov.filter(ImageFilter.GaussianBlur(6))); fr.alpha_composite(ov)
    T_INTRO1.draw(fr, W / 2, 880, seg(t, 0.8, 2.2)); T_INTRO2.draw(fr, W / 2, 1130, seg(t, 1.5, 2.9), shimmer=seg(t, 2.4, 3.4))
    return fr

def scene_liquid(t):
    lt = t - 3.5; img = liquid_gold(t * 0.9, zoom=lerp(1.0, 1.35, ease_io(seg(t, 3.5, 9.0))), cx=0.5, cy=0.5)
    fr = img.convert("RGBA")
    vg = Image.new("RGBA", (W, H), (0, 0, 0, 0)); a = np.clip(np.hypot((np.arange(W)[None] - W / 2) / W, (np.arange(H)[:, None] - H / 2) / H) * 2.0 - 0.35, 0, 1)
    vg.putalpha(Image.fromarray((a * 230).astype(np.uint8))); fr.alpha_composite(vg)
    dust(fr, t, 0.8, 0.5)
    sh = Image.new("L", (W // 4, H // 4), 0); ImageDraw.Draw(sh).ellipse((20, 190, W // 4 - 20, 290), fill=200)
    k = ease(seg(t, 4.3, 5.2)) * (1 - ease(seg(t, 7.6, 8.3)))
    if k > 0:
        sh = sh.resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(60)).point(lambda v: int(v * k))
        fr.alpha_composite(Image.merge("RGBA", (*[Image.new("L", (W, H), 4)] * 3, sh)))
    T_NUIT.draw(fr, W / 2, 960, seg(t, 4.6, 6.0), out=ease(seg(t, 7.6, 8.3)), shimmer=seg(t, 5.8, 7.0))
    return fr

def scene_bottle(t):
    lt = t - 9.0; fr = Image.new("RGB", (W, H), BLACK); fr = rays(fr, t, lerp(0.2, 1.0, ease(seg(lt, 0.3, 2.0))))
    fr = fr.convert("RGBA"); dust(fr, t, 0.15, 0.8, push=lt * 0.02)
    # sol : légère ligne d'horizon
    ImageDraw.Draw(fr).rectangle((0, 1420, W, H), fill=(10, 8, 6, 255))
    rim = ease(seg(lt, 0.4, 1.4)); rev = ease_io(seg(lt, 1.2, 2.8))
    draw_bottle(fr, W / 2, 1420 - BOTTLE.height / 2 * 1.0 + 6, 1.0 + 0.04 * ease(seg(lt, 0, 6)), rev, rim * (1 - 0.6 * rev), sweep=seg(lt, 2.4, 3.6))
    dust(fr, t, 0.15, 0.35, push=0.5 + lt * 0.02)
    T_LOGO.draw(fr, W / 2, 330, seg(lt, 3.0, 4.4), 0.09, 0.7); T_EDP.draw(fr, W / 2, 450, seg(lt, 3.8, 4.8), 0.03)
    return fr

def scene_hero(t):
    lt = t - 20.0
    pool = liquid_gold(t * 0.7, zoom=2.2, cx=0.5, cy=0.8); m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m); d.ellipse((W / 2 - 520, 1330, W / 2 + 520, 1600), fill=255); m = m.filter(ImageFilter.GaussianBlur(40))
    fr = Image.composite(pool, Image.new("RGB", (W, H), BLACK), m); fr = rays(fr, t, 0.9).convert("RGBA")
    dust(fr, t, 0.2, 0.9, push=lt * 0.03)
    draw_bottle(fr, W / 2, 1450 - BOTTLE.height / 2, 0.95 + 0.05 * ease_io(seg(lt, 0, 3.5)), 1, 0.35, sweep=seg(lt, 0.4, 1.8), refl=False)
    T_SOIR1.draw(fr, W / 2, 330, seg(lt, 0.5, 1.6)); T_SOIR2.draw(fr, W / 2, 470, seg(lt, 0.9, 2.2), shimmer=seg(lt, 2.0, 3.0))
    return fr

def scene_end(t):
    lt = t - 23.4; fr = Image.new("RGB", (W, H), BLACK); fr = rays(fr, t, 0.3).convert("RGBA"); dust(fr, t, 0.5, 0.6)
    out = ease(seg(t, 25.6, 26.4))
    T_END1.draw(fr, W / 2, 820, seg(lt, 0.2, 1.6), 0.08, 0.8, out=out, shimmer=seg(lt, 1.4, 2.4))
    T_PARIS.draw(fr, W / 2, 960, seg(lt, 0.9, 1.8), 0.05, out=out)
    T_INFO.draw(fr, W / 2, 1090, seg(lt, 1.2, 2.0), 0.02, out=out)
    bp = ease_io(seg(lt, 1.5, 2.3)) * (1 - out)
    if bp > 0:
        ov, d, s = ss((W, H), 2); w = 560 * bp; y0, y1 = 1240, 1330
        d.rectangle(((W / 2 - w / 2) * s, y0 * s, (W / 2 + w / 2) * s, y1 * s), outline=GOLD + (230,), width=2 * s)
        fr.alpha_composite(ov.resize((W, H), Image.LANCZOS))
    T_CTA.draw(fr, W / 2, 1285, seg(lt, 1.8, 2.5), 0.02, out=out); T_HANDLE.draw(fr, W / 2, 1440, seg(lt, 2.0, 2.6), 0.02, out=out)
    return fr

# ------------------------------------------------------------------ transitions
def tr_lightburn(t):
    """Le trait d'or s'ouvre verticalement en lumière et révèle l'or liquide."""
    p = seg(t, 3.0, 3.9); a = scene_intro(t).convert("RGB"); b = scene_liquid(t).convert("RGB")
    h = ease_in(p) * H * 1.2; yy = np.arange(H)[:, None]
    m = np.clip(1 - (np.abs(yy - 1010) - h / 2) / 120, 0, 1).repeat(W, 1)
    out = Image.composite(b, a, Image.fromarray((m * 255).astype(np.uint8)))
    edge = np.exp(-((np.abs(yy - 1010) - h / 2) / 60) ** 2).repeat(W, 1) * math.sin(math.pi * p)
    flare = Image.fromarray((np.dstack([edge * 255, edge * 225, edge * 170])).clip(0, 255).astype(np.uint8))
    return ImageChops.add(out, flare)

def tr_smoke(t, t0, t1, fa, fb):
    """Dissolution en fumée : un bruit animé ronge l'image A et laisse apparaître B."""
    p = seg(t, t0, t1); a = fa(t).convert("RGB"); b = fb(t).convert("RGB")
    n = smoke_noise(t, 1.4); thr = lerp(-0.15, 1.15, ease_io(p))
    m = np.clip((thr - n) / 0.18, 0, 1); edge = np.exp(-((n - thr) / 0.06) ** 2) * 0.9
    mi = Image.fromarray((m * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
    out = Image.composite(b, a, mi)
    e = Image.fromarray((edge * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(6))
    return ImageChops.add(out, Image.merge("RGB", [e.point(lambda v, c=c: v * c // 255) for c in (255, 210, 150)]))

def tr_rackfocus(t, t0, t1, fa, fb):
    """Bascule de point : A se floute pendant que la poussière du premier plan devient nette, puis B se précise."""
    p = seg(t, t0, t1)
    base = fa(t) if p < 0.5 else fb(t); bl = math.sin(math.pi * p) * 26
    img = base.convert("RGB").filter(ImageFilter.GaussianBlur(bl)) if bl > 0.5 else base.convert("RGB")
    fr = img.convert("RGBA"); dust(fr, t * 1.0, 1.0, math.sin(math.pi * p) * 1.4, push=0.3)
    return fr.convert("RGB")

def tr_ring(t, t0, t1, fa, fb):
    """Anneau d'or qui s'ouvre : l'intérieur montre la scène suivante."""
    p = ease_io(seg(t, t0, t1)); a = fa(t).convert("RGB"); b = fb(t).convert("RGB"); r = p * 1300
    m = Image.new("L", (W // 2, H // 2), 0); ImageDraw.Draw(m).ellipse(((540 - r) / 2, (860 - r) / 2, (540 + r) / 2, (860 + r) / 2), fill=255)
    out = Image.composite(b, a, m.resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(2)))
    ov, d, s = ss((W, H), 2); rr = r + 8
    d.ellipse(((540 - rr) * s, (860 - rr) * s, (540 + rr) * s, (860 + rr) * s), outline=GOLD_HI + (255,), width=3 * s)
    ov = ov.resize((W, H), Image.LANCZOS); o = out.convert("RGBA"); o.alpha_composite(ov.filter(ImageFilter.GaussianBlur(8))); o.alpha_composite(ov)
    return o.convert("RGB")

rngm = np.random.default_rng(21)
MIST = [(rngm.uniform(-0.5, 0.5), rngm.uniform(0.3, 1.0), rngm.uniform(0, 1)) for _ in range(160)]
def tr_spritz(t, t0, t1, fa, fb):
    """Brume de vaporisateur : un nuage de fines gouttes jaillit et éclaire tout."""
    p = seg(t, t0, t1); fr = (fa(t) if p < 0.45 else fb(t)).convert("RGBA")
    ox, oy = 540, 760
    for dx, sp, ph in MIST:
        q = clamp((p - ph * 0.25) / 0.75)
        if q <= 0: continue
        ang = -math.pi / 2 + dx * 1.6; dist = sp * 1100 * ease(q)
        x = ox + math.cos(ang) * dist * 1.3; y = oy + math.sin(ang) * dist * 0.5 + dist * 0.3
        a = (1 - q) * 0.9; spr = sprite(3 + q * 10, 1 + q * 8).point(lambda v, a=a: int(v * a))
        fr.paste(GOLDL.crop((0, 0, spr.width, spr.height)), (int(x), int(y)), spr)
    fl = math.sin(math.pi * clamp(seg(p, 0.3, 0.7))) * 0.42
    out = fr.convert("RGB")
    if fl > 0: out = Image.blend(out, Image.new("RGB", (W, H), (255, 232, 196)), fl)
    return out

# ------------------------------------------------------------------ montage
def N0(t): return scene_note(t, 0, 15.2)
def N1(t): return scene_note(t, 1, 16.75)
def N2(t): return scene_note(t, 2, 18.3)
def frame(t):
    if t < 3.0: return scene_intro(t).convert("RGB")
    if t < 3.9: return tr_lightburn(t)
    if t < 8.2: return scene_liquid(t).convert("RGB")
    if t < 9.4: return tr_smoke(t, 8.2, 9.4, scene_liquid, scene_bottle)
    if t < 14.6: return scene_bottle(t).convert("RGB")
    if t < 15.4: return tr_rackfocus(t, 14.6, 15.4, scene_bottle, N0)
    if t < 16.55: return N0(t).convert("RGB")
    if t < 17.05: return tr_ring(t, 16.55, 17.05, N0, N1)
    if t < 18.1: return N1(t).convert("RGB")
    if t < 18.6: return tr_ring(t, 18.1, 18.6, N1, N2)
    if t < 19.55: return N2(t).convert("RGB")
    if t < 20.35: return tr_spritz(t, 19.55, 20.35, N2, scene_hero)
    if t < 23.2: return scene_hero(t).convert("RGB")
    if t < 23.9: return tr_smoke(t, 23.2, 23.9, scene_hero, scene_end)
    return scene_end(t).convert("RGB")

FAST = [(3.0, 3.9), (19.55, 20.35)]
rng_g = np.random.default_rng(0)
GRAIN = [rng_g.normal(0, 4.0, (H // 2, W // 2, 1)).astype(np.float32).repeat(2, 0).repeat(2, 1) for _ in range(6)]
def post(img, n, t):
    # halo des hautes lumières
    sm = np.asarray(img.resize((W // 6, H // 6), Image.BILINEAR), np.float32)
    bl = Image.fromarray((np.clip(sm - 120, 0, 255) * 1.3).clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(8)).resize((W, H), Image.BICUBIC)
    img = ImageChops.add(img, bl.point(lambda v: int(v * 0.55)))
    a = np.asarray(img, np.float32)
    a = a * np.array([1.02, 1.0, 0.95])                      # étalonnage chaud
    a = 255 * (a / 255) ** 1.06
    a += GRAIN[n % 6]
    if t < 0.4: a *= t / 0.4
    if t > DUR - 0.6: a *= max(0, (DUR - t) / 0.6)
    out = Image.fromarray(a.clip(0, 255).astype(np.uint8)); letterbox(out, 1.0)
    return out
def render(n):
    t = n / FPS; k = 4 if any(a <= t < b for a, b in FAST) else 2
    acc = sum(np.asarray(frame(min(DUR - 0.001, max(0, t + (i / (k - 1) - 0.5) * 0.5 / FPS))), np.float32) for i in range(k)) / k
    return np.asarray(post(Image.fromarray(acc.clip(0, 255).astype(np.uint8)), n, t)).tobytes()

TIMES = {"dur": DUR, "linedraw": 0.3, "words": [0.8, 1.5], "burn": 3.0, "liquid": [3.6, 8.6], "nuit": 4.6, "smoke": [8.2, 23.2],
         "rim": 9.4, "sweep": [11.4, 20.4], "logo": 12.0, "rack": 14.6, "notes": [15.2, 16.75, 18.3], "rings": [16.55, 18.1],
         "spritz": 19.55, "hero": 20.35, "soir": 20.5, "end": 23.6, "endlogo": 23.6}

if __name__ == "__main__":
    wav = OUT.replace(".mp4", ".wav")
    subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "aurele_audio.py"), wav, json.dumps(TIMES)], check=True)
    ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "slow", "-crf", "20",
                           "-maxrate", "7M", "-bufsize", "14M", "-pix_fmt", "yuv420p",
                           "-af", "loudnorm=I=-14:TP=-1:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "256k",
                           "-shortest", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
    sel = [int(float(x) * FPS) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else range(int(DUR * FPS))
    with Pool(4) as pool:
        for i, b in enumerate(pool.imap(render, sel, chunksize=2)):
            ff.stdin.write(b)
            if i % 100 == 0: print(i, flush=True)
    ff.stdin.close(); ff.wait(); os.remove(wav); print("ok", OUT)
