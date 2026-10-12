"""Film publicitaire « Elle s'était oubliée » — Sorienka Studio (9:16, 1080x1920, 30 i/s).

Usage : python3 render_story.py <39|15> <dossier_images> <dossier_polices> <sortie.mp4>
Images attendues dans le dossier : s1 s3 s4 s6 s7 s9 (plans de vie) et c_texture c_sachet c_hero c_water (produit).
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

VERSION, IMG, FONTS, OUT = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
W, H, FPS = 1080, 1920, 30
PRUNE = (42, 31, 45); CREME = (250, 246, 240)
PEARL_TOP = (247, 234, 229); PEARL_BOT = (230, 196, 194)
URL = "sorienkastudio.myshopify.com"

def font(name, size):
    files = {"serif": "fontsource-cormorant-garamond-5.3.0/files/cormorant-garamond-latin-500-normal.woff",
             "serif-i": "fontsource-cormorant-garamond-5.3.0/files/cormorant-garamond-latin-500-italic.woff",
             "serif-l": "fontsource-cormorant-garamond-5.3.0/files/cormorant-garamond-latin-400-normal.woff",
             "sans": "fontsource-jost-5.3.0/files/jost-latin-400-normal.woff",
             "sans-l": "fontsource-jost-5.3.0/files/jost-latin-300-normal.woff",
             "sans-m": "fontsource-jost-5.3.0/files/jost-latin-500-normal.woff"}
    return ImageFont.truetype(os.path.join(FONTS, files[name]), size)

# ------------------------------------------------------------------ scénario
# photo : plan de vie plein cadre. box = recadrage 9:16 dans l'image source.
# grade = (température, saturation, luminosité) au début et à la fin du plan.
COOL = (-0.9, 0.55, 0.82); NEUTRE = (0.15, 0.9, 1.0); CHAUD = (0.55, 0.95, 1.04)
if VERSION == "39":
    SCENES = [
        dict(kind="photo", img="s1", box=(443, 0, 885, 786), dur=5.6, zoom=(1.0, 1.2), focus=(0.5, 0.36),
             grade=(COOL, COOL)),
        dict(kind="photo", img="s3", box=(600, 520, 940, 1124), dur=3.0, zoom=(1.08, 1.0), focus=(0.5, 0.5),
             grade=(COOL, CHAUD), leak=True),
        dict(kind="card", img="c_texture", dur=2.6, card_w=900, zoom=(1.04, 1.14)),
        dict(kind="card", img="c_sachet", dur=3.0, card_h=820, zoom=(1.0, 1.07), sweep=True),
        dict(kind="card", img="c_hero", dur=2.6, card_w=900, zoom=(1.0, 1.08), sweep=True),
        dict(kind="photo", img="s4", box=(210, 0, 652, 786), dur=3.2, zoom=(1.0, 1.12), focus=(0.5, 0.3),
             grade=(NEUTRE, NEUTRE)),
        dict(kind="photo", img="s6", box=(215, 0, 588, 664), dur=2.5, zoom=(1.04, 1.14), focus=(0.55, 0.32),
             grade=(NEUTRE, CHAUD)),
        dict(kind="photo", img="s7", box=(380, 0, 864, 860), dur=3.6, zoom=(1.0, 1.1), focus=(0.5, 0.42),
             grade=(CHAUD, CHAUD), leak=True),
        dict(kind="photo", img="s9", box=(300, 0, 963, 1179), dur=6.4, zoom=(1.0, 1.16), focus=(0.48, 0.36),
             grade=(CHAUD, CHAUD), leak=True),
        dict(kind="cta", dur=6.5),
    ]
    SUBS = [("À force de penser à tout le monde…", 0.6, 2.9),
            ("…elle avait oublié une personne.", 3.0, 5.5),
            ("Celle qui méritait aussi", 5.9, 7.3),
            ("un peu d'attention.", 7.3, 8.9),
            ("Parfois, il suffit de commencer", 11.6, 13.6),
            ("par un petit geste.", 13.6, 16.3),
            ("Quelques minutes pour ralentir.", 16.9, 19.6),
            ("Respirer.", 19.8, 21.6),
            ("Prendre soin de soi.", 21.8, 24.6),
            ("Parce que prendre soin de soi", 25.4, 27.3),
            ("n'est pas un luxe.", 27.3, 29.0),
            ("C'est aussi une façon", 29.2, 30.6),
            ("de se retrouver.", 30.6, 32.4)]
    TITLES = [("Sorienka Studio", "serif", 92, 330, 11.4, 16.3),
              ("Ton moment.", "serif", 70, 262, 17.2, 24.9),
              ("Ton rituel.", "serif", 70, 262, 18.6, 24.9),
              ("Toi.", "serif-i", 80, 262, 20.2, 24.9)]
    STAMP = ("21:47", 0.4, 5.0)
    CTA = dict(l1="Le début de ton rituel beauté.", l2="Découvre notre masque collagène.", btn="DÉCOUVRIR")
else:
    SCENES = [
        dict(kind="photo", img="s1", box=(443, 0, 885, 786), dur=3.6, zoom=(1.04, 1.2), focus=(0.5, 0.36),
             grade=(COOL, COOL)),
        dict(kind="card", img="c_sachet", dur=2.8, card_h=820, zoom=(1.0, 1.07), sweep=True),
        dict(kind="photo", img="s4", box=(210, 0, 652, 786), dur=2.4, zoom=(1.0, 1.1), focus=(0.5, 0.3),
             grade=(NEUTRE, CHAUD)),
        dict(kind="photo", img="s7", box=(380, 0, 864, 860), dur=2.4, zoom=(1.0, 1.1), focus=(0.5, 0.42),
             grade=(CHAUD, CHAUD), leak=True),
        dict(kind="cta", dur=3.8),
    ]
    SUBS = [("À force de penser à tout le monde…", 0.3, 2.0),
            ("…elle s'était oubliée.", 2.0, 3.7),
            ("Il suffit d'un petit geste.", 4.0, 6.4)]
    TITLES = [("Sorienka Studio", "serif", 92, 330, 3.9, 6.4),
              ("Ton moment.", "serif", 70, 262, 6.6, 11.0),
              ("Ton rituel.", "serif", 70, 262, 7.6, 11.0),
              ("Toi.", "serif-i", 80, 262, 8.6, 11.0)]
    STAMP = ("21:47", 0.2, 3.4)
    CTA = dict(l1="Le début de ton rituel beauté.", l2="Découvre notre masque collagène.", btn="DÉCOUVRIR")

XF = 0.8
starts = []; acc = 0.0
for s in SCENES: starts.append(acc); acc += s["dur"]
TOTAL = acc; NFR = int(round(TOTAL * FPS))

# ------------------------------------------------------------------ utilitaires
def ease(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3
def ease_io(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
def lerp(a, b, x): return a + (b - a) * x

def grade(im, g):
    temp, sat, br = g
    a = np.asarray(im).astype(np.float32)
    lum = (a @ np.array([0.299, 0.587, 0.114], np.float32))[..., None]
    a = lum + (a - lum) * sat
    a = a + np.array([18, 4, -20], np.float32) * temp
    a = a * br
    if temp < 0:   # nuit froide : on écrase un peu les hautes lumières
        a = a * (1 + temp * 0.06)
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))

def text_img(txt, fname, size, color, track=0, shadow=False):
    f = font(fname, size)
    widths = [f.getlength(c) for c in txt] if track else None
    tw = int(sum(widths) + track * (len(txt) - 1)) if track else int(f.getlength(txt))
    asc, desc = f.getmetrics(); th = asc + desc; pad = 40
    im = Image.new("RGBA", (tw + 2 * pad, th + 2 * pad), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    def draw(dr, fill):
        if track:
            x = pad
            for c, w_ in zip(txt, widths): dr.text((x, pad), c, font=f, fill=fill); x += w_ + track
        else:
            dr.text((pad, pad), txt, font=f, fill=fill)
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); draw(ImageDraw.Draw(sh), (20, 10, 15, 150))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(9)))
    draw(ImageDraw.Draw(im), color)
    return im

def with_alpha(im, a):
    if a >= 0.999: return im
    r, g, b, al = im.split()
    return Image.merge("RGBA", (r, g, b, al.point(lambda v: int(v * a))))

def vgrad(top_a, bot_a, y0, y1, color=(15, 8, 12)):
    a = np.zeros(H, np.float32); yy = np.arange(H)
    a = np.where(yy < y0, top_a * (1 - yy / max(1, y0)), 0) + np.where(yy > y1, bot_a * ((yy - y1) / (H - y1)), 0)
    al = (a[:, None].repeat(W, 1) * 255).clip(0, 255).astype(np.uint8)
    im = Image.new("RGBA", (W, H), color + (0,)); im.putalpha(Image.fromarray(al)); return im

SHADE = vgrad(0.78, 0.8, 620, 1080)        # assombrit haut et bas pour les textes clairs
yy, xx = np.mgrid[0:H, 0:W]
vig = (((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.7)) ** 2)
VIGNETTE = Image.new("RGBA", (W, H), (10, 5, 8, 0))
VIGNETTE.putalpha(Image.fromarray((np.clip(vig - 0.25, 0, 1) * 200).astype(np.uint8)))
leak = np.exp(-(((xx - W * 0.85) / (W * 0.55)) ** 2 + ((yy - H * 0.25) / (H * 0.45)) ** 2))
LEAK = Image.new("RGBA", (W, H), (255, 176, 120, 0)); LEAK.putalpha(Image.fromarray((leak * 255).astype(np.uint8)))
rng = np.random.default_rng(5)
GRAIN = [Image.fromarray(np.clip(128 + rng.normal(0, 10, (H // 2, W // 2)), 0, 255).astype(np.uint8)).resize((W, H))
         for _ in range(4)]
PEARL = np.repeat((np.array(PEARL_TOP)[None, None] * (1 - np.linspace(0, 1, H)[:, None, None])
                   + np.array(PEARL_BOT)[None, None] * np.linspace(0, 1, H)[:, None, None]), W, 1)

def pearl_bg(im, mix=0.4):
    sw, sh = im.size; sc = max(W / sw, H / sh)
    big = im.resize((int(sw * sc) + 2, int(sh * sc) + 2), Image.BICUBIC)
    l = (big.width - W) // 2; tp = (big.height - H) // 2
    big = big.crop((l, tp, l + W, tp + H)).resize((W // 8, H // 8)).filter(ImageFilter.GaussianBlur(6)).resize((W, H), Image.BICUBIC)
    a = np.asarray(big).astype(float) * mix + PEARL * (1 - mix)
    lift = np.clip(1 - np.linspace(0, 1, H) / 0.4, 0, 1)[:, None, None] * 0.5
    a = a * (1 - lift) + np.array(PEARL_TOP)[None, None] * lift
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))

def rounded(w, h, r):
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255); return m

SWEEP = Image.fromarray((np.sin(np.linspace(0, np.pi, 260)) ** 2 * 255).astype(np.uint8)[None].repeat(2600, 0)).rotate(
    -22, expand=True, resample=Image.BICUBIC)

# ------------------------------------------------------------------ préparation
OVER = 1.22
for s in SCENES:
    if s["kind"] == "photo":
        src = Image.open(os.path.join(IMG, s["img"] + ".png")).convert("RGB").crop(s["box"])
        big = src.resize((int(W * OVER), int(H * OVER)), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2.2, 60, 2))
        s["srcs"] = [grade(big, s["grade"][0]), grade(big, s["grade"][1])]
    else:
        name = s.get("img", "c_sachet")
        src = Image.open(os.path.join(IMG, name + ".png")).convert("RGB")
        ar = src.width / src.height
        if s["kind"] == "cta":
            ch = 640; cw = int(ch * ar); s["zoom"] = (1.0, 1.06)
            s["bg"] = pearl_bg(Image.open(os.path.join(IMG, "c_water.png")).convert("RGB"), 0.5); s["cy"] = 880
        elif "card_h" in s:
            ch = s["card_h"]; cw = min(920, int(ch * ar)); ch = int(cw / ar)
        else:
            cw = s["card_w"]; ch = int(cw / ar)
        if s["kind"] == "card": s["bg"] = pearl_bg(src); s["cy"] = 950
        s["card"] = (cw, ch)
        s["src"] = src.resize((int(cw * OVER), int(ch * OVER)), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 70, 2))
        s["mask"] = rounded(cw, ch, 34)
        sh = Image.new("L", (cw + 160, ch + 160), 0); sh.paste(s["mask"], (80, 80))
        s["shadow"] = sh.filter(ImageFilter.GaussianBlur(30)).point(lambda v: int(v * 0.4))

def window(img_size, out_size, z, focus, p):
    sw, sh = img_size; ow, oh = out_size
    vw = sw / z; vh = vw * oh / ow
    if vh > sh: vh = sh; vw = vh * ow / oh
    cx = lerp(sw / 2, focus[0] * sw, p); cy = lerp(sh / 2, focus[1] * sh, p)
    l = min(max(0, cx - vw / 2), sw - vw); t = min(max(0, cy - vh / 2), sh - vh)
    return (l, t, l + vw, t + vh)

# ------------------------------------------------------------------ dessin
def draw_photo(s, lt):
    p = ease_io((lt + XF) / (s["dur"] + XF))
    z = lerp(*s["zoom"], p)
    box = window(s["srcs"][0].size, (W, H), z, s["focus"], p)
    a = s["srcs"][0].resize((W, H), Image.BICUBIC, box=box)
    if s["grade"][0] != s["grade"][1]:
        b = s["srcs"][1].resize((W, H), Image.BICUBIC, box=box)
        a = Image.blend(a, b, ease_io(lt / s["dur"]))
    fr = a.convert("RGBA")
    if s.get("leak"):
        k = 0.22 + 0.10 * math.sin(lt * 1.4)
        fr.alpha_composite(with_alpha(LEAK, k))
    fr.alpha_composite(VIGNETTE); fr.alpha_composite(SHADE)
    return fr

def draw_card(s, lt):
    fr = s["bg"].copy().convert("RGBA")
    cw, ch = s["card"]; e = ease((lt + 0.3) / 0.8)
    p = (lt + XF) / (s["dur"] + XF)
    z = lerp(*s["zoom"], p)
    src = s["src"]
    box = window(src.size, (cw, ch), z * 1.0, (0.5, 0.5), p)
    im = src.resize((cw, ch), Image.BICUBIC, box=box)
    if s.get("sweep"):
        k = (lt - 0.3) / 1.8
        if 0 <= k <= 1:
            band = Image.new("L", (cw, ch), 0)
            band.paste(SWEEP, (int(lerp(-SWEEP.width, cw, k)), (ch - SWEEP.height) // 2))
            im = Image.composite(Image.new("RGB", (cw, ch), (255, 248, 246)), im, band.point(lambda v: int(v * 0.38)))
    x = (W - cw) // 2; y = s["cy"] - ch // 2 + int((1 - e) * 24)
    fr.paste(Image.new("RGBA", s["shadow"].size, (120, 70, 80, 255)), (x - 80, y - 62), s["shadow"])
    fr.paste(im, (x, y), s["mask"])
    return fr

LOGO1 = text_img("Sorienka", "serif-l", 176, PRUNE)
LOGO2 = text_img("STUDIO", "sans-l", 40, PRUNE, track=24)
CL1 = text_img(CTA["l1"], "serif-i", 66, PRUNE)
CL2 = text_img(CTA["l2"], "sans", 38, (92, 66, 78))
BTN = text_img(CTA["btn"], "sans-m", 40, CREME, track=8)
URLI = text_img(URL, "sans", 32, (92, 66, 78))

def put(fr, img, cy, a, rise=22, x=None):
    if a <= 0: return
    fr.alpha_composite(with_alpha(img, a), (((W - img.width) // 2) if x is None else x, int(cy - img.height / 2 + (1 - a) * rise)))

def draw_cta(s, lt):
    fr = draw_card(s, lt)
    put(fr, LOGO1, 300, ease((lt - 0.2) / 0.7)); put(fr, LOGO2, 418, ease((lt - 0.45) / 0.7))
    put(fr, CL1, 1290, ease((lt - 1.0) / 0.6)); put(fr, CL2, 1370, ease((lt - 2.0) / 0.6))
    a = ease((lt - 2.6) / 0.5)
    if a > 0:
        pul = 1 + 0.025 * math.sin(max(0, lt - 3.2) * 3.0) * (lt > 3.2)
        bw, bh = int(440 * pul), int(104 * pul)
        btn = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        ImageDraw.Draw(btn).rounded_rectangle((0, 0, bw - 1, bh - 1), bh // 2, fill=PRUNE + (255,))
        btn.alpha_composite(BTN, ((bw - BTN.width) // 2, (bh - BTN.height) // 2 + 2))
        put(fr, btn, 1480, a)
    put(fr, URLI, 1575, ease((lt - 3.0) / 0.6))
    return fr

def draw_scene(i, lt):
    s = SCENES[i]
    return {"photo": draw_photo, "card": draw_card, "cta": draw_cta}[s["kind"]](s, lt)

def scene_at(t): return max(k for k in range(len(SCENES)) if starts[k] <= t)

# textes pré-rendus (version claire pour les plans de vie, foncée pour les plans produit)
def both(txt, fn, sz, track=0):
    return {"light": text_img(txt, fn, sz, CREME, track, shadow=True), "dark": text_img(txt, fn, sz, PRUNE, track)}
SUBI = [(both(tx, "sans", 44), a, b) for tx, a, b in SUBS]
TITI = [[both(tx, fn, sz), y, a, b, None] for tx, fn, sz, y, a, b in TITLES]
for y in {r[1] for r in TITI}:            # titres d'une même ligne : posés côte à côte
    row = [r for r in TITI if r[1] == y]
    if len(row) > 1:
        gap = -46; tw = sum(r[0]["light"].width for r in row) + gap * (len(row) - 1); x = (W - tw) // 2
        for r in row: r[4] = x; x += r[0]["light"].width + gap
STAMPI = both(STAMP[0], "sans-l", 36, track=6)

def fade(t, a, b, fi=0.35, fo=0.3): return min(ease((t - a) / fi), ease((b - t) / fo))

# ------------------------------------------------------------------ rendu
wav = OUT.replace(".mp4", ".wav")
cuts = starts[1:]
cta_t = starts[-1]
mus = {"dur": TOTAL, "pad": starts[1], "arp": starts[2] if VERSION == "39" else starts[1] + 0.5,
       "full": starts[5] if VERSION == "39" else starts[2], "end": cta_t, "cuts": cuts}
subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "music_story.py"),
                wav, json.dumps(mus)], check=True)
ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "slow", "-crf", "20",
                       "-pix_fmt", "yuv420p", "-profile:v", "high", "-c:a", "aac", "-b:a", "192k",
                       "-shortest", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
for n in range(NFR):
    t = n / FPS; i = scene_at(t)
    fr = draw_scene(i, t - starts[i])
    tone = "dark" if SCENES[i]["kind"] != "photo" else "light"
    if i + 1 < len(SCENES) and t > starts[i + 1] - XF:
        k = ease_io((t - (starts[i + 1] - XF)) / XF)
        fr = Image.blend(fr, draw_scene(i + 1, t - starts[i + 1]), k)
        if k > 0.5: tone = "dark" if SCENES[i + 1]["kind"] != "photo" else "light"
    for im, a, b in SUBI:
        al = fade(t, a, b)
        if al > 0: put(fr, im[tone], 1420, al, rise=10)
    for im, y, a, b, x in TITI:
        al = fade(t, a, b, 0.6, 0.5)
        if al > 0: put(fr, im[tone], y, al, rise=26, x=x)
    al = fade(t, STAMP[1], STAMP[2], 0.6, 0.6)
    if al > 0: put(fr, STAMPI["light"], 250, al * 0.9, rise=0, x=60)
    rgb = fr.convert("RGB")
    g = GRAIN[n % 4]
    rgb = Image.blend(rgb, Image.merge("RGB", (g, g, g)), 0.035)
    if t < 0.4: rgb = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), rgb, ease(t / 0.4))
    ff.stdin.write(rgb.tobytes())
    if n % 150 == 0: print(f"{n}/{NFR}", flush=True)
ff.stdin.close(); ff.wait(); os.remove(wav)
print("ok", OUT, TOTAL)
