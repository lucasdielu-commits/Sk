"""ORVA — motion design « app promo » (marque fictive), 9:16, 1080x1920, 30 i/s, ~29,5 s.

Usage : python3 orva.py <dossier_polices> <sortie.mp4> [temps,à,prévisualiser]
"""
import json, math, os, subprocess, sys
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

FONTS, OUT = sys.argv[1], sys.argv[2]
W, H, FPS = 1080, 1920, 30
DUR = 29.5
BLACK = (7, 7, 10); PANEL = (19, 19, 25); PANEL2 = (32, 32, 41); LINE = (48, 48, 60)
RED = (255, 46, 59); RED2 = (170, 14, 30); WHITE = (246, 246, 248); GREY = (138, 138, 152)

# ------------------------------------------------------------------ base
def font(w, size):
    return ImageFont.truetype(os.path.join(FONTS, f"fontsource-jost-5.3.0/files/jost-latin-{w}-normal.woff"), size)

def text(txt, w, size, color, track=0, pad=30, skew=0.0):
    f = font(w, size); ws = [f.getlength(c) for c in txt]
    tw = int(sum(ws) + track * (len(txt) - 1)); asc, desc = f.getmetrics()
    im = Image.new("RGBA", (tw + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    x = pad
    for c, w_ in zip(txt, ws): d.text((x, pad), c, font=f, fill=color); x += w_ + track
    if skew:
        ext = int(im.height * abs(skew)) + 4
        im = im.transform((im.width + ext, im.height), Image.AFFINE, (1, skew, -ext if skew < 0 else 0, 0, 1, 0), Image.BICUBIC)
    return im

def glow(im, radius=18, strength=1.0, color=RED):
    pad = radius * 3
    big = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0)); big.paste(im, (pad, pad), im)
    a = big.split()[3].filter(ImageFilter.GaussianBlur(radius)).point(lambda v: min(255, int(v * strength)))
    halo = Image.new("RGBA", big.size, color + (0,)); halo.putalpha(a); halo.alpha_composite(big); return halo

def alpha(im, a):
    if im is None or a <= 0: return None
    if a >= 0.999: return im
    r, g, b, al = im.split(); return Image.merge("RGBA", (r, g, b, al.point(lambda v: int(v * a))))

def put(fr, im, cx, cy, a=1.0, scale=1.0):
    if im is None or a <= 0 or scale <= 0.01: return
    if abs(scale - 1) > 0.004:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    im = alpha(im, a)
    if im is not None: fr.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def put_tl(fr, im, x, y, a=1.0):
    im = alpha(im, a)
    if im is not None: fr.alpha_composite(im, (int(x), int(y)))

def mblur(im, dx, dy=0, n=9):
    if abs(dx) < 2 and abs(dy) < 2: return im
    px, py = int(abs(dx)) + 2, int(abs(dy)) + 2
    a = np.zeros((im.height + 2 * py, im.width + 2 * px, 4), np.float32)
    src = np.asarray(im).astype(np.float32); src[..., :3] *= src[..., 3:4] / 255
    for k in range(n):
        f = k / (n - 1) - 0.5; ox, oy = int(px + dx * f), int(py + dy * f)
        a[oy:oy + im.height, ox:ox + im.width] += src
    a /= n; rgb = a[..., :3] / np.maximum(a[..., 3:4], 1) * 255
    return Image.fromarray(np.dstack([rgb, a[..., 3:4]]).clip(0, 255).astype(np.uint8))

def frame_mblur(arr, dx, dy=0, n=10):
    if abs(dx) < 2 and abs(dy) < 2: return arr
    ix, iy = np.arange(W), np.arange(H); acc = np.zeros(arr.shape, np.float32)
    for k in range(n):
        f = k / (n - 1) - 0.5
        acc += arr[np.clip(iy - int(dy * f), 0, H - 1)][:, np.clip(ix - int(dx * f), 0, W - 1)]
    return (acc / n).astype(np.uint8)

def zoom_blur(img, amount, n=8, cx=W / 2, cy=H / 2):
    """Flou radial (zoom) d'une image RGB."""
    if amount < 0.005: return img
    acc = np.zeros((H, W, 3), np.float32)
    for k in range(n):
        s = 1 + amount * k / (n - 1); w_, h_ = W / s, H / s
        box = (cx - w_ * cx / W, cy - h_ * cy / H, cx - w_ * cx / W + w_, cy - h_ * cy / H + h_)
        acc += np.asarray(img.resize((W, H), Image.BILINEAR, box=box), np.float32)
    return Image.fromarray((acc / n).astype(np.uint8))

def chroma(img, k):
    if k < 1: return img
    r, g, b = img.split()
    return Image.merge("RGB", (ImageChops.offset(r, int(k), 0), g, ImageChops.offset(b, -int(k), 0)))

def ease(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3
def ease_in(x): x = min(1, max(0, x)); return x ** 3
def ease_io(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
def back(x, s=1.8): x = min(1, max(0, x)) - 1; return x * x * ((s + 1) * x + s) + 1
def lerp(a, b, x): return a + (b - a) * x
def seg(t, a, b): return (t - a) / (b - a)

class SSDraw:
    """Dessin sur-échantillonné (anti-crénelage) : mêmes appels qu'ImageDraw, coordonnées d'origine."""
    def __init__(self, size, s=3, ox=0, oy=0):
        self.size = (int(size[0]), int(size[1])); self.s, self.ox, self.oy = s, ox, oy
        self.im = Image.new("RGBA", (self.size[0] * s, self.size[1] * s), (0, 0, 0, 0)); self.d = ImageDraw.Draw(self.im)
    def _p(self, xy):
        flat = []
        for v in xy:
            if isinstance(v, (tuple, list)): flat += [v[0], v[1]]
            else: flat.append(v)
        return [((flat[i] - self.ox) * self.s, (flat[i + 1] - self.oy) * self.s) for i in range(0, len(flat), 2)]
    def _box(self, xy):
        p = self._p(xy); return (p[0][0], p[0][1], p[1][0], p[1][1])
    def line(self, xy, fill=None, width=1, joint=None):
        pts = self._p(xy); w = max(1, int(width * self.s)); self.d.line(pts, fill=fill, width=w, joint=joint)
        if width >= 3:
            for x, y in (pts[0], pts[-1]): self.d.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=fill)
    def ellipse(self, xy, fill=None, outline=None, width=1): self.d.ellipse(self._box(xy), fill=fill, outline=outline, width=int(width * self.s))
    def arc(self, xy, start, end, fill=None, width=1): self.d.arc(self._box(xy), start, end, fill=fill, width=int(width * self.s))
    def rectangle(self, xy, fill=None, outline=None, width=1): self.d.rectangle(self._box(xy), fill=fill, outline=outline, width=int(width * self.s))
    def rounded_rectangle(self, xy, radius, fill=None, outline=None, width=1):
        self.d.rounded_rectangle(self._box(xy), radius * self.s, fill=fill, outline=outline, width=int(width * self.s))
    def polygon(self, xy, fill=None, outline=None, width=1):
        self.d.polygon(self._p(xy), fill=fill, outline=outline, width=int(width * self.s))
    def result(self): return self.im.resize(self.size, Image.LANCZOS)

def rounded(w, h, r, fill, outline=None, width=0):
    d = SSDraw((w, h), 3); d.rounded_rectangle((0, 0, w - 1, h - 1), r, fill=fill, outline=outline, width=width); return d.result()

def disc(s, fill, outline=None, width=0):
    d = SSDraw((s, s), 3); d.ellipse((0, 0, s - 1, s - 1), fill=fill, outline=outline, width=width); return d.result()

def grad(w, h, c0, c1, angle=0.0):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    k = (xx / w * math.cos(angle) + yy / h * math.sin(angle)); k = (k - k.min()) / (k.max() - k.min())
    a = np.array(c0)[None, None] * (1 - k[..., None]) + np.array(c1)[None, None] * k[..., None]
    return Image.fromarray(a.clip(0, 255).astype(np.uint8)).convert("RGBA")

def mask_round(im, r):
    m = rounded(im.width, im.height, r, (255, 255, 255, 255)).split()[3]
    out = im.copy(); out.putalpha(ImageChops.multiply(out.split()[3], m)); return out

# perspective 3D
def persp_coeffs(src, dst):
    A, B = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    return np.linalg.solve(np.array(A, float), np.array(B, float)).tolist()

def tilt(im, ry=0.0, rx=0.0, rz=0.0, f=1900):
    w, h = im.size; ry, rx, rz = map(math.radians, (ry, rx, rz)); pts = []
    for x, y in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
        x, y = x * math.cos(rz) - y * math.sin(rz), x * math.sin(rz) + y * math.cos(rz)
        x1 = x * math.cos(ry); z1 = x * math.sin(ry)
        y1 = y * math.cos(rx) - z1 * math.sin(rx); z2 = y * math.sin(rx) + z1 * math.cos(rx)
        s = f / (f + z2); pts.append((x1 * s, y1 * s))
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]; ox, oy = min(xs), min(ys)
    ow, oh = int(max(xs) - ox) + 2, int(max(ys) - oy) + 2
    c = persp_coeffs([(0, 0), (w, 0), (w, h), (0, h)], [(p[0] - ox, p[1] - oy) for p in pts])
    return im.transform((ow, oh), Image.PERSPECTIVE, c, Image.BICUBIC), (ox + ow / 2, oy + oh / 2)

def put3d(fr, im, cx, cy, ry=0, rx=0, rz=0, a=1.0, scale=1.0):
    if im is None or a <= 0: return
    if abs(scale - 1) > 0.004: im = im.resize((max(2, int(im.width * scale)), max(2, int(im.height * scale))), Image.BICUBIC)
    if abs(ry) > 0.2 or abs(rx) > 0.2 or abs(rz) > 0.2:
        im, (dx, dy) = tilt(im, ry, rx, rz); cx += dx; cy += dy
    put(fr, im, cx, cy, a)

# ------------------------------------------------------------------ fond
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H * 0.95) / H) ** 2)
BG = Image.fromarray((np.array(BLACK)[None, None] + np.array([60, 4, 10])[None, None]
                      * np.clip(1 - _r * 1.9, 0, 1)[..., None] ** 2).clip(0, 255).astype(np.uint8)).convert("RGBA")
_s = np.sqrt(((xx - W / 2) / (W * 0.55)) ** 2 + ((yy - H * 0.55) / (H * 0.3)) ** 2)
SPOT = Image.new("RGBA", (W, H), RED + (0,)); SPOT.putalpha(Image.fromarray((np.exp(-_s ** 2 * 1.4) * 200).astype(np.uint8)))
VIG = Image.new("RGBA", (W, H), (0, 0, 0, 0))
VIG.putalpha(Image.fromarray((np.clip(((xx - W / 2) / (W * .7)) ** 2 + ((yy - H / 2) / (H * .65)) ** 2 - .3, 0, 1) * 150).astype(np.uint8)))

def dot(r, a=1.0):
    s = int(r * 7); im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); dd = disc(int(2 * r), (255, 90, 100, 255))
    im.alpha_composite(dd, (int(s / 2 - r), int(s / 2 - r)))
    return alpha(glow(glow(im, max(3, int(r * .8)), 2.5), max(6, int(r * 2.2)), 1.4), a)

# ------------------------------------------------------------------ icônes
def _icon_raw(kind, s=76, color=WHITE):
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = color + (255,); w = max(3, s // 14)
    if kind == "arrow":
        d.line((s * .25, s * .75, s * .75, s * .25), fill=c, width=w); d.line((s * .4, s * .25, s * .75, s * .25, s * .75, s * .6), fill=c, width=w)
    elif kind == "down":
        d.line((s * .75, s * .25, s * .25, s * .75), fill=c, width=w); d.line((s * .6, s * .75, s * .25, s * .75, s * .25, s * .4), fill=c, width=w)
    elif kind == "card":
        d.rounded_rectangle((s * .15, s * .28, s * .85, s * .72), s * .08, outline=c, width=w); d.line((s * .15, s * .42, s * .85, s * .42), fill=c, width=w)
    elif kind == "lock":
        d.rounded_rectangle((s * .25, s * .45, s * .75, s * .82), s * .07, outline=c, width=w); d.arc((s * .33, s * .18, s * .67, s * .62), 180, 360, fill=c, width=w)
    elif kind == "vault":
        d.ellipse((s * .2, s * .2, s * .8, s * .8), outline=c, width=w); d.ellipse((s * .42, s * .42, s * .58, s * .58), fill=c)
    elif kind == "check":
        d.line((s * .25, s * .52, s * .43, s * .7, s * .76, s * .32), fill=c, width=int(w * 1.4), joint="curve")
    elif kind == "plane":
        d.polygon([(s * .15, s * .5), (s * .85, s * .2), (s * .6, s * .85), (s * .5, s * .58)], outline=c, width=w)
    elif kind == "search":
        d.ellipse((s * .18, s * .18, s * .62, s * .62), outline=c, width=w); d.line((s * .56, s * .56, s * .82, s * .82), fill=c, width=w)
    elif kind == "clock":
        d.ellipse((s * .18, s * .18, s * .82, s * .82), outline=c, width=w); d.line((s * .5, s * .32, s * .5, s * .5, s * .64, s * .6), fill=c, width=w)
    elif kind == "shield":
        d.polygon([(s * .5, s * .1), (s * .86, s * .24), (s * .8, s * .62), (s * .5, s * .9), (s * .2, s * .62), (s * .14, s * .24)], outline=c, width=w)
        d.line((s * .33, s * .5, s * .46, s * .63, s * .68, s * .38), fill=c, width=w)
    elif kind == "wave":
        for k in range(3): d.arc((s * (.1 - k * .0) + k * s * .12, s * .2, s * .9 - k * 0, s * .8), -50, 50, fill=c, width=w)
    return im

def icon(kind, s=76, color=WHITE):
    return _icon_raw(kind, s * 3, color).resize((s, s), Image.LANCZOS)

def circle_icon(kind, s=96, bg=RED, fg=WHITE):
    im = disc(s, bg + (255,))
    ic = icon(kind, int(s * .62), fg); im.alpha_composite(ic, ((s - ic.width) // 2, (s - ic.height) // 2)); return im

# ------------------------------------------------------------------ logo
def logo(scale=1.0):
    t = text("ORVA", "900", int(250 * scale), WHITE, track=int(8 * scale), skew=-0.22)
    im = Image.new("RGBA", (t.width + 40, t.height + int(70 * scale)), (0, 0, 0, 0)); im.alpha_composite(t, (20, 0))
    d = SSDraw(im.size, 3); y = t.height - int(48 * scale); x0 = 60 * scale
    d.polygon([(x0 + 40 * scale, y), (im.width - 40 * scale, y), (im.width - 80 * scale, y + 26 * scale), (x0, y + 26 * scale)], fill=RED + (255,))
    im.alpha_composite(d.result())
    return glow(im, int(16 * scale), 0.6)
LOGO = logo(); LOGO_SUB = text("BANQUE MOBILE", "500", 40, (220, 220, 228), track=22)

# ------------------------------------------------------------------ écrans d'appli
HOME_BAR = None
def status_bar(fr, a=1.0):
    put_tl(fr, text("9:41", "600", 36, WHITE, pad=0), 70, 52, a)
    d = SSDraw((150, 40), 3)
    for k in range(4): d.rectangle((k * 14, 26 - k * 7, k * 14 + 9, 34), fill=WHITE + (255,))
    d.rounded_rectangle((70, 8, 128, 34), 8, outline=WHITE + (180,), width=3); d.rounded_rectangle((75, 13, 116, 29), 4, fill=WHITE + (255,))
    d.rounded_rectangle((131, 16, 135, 26), 2, fill=WHITE + (180,))
    put_tl(fr, d.result(), W - 210, 50, a)
    isl = rounded(250, 74, 37, (0, 0, 0, 255)); put_tl(fr, isl, W / 2 - 125, 28, a)
    put_tl(fr, HOME_BAR, W / 2 - 160, H - 44, a)

HOME_BAR = rounded(320, 12, 6, (255, 255, 255, 150))
RECENTS = [("arrow", "Virement à Léa", "Hier · 24,50 €"), ("card", "Carte virtuelle", "Créée en 3 s"),
           ("plane", "Coffre « Lisbonne »", "62 % de l'objectif"), ("lock", "Bloquer ma carte", "En un geste")]
def screen_search(t):
    fr = Image.new("RGBA", (W, H), BLACK + (255,)); lt = t - 3.6
    status_bar(fr)
    put_tl(fr, text("Rechercher", "800", 84, WHITE, pad=0), 70, 150)
    fr.alpha_composite(rounded(940, 128, 64, PANEL2 + (255,)), (70, 290))
    put_tl(fr, icon("search", 64, GREY), 110, 322)
    q = "carte"; n = int(max(0, min(len(q), (lt - 0.45) / 0.09)))
    qt = text(q[:n] if n else "Paiement, ami, coffre…", "400", 48, WHITE if n else GREY, pad=0); put_tl(fr, qt, 200, 326)
    if n and (int(t * 4) % 2 == 0 or n < len(q)): fr.alpha_composite(rounded(5, 60, 2, RED + (255,)), (206 + qt.width, 324))
    put_tl(fr, text("Récent", "600", 40, GREY, pad=0, track=2), 70, 480, ease(seg(lt, 0.3, 0.6)))
    for k, (ic, a_, b_) in enumerate(RECENTS):
        p = ease(seg(lt, 0.55 + 0.11 * k, 0.9 + 0.11 * k))
        if p <= 0: continue
        row = Image.new("RGBA", (W, 160), (0, 0, 0, 0))
        row.alpha_composite(circle_icon(ic, 104, PANEL2, RED), (70, 28))
        row.alpha_composite(text(a_, "500", 46, WHITE, pad=0), (210, 34)); row.alpha_composite(text(b_, "400", 34, GREY, pad=0), (210, 96))
        ImageDraw.Draw(row).line((210, 158, 1010, 158), fill=LINE + (255,), width=2)
        put_tl(fr, row, (1 - p) * 120, 560 + k * 170, p)
    rp = seg(lt, 1.7, 2.1)
    if 0 < rp < 1:
        r_ = 30 + 700 * ease(rp); d = SSDraw((2 * r_ + 4, 2 * r_ + 4), 2, W / 2 - r_ - 2, 810 - r_ - 2)
        d.ellipse((W / 2 - r_, 810 - r_, W / 2 + r_, 810 + r_), fill=RED + (int(90 * (1 - rp)),))
        fr.alpha_composite(d.result(), (int(W / 2 - r_ - 2), int(810 - r_ - 2)))
    return fr

rng0 = np.random.default_rng(4)
CHART = np.cumsum(rng0.normal(0.6, 2.2, 60)); CHART = np.convolve(CHART, np.ones(5) / 5, "valid")
CHART = (CHART - CHART.min()) / (CHART.max() - CHART.min())
TXS = [("arrow", "Café Lumière", "Aujourd'hui", "-3,80 €"), ("down", "Salaire", "1er du mois", "+2 100,00 €"), ("card", "Métro", "Hier", "-2,10 €")]
def screen_home(t):
    fr = Image.new("RGBA", (W, H), BLACK + (255,)); lt = t - 6.15
    status_bar(fr)
    put_tl(fr, text("Bonjour Inès", "400", 46, GREY, pad=0), 70, 150)
    fr.alpha_composite(circle_icon("vault", 96, PANEL2, WHITE), (W - 170, 135))
    put_tl(fr, text("Solde total", "500", 38, GREY, pad=0), 70, 262)
    v = 2480 * ease(seg(lt, 0.15, 1.3)); s = f"{v:,.2f}".replace(",", " ").replace(".", ",") + " €"
    put_tl(fr, text(s, "800", 150, WHITE, pad=0), 62, 300)
    pill = rounded(300, 64, 32, (60, 14, 20, 255)); pill.alpha_composite(text("+12,4 % ce mois", "600", 30, RED, pad=0), (28, 14))
    put_tl(fr, pill, 70, 500, ease(seg(lt, 1.0, 1.3)))
    # courbe dessinée
    x0, y0, cw, ch = 70, 620, 940, 330; p = ease_io(seg(lt, 0.3, 1.5)); n = max(2, int(len(CHART) * p))
    pts = [(x0 + cw * i / (len(CHART) - 1), y0 + ch * (1 - CHART[i])) for i in range(n)]
    d = SSDraw((cw + 80, ch + 80), 3, x0 - 40, y0 - 40)
    fill = grad(cw + 80, ch + 80, (255, 46, 59), (7, 7, 10), math.pi / 2)
    d.polygon(pts + [(pts[-1][0], y0 + ch), (pts[0][0], y0 + ch)], fill=(255, 255, 255, 255))
    area = d.result().split()[3].point(lambda v: v * 70 // 255); fill.putalpha(area); fr.alpha_composite(fill, (x0 - 40, y0 - 40))
    d = SSDraw((cw + 80, ch + 80), 3, x0 - 40, y0 - 40); d.line(pts, fill=RED + (255,), width=7, joint="curve")
    fr.alpha_composite(glow(d.result(), 8, 0.45), (x0 - 40 - 24, y0 - 40 - 24))
    put(fr, dot(10), pts[-1][0], pts[-1][1])
    for k, (ic, lab) in enumerate((("arrow", "Envoyer"), ("down", "Recevoir"), ("card", "Carte"), ("vault", "Coffre"))):
        b = back(seg(lt, 0.9 + 0.08 * k, 1.25 + 0.08 * k)); cx = 70 + 120 + k * 233
        put(fr, circle_icon(ic, 150, RED if k == 0 else PANEL2, WHITE), cx - 50, 1100, 1 if b > 0 else 0, b)
        put(fr, text(lab, "500", 32, WHITE, pad=0), cx - 50, 1210, ease(seg(lt, 1.1 + 0.08 * k, 1.4 + 0.08 * k)))
    put_tl(fr, text("Activité", "700", 48, WHITE, pad=0), 70, 1300, ease(seg(lt, 1.2, 1.5)))
    for k, (ic, a_, b_, amt) in enumerate(TXS):
        p = ease(seg(lt, 1.3 + 0.1 * k, 1.65 + 0.1 * k))
        if p <= 0: continue
        row = Image.new("RGBA", (W, 150), (0, 0, 0, 0)); row.alpha_composite(circle_icon(ic, 96, PANEL2, WHITE), (70, 24))
        row.alpha_composite(text(a_, "500", 42, WHITE, pad=0), (200, 30)); row.alpha_composite(text(b_, "400", 30, GREY, pad=0), (200, 86))
        at = text(amt, "600", 42, RED if amt.startswith("+") else WHITE, pad=0); row.alpha_composite(at, (1010 - at.width, 46))
        put_tl(fr, row, 0, 1390 + k * 150 + (1 - p) * 60, p)
    return fr

# tuiles de la grille
def tile(k):
    w, h = 320, 440; rng = np.random.default_rng(k + 10)
    styles = [(RED, RED2), (PANEL2, BLACK), ((245, 245, 248), (200, 200, 210)), ((90, 8, 18), BLACK), (RED2, (40, 2, 8))]
    c0, c1 = styles[k % len(styles)]; im = grad(w, h, c0, c1, rng.uniform(0.3, 1.2))
    light = c0[0] > 200 and c0[1] > 200; fg = BLACK if light else WHITE
    kind = k % 4
    if kind == 0:
        im.alpha_composite(text(rng.choice(["+24 €", "-3,80 €", "+120 €", "-12 €"]), "800", 70, fg, pad=0), (28, h - 130))
        im.alpha_composite(icon(rng.choice(["arrow", "down"]), 70, fg), (28, 28))
    elif kind == 1:
        im.alpha_composite(rounded(260, 160, 18, None, fg + (255,), 5), (30, 150))
        im.alpha_composite(text("ORVA", "900", 44, fg, pad=0, skew=-0.2), (50, 170))
    elif kind == 2:
        im.alpha_composite(icon(rng.choice(["plane", "vault", "lock", "shield"]), 160, fg), (80, 100))
        im.alpha_composite(text(rng.choice(["Voyage", "Coffre", "Sécurité", "Projet"]), "600", 46, fg, pad=0), (28, h - 100))
    else:
        vals = rng.uniform(0.2, 1, 6)
        for i, v in enumerate(vals): im.alpha_composite(rounded(30, int(v * 260), 10, fg + (255,)), (34 + i * 45, int(380 - v * 260)))
    return mask_round(im, 34)
TILES = [tile(k) for k in range(15)]
def tile248():
    w, h = 320, 440; im = grad(w, h, RED, RED2, 1.0)
    im.alpha_composite(text("248 k", "900", 92, WHITE, pad=0), (26, 150)); im.alpha_composite(text("membres", "500", 34, WHITE, pad=0), (30, 270))
    return mask_round(im, 34)
T248 = tile248()

def scene_grid(t):
    fr = BG.copy(); lt = t - 8.6
    cols = [(-350, 1.0, 0.0), (0, 1.35, 120), (350, 0.85, 260)]
    for ci, (dx, sp, off) in enumerate(cols):
        # défilement qui freine : la tuile « 248 k » finit pile au centre
        k = ease(seg(lt, 0, 1.65)); D = 2180 * sp / 1.35
        y0 = 2200 + off * (1 - k) - D * k - (0 if ci == 1 else off)
        speed = D * 3 * (1 - min(1, lt / 1.65)) ** 2 / 1.65
        for r in range(5):
            idx = (ci * 5 + r) % 15
            im = T248 if (ci == 1 and r == 2) else TILES[idx]
            y = y0 + r * 470
            if -300 < y < H + 300:
                put(fr, mblur(im, 0, -speed / FPS * 1.2, 7), W / 2 + dx, y)
    return fr

def scene_counter(t):
    fr = BG.copy(); fr.alpha_composite(alpha(SPOT, 0.5)); lt = t - 10.4
    z = ease_io(seg(lt, 0, 0.35))
    w, h = int(lerp(320, 780, z)), int(lerp(440, 1060, z))
    c = grad(w, h, RED, RED2, 1.0)
    v = int(248 * ease(seg(lt, 0.2, 1.1)))
    big = text(f"{v} k", "900", int(lerp(92, 230, z)), WHITE, pad=0); c.alpha_composite(big, ((w - big.width) // 2, int(h * .32)))
    lab = text("membres actifs", "500", int(lerp(34, 56, z)), WHITE, pad=0); c.alpha_composite(lab, ((w - lab.width) // 2, int(h * .32) + big.height + 20))
    for i, col in enumerate((WHITE, (255, 200, 205), (40, 8, 14), (255, 140, 150), WHITE)):
        b = back(seg(lt, 0.6 + 0.07 * i, 0.9 + 0.07 * i))
        if b > 0 and z > 0.9:
            av = Image.new("RGBA", (110, 110), (0, 0, 0, 0)); av.alpha_composite(disc(104, col + (255,), RED2 + (255,), 6), (3, 3))
            ini = text("AJLMS"[i], "700", 46, RED2 if col != (40, 8, 14) else WHITE, pad=0); av.alpha_composite(ini, ((110 - ini.width) // 2, 24))
            av = av.resize((max(1, int(110 * b)), max(1, int(110 * b)))); c.alpha_composite(av, (int(w / 2 - 230 + i * 92 - av.width / 2), int(h * .86 - av.height / 2)))
    c = mask_round(c, 50)
    put3d(fr, glow(c, 40, 0.35), W / 2, H / 2, 10 * math.sin(lt * 2.2), 6 * math.cos(lt * 1.7), 0, 1)
    for i in range(6):
        b = seg(lt, 0.7 + 0.12 * i, 1.3 + 0.12 * i)
        if 0 < b < 1:
            put(fr, text("+1", "700", 56, WHITE), W / 2 + math.cos(i * 2.1) * 470, H / 2 - 300 + math.sin(i * 1.7) * 600 - b * 160, 1 - b, back(b * 2))
    return fr

def bubble(txt, mine, w_max=720):
    tt = text(txt, "500", 42, WHITE, pad=0); w = tt.width + 70; h = tt.height + 56
    b = rounded(w, h, 40, (RED if mine else PANEL2) + (255,)); b.alpha_composite(tt, (35, 24)); return b
CHAT = [(12.25, bubble("Tu me rembourses le resto ?", False), False), (12.75, bubble("C'est fait !", True), True)]
def transfer_card():
    c = rounded(640, 210, 40, PANEL + (255,), RED + (255,), 4)
    c.alpha_composite(circle_icon("check", 110, RED, WHITE), (36, 50))
    c.alpha_composite(text("Virement envoyé", "600", 40, WHITE, pad=0), (170, 52)); c.alpha_composite(text("24,50 € · instantané", "400", 34, GREY, pad=0), (170, 110))
    return c
TRANSFER = transfer_card(); LAST = bubble("Déjà reçu. Trop rapide.", False)
def scene_chat(t):
    fr = Image.new("RGBA", (W, H), BLACK + (255,)); lt = t - 12.0
    status_bar(fr)
    av = disc(110, (255, 200, 205, 255))
    av.alpha_composite(text("L", "700", 56, RED2, pad=0), (36, 16)); fr.alpha_composite(av, (70, 150))
    put_tl(fr, text("Léa", "700", 54, WHITE, pad=0), 210, 154); put_tl(fr, text("en ligne", "400", 32, RED, pad=0), 212, 222)
    ImageDraw.Draw(fr).line((0, 300, W, 300), fill=LINE + (255,), width=2)
    items = [(12.25, CHAT[0][1], False), (12.75, CHAT[1][1], True), (13.1, TRANSFER, True), (13.65, LAST, False)]
    y = 380
    for t0, im, mine in items:
        p = back(seg(t, t0, t0 + 0.3))
        if t < t0 - 0.35: break
        if t < t0 and not mine:          # trois petits points « en train d'écrire »
            ty = rounded(180, 90, 45, PANEL2 + (255,))
            for i in range(3):
                o = 8 * math.sin(t * 14 - i * 0.9); ty.alpha_composite(disc(24, GREY + (255,)), (38 + i * 40, int(36 - o)))
            put_tl(fr, ty, 70, y); break
        if p > 0:
            x = W - 70 - im.width if mine else 70
            sc = max(0.01, p); ims = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))))
            put_tl(fr, ims, x + (im.width - ims.width) * (1 if mine else 0), y + (im.height - ims.height) / 2)
        y += im.height + 34
    return fr

def card_face(w=856, h=540):
    c = grad(w, h, (226, 32, 46), (34, 3, 8), 0.9); d = SSDraw((w, h), 2)
    for k in range(9): d.arc((-400 + k * 70, 120, 900 + k * 70, 1300), 200, 300, fill=(255, 255, 255, 16), width=2)
    c.alpha_composite(d.result())
    chip = rounded(120, 92, 18, (232, 200, 140, 255)); cd = ImageDraw.Draw(chip)
    for y in (30, 60): cd.line((0, y, 120, y), fill=(190, 150, 90, 255), width=3)
    cd.line((60, 0, 60, 92), fill=(190, 150, 90, 255), width=3); c.alpha_composite(chip, (70, 190))
    c.alpha_composite(icon("wave", 80, WHITE), (210, 196))
    c.alpha_composite(text("ORVA", "900", 84, WHITE, pad=0, skew=-0.22), (66, 50))
    c.alpha_composite(text("•••• 4821", "500", 48, WHITE, pad=0, track=4), (70, 340))
    c.alpha_composite(text("INÈS MARCHAL", "500", 34, (255, 220, 224), pad=0, track=4), (70, 440))
    c.alpha_composite(text("BLACK", "800", 38, WHITE, pad=0, track=6), (w - 190, 445))
    return mask_round(c, 40)
def card_back(w=856, h=540):
    c = grad(w, h, (40, 4, 10), (12, 2, 4), 0.4); ImageDraw.Draw(c).rectangle((0, 70, w, 170), fill=(5, 5, 5, 255))
    c.alpha_composite(rounded(540, 70, 10, (240, 236, 236, 255)), (60, 240)); c.alpha_composite(text("ORVA", "900", 54, RED, pad=0, skew=-0.22), (w - 220, 420))
    return mask_round(c, 40)
CARD = card_face(); CARDB = card_back()
def sweep(im, k, strength=0.5):
    if not (0 < k < 1): return im
    band = Image.new("L", im.size, 0); bw = 220
    x = int(lerp(-bw * 2, im.width + bw, k))
    ImageDraw.Draw(band).polygon([(x, 0), (x + bw, 0), (x + bw - 160, im.height), (x - 160, im.height)], fill=int(255 * strength))
    band = ImageChops.multiply(band.filter(ImageFilter.GaussianBlur(30)), im.split()[3])
    out = im.copy(); out.alpha_composite(Image.merge("RGBA", (Image.new("L", im.size, 255),) * 3 + (band,))); return out

def scene_card3d(t):
    fr = BG.copy(); lt = t - 14.0
    put_tl(fr, SPOT, 0, 0, 0.85 + 0.15 * math.sin(lt * 5))
    ry = lerp(200, -18, ease(seg(lt, 0, 1.3))) + 5 * math.sin(lt * 2)
    face = CARD if math.cos(math.radians(ry)) >= 0 else CARDB
    face = sweep(face, seg(lt, 1.0, 1.7))
    rx = 14; cy = 900 + 14 * math.sin(lt * 2.4)
    put3d(fr, glow(face, 34, 0.5, RED), W / 2, cy, ry, rx, -6)
    refl = face.transpose(Image.FLIP_TOP_BOTTOM)
    m = Image.fromarray((np.linspace(110, 0, refl.height)[:, None].repeat(refl.width, 1)).astype(np.uint8))
    refl.putalpha(ImageChops.multiply(refl.split()[3], m))
    put3d(fr, refl, W / 2, cy + 560, ry, -rx, 6, 0.6)
    put(fr, text("ORVA Black", "700", 92, WHITE, track=-2), W / 2, 1460, ease(seg(lt, 0.9, 1.3)))
    put(fr, text("Carte métal · paiement sans contact", "400", 40, GREY), W / 2, 1560, ease(seg(lt, 1.1, 1.5)))
    return fr

rng1 = np.random.default_rng(9)
STREAKS = [(rng1.uniform(0, H), rng1.uniform(0.3, 1.0), rng1.uniform(0, W * 3), rng1.choice([0, 1, 1])) for _ in range(70)]
T_PARTOUT = glow(text("PARTOUT.", "800", 150, WHITE, track=-3), 10, 0.3)
T_TOUT = glow(text("TOUT LE TEMPS.", "800", 112, RED, track=-2), 12, 0.4, RED)
def scene_streaks(t):
    fr = BG.copy(); lt = t - 16.0; ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for y, z, x0, col in STREAKS:
        sp = 2600 * z; x = (x0 - lt * sp) % (W * 3) - W; L = 260 * z + 80
        c = (RED if col else WHITE) + (int(255 * z * 0.8),)
        d.line((x, y, x + L, y), fill=c, width=max(2, int(7 * z)))
    fr.alpha_composite(ov.filter(ImageFilter.GaussianBlur(2))); fr.alpha_composite(ov)
    p = ease_in(seg(lt, 0.0, 1.75)); sc = lerp(0.12, 2.4, p)
    put3d(fr, CARD, W / 2, H / 2 + 60, lerp(-25, 10, p), 20 * (1 - p), lerp(-14, 4, p), min(1, p * 4), sc)
    for im, y, t0 in ((T_PARTOUT, 520, 0.2), (T_TOUT, 680, 0.5)):
        k = ease(seg(lt, t0, t0 + 0.25))
        if k > 0: put(fr, mblur(im, (1 - k) * 260), lerp(W / 2 + 400, W / 2, k), y, k)
    return fr

NOTIFS = [("check", "Paiement accepté", "Boulangerie · 4,20 €"), ("arrow", "Virement reçu", "De Hugo · 15,00 €"),
          ("shield", "Connexion vérifiée", "iPhone d'Inès"), ("check", "Paiement accepté", "Ciné · 11,90 €"),
          ("vault", "Coffre arrondi", "+0,80 € épargnés")]
def notif(ic, a_, b_):
    c = rounded(920, 170, 44, PANEL2 + (245,)); c.alpha_composite(circle_icon(ic, 104, RED, WHITE), (34, 33))
    c.alpha_composite(text(a_, "600", 42, WHITE, pad=0), (168, 38)); c.alpha_composite(text(b_, "400", 34, GREY, pad=0), (168, 98))
    c.alpha_composite(text("maintenant", "400", 28, GREY, pad=0), (760, 40)); return c
NOTIF_IMG = [notif(*n) for n in NOTIFS]
T_TRANS = glow(text("Transaction", "800", 132, WHITE, track=-3), 10, 0.3)
T_SECU = glow(text("sécurisée", "800", 150, RED, track=-3), 14, 0.5, RED)
SHIELD = glow(circle_icon("shield", 300, RED, WHITE), 40, 0.7)
def scene_notifs(t):
    fr = BG.copy(); lt = t - 18.0
    fly = ease_in(seg(lt, 1.85, 2.2))
    for k, im in enumerate(NOTIF_IMG):
        p = ease(seg(lt, 0.05 + 0.2 * k, 0.4 + 0.2 * k))
        if p <= 0: continue
        depth = sum(1 for j in range(len(NOTIF_IMG)) if j > k and lt > 0.05 + 0.2 * j + 0.2)
        y = lerp(1180 - depth * 40 - 380, 1180 - depth * 40, p) + fly * (900 + k * 120)
        put(fr, im, W / 2, y, min(1, p * 1.6) * (1 - 0.18 * depth) * (1 - fly), (1 - 0.05 * depth) * lerp(0.92, 1, p))
    for im, y, t0 in ((T_TRANS, 560, 1.0), (T_SECU, 720, 1.2)):
        k = ease(seg(lt, t0, t0 + 0.22))
        if k > 0: put(fr, mblur(im, 0, (1 - k) * -200), W / 2, lerp(y - 160, y, k), k, lerp(1.4, 1, k))
    return fr

def scene_secure(t):
    fr = BG.copy(); lt = t - 19.8
    put_tl(fr, SPOT, 0, 0, 0.4 + 0.4 * ease(seg(lt, 0.4, 0.8)))
    z = lerp(1.0, 1.25, ease_io(seg(lt, 0, 1.7)))
    put(fr, T_TRANS, W / 2, 560 - (z - 1) * 300, 1, z); put(fr, T_SECU, W / 2, 720 - (z - 1) * 150, 1, z)
    b = back(seg(lt, 0.45, 0.8), 2.4)
    if b > 0:
        put(fr, SHIELD, W / 2, 1180, 1, b)
        rp = seg(lt, 0.5, 1.2)
        if 0 < rp < 1:
            r_ = 160 + 600 * ease(rp); d = SSDraw((2 * r_ + 20, 2 * r_ + 20), 2, W / 2 - r_ - 10, 1180 - r_ - 10)
            d.ellipse((W / 2 - r_, 1180 - r_, W / 2 + r_, 1180 + r_), outline=RED + (int(220 * (1 - rp)),), width=6)
            fr.alpha_composite(d.result(), (int(W / 2 - r_ - 10), int(1180 - r_ - 10)))
    put(fr, text("Chiffrement · 3D Secure · alertes en direct", "500", 36, GREY), W / 2, 1520, ease(seg(lt, 0.8, 1.1)))
    return fr

def iso_box(d, x, y, w, dpt, h, top, left, right):
    """Parallélépipède isométrique : (x,y) = coin avant au sol."""
    c, s = math.cos(math.radians(30)), math.sin(math.radians(30))
    A = (x, y); B = (x + w * c, y - w * s); D = (x - dpt * c, y - dpt * s); C = (B[0] - dpt * c, B[1] - dpt * s)
    up = lambda p: (p[0], p[1] - h)
    d.polygon([A, B, up(B), up(A)], fill=right); d.polygon([A, D, up(D), up(A)], fill=left)
    d.polygon([up(A), up(B), up(C), up(D)], fill=top)
    return A, B, D, up
rng2 = np.random.default_rng(2)
WIN = rng2.random((3, 30, 12))
def scene_iso(t):
    fr = BG.copy(); lt = t - 21.8; d = SSDraw((W, H), 2)
    gx, gy = W / 2, 1450
    d.polygon([(gx, gy + 260), (gx + 600, gy - 86), (gx, gy - 430), (gx - 600, gy - 86)], fill=(22, 18, 24, 255))
    blds = [(-250, 30, 260, 260, 760, 0.0), (120, -60, 300, 240, 1040, 0.12), (-40, 170, 220, 200, 520, 0.24)]
    c, s = math.cos(math.radians(30)), math.sin(math.radians(30))
    for bi, (ox, oy, w, dp, h, dl) in enumerate(sorted(blds, key=lambda b: b[1])):
        hh = h * back(seg(lt, dl, dl + 0.55), 1.2)
        if hh <= 2: continue
        x, y = gx + ox, gy + oy
        A, B, D, up = iso_box(d, x, y, w, dp, hh, (70, 64, 76, 255), (34, 30, 38, 255), (50, 44, 56, 255))
        rows = int(hh // 46)
        for r in range(rows):
            for k in range(int(w // 44)):
                on = WIN[bi, r % 30, k % 12] > 0.62 and lt > dl + 0.4 + r * 0.01
                col = (RED + (255,)) if (on and WIN[bi, r % 30, (k + 3) % 12] > 0.5) else ((255, 236, 220, 230) if on else (24, 22, 28, 255))
                px = x + (k + 0.5) * 44 * c; py = y - (k + 0.5) * 44 * s - 30 - r * 46
                d.polygon([(px - 12 * c, py + 12 * s), (px + 12 * c, py - 12 * s), (px + 12 * c, py - 12 * s - 26), (px - 12 * c, py + 12 * s - 26)], fill=col)
    ov = d.result(); fr.alpha_composite(glow(ov, 30, 0.18, RED).crop((90, 90, W + 90, H + 90)))
    sign = glow(text("ORVA", "900", 90, RED, skew=-0.22), 12, 0.8)
    put(fr, sign, gx + 120 + 300 * c / 2 - 80, gy - 60 - 1040 - 70, ease(seg(lt, 0.7, 1.0)))
    b = back(seg(lt, 0.85, 1.2))
    if b > 0:
        cd = rounded(860, 260, 46, PANEL + (250,), LINE + (255,), 3)
        cd.alpha_composite(circle_icon("vault", 140, RED, WHITE), (40, 60))
        cd.alpha_composite(text("ORVA · Banque mobile", "700", 46, WHITE, pad=0), (210, 62))
        cd.alpha_composite(text("Compte ouvert en 8 minutes", "400", 36, GREY, pad=0), (210, 128))
        put(fr, glow(cd, 24, 0.5), W / 2, 560, 1, b)
    return fr

T_CARTE = glow(text("Ta carte.", "800", 140, WHITE, track=-3), 10, 0.3)
T_STYLE = glow(text("Ton style.", "800", 140, RED, track=-3), 14, 0.5, RED)
def scene_hero(t):
    fr = BG.copy(); lt = t - 24.0; put_tl(fr, SPOT, 0, 0, 0.7)
    face = sweep(CARD, seg(lt, 0.15, 0.9), 0.6)
    put3d(fr, glow(face, 40, 0.6), W / 2, 1050, -12 + 6 * lt, 18, -8, 1, 1.12 + 0.05 * lt)
    for im, y, t0 in ((T_CARTE, 420, 0.1), (T_STYLE, 580, 0.35)):
        k = ease(seg(lt, t0, t0 + 0.22))
        if k > 0: put(fr, mblur(im, (1 - k) * -260), lerp(W / 2 - 420, W / 2, k), y, k)
    return fr

T_PAY1 = glow(text("Tu payes.", "800", 140, WHITE, track=-3), 10, 0.3)
T_PAY2 = glow(text("C'est tout.", "800", 140, RED, track=-3), 14, 0.5, RED)
def terminal():
    tm = rounded(520, 640, 60, (26, 26, 32, 255), LINE + (255,), 4)
    tm.alpha_composite(rounded(420, 250, 26, (10, 10, 14, 255)), (50, 50))
    for r in range(3):
        for k in range(3): tm.alpha_composite(rounded(105, 70, 18, (44, 44, 54, 255)), (70 + k * 135, 350 + r * 90))
    return tm
TERM = terminal()
def scene_pay(t):
    fr = BG.copy(); lt = t - 25.4; put_tl(fr, SPOT, 0, 0, 0.5)
    tx, ty = W / 2, 1300; tm = TERM.copy()
    ok = lt > 0.75
    if ok:
        tm.alpha_composite(circle_icon("check", 170, RED, WHITE).resize((int(170 * back(seg(lt, 0.75, 1.0))) or 1,) * 2), (260 - int(85 * back(seg(lt, 0.75, 1.0))), 90))
    else:
        tm.alpha_composite(text("29,90 €", "700", 70, WHITE, pad=0), (130, 130))
    put(fr, tm, tx, ty)
    p = ease_io(seg(lt, 0.0, 0.6)); back_ = ease_in(seg(lt, 0.9, 1.3))
    for k in range(3):
        rp = (lt * 1.8 - k * 0.33)
        if 0.45 < lt < 1.0 and 0 < rp % 1 < 1:
            r_ = 120 + 260 * (rp % 1); d = SSDraw((2 * r_ + 20, 2 * r_ + 20), 2, tx - r_ - 10, 980 - r_ - 10)
            d.arc((tx - r_, 980 - r_, tx + r_, 980 + r_), 200, 340, fill=RED + (int(255 * (1 - rp % 1)),), width=8)
            fr.alpha_composite(d.result(), (int(tx - r_ - 10), int(980 - r_ - 10)))
    put3d(fr, glow(CARD, 30, 0.6), lerp(W + 500, tx, p) + back_ * 600, lerp(700, 960, p) - back_ * 200, 0, 55, lerp(-30, -8, p), 1, 0.6)
    for im, y, t0 in ((T_PAY1, 360, 0.6), (T_PAY2, 520, 0.85)):
        k = ease(seg(lt, t0, t0 + 0.22))
        if k > 0: put(fr, mblur(im, (1 - k) * 260), lerp(W / 2 + 420, W / 2, k), y, k)
    return fr

T_HANDLE = text("@orva.app", "600", 48, WHITE); T_CATS = text("Payer  ·  Envoyer  ·  Épargner", "500", 40, GREY)
def scene_end(t):
    fr = BG.copy(); lt = t - 26.8; col = ease_in(seg(t, 28.55, 28.95)); sc = 1 - col
    put_tl(fr, SPOT, 0, 0, 0.35 * sc)
    if sc > 0.03:
        k = ease(lt / 0.45); lg = LOGO if k > 0.98 else LOGO.filter(ImageFilter.GaussianBlur((1 - k) * 16))
        c = lambda y: H / 2 + (y - H / 2) * sc
        put(fr, lg, W / 2, c(900), k, lerp(1.25, 1, k) * sc)
        put(fr, T_HANDLE, W / 2, c(1120), ease(seg(lt, 0.35, 0.6)), sc)
        put(fr, T_CATS, W / 2, c(1200), ease(seg(lt, 0.5, 0.8)), sc)
    if t > 28.75:
        r = 12 + 10 * math.exp(-max(0, t - 28.95) * 7)
        put(fr, dot(int(r)), W / 2, H / 2, 1 - ease(seg(t, 29.15, 29.5)))
    return fr

def scene_intro(t):
    fr = BG.copy()
    if t < 2.45:
        b = t % 1.0; r = 10 + 7 * math.exp(-b * 9) + 4 * math.exp(-max(0, b - 0.3) * 9) * (b > 0.3)
        put(fr, dot(int(r * (1 + 0.8 * ease(seg(t, 2.1, 2.45))))), W / 2, H / 2, ease(t / 0.3))
    rp = seg(t, 2.42, 3.0)
    if 0 < rp < 1:
        fl = Image.new("RGBA", (W, H), RED + (int(230 * max(0, 1 - rp * 2.2)),)); fr.alpha_composite(fl)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); r_ = 30 + 1400 * ease(rp)
        ImageDraw.Draw(ov).ellipse((W / 2 - r_, H / 2 - r_, W / 2 + r_, H / 2 + r_), outline=(255, 120, 128, int(255 * (1 - rp))), width=int(8 + 60 * (1 - rp)))
        fr.alpha_composite(ov.filter(ImageFilter.GaussianBlur(4)))
    if t >= 2.5:
        k = ease(seg(t, 2.5, 2.95)); out = ease_in(seg(t, 3.35, 3.65))
        lg = LOGO if k > 0.98 else LOGO.filter(ImageFilter.GaussianBlur((1 - k) * 18))
        put(fr, mblur(lg, 0, out * 300), W / 2, H / 2 - 60 - out * 500, k, lerp(1.3, 1, k))
        put(fr, LOGO_SUB, W / 2, H / 2 + 120 - out * 500, ease(seg(t, 2.75, 3.1)) * (1 - out))
    return fr

# ------------------------------------------------------------------ montage
SCENES = [(0.0, 3.6, scene_intro), (3.6, 5.8, screen_search), (5.8, 8.6, screen_home), (8.6, 10.4, scene_grid),
          (10.4, 12.0, scene_counter), (12.0, 14.0, scene_chat), (14.0, 16.0, scene_card3d), (16.0, 18.0, scene_streaks),
          (18.0, 19.8, scene_notifs), (19.8, 21.8, scene_secure), (21.8, 23.7, scene_iso), (23.7, 25.4, scene_hero),
          (25.4, 26.8, scene_pay), (26.8, DUR, scene_end)]
EPS = 1e-4
def base(t):
    for a, b, f in SCENES:
        if a <= t < b: return f(t)
    return scene_end(t)

# fuite de lumière : grandes taches chaudes et floues, déplacées pendant les flashs
def _leak():
    im = Image.new("RGB", (W // 4, H // 4), (0, 0, 0)); d = ImageDraw.Draw(im); r = np.random.default_rng(12)
    for _ in range(9):
        x, y, rad = r.uniform(0, W / 4), r.uniform(0, H / 4), r.uniform(60, 200)
        c = [(255, 60, 40), (255, 140, 70), (255, 230, 200), (220, 20, 50)][r.integers(0, 4)]
        d.ellipse((x - rad, y - rad, x + rad, y + rad), fill=c)
    return im.filter(ImageFilter.GaussianBlur(60)).resize((W * 2, H), Image.BICUBIC)
LEAK = _leak()
def light_leak(rgb, k, phase):
    if k <= 0.01: return rgb
    x = int(phase * W); lk = LEAK.crop((x, 0, x + W, H))
    return Image.blend(rgb, ImageChops.screen(rgb, lk), min(1, k))

def smooth_noise(t, seed):
    return sum(math.sin(t * f + seed * p) * a for f, p, a in ((1.7, 1.3, 1), (2.9, 2.1, .6), (5.3, .7, .3)))

def whip(t, T, d, dirx):
    """Balayage réel : les deux plans bougent ensemble, accélération puis freinage."""
    p = seg(t, T - d, T + d); e = ease_io(p)
    a = np.asarray(base(min(t, T - EPS)).convert("RGB")); b = np.asarray(base(max(t, T)).convert("RGB"))
    off = int(e * W); out = np.empty_like(a)
    if dirx > 0:   # le contenu part vers la gauche
        out[:, :W - off] = a[:, off:]; out[:, W - off:] = b[:, :off]
    else:
        out[:, off:] = a[:, :W - off]; out[:, :off] = b[:, W - off:]
    v = math.sin(math.pi * p)
    return Image.fromarray(frame_mblur(out, -dirx * 220 * v, 0, 8))

def glitch(img, k, seed):
    if k <= 0.02: return img
    a = np.asarray(img).copy(); r = np.random.default_rng(seed)
    for _ in range(int(6 + 14 * k)):
        y = r.integers(0, H - 40); h = r.integers(8, 90); dx = int(r.normal(0, 80 * k))
        a[y:y + h] = np.roll(a[y:y + h], dx, axis=1)
    return chroma(Image.fromarray(a), 14 * k)

def frame_at(t):
    # transitions à deux plans
    for T, d, dx in ((12.0, 0.16, 1), (23.7, 0.16, 1), (25.4, 0.15, 1)):
        if T - d <= t < T + d: return whip(t, T, d, dx)
    if 15.85 <= t < 16.15: return whip(t, 16.0, 0.15, -1)
    if 8.45 <= t < 8.75:       # zoom traversant : l'accueil plonge dans la grille
        p = seg(t, 8.45, 8.75); a = base(min(t, 8.6 - EPS)).convert("RGB"); b = base(max(t, 8.6)).convert("RGB")
        a = zoom_blur(a.resize((W, H), Image.BICUBIC, box=(W * .5 * (1 - 1 / (1 + p)), H * .5 * (1 - 1 / (1 + p)),
                      W * (.5 + .5 / (1 + p)), H * (.5 + .5 / (1 + p)))), 0.25 * p)
        return Image.blend(a, b, ease_io(p))
    if 26.65 <= t < 26.95:     # passage par le noir
        p = seg(t, 26.65, 26.95); img = base(t).convert("RGB")
        return Image.blend(img, Image.new("RGB", (W, H), BLACK), math.sin(math.pi * p) * 0.95)
    fr = base(t)
    if 3.6 <= t < 3.95:
        p = ease(seg(t, 3.6, 3.95)); bg = scene_intro(t); off = int((1 - p) * H)
        bg.alpha_composite(fr.crop((0, 0, W, H - off)), (0, off))
        v = math.sin(math.pi * min(1, seg(t, 3.6, 3.95) * 1.4)) * 160
        return Image.fromarray(frame_mblur(np.asarray(bg.convert("RGB")), 0, v, 8))
    return fr.convert("RGB")

def render_sub(t):
    rgb = frame_at(t)
    if 5.55 <= t < 6.35:       # flash rouge + fuite de lumière
        p = seg(t, 5.55, 6.35); k = math.sin(math.pi * p)
        if t < 5.95: rgb = zoom_blur(rgb, 0.4 * k)
        rgb = Image.blend(rgb, Image.new("RGB", (W, H), RED), 0.7 * k ** 1.5); rgb = light_leak(rgb, k, p)
    if 2.4 <= t < 2.9: rgb = light_leak(rgb, math.sin(math.pi * seg(t, 2.4, 2.9)) * 0.8, 0.3 + seg(t, 2.4, 2.9) * 0.4)
    if 10.25 <= t < 10.55: rgb = zoom_blur(rgb, 0.3 * math.sin(math.pi * seg(t, 10.25, 10.55)))
    if 13.9 <= t < 14.2: rgb = glitch(rgb, math.sin(math.pi * seg(t, 13.9, 14.2)), int(t * 60))
    if 17.75 <= t < 18.2:      # la carte traverse l'objectif
        p = seg(t, 17.75, 18.2); k = math.sin(math.pi * p)
        rgb = light_leak(Image.blend(rgb, Image.new("RGB", (W, H), (255, 236, 236)), 0.55 * k), k, 0.6 + p * 0.3)
    if 21.35 <= t < 21.95:
        p = seg(t, 21.35, 21.95)
        if t < 21.8: rgb = zoom_blur(rgb, 1.1 * ease_in(seg(t, 21.35, 21.8)), n=10, cy=900)
        rgb = light_leak(rgb, math.sin(math.pi * p) * 0.9, 1 - p * 0.5)
    for T in (2.45, 6.3, 14.0, 19.85, 20.3):   # secousse naturelle sur les impacts
        if T <= t < T + 0.28:
            k = (1 - seg(t, T, T + 0.28)) ** 2 * 16
            rgb = ImageChops.offset(rgb, int(smooth_noise(t * 30, 1) * k), int(smooth_noise(t * 30, 2) * k))
    return np.asarray(rgb, np.float32)

SUB = (-1 / 3, 0.0, 1 / 3)
def post(arr, n, t):
    img = Image.fromarray(arr.clip(0, 255).astype(np.uint8))
    # caméra portée très légère (dérive douce)
    z = 1.012; dx = smooth_noise(t * 0.8, 3) * 3; dy = smooth_noise(t * 0.7, 4) * 3
    bw, bh = W / z, H / z; l = (W - bw) / 2 + dx; tp = (H - bh) / 2 + dy
    img = img.resize((W, H), Image.BICUBIC, box=(l, tp, l + bw, tp + bh))
    # halo des hautes lumières (bloom)
    sm = np.asarray(img.resize((W // 6, H // 6), Image.BILINEAR), np.float32)
    hi = np.clip(sm - 150, 0, 255) * 1.4
    bl = Image.fromarray(hi.clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(7)).resize((W, H), Image.BICUBIC)
    img = ImageChops.add(img, bl.point(lambda v: int(v * 0.45)))
    # aberration chromatique sur les bords uniquement
    r, g, b = img.split()
    r = r.resize((int(W * 1.0035), int(H * 1.0035)), Image.BILINEAR).crop((int(W * .00175), int(H * .00175), int(W * .00175) + W, int(H * .00175) + H))
    img = Image.merge("RGB", (r, g, b))
    out = img.convert("RGBA"); out.alpha_composite(VIG)
    a = np.asarray(out.convert("RGB")).astype(np.int16)
    a += np.random.default_rng(n).normal(0, 3.2, (H // 2, W // 2, 1)).astype(np.int16).repeat(2, 0).repeat(2, 1)
    if t < 0.15: a = (a * (t / 0.15)).astype(np.int16)
    return np.clip(a, 0, 255).astype(np.uint8)

FAST = [(3.6, 3.95), (5.55, 6.35), (8.45, 9.8), (10.25, 10.55), (11.82, 12.18), (13.9, 14.2), (15.82, 16.18),
        (17.6, 19.15), (21.3, 21.95), (23.52, 23.88), (25.23, 25.57), (26.6, 27.0)]
def render(n):
    t = n / FPS
    k = 9 if any(a <= t < b for a, b in FAST) else 3
    subs = [(i / (k - 1) - 0.5) for i in range(k)]
    acc = sum(render_sub(max(0, min(DUR - 0.001, t + d * 0.6 / FPS))) for d in subs) / k
    return post(acc, n, t).tobytes()

SECTIONS = {"intro_end": 3.6, "drop": 6.3, "break_start": 16.0, "break_end": 18.0, "cut": 19.5, "hit": 19.8, "outro": 26.8}
EV = {
    "heart": [0.0, 1.0, 2.0], "flash": [2.42, 5.7], "impact": [2.45, 6.3, 19.8, 28.9],
    "shimmer": [2.5, 26.85],
    "whoosh": [[3.75, 1], [12.0, 1], [16.0, -1], [23.7, 1], [25.4, 1]],
    "whoosh_low": [3.62, 8.6, 10.35, 18.0, 26.8],
    "key": [3.6 + 0.45 + 0.09 * i for i in range(5)],
    "tap": [5.3, 7.75],
    "pop": [3.6 + 0.6 + 0.11 * k for k in range(4)] + [6.15 + 0.92 + 0.08 * k for k in range(4)]
           + [11.0 + 0.07 * i for i in range(5)] + [22.7],
    "tickroll": [[6.32, 7.45], [10.6, 11.5]],
    "received": [12.25, 13.65], "sent": [12.75], "success": [13.12, 20.3, 26.15],
    "glitch": [13.92, 14.02], "swish": [14.0, 23.72],
    "riser": [[5.0, 5.7], [16.1, 17.95], [18.9, 19.5]],
    "slam": [16.22, 16.52, 19.0, 19.22, 24.12, 24.37, 26.02, 26.27],
    "notif": [18.07 + 0.2 * k for k in range(5)],
    "rumble": [[21.8, 22.7]], "thud": [22.33, 22.45, 22.57],
    "beep": [26.15], "revcym": [19.8, 6.3],
}

if __name__ == "__main__":
    wav = OUT.replace(".mp4", ".wav")
    subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "orva_audio.py"),
                    wav, json.dumps({"dur": DUR, "sections": SECTIONS, "events": EV})], check=True)
    ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "slow", "-crf", "21",
                           "-maxrate", "7M", "-bufsize", "14M", "-pix_fmt", "yuv420p", "-af", "loudnorm=I=-13:TP=-1:LRA=9", "-ar", "48000", "-c:a", "aac", "-b:a", "256k",
                           "-shortest", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
    sel = [int(float(x) * FPS) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else range(int(DUR * FPS))
    with Pool(4) as pool:
        for i, b in enumerate(pool.imap(render, sel, chunksize=2)):
            ff.stdin.write(b)
            if i % 100 == 0: print(i, flush=True)
    ff.stdin.close(); ff.wait(); os.remove(wav); print("ok", OUT)
