"""Motion design publicitaire Sorienka Studio — style « app promo » (9:16, 1080x1920, 30 i/s).

Usage : python3 motion.py <dossier_images> <dossier_polices> <sortie.mp4>
"""
import json, math, os, subprocess, sys
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

IMG, FONTS, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
W, H, FPS = 1080, 1920, 30
DUR = 24.5
INK = (24, 14, 21)                  # prune presque noir
CREME = (250, 244, 238); ROSE = (232, 196, 196); NACRE = (241, 220, 217); PRUNE = (42, 31, 45)
GOLD = (214, 178, 140); GREY = (122, 102, 112)

# ------------------------------------------------------------------ polices et textes
def font(kind, size):
    if kind.startswith("j"):
        return ImageFont.truetype(os.path.join(FONTS, f"fontsource-jost-5.3.0/files/jost-latin-{kind[1:]}-normal.woff"), size)
    w, st = kind[1:4], ("italic" if kind.endswith("i") else "normal")
    return ImageFont.truetype(os.path.join(FONTS, f"fontsource-cormorant-garamond-5.3.0/files/cormorant-garamond-latin-{w}-{st}.woff"), size)

def text(txt, kind, size, color, track=0, pad=30):
    f = font(kind, size)
    ws = [f.getlength(c) for c in txt]
    tw = int(sum(ws) + track * (len(txt) - 1)); asc, desc = f.getmetrics()
    im = Image.new("RGBA", (tw + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if track:
        x = pad
        for c, w_ in zip(txt, ws): d.text((x, pad), c, font=f, fill=color); x += w_ + track
    else:
        d.text((pad, pad), txt, font=f, fill=color)
    return im

def glow(im, radius=18, strength=1.0, color=ROSE):
    """Ajoute un halo coloré sous un calque RGBA."""
    pad = radius * 3
    big = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0)); big.paste(im, (pad, pad), im)
    a = big.split()[3].filter(ImageFilter.GaussianBlur(radius)).point(lambda v: min(255, int(v * strength)))
    halo = Image.new("RGBA", big.size, color + (0,)); halo.putalpha(a)
    halo.alpha_composite(big); return halo

def alpha(im, a):
    if a >= 0.999: return im
    if a <= 0: return None
    r, g, b, al = im.split(); return Image.merge("RGBA", (r, g, b, al.point(lambda v: int(v * a))))

def put(fr, im, cx, cy, a=1.0, scale=1.0):
    if im is None or a <= 0 or scale <= 0.01: return
    if abs(scale - 1) > 0.005:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    im = alpha(im, a)
    if im is not None: fr.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def mblur(im, dx, n=9):
    """Flou de mouvement horizontal d'un calque RGBA (dx en pixels)."""
    if abs(dx) < 2: return im
    pad = int(abs(dx)) + 2
    a = np.zeros((im.height, im.width + 2 * pad, 4), np.float32)
    src = np.asarray(im).astype(np.float32); src[..., :3] *= src[..., 3:4] / 255
    for k in range(n):
        o = int(pad + dx * (k / (n - 1) - 0.5)); a[:, o:o + im.width] += src
    a /= n; rgb = a[..., :3] / np.maximum(a[..., 3:4], 1) * 255
    return Image.fromarray(np.dstack([rgb, a[..., 3:4]]).clip(0, 255).astype(np.uint8))

def frame_mblur(arr, dx, n=10):
    if abs(dx) < 2: return arr
    idx = np.arange(W); acc = np.zeros_like(arr, np.float32)
    for k in range(n):
        o = int(dx * (k / (n - 1) - 0.5)); acc += arr[:, np.clip(idx - o, 0, W - 1)]
    return (acc / n).astype(np.uint8)

def ease(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3
def ease_in(x): x = min(1, max(0, x)); return x ** 3
def ease_io(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
def back(x, s=1.7):            # dépassement léger (effet « pop »)
    x = min(1, max(0, x)) - 1; return x * x * ((s + 1) * x + s) + 1
def lerp(a, b, x): return a + (b - a) * x
def seg(t, a, b): return (t - a) / (b - a)

# ------------------------------------------------------------------ perspective 3D
def persp_coeffs(src_pts, dst_pts):
    A = []; B = []
    for (x, y), (u, v) in zip(dst_pts, src_pts):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    return np.linalg.solve(np.array(A, float), np.array(B, float)).tolist()

def tilt(im, ry=0.0, rx=0.0, f=1900):
    """Fait pivoter un calque autour de ses axes (degrés) et le projette, renvoie (image, décalage du centre)."""
    w, h = im.size; ry, rx = math.radians(ry), math.radians(rx)
    pts = []
    for x, y in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
        x1 = x * math.cos(ry); z1 = x * math.sin(ry)
        y1 = y * math.cos(rx) - z1 * math.sin(rx); z2 = y * math.sin(rx) + z1 * math.cos(rx)
        s = f / (f + z2); pts.append((x1 * s, y1 * s))
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    ox, oy = min(xs), min(ys); ow, oh = int(max(xs) - ox) + 2, int(max(ys) - oy) + 2
    dst = [(p[0] - ox, p[1] - oy) for p in pts]
    c = persp_coeffs([(0, 0), (w, 0), (w, h), (0, h)], dst)
    out = im.transform((ow, oh), Image.PERSPECTIVE, c, Image.BICUBIC)
    return out, (ox + ow / 2, oy + oh / 2)

def put3d(fr, im, cx, cy, ry=0, rx=0, a=1.0, scale=1.0):
    if scale != 1: im = im.resize((max(2, int(im.width * scale)), max(2, int(im.height * scale))), Image.BICUBIC)
    if abs(ry) > 0.2 or abs(rx) > 0.2:
        im, (dx, dy) = tilt(im, ry, rx); cx += dx; cy += dy
    put(fr, im, cx, cy, a)

# ------------------------------------------------------------------ éléments graphiques
def rounded(w, h, r, fill):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); ImageDraw.Draw(im).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=fill); return im

def cover(im, w, h):
    sc = max(w / im.width, h / im.height); r = im.resize((int(im.width * sc) + 1, int(im.height * sc) + 1), Image.LANCZOS)
    l = (r.width - w) // 2; t = (r.height - h) // 2; return r.crop((l, t, l + w, t + h))

def card_img(im, w, h, r=34):
    c = cover(im, w, h).convert("RGBA"); m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255); c.putalpha(m); return c

def load(name): return Image.open(os.path.join(IMG, name + ".png")).convert("RGB")

# fond : dégradé radial prune + nappes roses qui dérivent
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
rad = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H * 0.45) / H) ** 2)
BG = Image.fromarray((np.array([46, 26, 38])[None, None] * np.clip(1 - rad * 1.6, 0, 1)[..., None]
                      + np.array(INK)[None, None] * np.clip(rad * 1.6, 0, 1)[..., None]).astype(np.uint8))
def blob(r, color, a):
    s = Image.new("RGBA", (r * 2, r * 2), color + (0,)); m = Image.new("L", (r * 2, r * 2), 0)
    ImageDraw.Draw(m).ellipse((r // 2, r // 2, r * 3 // 2, r * 3 // 2), fill=int(255 * a))
    s.putalpha(m.filter(ImageFilter.GaussianBlur(r / 3))); return s
BLOBS = [(blob(420, ROSE, 0.22), 0.2, 0.3, 0.07, 1.1), (blob(520, (200, 120, 150), 0.16), 0.85, 0.7, 0.05, 2.3),
         (blob(360, GOLD, 0.10), 0.6, 0.15, 0.09, 4.0)]

def background(t):
    fr = BG.convert("RGBA")
    for b, x, y, sp, ph in BLOBS:
        fr.alpha_composite(b, (int(W * x + 120 * math.sin(t * sp * 6 + ph) - b.width / 2),
                               int(H * y + 160 * math.cos(t * sp * 5 + ph) - b.height / 2)))
    return fr

def dot(r, a=1.0):
    s = r * 6; im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((s / 2 - r, s / 2 - r, s / 2 + r, s / 2 + r), fill=CREME + (255,))
    g = glow(im, max(4, r), 2.2, ROSE)
    return alpha(g, a)

# ------------------------------------------------------------------ textes pré-rendus
LOGO = glow(text("Sorienka", "c400", 190, CREME), 22, 0.9)
LOGO_S = glow(text("STUDIO", "j300", 44, CREME, track=26), 12, 0.8)
T_15 = glow(text("15 MIN", "j800", 190, CREME, track=6), 26, 1.0)
T_POUR = glow(text("POUR TOI", "j800", 170, CREME, track=6), 26, 1.0)
T_RIT = glow(text("TON RITUEL", "j800", 150, CREME, track=4), 26, 1.0)
K_15 = text("rien que", "c500i", 72, NACRE); K_POUR = text("ce soir,", "c500i", 72, NACRE); K_RIT = text("ton moment,", "c500i", 72, NACRE)
T_PACK = glow(text("PACK DE 5", "j800", 130, CREME, track=8), 20, 0.9)
T_OLD = text("9,99 €", "j500", 84, GREY)
T_PRICE = glow(text("4,00 €", "j800", 250, NACRE), 30, 1.2)
T_LEM = text("le masque", "c500i", 80, NACRE)
T_UNIT = text("au lieu de 9,99 € à l'unité", "j400", 34, GREY)
T_LIV1 = glow(text("LIVRAISON", "j800", 150, CREME, track=6), 22, 0.9)
T_LIV2 = glow(text("OFFERTE", "j800", 150, NACRE, track=6), 22, 0.9)
T_LIV3 = text("dès 35 € d'achat", "c500i", 76, NACRE)
T_CODE_K = text("Offre d'automne", "c500i", 70, NACRE)
T_ADDED = text("Ajouté au panier", "j500", 40, CREME)
T_END = text("Ton rituel du soir commence ici.", "c500i", 66, NACRE)
T_URL = text("sorienkastudio.myshopify.com", "j400", 32, (196, 170, 180))
T_HEAD = text("Sorienka Studio", "c500", 52, CREME)

def button(label, w=460, h=108):
    b = rounded(w, h, h // 2, NACRE + (255,)); t = text(label, "j600", 40, PRUNE, track=8)
    b.alpha_composite(t, ((w - t.width) // 2, (h - t.height) // 2 + 2)); return glow(b, 18, 0.7)
BTN = button("DÉCOUVRIR")

def ticket():
    w, h = 820, 330; im = rounded(w, h, 40, CREME + (255,)); d = ImageDraw.Draw(im)
    for y in range(30, h - 30, 26): d.line((300, y, 300, y + 13), fill=(214, 190, 192), width=4)
    for cx in (300,):
        d.ellipse((cx - 28, -28, cx + 28, 28), fill=(0, 0, 0, 0)); d.ellipse((cx - 28, h - 28, cx + 28, h + 28), fill=(0, 0, 0, 0))
    big = text("-15 %", "j800", 86, PRUNE); im.alpha_composite(big, (150 - big.width // 2, h // 2 - big.height // 2))
    a = text("CODE", "j500", 30, GREY, track=8); b = text("AUTOMNE15", "j700", 66, PRUNE, track=3)
    c = text("jusqu'au 31/10", "j400", 32, GREY)
    im.alpha_composite(a, (330, 52)); im.alpha_composite(b, (330, 108)); im.alpha_composite(c, (330, 210))
    return glow(im, 24, 0.6)
TICKET = ticket()

def bag(n_badge=None, sc=1.0):
    s = 360; im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((70, 120, 290, 320), 30, outline=NACRE + (255,), width=12)
    d.arc((125, 50, 235, 170), 180, 360, fill=NACRE + (255,), width=12)
    return glow(im, 14, 0.8)
BAG = bag()
def badge(n):
    im = Image.new("RGBA", (110, 110), (0, 0, 0, 0)); d = ImageDraw.Draw(im); d.ellipse((5, 5, 105, 105), fill=ROSE + (255,))
    t = text(str(n), "j700", 56, PRUNE); im.alpha_composite(t, ((110 - t.width) // 2, (110 - t.height) // 2 - 2)); return im
BADGE = badge(1)

def parcel():
    s = 260; im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = NACRE + (255,)
    d.polygon([(130, 40), (230, 85), (230, 195), (130, 240), (30, 195), (30, 85)], outline=c, width=10)
    d.line((30, 85, 130, 130, 230, 85), fill=c, width=10); d.line((130, 130, 130, 240), fill=c, width=10)
    d.line((80, 62, 180, 108), fill=c, width=8)
    return glow(im, 12, 0.8)
PARCEL = parcel()

# ------------------------------------------------------------------ images
SACHET = load("c_sachet"); HERO = load("c_hero"); TEXTURE = load("c_texture")
S4 = load("s4").crop((210, 0, 652, 786)); S7 = load("s7").crop((380, 0, 864, 860)); S9 = load("s9").crop((300, 0, 963, 1179))
S6 = load("s6").crop((215, 0, 588, 664))
FULL = {k: v.resize((int(W * 1.18), int(H * 1.18)), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 60, 2))
        for k, v in (("s7", S7), ("s4", S4), ("s9", S9))}
TILES = [card_img(im, 300, 420, 30) for im in (S4, TEXTURE, S9, SACHET, S7, HERO)]
SACHET_CARD = card_img(SACHET, 420, 560, 34)
SHADE = Image.new("RGBA", (W, H), INK + (0,))
SHADE.putalpha(Image.fromarray((np.clip((yy - H * 0.45) / (H * 0.55), 0, 1) ** 1.4 * 215).astype(np.uint8)))

# ------------------------------------------------------------------ écran du téléphone
PW, PH = 600, 1240
def phone_screen(t):
    sc = Image.new("RGBA", (PW, PH), (251, 246, 242, 255)); d = ImageDraw.Draw(sc)
    st = text("21:47", "j600", 26, PRUNE, pad=0); sc.alpha_composite(st, (44, 30))
    d.rounded_rectangle((506, 34, 552, 56), 6, outline=PRUNE, width=3); d.rectangle((510, 38, 540, 52), fill=PRUNE)
    ts = t - 3.4
    # --- recherche
    h1 = text("Rechercher", "j600", 46, PRUNE, pad=0); sc.alpha_composite(h1, (40, 100))
    d.rounded_rectangle((32, 180, 568, 270), 45, fill=(241, 230, 227))
    d.ellipse((62, 206, 96, 240), outline=GREY, width=5); d.line((92, 236, 106, 250), fill=GREY, width=6)
    q = "masque collagène"; n = int(max(0, min(len(q), (ts - 0.25) / 0.07)))
    qt = text(q[:n] if n else "Ton rituel…", "j400", 34, PRUNE if n else GREY, pad=0); sc.alpha_composite(qt, (124, 205))
    if n and (int(t * 3) % 2 == 0 or n < len(q)):
        d.rectangle((126 + qt.width, 208, 129 + qt.width, 250), fill=(200, 120, 140))
    lab = text("Suggestions", "j500", 24, GREY, pad=0, track=2); sc.alpha_composite(lab, (40, 310))
    rows = ["masque collagène sorienka", "masque collagène pack de 5", "rituel skincare du soir"]
    for k, r in enumerate(rows):
        a = ease(seg(ts, 1.45 + 0.1 * k, 1.75 + 0.1 * k))
        if a <= 0: continue
        y = 350 + k * 96 + int((1 - a) * 30)
        row = Image.new("RGBA", (PW, 96), (0, 0, 0, 0)); rd = ImageDraw.Draw(row)
        rd.ellipse((40, 26, 84, 70), fill=(241, 230, 227)); rd.ellipse((54, 40, 70, 56), outline=GREY, width=3)
        rt = text(r, "j400", 31, PRUNE, pad=0); row.alpha_composite(rt, (108, 30))
        rd.line((40, 95, 560, 95), fill=(236, 226, 224), width=2)
        sc.alpha_composite(alpha(row, a), (0, y))
    rp = seg(ts, 2.0, 2.4)                       # « tap » sur la première suggestion
    if 0 < rp < 1:
        ov = Image.new("RGBA", (PW, PH), (0, 0, 0, 0)); r_ = 20 + 260 * ease(rp)
        ImageDraw.Draw(ov).ellipse((300 - r_, 398 - r_, 300 + r_, 398 + r_), fill=ROSE + (int(120 * (1 - rp)),))
        sc.alpha_composite(ov)
    # --- fiche produit qui monte
    pu = ease(seg(t, 5.2, 5.65))
    if pu > 0:
        pg = Image.new("RGBA", (PW, PH), (251, 246, 242, 255)); pd = ImageDraw.Draw(pg)
        lt = t - 5.2; z = 1 + 0.04 * lt
        img = cover(SACHET, int(PW * z), int(720 * z)).crop((0, 0, PW, 720)); pg.paste(img, (0, 0))
        pill = rounded(372, 56, 28, PRUNE + (235,)); pt = text("Jusqu'à -63 % par masque", "j500", 24, CREME, pad=0)
        pill.alpha_composite(pt, ((372 - pt.width) // 2, 14)); pg.alpha_composite(pill, (28, 640))
        pg.alpha_composite(text("Masque Collagène", "c600", 56, PRUNE, pad=0), (36, 744))
        pg.alpha_composite(text("Sorienka Studio · usage unique", "j400", 24, GREY, pad=0), (38, 816))
        pr = text("dès 3,70 €", "j700", 46, PRUNE, pad=0); pg.alpha_composite(pr, (36, 862))
        pg.alpha_composite(text("/ masque (pack de 10)", "j400", 26, GREY, pad=0), (50 + pr.width, 878))
        sel = 0 if lt < 1.3 else 2
        for k, (lab_, w_) in enumerate((("1", 0), ("3", 0), ("5", 0), ("10", 0))):
            x0 = 36 + k * 134; on = (k == sel)
            bump = back(seg(lt, 1.3, 1.6)) if on and sel == 2 else 1
            cw_, ch_ = int(118 * bump), int(70 * bump)
            chip = rounded(cw_, ch_, 35, (PRUNE if on else (241, 230, 227)) + (255,))
            ct = text(lab_, "j600", 32, CREME if on else PRUNE, pad=0)
            chip.alpha_composite(ct, ((cw_ - ct.width) // 2, (ch_ - ct.height) // 2 - 3))
            pg.alpha_composite(chip, (x0 + (118 - cw_) // 2, 942 + (70 - ch_) // 2))
        press = 1 - 0.06 * math.sin(math.pi * min(1, max(0, seg(lt, 1.9, 2.15))))
        bw, bh = int(528 * press), int(100 * press)
        btn = rounded(bw, bh, bh // 2, PRUNE + (255,)); bt = text("Ajouter au panier", "j600", 34, CREME, pad=0)
        btn.alpha_composite(bt, ((bw - bt.width) // 2, (bh - bt.height) // 2 - 3))
        pg.alpha_composite(btn, (36 + (528 - bw) // 2, 1060 + (100 - bh) // 2))
        sc.alpha_composite(pg, (0, int((1 - pu) * PH)))
    m = Image.new("L", (PW, PH), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, PW - 1, PH - 1), 64, fill=255)
    sc.putalpha(m); return sc

BODY = rounded(PW + 40, PH + 40, 84, (14, 9, 12, 255))
ImageDraw.Draw(BODY).rounded_rectangle((1, 1, PW + 38, PH + 38), 83, outline=(92, 64, 78, 255), width=3)
def phone(t):
    p = BODY.copy(); p.alpha_composite(phone_screen(t), (20, 20))
    ImageDraw.Draw(p).rounded_rectangle((PW / 2 - 70 + 20, 34, PW / 2 + 70 + 20, 70), 18, fill=(14, 9, 12, 255))
    return p

# ------------------------------------------------------------------ scènes
def s_intro(t, fr):
    # point lumineux qui bat, puis explose en anneau → logo
    if t < 2.45:
        beat = (t % 1.0); r = 9 + 6 * math.exp(-beat * 9) + 3 * math.exp(-max(0, beat - 0.32) * 9) * (beat > 0.32)
        put(fr, dot(int(r * (1 + 0.5 * ease(seg(t, 2.1, 2.45))))), W / 2, H / 2, ease(t / 0.3))
    rp = seg(t, 2.45, 3.1)
    if 0 < rp < 1:
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); r_ = 20 + 1300 * ease(rp); w_ = int(6 + 40 * (1 - rp))
        ImageDraw.Draw(ov).ellipse((W / 2 - r_, H / 2 - r_, W / 2 + r_, H / 2 + r_), outline=NACRE + (int(255 * (1 - rp)),), width=w_)
        fr.alpha_composite(ov.filter(ImageFilter.GaussianBlur(3)))
        fl = Image.new("RGBA", (W, H), NACRE + (int(150 * max(0, 1 - rp * 3)),)); fr.alpha_composite(fl)
    if 2.5 <= t < 7.7:
        k = ease(seg(t, 2.5, 3.0)); up = ease_io(seg(t, 3.25, 3.75))
        sc = lerp(1.18, 1.0, k) * lerp(1, 0.38, up); cy = lerp(H / 2 - 40, 170, up)
        lg = LOGO if k > 0.98 else LOGO.filter(ImageFilter.GaussianBlur((1 - k) * 14))
        put(fr, lg, W / 2, cy, k * (1 - ease(seg(t, 7.35, 7.65))), sc)
        put(fr, LOGO_S, W / 2, cy + 130 * sc, ease(seg(t, 2.7, 3.1)) * (1 - up), sc)

def s_phone(t, fr):
    if t < 3.2 or t > 8.3: return
    k = ease(seg(t, 3.2, 3.75)); ex = ease_in(seg(t, 7.35, 7.9))
    ry = lerp(-38, 0, k) + 7 * math.sin((t - 3.2) * 1.3) * (1 - ex)
    rx = lerp(24, 4, k)
    cy = lerp(H + 700, 1040, k) + lerp(0, 60, ex)
    sc = lerp(0.82, 0.9, k) * lerp(1, 0.55, ex)
    ph = phone(t)
    g = glow(ph.resize((ph.width // 4, ph.height // 4)), 10, 0.5, ROSE).resize((ph.width + 120, ph.height + 120))
    put3d(fr, g, W / 2, cy + 30, ry, rx, 0.7 * (1 - ex), sc)
    put3d(fr, ph, W / 2, cy, ry, rx, 1 - ease(seg(t, 7.75, 8.0)), sc)

GRID = [(-1, -1), (0, -1), (1, -1), (-1, 1), (0, 1), (1, 1)]
def s_grid(t, fr):
    if not (7.4 <= t < 8.6): return
    for k, (gx, gy) in enumerate(GRID):
        if k == 4: continue
        p = ease(seg(t, 7.45 + 0.04 * k, 7.95 + 0.04 * k)); out = ease_in(seg(t, 8.05, 8.45))
        x = W / 2 + gx * 340 * p * (1 + out * 1.6); y = 1040 + gy * 240 * p * (1 + out * 1.6)
        put3d(fr, TILES[k], x, y, gx * 25 * (1 - p) + gx * 20 * out, -gy * 18 * (1 - p), p * (1 - out), lerp(0.4, 0.86, p))

FULLS = [("s7", 7.95, 9.5, T_15, K_15), ("s4", 9.5, 11.0, T_POUR, K_POUR), ("s9", 11.0, 12.6, T_RIT, K_RIT)]
def full_shot(name, t, t0, t1, big, kick):
    im = FULL[name]; p = seg(t, t0, t1); z = lerp(1.0, 1.12, p)
    vw, vh = im.width / z, im.height / z
    l = (im.width - vw) / 2; tp = (im.height - vh) * lerp(0.5, 0.35, p)
    fr = im.resize((W, H), Image.BICUBIC, box=(l, tp, l + vw, tp + vh)).convert("RGBA")
    fr.alpha_composite(SHADE)
    lt = t - t0 - 0.12; a = ease(lt / 0.18); s = lerp(1.35, 1.0, ease(lt / 0.25))
    if lt > 0:
        put(fr, kick, W / 2, 1380, ease(seg(lt, 0.15, 0.45)))
        bb = mblur(big, (1 - ease(lt / 0.2)) * 160)
        put(fr, bb, W / 2, 1520, a, s)
    return fr

def zoom_tile_to_full(t, fr):
    """La tuile du bain grandit jusqu'au plein écran (7,6 → 8,0)."""
    p = ease_io(seg(t, 7.55, 8.0))
    if p <= 0: return fr
    gx, gy = GRID[4]; x0 = W / 2 + gx * 340; y0 = 1040 + gy * 240
    w_ = int(lerp(258, W, p)); h_ = int(lerp(361, H, p))
    im = cover(S7, w_, h_).convert("RGBA")
    r_ = int(lerp(30, 0, p)); m = Image.new("L", (w_, h_), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w_ - 1, h_ - 1), r_, fill=255)
    im.putalpha(m); fr.alpha_composite(im, (int(lerp(x0, W / 2, p) - w_ / 2), int(lerp(y0, H / 2, p) - h_ / 2)))
    return fr

def s_offer(t, fr):
    if not (12.45 <= t < 14.95): return
    lt = t - 12.6
    a = ease(lt / 0.2); dx = (1 - ease(lt / 0.25))
    put(fr, mblur(T_PACK, dx * 220), lerp(W / 2 - 500, W / 2, ease(lt / 0.25)), 560, a)
    lo = seg(lt, 0.5, 0.9)
    if lo > 0:
        put(fr, T_OLD, W / 2, 760, ease(lo))
        sp = ease(seg(lt, 0.7, 0.95))
        if sp > 0:
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); x0 = W / 2 - T_OLD.width / 2 + 30
            ImageDraw.Draw(ov).line((x0, 768, x0 + (T_OLD.width - 60) * sp, 752), fill=ROSE + (255,), width=8); fr.alpha_composite(ov)
    pp = seg(lt, 1.0, 1.25)
    if pp > 0:
        put(fr, T_PRICE, W / 2, 1010, ease(pp * 1.6), lerp(1.6, 1.0, back(pp)))
        put(fr, T_LEM, W / 2, 1200, ease(seg(lt, 1.3, 1.6)))
        put(fr, T_UNIT, W / 2, 1300, ease(seg(lt, 1.5, 1.8)))
    fo = ease(seg(t, 14.75, 14.95))
    if fo > 0: fr.alpha_composite(Image.new("RGBA", (W, H), INK + (int(255 * fo),)))

def s_liv(t, fr):
    if not (14.85 <= t < 17.0): return
    lt = t - 14.95
    for img, y, d in ((T_LIV1, 720, 0.0), (T_LIV2, 880, 0.12)):
        k = ease((lt - d) / 0.25)
        if k > 0: put(fr, mblur(img, (1 - k) * -240), lerp(W / 2 + 520, W / 2, k), y, min(1, k * 1.5))
    put(fr, T_LIV3, W / 2, 1020, ease(seg(lt, 0.4, 0.7)))
    pk = seg(lt, 0.5, 1.9)
    if pk > 0:
        x = lerp(-200, W + 200, ease_io(pk)); y = 1320 + 10 * math.sin(lt * 14)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
        for k in range(4): d.line((x - 190 - k * 40, y - 60 + k * 40, x - 110 - k * 40, y - 60 + k * 40), fill=NACRE + (150,), width=6)
        fr.alpha_composite(ov); put(fr, PARCEL, x, y)
    fo = ease(seg(t, 16.8, 17.0))
    if fo > 0: fr.alpha_composite(Image.new("RGBA", (W, H), INK + (int(255 * fo),)))

def s_code(t, fr):
    if not (16.9 <= t < 21.1): return
    lt = t - 17.0
    fl = ease(seg(lt, 0.15, 0.7)); out = ease_in(seg(t, 19.15, 19.5))
    put(fr, T_CODE_K, W / 2, 640, ease(seg(lt, 0.0, 0.35)) * (1 - out))
    if fl > 0 and out < 1:
        put3d(fr, TICKET, W / 2, 960 - out * 200, lerp(88, 0, fl), 6 * math.sin(lt * 1.6) * (1 - out), fl * (1 - out), lerp(1, 0.6, out))
    # produit qui tombe dans le panier
    if t >= 19.5:
        p = seg(t, 19.6, 20.3); land = ease_in(p)
        put(fr, BAG, W / 2, 1180, ease(seg(t, 19.5, 19.8)), back(seg(t, 19.5, 19.85)) * (1 + 0.08 * math.exp(-max(0, t - 20.3) * 10) * (t > 20.3)))
        if p < 1:
            put3d(fr, SACHET_CARD, W / 2, lerp(500, 1150, land), lerp(0, 18, land), lerp(-12, 25, land), 1 - ease(seg(p, 0.85, 1.0)), lerp(0.9, 0.25, land))
        if t > 20.3:
            put(fr, BADGE, W / 2 + 110, 1080, 1, back(seg(t, 20.3, 20.55)))
            put(fr, T_ADDED, W / 2, 1420, ease(seg(t, 20.4, 20.7)))
    fo = ease(seg(t, 20.85, 21.05))
    if fo > 0: fr.alpha_composite(Image.new("RGBA", (W, H), INK + (int(255 * fo),)))

def s_end(t, fr):
    if t < 20.95: return
    lt = t - 21.05; col = ease_in(seg(t, 23.45, 23.85))
    sc = 1 - col
    if sc > 0.02:
        k = ease(lt / 0.5)
        lg = LOGO if k > 0.98 else LOGO.filter(ImageFilter.GaussianBlur((1 - k) * 14))
        cy = lerp(H / 2, 700, 0) ; c = lambda y: H / 2 + (y - H / 2) * sc
        put(fr, lg, W / 2, c(700), k, lerp(1.15, 1, k) * sc)
        put(fr, LOGO_S, W / 2, c(830), ease(seg(lt, 0.25, 0.6)), sc)
        put(fr, T_END, W / 2, c(1050), ease(seg(lt, 0.55, 0.9)), sc)
        put(fr, BTN, W / 2, c(1230), ease(seg(lt, 0.9, 1.2)), back(seg(lt, 0.9, 1.25)) * sc * (1 + 0.025 * math.sin(max(0, lt - 1.4) * 4)))
        put(fr, T_URL, W / 2, c(1380), ease(seg(lt, 1.2, 1.5)), sc)
    if t > 23.7:
        r = 10 + 8 * math.exp(-max(0, t - 23.85) * 8)
        put(fr, dot(int(r)), W / 2, H / 2, 1 - ease(seg(t, 24.2, 24.5)))

# ------------------------------------------------------------------ assemblage d'une image
def render(n):
    t = n / FPS
    if 7.95 <= t < 12.6:
        cur = [f for f in FULLS if f[1] <= t < f[2]][0]
        fr = full_shot(cur[0], t, *cur[1:])
        if t < 8.6:
            s_grid(t, fr)
        # balayages (whip) entre plans pleins
        for name0, name1, T in (("s7", "s4", 9.5), ("s4", "s9", 11.0)):
            if T - 0.14 <= t < T + 0.14:
                p = ease_io(seg(t, T - 0.14, T + 0.14))
                f0 = full_shot(name0, min(t, T - 0.001), *[f for f in FULLS if f[0] == name0][0][1:])
                f1 = full_shot(name1, max(t, T), *[f for f in FULLS if f[0] == name1][0][1:])
                cv = Image.new("RGBA", (W, H)); off = int(p * W)
                cv.paste(f0.crop((off, 0, W, H)), (0, 0)); cv.paste(f1.crop((0, 0, off, H)) if off > 0 else f1.crop((0, 0, 1, H)), (W - off, 0))
                fr = Image.fromarray(frame_mblur(np.asarray(cv.convert("RGB")), 260 * math.sin(math.pi * p))).convert("RGBA")
        if t >= 12.45:
            pass
    else:
        fr = background(t)
        s_intro(t, fr); s_grid(t, fr); s_phone(t, fr)
        if 7.55 <= t < 7.95: fr = zoom_tile_to_full(t, fr)
        s_offer(t, fr); s_liv(t, fr); s_code(t, fr); s_end(t, fr)
    # sortie du dernier plan plein → fond sombre (balayage)
    if 12.46 <= t < 12.74:
        p = ease_io(seg(t, 12.46, 12.74)); f0 = full_shot("s9", 12.59, *FULLS[2][1:])
        bg = background(t); s_offer(t, bg); off = int(p * W)
        cv = Image.new("RGBA", (W, H)); cv.paste(f0.crop((off, 0, W, H)), (0, 0))
        if off > 0: cv.paste(bg.crop((0, 0, off, H)), (W - off, 0))
        fr = Image.fromarray(frame_mblur(np.asarray(cv.convert("RGB")), 260 * math.sin(math.pi * p))).convert("RGBA")
    rgb = np.asarray(fr.convert("RGB")).astype(np.int16)
    rgb += np.random.default_rng(n).integers(-6, 7, (H // 2, W // 2, 1), dtype=np.int16).repeat(2, 0).repeat(2, 1)
    if t < 0.15: rgb = (rgb * (t / 0.15)).astype(np.int16)
    return np.clip(rgb, 0, 255).astype(np.uint8).tobytes()

EVENTS = {"dur": DUR, "drop": 8.0, "end": 21.0, "collapse": 23.6,
          "whoosh": [3.3, 5.2, 7.5, 9.5, 11.0, 12.6, 14.95, 17.15, 19.6, 21.05],
          "pop": [4.85, 5.4, 6.5, 7.1, 7.32, 13.1, 13.45, 20.3, 22.0],
          "type": [3.4 + 0.25 + 0.07 * i for i in range(16)],
          "ding": [20.32], "slam": [8.12, 9.62, 11.12, 12.62, 13.6, 14.95]}

if __name__ == "__main__":
    wav = OUT.replace(".mp4", ".wav")
    subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "music_motion.py"),
                    wav, json.dumps(EVENTS)], check=True)
    ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", wav, "-vf", "hqdn3d=1.5:1.5:3:3", "-c:v", "libx264", "-preset", "slow", "-crf", "23",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT],
                          stdin=subprocess.PIPE)
    frames = sys.argv[4].split(",") if len(sys.argv) > 4 else None
    rng_ = [int(float(x) * FPS) for x in frames] if frames else range(int(DUR * FPS))
    with Pool(4) as pool:
        for i, b in enumerate(pool.imap(render, rng_, chunksize=4)):
            ff.stdin.write(b)
            if i % 150 == 0: print(i, flush=True)
    ff.stdin.close(); ff.wait(); os.remove(wav); print("ok", OUT)
