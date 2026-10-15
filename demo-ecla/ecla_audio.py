"""Bande-son ÉCLA (base : banque de bruitages ORVA v2) : musique 120 BPM produite (filtres, sidechain, coupures) + banque de bruitages d'interface.

Usage : python3 orva_audio.py sortie.wav '<json>'
Le json donne la durée, la structure (sections) et une liste d'événements {type: [temps, ...]}.
"""
import json, sys, wave
import numpy as np
from scipy import signal

SR = 48000
P = json.loads(sys.argv[2]); DUR = P["dur"]; N = int(SR * DUR)
rng = np.random.default_rng(31)
BUS = {k: np.zeros((N, 2)) for k in ("drums", "kick", "music", "fx", "ui")}

def hz(m): return 440.0 * 2 ** ((m - 69) / 12)
def T(n): return np.arange(n) / SR
def add(bus, sig, start, pan=0.0, gain=1.0):
    if sig.ndim == 1: sig = np.stack([sig * np.sqrt((1 - pan) / 2), sig * np.sqrt((1 + pan) / 2)], 1)
    i = int(round(start * SR))
    if i < 0: sig = sig[-i:]; i = 0
    j = min(N, i + len(sig))
    if j > i: BUS[bus][i:j] += sig[: j - i] * gain
def bp(x, lo, hi, order=2):
    b, a = signal.butter(order, [lo / (SR / 2), min(hi, SR / 2 - 100) / (SR / 2)], "band"); return signal.lfilter(b, a, x)
def hpf(x, f, order=2): b, a = signal.butter(order, f / (SR / 2), "high"); return signal.lfilter(b, a, x)
def lpf(x, f, order=2): b, a = signal.butter(order, min(f, SR / 2 - 100) / (SR / 2), "low"); return signal.lfilter(b, a, x)
def noise(n): return rng.standard_normal(n)
def sweep_filter(x, f0, f1, q=2.0, kind="band"):
    """Filtre dont la fréquence glisse de f0 à f1 (traitement par blocs)."""
    out = np.zeros_like(x); blk = 512; zi = None; nb = int(np.ceil(len(x) / blk))
    for k in range(nb):
        f = f0 * (f1 / f0) ** (k / max(1, nb - 1))
        if kind == "band":
            lo, hi = f / (1 + 1 / q), f * (1 + 1 / q); b, a = signal.butter(2, [lo / (SR / 2), min(hi, SR / 2 - 200) / (SR / 2)], "band")
        else:
            b, a = signal.butter(2, min(f, SR / 2 - 200) / (SR / 2), "low")
        if zi is None or len(zi) != max(len(a), len(b)) - 1: zi = signal.lfilter_zi(b, a) * 0
        out[k * blk:(k + 1) * blk], zi = signal.lfilter(b, a, x[k * blk:(k + 1) * blk], zi=zi)
    return out

# ================================================================ bruitages
def sfx_tap(t, g=0.5):              # toucher d'écran : clic sec + petit corps
    n = int(0.05 * SR); tt = T(n)
    s = hpf(noise(n), 2500) * np.exp(-tt * 900) * 0.6 + np.sin(2 * np.pi * 1700 * tt) * np.exp(-tt * 160) * 0.4
    add("ui", s, t, rng.uniform(-.15, .15), g)
def sfx_key(t, g=0.35):             # touche de clavier virtuel
    n = int(0.04 * SR); tt = T(n); f = rng.uniform(1100, 1500)
    s = bp(noise(n), 1500, 7000) * np.exp(-tt * 700) * 0.7 + np.sin(2 * np.pi * f * tt) * np.exp(-tt * 220) * 0.3
    add("ui", s, t + rng.uniform(-0.006, 0.006), rng.uniform(-.25, .25), g * rng.uniform(.7, 1))
def sfx_pop(t, g=0.4, f0=520, f1=1250):   # apparition d'élément (bulle)
    n = int(0.09 * SR); tt = T(n); f = f0 + (f1 - f0) * (1 - np.exp(-tt * 70))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 45) * (1 - np.exp(-tt * 3000))
    add("ui", s, t, rng.uniform(-.3, .3), g)
def sfx_whoosh(t, g=0.5, length=0.5, direction=1, hi=True):   # passage de caméra / balayage
    n = int(length * SR); tt = T(n); x = noise(n)
    s = sweep_filter(x, 300 if hi else 150, 3500 if hi else 900, 1.6) * np.sin(np.pi * tt / length) ** 2
    pan = np.linspace(-0.8 * direction, 0.8 * direction, n)
    st = np.stack([s * np.sqrt((1 - pan) / 2), s * np.sqrt((1 + pan) / 2)], 1)
    add("fx", st, t - length * 0.55, 0, g * 3)
def sfx_swish(t, g=0.4, length=0.9):      # carte qui tourne : souffle avec battements
    n = int(length * SR); tt = T(n); rate = 7 + 10 * (1 - tt / length)
    trem = 0.5 + 0.5 * np.sin(2 * np.pi * np.cumsum(rate) / SR)
    s = bp(noise(n), 500, 4000) * trem * np.sin(np.pi * tt / length) * np.exp(-tt * 1.2)
    add("fx", s, t, 0, g * 2.2)
def sfx_impact(t, g=0.8):            # impact grave cinéma
    n = int(2.2 * SR); tt = T(n); f = 34 + 90 * np.exp(-tt * 16)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 2.2)
    crack = lpf(noise(n), 3000) * np.exp(-tt * 18) * 0.6
    tail = lpf(noise(n), 900) * np.exp(-tt * 2.8) * 0.25
    add("fx", sub + crack + tail, t, 0, g)
def sfx_riser(t0, t1, g=0.35):       # montée : bruit filtré + nappe qui monte
    n = int((t1 - t0) * SR); tt = T(n); L = t1 - t0
    s = sweep_filter(noise(n), 400, 9000, 1.4) * (tt / L) ** 2.3
    f = 200 * 4 ** (tt / L); tone = signal.sawtooth(2 * np.pi * np.cumsum(f) / SR) * (tt / L) ** 3 * 0.12
    add("fx", s + lpf(tone, 4000), t0, 0, g * 2)
def sfx_revcym(t, length=0.8, g=0.3):
    n = int(length * SR); tt = T(n); s = hpf(noise(n), 5000) * (tt / length) ** 3
    add("fx", s, t - length, 0, g * 1.6)
def sfx_tickroll(t0, t1, g=0.18):    # roulement de compteur qui ralentit
    t = t0; k = 0
    while t < t1:
        p = (t - t0) / (t1 - t0); n = int(0.012 * SR); tt = T(n)
        add("ui", hpf(noise(n), 3000) * np.exp(-tt * 600) + 0.3 * np.sin(2 * np.pi * 2600 * tt) * np.exp(-tt * 400), t, (-1) ** k * 0.2, g)
        t += 0.022 + 0.11 * p ** 2.2; k += 1
def bell(m, n_s, decay=3.0):
    tt = T(int(n_s * SR)); s = np.zeros(len(tt))
    for r, a, d in ((1, 1, 1), (2.0, .25, 1.6), (3.01, .12, 2.4), (4.2, .05, 3.5)):
        s += a * np.sin(2 * np.pi * hz(m) * r * tt) * np.exp(-tt * decay * d)
    return s * (1 - np.exp(-tt * 2000))
def sfx_notif(t, g=0.32):            # notification : deux notes douces
    add("ui", bell(88, 0.8, 5), t, 0.15, g); add("ui", bell(95, 0.9, 4.5), t + 0.085, 0.15, g * 0.8)
def sfx_sent(t, g=0.35):             # message envoyé : souffle montant + bulle
    n = int(0.22 * SR); tt = T(n); s = sweep_filter(noise(n), 800, 5000, 2) * np.sin(np.pi * tt / 0.22)
    add("ui", s, t - 0.12, 0.4, g * 1.4); sfx_pop(t, g * 0.8, 700, 1500)
def sfx_received(t, g=0.3):
    add("ui", bell(84, 0.5, 7), t, -0.3, g); add("ui", bell(88, 0.6, 6), t + 0.07, -0.3, g * 0.7)
def sfx_success(t, g=0.32):          # validation : arpège majeur cristallin
    for i, m in enumerate((84, 88, 91, 96)): add("ui", bell(m, 1.4, 2.6), t + i * 0.055, -0.2 + 0.13 * i, g * (1 - i * 0.12))
def sfx_beep(t, g=0.3):              # terminal de paiement : double bip
    for k in range(2):
        n = int(0.075 * SR); tt = T(n)
        s = lpf(signal.square(2 * np.pi * 1850 * tt), 6000) * np.minimum(1, tt / 0.003) * np.clip((0.075 - tt) / 0.004, 0, 1)
        add("ui", s * 0.5, t + k * 0.12, 0, g)
def sfx_glitch(t, g=0.35, length=0.18):
    n = int(length * SR); x = noise(n); hold = 30 + rng.integers(0, 60)
    x = np.repeat(x[::hold], hold)[:n]; x = np.round(x * 4) / 4
    gate = (np.sin(2 * np.pi * 38 * T(n)) > -0.2).astype(float)
    add("fx", bp(x, 300, 6000) * gate * 0.6, t, 0, g)
def sfx_rumble(t, length, g=0.4):    # bâtiments qui sortent du sol
    n = int(length * SR); tt = T(n)
    s = lpf(noise(n), 160) * np.minimum(1, tt / 0.2) * np.clip((length - tt) / 0.3, 0, 1) * 3
    add("fx", s, t, 0, g)
def sfx_thud(t, g=0.45):
    n = int(0.5 * SR); tt = T(n); f = 60 + 60 * np.exp(-tt * 30)
    add("fx", np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 9) + lpf(noise(n), 1200) * np.exp(-tt * 30) * 0.3, t, rng.uniform(-.3, .3), g)
def sfx_shimmer(t, length=1.2, g=0.18):  # scintillement du logo
    for k in range(40):
        tk = t + rng.uniform(0, length * 0.7); m = rng.integers(96, 110)
        add("fx", bell(m, 0.4, 9) * 0.5, tk, rng.uniform(-.7, .7), g * rng.uniform(.3, 1) * np.exp(-(tk - t) * 1.5))
def sfx_slam(t, g=0.6):              # mot qui claque
    n = int(0.35 * SR); tt = T(n); f = 55 + 110 * np.exp(-tt * 40)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 10) + hpf(noise(n), 2000) * np.exp(-tt * 70) * 0.5
    add("fx", s, t, 0, g); sfx_revcym(t, 0.35, 0.12)
def sfx_heart(t, g=0.5):
    for d, a in ((0, 1), (0.28, 0.6)):
        n = int(0.3 * SR); tt = T(n); f = 48 + 24 * np.exp(-tt * 25)
        add("kick", np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 13), t + d, 0, g * a)
def sfx_flash(t, g=0.5):             # flash lumineux : « whoomp » + éclat aigu
    sfx_whoosh(t + 0.15, g * 0.8, 0.6, 1, hi=False)
    n = int(1.0 * SR); tt = T(n); add("fx", hpf(noise(n), 6000) * np.exp(-tt * 4) * 0.4, t, 0, g)


# ================================================================ bruitages ÉCLA
def sfx_open(t, g=0.6):              # ouverture de canette : clic métallique + « pssht »
    n = int(0.03 * SR); tt = T(n)
    add("fx", hpf(noise(n), 3000) * np.exp(-tt * 300) + np.sin(2 * np.pi * 3200 * tt) * np.exp(-tt * 200) * 0.3, t, 0, g)
    n = int(0.7 * SR); tt = T(n); h = bp(noise(n), 2500, 12000) * np.exp(-tt * 4.5) * np.minimum(1, tt / 0.01)
    add("fx", h, t + 0.02, 0, g * 1.1)
def sfx_fizz(t0, t1, g=0.12):        # pétillement : micro-crépitements
    n = int((t1 - t0) * SR); x = np.zeros(n); r = np.random.default_rng(int(t0 * 100))
    idx = r.integers(0, n, int((t1 - t0) * 900)); x[idx] = r.uniform(-1, 1, len(idx))
    x = hpf(x, 4000) * np.minimum(1, T(n) / 0.1) * np.clip((t1 - t0 - T(n)) / 0.3, 0, 1)
    add("fx", np.stack([x, np.roll(x, 37)], 1), t0, 0, g * 4)
def sfx_bubble(t, g=0.18, f=None):   # bulle qui éclate : petit « bloup » montant
    n = int(0.07 * SR); tt = T(n); f0 = f or rng.uniform(500, 1100)
    fr = f0 * (1 + 1.6 * tt / 0.07); s = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-tt * 50) * (1 - np.exp(-tt * 3000))
    add("ui", s, t, rng.uniform(-.6, .6), g)
def sfx_bubbles(t0, t1, g=0.15):
    for k in range(int((t1 - t0) * 50)): sfx_bubble(t0 + rng.uniform(0, t1 - t0), g * rng.uniform(.5, 1))
def sfx_gloop(t, g=0.5):             # vague de liquide
    n = int(0.9 * SR); tt = T(n); s = sweep_filter(noise(n), 200, 1400, 1.2, "low") * np.sin(np.pi * tt / 0.9) ** 1.5
    add("fx", s * 1.5, t - 0.1, 0, g); sfx_bubbles(t + 0.2, t + 0.7, 0.12)
    tt2 = T(int(0.25 * SR)); f = 180 + 300 * (tt2 / 0.25); add("fx", np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt2 * 10), t + 0.35, 0, g * 0.5)
def sfx_iris(t, g=0.45):
    sfx_whoosh(t + 0.3, g, 0.5, 1)
    tt = T(int(0.3 * SR)); f = 900 * np.exp(-tt * 6) + 200; add("ui", np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 9), t + 0.25, 0, g * 0.6)
def sfx_land(t, g=0.5):              # canette posée : choc + tintement d'alu
    sfx_thud(t, g * 0.9)
    tt = T(int(0.5 * SR)); s = sum(a * np.sin(2 * np.pi * f * tt) * np.exp(-tt * d) for f, a, d in ((2900, .4, 14), (4700, .25, 20), (6100, .15, 26)))
    add("fx", s, t, rng.uniform(-.2, .2), g * 0.5)
def sfx_boing(t, g=0.3):
    tt = T(int(0.35 * SR)); f = 220 + 160 * np.sin(tt * 40) * np.exp(-tt * 8) + 200 * tt
    add("ui", np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 7), t, rng.uniform(-.3, .3), g)
def sfx_clink(t, g=0.22):            # glaçon contre glaçon
    tt = T(int(0.4 * SR)); f0 = rng.uniform(2600, 3600)
    s = sum(a * np.sin(2 * np.pi * f0 * r * tt) * np.exp(-tt * d) for r, a, d in ((1, 1, 18), (2.3, .5, 26), (3.9, .3, 34)))
    add("ui", s, t, rng.uniform(-.5, .5), g)
def sfx_tick(t, g=0.18):             # révélation de texte : petit « tic » feutré
    n = int(0.06 * SR); tt = T(n); add("ui", bp(noise(n), 1800, 6000) * np.exp(-tt * 120), t, rng.uniform(-.2, .2), g)
    sfx_whoosh(t + 0.05, 0.12, 0.25, 1)
def sfx_letter(t, g=0.28):
    sfx_pop(t + 0.18, g, 400 + rng.uniform(0, 400), 1000 + rng.uniform(0, 600))
def sfx_zoom(t, g=0.5):
    sfx_riser(t - 0.4, t + 0.45, 0.25); sfx_whoosh(t + 0.55, g, 0.7, 1, hi=False)

# ================================================================ musique : funk-pop en do majeur, 116 BPM
BPM = 116; BEAT = 60 / BPM; BAR = BEAT * 4
prog = [(48, [64, 67, 72, 74]), (45, [64, 69, 72, 76]), (41, [65, 69, 72, 76]), (43, [62, 67, 71, 74])]   # Cadd9 Am7 Fmaj7 G6
def kick(t, g=1.0):
    n = int(0.35 * SR); tt = T(n); f = 52 + 110 * np.exp(-tt * 38)
    add("kick", np.tanh(1.6 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 9)) + hpf(noise(n), 3500) * np.exp(-tt * 600) * 0.35, t, 0, g * 0.75)
def clap(t, g=0.42):
    n = int(0.25 * SR); tt = T(n); x = bp(noise(n), 900, 7000)
    for d in (0, 0.008, 0.017, 0.026): add("drums", x * np.exp(-(tt) * (60 if d < 0.02 else 16)), t + d, 0.0, g * (0.6 if d < 0.02 else 1))
def snap(t, g=0.3):
    n = int(0.08 * SR); tt = T(n); add("drums", bp(noise(n), 2000, 9000) * np.exp(-tt * 70) + np.sin(2 * np.pi * 1400 * tt) * np.exp(-tt * 90) * .3, t, -0.2, g)
def shaker(t, g=0.06):
    n = int(0.07 * SR); tt = T(n); add("drums", hpf(noise(n), 6000, 3) * np.sin(np.pi * tt / 0.07) ** 2, t, 0.45, g * rng.uniform(.6, 1))
def marimba(m, t, g=0.16, pan=0.0):
    n = int(0.8 * SR); tt = T(n); f = hz(m)
    s = np.sin(2 * np.pi * f * tt) * np.exp(-tt * 9) + 0.35 * np.sin(2 * np.pi * f * 4 * tt) * np.exp(-tt * 40) + 0.15 * np.sin(2 * np.pi * f * 9.2 * tt) * np.exp(-tt * 70)
    add("music", s * (1 - np.exp(-tt * 3000)), t, pan, g)
def ebass(m, t, length, g=0.32):
    n = int(length * SR); tt = T(n); f = hz(m)
    s = np.sin(2 * np.pi * f * tt) + 0.5 * np.sin(4 * np.pi * f * tt) * np.exp(-tt * 12) + 0.25 * signal.square(2 * np.pi * f * tt) * np.exp(-tt * 20)
    s = lpf(np.tanh(1.5 * s), 1500) * np.minimum(1, tt / 0.004) * np.clip((length - tt) / 0.02, 0, 1)
    add("music", s, t, 0, g)
def keys(notes, t, length, g=0.07):  # piano électrique doux
    n = int(length * SR); tt = T(n); s = np.zeros(n)
    for m in notes:
        f = hz(m); s += (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt) * np.exp(-tt * 3)) * (1 + 0.15 * np.sin(2 * np.pi * 5 * tt))
    s *= np.exp(-tt * 1.2) * np.minimum(1, tt / 0.01) * np.clip((length - tt) / 0.1, 0, 1)
    add("music", np.stack([s, np.roll(s, 220)], 1) / len(notes), t, 0, g)

S = P["sections"]; OUTRO = S["outro"]
def in_rng(t, r): return r[0] <= t < r[1]
t = S["intro_end"]; bar = 0
while t < OUTRO - 1e-6:
    root, ch = prog[bar % 4]
    for i in range(4):
        bt = t + i * BEAT
        if bt >= OUTRO or in_rng(bt, S["stop1"]): continue
        chill = in_rng(bt, S["chill"]); ris = in_rng(bt, S["riser"])
        if not chill: kick(bt)
        elif i == 0: kick(bt, 0.8)
        if i % 2 == 1: (snap if chill else clap)(bt)
        for h in range(4):
            if not (ris and h % 2): shaker(bt + h * BEAT / 4 + (0.018 if h % 2 else 0), 0.08 if h == 2 else 0.05)
        # basse funk : fondamentale, octave, note de passage
        if not ris:
            pat = [(0, 0, .35), (0.75, 12, .2), (1.5, 7, .2)] if i % 2 == 0 else [(0, 0, .2), (0.5, 10 if i == 3 else 12, .2)]
            for off, iv, ln in pat: ebass(root - 12 + iv, bt + off * BEAT / 1.5, ln * BEAT * 1.4, 0.24 if chill else 0.32)
    # marimba syncopée
    rhythm = [0, 0.75, 1.5, 2.0, 2.75, 3.5]
    for j, r in enumerate(rhythm):
        at = t + r * BEAT
        if at < OUTRO and not in_rng(at, S["stop1"]): marimba(ch[(j * 2 + bar) % 4] + (12 if j == 4 else 0), at, 0.15, -.4 + .16 * j)
    keys([n - 12 for n in ch], t, BAR, 0.08 if not in_rng(t, S["chill"]) else 0.11)
    t += BAR; bar += 1
# intro : marimba seule sur les lettres
for i, m in enumerate([72, 76, 79, 84, 79, 76, 81, 84]): marimba(m, 0.3 + i * 0.075, 0.14, -.5 + .14 * i)
keys([60, 64, 67, 71], 0.0, S["intro_end"], 0.05)
# outro : accord final et petite cadence
keys([48, 60, 64, 67, 72, 76], OUTRO, DUR - OUTRO, 0.12)
for i, m in enumerate([72, 76, 79, 84, 88]): marimba(m, OUTRO + 0.1 + i * BEAT / 2, 0.17, -.4 + .2 * i)
kick(OUTRO, 1.0); clap(OUTRO + 0.01, 0.5)

# ================================================================ événements
E = P["events"]
for k, fn in (("letter", sfx_letter), ("open", sfx_open), ("gloop", sfx_gloop), ("iris", sfx_iris), ("land", sfx_land),
              ("minilands", sfx_land), ("lands3", sfx_land), ("hop", sfx_boing), ("pop", sfx_pop), ("tick", sfx_tick),
              ("zoom", sfx_zoom), ("clink", sfx_clink), ("chime", sfx_success)):
    for x in E.get(k, []): fn(x)
for x in E.get("fall", []): sfx_whoosh(x + 0.35, 0.4, 0.4, 1, hi=False)
for a, b in E.get("fizz", []): sfx_fizz(a, b)
for a, b in E.get("bubbles", []): sfx_bubbles(a, b)
for x in E.get("swish3", []):
    for i in range(3): sfx_whoosh(x + 0.15 + i * 0.07, 0.35, 0.35, 1)
for x in E.get("logo", []): sfx_pop(x + 0.15, 0.5, 300, 900); sfx_shimmer(x + 0.2, 1.0, 0.12)

# ================================================================ mixage
def reverb(x, mix=0.25):
    ir_n = int(1.6 * SR); tt = T(ir_n)
    ir = noise(ir_n) * np.exp(-tt * 3.2); ir = lpf(ir, 5000); ir /= np.abs(ir).sum() / 30
    out = np.stack([signal.fftconvolve(x[:, 0], ir)[:N], signal.fftconvolve(x[:, 1], np.roll(ir, 211))[:N]], 1)
    return x + out * mix
# sidechain : musique et charleys respirent sous le kick
env = np.abs(BUS["kick"][:, 0]); env = signal.lfilter([1], [1, -0.9995], env) / 2000
duck = 1 - np.clip(env * 6, 0, 0.6)
music = reverb(BUS["music"], 0.3) * duck[:, None]
drums = reverb(BUS["drums"], 0.12) * (0.7 + 0.3 * duck[:, None])
fx = reverb(BUS["fx"], 0.22); ui = reverb(BUS["ui"], 0.12)
mix = music * 0.9 + drums * 0.8 + BUS["kick"] * 0.85 + fx * 0.9 + ui * 1.1
mix = hpf(mix.T, 25).T
mix = np.tanh(mix * 1.0) / np.tanh(1.0)
tt = T(N); mix *= np.clip((DUR - tt) / 0.6, 0, 1)[:, None] * np.clip(tt / 0.02, 0, 1)[:, None]
mix /= np.abs(mix).max() / 0.93
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
