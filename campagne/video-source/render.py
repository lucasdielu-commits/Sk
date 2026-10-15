"""Rendu des vidéos publicitaires Sorienka Studio (9:16, 1080x1920, 30 i/s).

Usage : python3 render.py <version: 25|15> <dossier_images> <dossier_polices> <sortie.mp4>
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

VERSION, IMG, FONTS, OUT = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
W, H, FPS = 1080, 1920, 30
XF = 0.45                               # durée des fondus entre scènes

PRUNE = (42, 31, 45); CREME = (250, 246, 240)
PEARL_TOP = (246, 232, 228); PEARL_BOT = (232, 196, 196)

def font(name, size):
    files = {"serif": "fontsource-cormorant-garamond-5.3.0/files/cormorant-garamond-latin-500-normal.woff",
             "serif-i": "fontsource-cormorant-garamond-5.3.0/files/cormorant-garamond-latin-500-italic.woff",
             "serif-l": "fontsource-cormorant-garamond-5.3.0/files/cormorant-garamond-latin-400-normal.woff",
             "sans": "fontsource-jost-5.3.0/files/jost-latin-400-normal.woff",
             "sans-l": "fontsource-jost-5.3.0/files/jost-latin-300-normal.woff",
             "sans-m": "fontsource-jost-5.3.0/files/jost-latin-500-normal.woff"}
    return ImageFont.truetype(os.path.join(FONTS, files[name]), size)

# ---------------------------------------------------------------- scénarios
URL = "sorienkastudio.myshopify.com"
S25 = [
    dict(img="c_hook", dur=2.4, zoom=(1.16, 1.02), pan=(0, -0.04), card_h=1010,
         texts=[("Et si tu prenais enfin", "serif", 82, 300, 0.0),
                ("15 minutes pour toi ?", "serif-i", 96, 400, 0.55)]),
    dict(img="c_sachet", dur=3.7, zoom=(1.0, 1.08), pan=(0, 0.02), sweep=True, card_h=1000,
         texts=[("Découvre ton nouveau", "serif", 78, 300, 0.25),
                ("rituel skincare.", "serif-i", 88, 395, 0.6)]),
    dict(img="c_texture", dur=3.5, zoom=(1.06, 1.16), pan=(0.03, 0.0), card_w=920,
         texts=[("Il se pose", "serif", 80, 330, 0.25),
                ("tout en douceur.", "serif-i", 88, 425, 0.6)]),
    dict(img="c_relax", dur=4.9, zoom=(1.0, 1.1), pan=(0, -0.03), card_h=1000,
         texts=[("Un instant", "serif", 80, 300, 0.3),
                ("rien que pour toi.", "serif-i", 90, 395, 0.75)]),
    dict(img="c_hero", dur=5.3, zoom=(1.0, 1.1), pan=(0.02, 0.0), sweep=True, card_w=920,
         texts=[("Sorienka Studio", "serif", 104, 330, 0.3),
                ("Révèle ton rituel beauté.", "serif-i", 70, 455, 1.4)]),
    dict(cta=True, dur=5.2),
]
S15 = [
    dict(img="c_hook", dur=2.2, zoom=(1.16, 1.02), pan=(0, -0.04), card_h=1010,
         texts=[("15 minutes", "serif", 96, 300, 0.0),
                ("pour toi ?", "serif-i", 100, 405, 0.4)]),
    dict(img="c_sachet", dur=2.6, zoom=(1.0, 1.08), pan=(0, 0.02), sweep=True, card_h=1000,
         texts=[("Ton nouveau", "serif", 80, 300, 0.15),
                ("rituel skincare.", "serif-i", 88, 395, 0.4)]),
    dict(img="c_texture", dur=2.0, zoom=(1.06, 1.16), pan=(0.03, 0.0), card_w=920,
         texts=[("Masque Collagène", "serif", 84, 340, 0.15)]),
    dict(img="c_relax", dur=3.4, zoom=(1.0, 1.1), pan=(0, -0.03), card_h=1000,
         texts=[("Un instant", "serif", 80, 300, 0.2),
                ("rien que pour toi.", "serif-i", 90, 395, 0.55)]),
    dict(cta=True, dur=4.8),
]
SCENES = S25 if VERSION == "25" else S15
starts = []; t0 = 0.0
for s in SCENES:
    starts.append(t0); t0 += s["dur"]
TOTAL = t0
NFR = int(round(TOTAL * FPS))

# ---------------------------------------------------------------- utilitaires
def ease(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3
def lerp(a, b, x): return a + (b - a) * x

def gradient(top, bot):
    g = np.linspace(0, 1, H)[:, None, None]
    a = np.array(top)[None, None] * (1 - g) + np.array(bot)[None, None] * g
    return np.repeat(a, W, 1)

PEARL = gradient(PEARL_TOP, PEARL_BOT)

def background(im, mix=0.45):
    """Image floutée en plein cadre, fondue dans le dégradé nacré."""
    sw, sh = im.size; sc = max(W / sw, H / sh)
    big = im.resize((int(sw * sc) + 2, int(sh * sc) + 2), Image.BICUBIC)
    l = (big.width - W) // 2; tp = (big.height - H) // 2
    big = big.crop((l, tp, l + W, tp + H)).resize((W // 8, H // 8), Image.BILINEAR)
    big = big.filter(ImageFilter.GaussianBlur(6)).resize((W, H), Image.BICUBIC)
    a = np.asarray(big).astype(float) * mix + PEARL * (1 - mix)
    # éclaircit le haut pour la lisibilité des titres
    lift = np.clip(1 - np.linspace(0, 1, H) / 0.42, 0, 1)[:, None, None] * 0.55
    a = a * (1 - lift) + np.array(PEARL_TOP)[None, None] * lift
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))

def rounded_mask(w, h, r):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    return m

def text_img(txt, fname, size, color=PRUNE, track=0):
    f = font(fname, size)
    if track:
        widths = [f.getlength(c) for c in txt]; tw = int(sum(widths) + track * (len(txt) - 1))
    else:
        tw = int(f.getlength(txt))
    asc, desc = f.getmetrics(); th = asc + desc
    im = Image.new("RGBA", (tw + 20, th + 20), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if track:
        x = 10
        for c, w_ in zip(txt, widths): d.text((x, 10), c, font=f, fill=color); x += w_ + track
    else:
        d.text((10, 10), txt, font=f, fill=color)
    return im

def with_alpha(im, a):
    if a >= 0.999: return im
    r, g, b, al = im.split()
    return Image.merge("RGBA", (r, g, b, al.point(lambda v: int(v * a))))

# ---------------------------------------------------------------- bokeh
rng = np.random.default_rng(3)
def sprite(d):
    m = Image.new("L", (d * 2, d * 2), 0)
    ImageDraw.Draw(m).ellipse((d // 2, d // 2, d * 3 // 2, d * 3 // 2), fill=255)
    return m.filter(ImageFilter.GaussianBlur(d / 5))
SPRITES = [sprite(d) for d in (28, 46, 70, 110)]
PARTS = [dict(x=rng.uniform(0, W), y=rng.uniform(0, H), vx=rng.uniform(-8, 8), vy=rng.uniform(-38, -12),
              s=int(rng.integers(0, 4)), a=rng.uniform(0.18, 0.45), ph=rng.uniform(0, 6)) for _ in range(22)]
WHITE = Image.new("RGB", (240, 240), (255, 250, 248))

def bokeh(frame, t):
    for p in PARTS:
        sp = SPRITES[p["s"]]; sw = sp.width
        x = (p["x"] + p["vx"] * t) % (W + sw) - sw; y = (p["y"] + p["vy"] * t) % (H + sw) - sw
        a = p["a"] * (0.65 + 0.35 * math.sin(t * 1.3 + p["ph"]))
        frame.paste(WHITE.crop((0, 0, sw, sw)), (int(x), int(y)), sp.point(lambda v, a=a: int(v * a)))

# ---------------------------------------------------------------- préparation des scènes
GRAIN = [Image.fromarray(np.clip(128 + rng.normal(0, 9, (H // 2, W // 2)), 0, 255).astype(np.uint8)).resize((W, H))
         for _ in range(4)]
SWEEP = Image.fromarray((np.sin(np.linspace(0, np.pi, 260)) ** 2 * 255).astype(np.uint8)[None].repeat(2600, 0)).rotate(
    -22, expand=True, resample=Image.BICUBIC)

for s in SCENES:
    if s.get("cta"):
        s["bg"] = background(Image.open(os.path.join(IMG, "c_water.png")).convert("RGB"), 0.55)
        src = Image.open(os.path.join(IMG, "c_cta.png")).convert("RGB")
        cw = 640; ch = int(cw * src.height / src.width)
        s["card"] = (cw, ch); s["src"] = src.resize((int(cw * 1.12), int(ch * 1.12)), Image.LANCZOS).filter(
            ImageFilter.UnsharpMask(2, 70, 2))
        s["zoom"] = (1.0, 1.06); s["pan"] = (0, 0)
        s["cy"] = 1010
        s["texts"] = []
        s["logo1"] = text_img("Sorienka", "serif-l", 168)
        s["logo2"] = text_img("STUDIO", "sans-l", 38, track=22)
        s["line"] = text_img("Ton prochain rituel commence ici.", "serif-i", 66)
        s["btn"] = text_img("DÉCOUVRIR LE MASQUE", "sans-m", 38, CREME, track=5)
        s["url"] = text_img(URL, "sans", 32, PRUNE)
        continue
    src = Image.open(os.path.join(IMG, s["img"] + ".png")).convert("RGB")
    ar = src.width / src.height
    if "card_h" in s:
        ch = s["card_h"]; cw = int(ch * ar)
        if cw > 920: cw = 920; ch = int(cw / ar)
    else:
        cw = s["card_w"]; ch = int(cw / ar)
    s["card"] = (cw, ch)
    s["src"] = src.resize((int(cw * 1.18), int(ch * 1.18)), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 70, 2))
    s["bg"] = background(src)
    s["cy"] = 1080
    s["timgs"] = [(text_img(tx, fn, sz), y, ti) for tx, fn, sz, y, ti in s["texts"]]
for s in SCENES:
    cw, ch = s["card"]
    s["mask"] = rounded_mask(cw, ch, 34)
    sh = Image.new("L", (cw + 160, ch + 160), 0); sh.paste(s["mask"], (80, 80))
    s["shadow"] = sh.filter(ImageFilter.GaussianBlur(30)).point(lambda v: int(v * 0.42))
TAG = text_img("SORIENKA STUDIO  ·  MASQUE COLLAGÈNE", "sans", 26, (122, 92, 104), track=4)

# ---------------------------------------------------------------- dessin d'une scène
def card_frame(s, lt):
    """Image de la carte à l'instant local lt (zoom lent + reflet nacré)."""
    cw, ch = s["card"]; p = lt / s["dur"]
    z = lerp(s["zoom"][0], s["zoom"][1], p)
    src = s["src"]; sw, sh_ = src.size
    # fenêtre visible dans l'image agrandie (zoom 1 = image entière)
    vw = cw * 1.18 / z; vh = ch * 1.18 / z
    vw = min(vw, sw); vh = min(vh, sh_)
    cx = sw / 2 + s["pan"][0] * sw * p; cy = sh_ / 2 + s["pan"][1] * sh_ * p
    l = min(max(0, cx - vw / 2), sw - vw); tp = min(max(0, cy - vh / 2), sh_ - vh)
    im = src.resize((cw, ch), Image.BICUBIC, box=(l, tp, l + vw, tp + vh))
    if s.get("sweep"):
        k = (lt - 0.5) / 1.8
        if 0 <= k <= 1:
            x = int(lerp(-SWEEP.width, cw, k)); band = Image.new("L", (cw, ch), 0)
            band.paste(SWEEP, (x, (ch - SWEEP.height) // 2))
            im = Image.composite(Image.new("RGB", (cw, ch), (255, 248, 246)), im, band.point(lambda v: int(v * 0.38)))
    return im

def draw_scene(i, lt):
    s = SCENES[i]
    fr = s["bg"].copy()
    bokeh(fr, starts[i] + lt)
    cw, ch = s["card"]
    e = ease(lt / 0.6); sc = lerp(0.955, 1.0, e)
    im = card_frame(s, lt)
    if sc < 0.999:
        nw, nh = int(cw * sc), int(ch * sc)
        im = im.resize((nw, nh), Image.BICUBIC); mk = s["mask"].resize((nw, nh), Image.BICUBIC)
    else:
        nw, nh, mk = cw, ch, s["mask"]
    x = (W - nw) // 2; y = s["cy"] - nh // 2 + int((1 - e) * 30)
    shadow = s["shadow"] if sc >= 0.999 else s["shadow"].resize((nw + 160, nh + 160))
    fr.paste(Image.new("RGB", shadow.size, (120, 70, 80)), (x - 80, y - 80 + 18), shadow)
    fr.paste(im, (x, y), mk)
    fr = fr.convert("RGBA")
    if s.get("cta"):
        def put(img, cy, t_in, rise=22):
            a = ease((lt - t_in) / 0.5)
            if a <= 0: return
            fr.alpha_composite(with_alpha(img, a), ((W - img.width) // 2, int(cy - img.height / 2 + (1 - a) * rise)))
        put(s["logo1"], 300, 0.15); put(s["logo2"], 410, 0.35)
        put(s["line"], 1430, 0.7)
        # bouton (pilule) avec légère pulsation
        a = ease((lt - 1.0) / 0.5)
        if a > 0:
            pul = 1 + 0.025 * math.sin(max(0, lt - 1.6) * 3.2) * (lt > 1.6)
            bw, bh = int(560 * pul), int(104 * pul)
            btn = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
            ImageDraw.Draw(btn).rounded_rectangle((0, 0, bw - 1, bh - 1), bh // 2, fill=PRUNE + (255,))
            t_ = s["btn"]; btn.alpha_composite(t_, ((bw - t_.width) // 2, (bh - t_.height) // 2 + 2))
            fr.alpha_composite(with_alpha(btn, a), ((W - bw) // 2, int(1545 - bh / 2 + (1 - a) * 22)))
        put(s["url"], 1650, 1.3)
    else:
        a = ease((lt - 0.1) / 0.5)
        if a > 0: fr.alpha_composite(with_alpha(TAG, a * 0.9), ((W - TAG.width) // 2, 190))
        for img, cy, ti in s["timgs"]:
            a = ease((lt - ti) / 0.5)
            if a > 0:
                fr.alpha_composite(with_alpha(img, a), ((W - img.width) // 2, int(cy - img.height / 2 + (1 - a) * 26)))
    return fr.convert("RGB")

# ---------------------------------------------------------------- rendu
wav = OUT.replace(".mp4", ".wav")
cuts = [starts[i] for i in range(1, len(SCENES))]
drop_t = starts[min(4, len(SCENES) - 1)] + 0.25 if VERSION == "25" else starts[-1] - 1.0
subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "music.py"), wav, str(TOTAL),
                json.dumps(cuts), str(drop_t)], check=True)
ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "slow", "-crf", "17",
                       "-pix_fmt", "yuv420p", "-profile:v", "high", "-c:a", "aac", "-b:a", "192k",
                       "-shortest", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
for n in range(NFR):
    t = n / FPS
    i = max(k for k in range(len(SCENES)) if starts[k] <= t)
    fr = draw_scene(i, t - starts[i])
    # fondu enchaîné : la scène suivante apparaît sur les XF dernières secondes
    if i + 1 < len(SCENES) and t > starts[i + 1] - XF:
        k = (t - (starts[i + 1] - XF)) / XF
        nxt = draw_scene(i + 1, 0.0)
        fr = Image.blend(fr, nxt, ease(k))
    g = GRAIN[n % 4]
    fr = Image.blend(fr, ImageChops.soft_light(fr, Image.merge("RGB", (g, g, g))), 0.5)
    if t < 0.12: fr = Image.blend(Image.new("RGB", (W, H), PEARL_TOP), fr, t / 0.12)
    ff.stdin.write(fr.tobytes())
    if n % 150 == 0: print(f"{n}/{NFR}", flush=True)
ff.stdin.close(); ff.wait()
os.remove(wav)
print("ok", OUT, TOTAL)
