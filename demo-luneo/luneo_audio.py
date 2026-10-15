"""Bande-son LUNÉO (base : banque de bruitages ORVA v2) : musique 120 BPM produite (filtres, sidechain, coupures) + banque de bruitages d'interface.

Usage : python3 orva_audio.py sortie.wav '<json>'
Le json donne la durée, la structure (sections) et une liste d'événements {type: [temps, ...]}.
"""
import json, sys, wave
import numpy as np
from scipy import signal

SR = 48000
P = json.loads(sys.argv[2]); DUR = P["dur"]; TM = P; N = int(SR * DUR)
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


# ================================================================ instruments folk
def ks(m, t, g=0.3, length=2.2, bright=0.5, pan=0.0):
    """Corde pincée (Karplus-Strong)."""
    f = hz(m); n = int(length * SR); p = max(2, int(SR / f)); buf = rng.uniform(-1, 1, p)
    buf = lpf(buf, 2000 + 6000 * bright) if p > 20 else buf
    out = np.zeros(n); b = buf.copy(); i = 0; damp = 0.996
    # boucle vectorisée par blocs de période
    reps = n // p + 1; y = np.zeros(reps * p); prev = b
    for r_ in range(reps):
        y[r_ * p:(r_ + 1) * p] = prev; nxt = damp * 0.5 * (prev + np.roll(prev, -1)); prev = nxt
    out = y[:n] * np.exp(-T(n) * 0.8)
    add("music", out, t, pan, g)
def strum(chord, t, g=0.22, down=True, gap=0.012):
    notes = chord if down else chord[::-1]
    for k, m in enumerate(notes): ks(m, t + k * gap, g * (0.8 + 0.2 * (k == 0)), 1.8, 0.45, -0.3 + 0.12 * k)
def glock(m, t, g=0.14, pan=0.2):
    tt = T(int(1.6 * SR)); f = hz(m)
    s = np.sin(2 * np.pi * f * tt) * np.exp(-tt * 3) + 0.4 * np.sin(2 * np.pi * f * 2.76 * tt) * np.exp(-tt * 7) + 0.2 * np.sin(2 * np.pi * f * 5.4 * tt) * np.exp(-tt * 12)
    add("music", s * (1 - np.exp(-tt * 2500)), t, pan, g)
def ubass(m, t, length, g=0.28):
    n = int(length * SR); tt = T(n); f = hz(m)
    s = lpf(np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(4 * np.pi * f * tt), 700) * np.exp(-tt * 2.5) * np.minimum(1, tt / 0.01)
    add("music", s, t, 0, g)
def brush(t, g=0.07):
    n = int(0.18 * SR); tt = T(n); add("drums", bp(noise(n), 2000, 9000) * np.sin(np.pi * tt / 0.18) ** 2, t, 0.3, g)
def softkick(t, g=0.5):
    n = int(0.3 * SR); tt = T(n); f = 50 + 60 * np.exp(-tt * 30); add("kick", np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 10), t, 0, g)
def handclap(t, g=0.25):
    n = int(0.2 * SR); tt = T(n); x = bp(noise(n), 800, 5000)
    for d in (0, 0.012): add("drums", x * np.exp(-tt * (50 if d == 0 else 18)), t + d, -0.1, g)

# ================================================================ bruitages papier & voyage
def rustle(t, length=0.4, g=0.2):     # froissement de papier
    n = int(length * SR); x = np.zeros(n); r = np.random.default_rng(int(t * 1000))
    idx = r.integers(0, n, int(length * 1400)); x[idx] = r.uniform(-1, 1, len(idx))
    x = bp(x, 1500, 9000) * 3 + bp(noise(n), 2500, 7000) * 0.15
    add("fx", x * np.sin(np.pi * T(n) / length) ** 0.7, t, r.uniform(-.4, .4), g)
def tear(t, length=0.7, g=0.45):      # déchirure : crépitement qui accélère
    n = int(length * SR); tt = T(n); r = np.random.default_rng(int(t * 77))
    dens = 400 + 5000 * (tt / length); x = (r.random(n) < dens / SR).astype(float) * r.uniform(-1, 1, n)
    x = bp(x, 800, 7000) * 4 + bp(noise(n), 1200, 5000) * 0.3 * (tt / length)
    add("fx", x * np.minimum(1, tt / 0.05), t, 0, g)
def page(t, g=0.35):
    sfx_whoosh(t + 0.35, g * 0.6, 0.5, 1); rustle(t + 0.05, 0.55, g * 0.7)
def stamp_s(t, g=0.6):
    n = int(0.3 * SR); tt = T(n); f = 90 + 80 * np.exp(-tt * 40)
    add("fx", np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 14) + lpf(noise(n), 2500) * np.exp(-tt * 40) * 0.6, t, 0, g)
def chug(t0, t1, g=0.12, rate=5.0):    # train sur les rails : tchou-tchou feutré + clac des rails
    k = 0; t = t0
    while t < t1:
        n = int(0.12 * SR); tt = T(n); add("fx", bp(noise(n), 300, 2500) * np.exp(-tt * 30), t, 0.1 * (-1) ** k, g * (1 if k % 2 == 0 else 0.6))
        if k % 4 == 0:
            n2 = int(0.06 * SR); add("fx", bp(noise(n2), 2000, 6000) * np.exp(-T(n2) * 80), t + 0.03, 0, g * 0.6)
        t += 1 / rate; k += 1
def horn(t, g=0.18):
    n = int(0.9 * SR); tt = T(n); env = np.minimum(1, tt / 0.05) * np.clip((0.9 - tt) / 0.2, 0, 1)
    s = sum(lpf(signal.square(2 * np.pi * f * tt), 2500) for f in (hz(66), hz(70)))
    add("fx", s * env * 0.3, t, -0.3, g)
def gull_s(t, g=0.1):
    n = int(0.35 * SR); tt = T(n); f = 1600 + 900 * np.sin(np.pi * tt / 0.35) - 600 * tt
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / 0.35) ** 2
    add("fx", bp(s + 0.2 * noise(n), 1000, 4000), t, rng.uniform(-.7, .7), g)
def waves(t0, t1, g=0.25):
    n = int((t1 - t0) * SR); tt = T(n); x = lpf(noise(n), 1200) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.35 * tt - 1.5)) ** 2 * 2
    x *= np.minimum(1, tt / 0.6) * np.clip((t1 - t0 - tt) / 0.6, 0, 1)
    add("fx", np.stack([x, np.roll(x, 2000)], 1), t0, 0, g)
def spoon(t, g=0.15):
    for k in range(3): add("fx", bell(100 + k, 0.4, 9) * 0.6, t + k * 0.14, 0.4, g)
def boing_paper(t, g=0.22):
    tt = T(int(0.25 * SR)); f = 300 + 500 * (1 - np.exp(-tt * 20)); add("ui", np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 14), t, rng.uniform(-.3, .3), g)
    rustle(t, 0.12, 0.12)

# ================================================================ partition : folk en sol majeur, 100 BPM
BPM = 100; BEAT = 60 / BPM; BAR = 4 * BEAT
G_, D_, Em, C_ = [55, 59, 62, 67, 71], [50, 57, 62, 66, 69], [52, 59, 64, 67, 71], [48, 55, 60, 64, 67]
PROG = [(G_, 43), (D_, 38), (Em, 40), (C_, 36)]
mel = [74, 76, 79, 76, 74, 71, 74, 72]
t = 0.0; bar = 0
while t < DUR - 2.2:
    ch, root = PROG[bar % 4]
    for i in range(8):                            # rythme de grattage : D . D U . U D U
        pat = "D.DU.UDU"[i]
        if pat != "." and t >= 1.2: strum(ch, t + i * BEAT / 2, 0.16 if pat == "D" else 0.1, pat == "D")
    if t >= 3.0:
        ubass(root - 12, t, BEAT * 1.6); ubass(root - 5, t + BEAT * 2, BEAT * 1.6)
        for i in range(4):
            if bar % 8 not in (7,): brush(t + i * BEAT + BEAT / 2)
            if i in (1, 3): handclap(t + i * BEAT, 0.2 if t > 11 else 0.12)
            if i in (0, 2): softkick(t + i * BEAT, 0.45)
    if t >= 7.6:
        for i in range(4): glock(mel[(bar * 4 + i) % 8] + 12, t + i * BEAT + (BEAT / 2 if i % 2 else 0), 0.09, 0.35)
    t += BAR; bar += 1
for i, m in enumerate([67, 71, 74, 79]): ks(m, i * 0.3, 0.22, 2.4, 0.6)
# fin : accord tenu + glockenspiel
strum(G_, DUR - 2.4, 0.24); ks(43, DUR - 2.4, 0.3, 2.4, 0.3)
for i, m in enumerate([86, 91, 95]): glock(m, DUR - 2.2 + i * 0.25, 0.12)

# ================================================================ événements
rustle(TM["ticket"], 0.5, 0.3); stamp_s(TM["stamp"] + 0.05)
for x in TM["letters"]: rustle(x + 0.05, 0.08, 0.12); sfx_pop(x + 0.08, 0.12, 500, 1000)
for x in TM["tears"]: tear(x, 0.8, 0.5)
chug(TM["train"][0], TM["train"][1], 0.10, 4.0); chug(TM["train"][2], TM["train"][2] + 3.2, 0.08, 5.0); chug(TM["train"][3], DUR - 0.5, 0.07, 4.5)
chug(TM["train"][1], TM["train"][1] + 3.2, 0.09, 6.0)
for x in TM["horn"]: horn(x)
page(TM["page"]); sfx_whoosh(TM["fold"] + 0.5, 0.35, 0.6, 1, hi=False); rustle(TM["fold"] + 0.4, 0.4, 0.25)
waves(TM["sea"][0], TM["sea"][1], 0.28)
for k in range(5): gull_s(TM["sea"][0] + 0.6 + k * 0.6)
for k in range(5): rustle(TM["strips"] + 0.08 + k * 0.08, 0.2, 0.18); sfx_whoosh(TM["strips"] + 0.2 + k * 0.08, 0.12, 0.3, (-1) ** k)
for x in TM["pins"]: boing_paper(x)
for k in range(30): sfx_tap(TM["dots"][0] + k * (TM["dots"][1] - TM["dots"][0]) / 30, 0.05)
stamp_s(TM["price"] + 0.05, 0.4); boing_paper(TM["price"])
rustle(TM["circle"], 0.6, 0.3); sfx_whoosh(TM["circle"] + 0.5, 0.25, 0.6, 1)
chug(TM["cabin"][0], TM["cabin"][1], 0.06, 3.0); spoon(TM["cabin"][0] + 0.8)
for x in TM["tags"]: rustle(x, 0.15, 0.14); sfx_pop(x + 0.04, 0.1, 450, 900)
for x in TM["logo"]: boing_paper(x + 0.1, 0.18)
sfx_success(TM["logo"][-1] + 0.4, 0.2)

# ================================================================ mixage
def reverb(x, mix=0.25, length=1.8):
    ir_n = int(length * SR); tt = T(ir_n); ir = noise(ir_n) * np.exp(-tt * 3.5); ir = lpf(ir, 6000); ir /= np.abs(ir).sum() / 30
    return x + np.stack([signal.fftconvolve(x[:, 0], ir)[:N], signal.fftconvolve(x[:, 1], np.roll(ir, 251))[:N]], 1) * mix
env = np.abs(BUS["kick"][:, 0]); env = signal.lfilter([1], [1, -0.9993], env) / 2000; duck = 1 - np.clip(env * 4, 0, 0.35)
mix = reverb(BUS["music"], 0.28) * duck[:, None] + reverb(BUS["drums"], 0.18) * 0.9 + BUS["kick"] * 0.7 + reverb(BUS["fx"], 0.15) + reverb(BUS["ui"], 0.12)
mix = hpf(mix.T, 30).T; mix = np.tanh(mix * 0.9) / np.tanh(0.9)
tt = T(N); mix *= np.clip((DUR - tt) / 0.8, 0, 1)[:, None]; mix /= np.abs(mix).max() / 0.92
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
