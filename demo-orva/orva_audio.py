"""Bande-son ORVA v2 : musique 120 BPM produite (filtres, sidechain, coupures) + banque de bruitages d'interface.

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

# ================================================================ musique
BEAT = 0.5; prog = [(45, [69, 72, 76]), (41, [69, 72, 77]), (48, [67, 72, 76]), (43, [67, 71, 74])]  # Am F C G
def kick(t, g=1.0):
    n = int(0.5 * SR); tt = T(n); f = 46 + 120 * np.exp(-tt * 32)
    s = np.tanh(2.2 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 6.5))
    s += hpf(noise(n), 3000) * np.exp(-tt * 500) * 0.5
    add("kick", s, t, 0, g * 0.85)
def snare(t, g=0.5):
    n = int(0.3 * SR); tt = T(n)
    body = np.sin(2 * np.pi * 190 * tt) * np.exp(-tt * 28) * 0.5
    nz = bp(noise(n), 1500, 9000) * np.exp(-tt * 20)
    for d in (0.0, 0.009, 0.019): add("drums", (body + nz) * (1 if d == 0 else 0.4), t + d, 0.03, g)
def hat(t, g=0.12, open_=False):
    n = int((0.22 if open_ else 0.05) * SR); tt = T(n)
    s = hpf(noise(n), 7500, 3) * np.exp(-tt * (14 if open_ else 80))
    add("drums", s, t, 0.35, g * rng.uniform(0.75, 1.0))
def pluck(m, t, g=0.15, pan=0.0, cutoff=5000):
    n = int(0.9 * SR); tt = T(n); f = hz(m)
    s = signal.sawtooth(2 * np.pi * f * tt) * 0.5 + signal.sawtooth(2 * np.pi * f * 1.005 * tt) * 0.5
    s = lpf(s, cutoff) * np.exp(-tt * 7) * (1 - np.exp(-tt * 1500))
    add("music", s, t, pan, g)
def bass(m, t, length, g=0.3):
    n = int(length * SR); tt = T(n); f = hz(m)
    s = np.tanh(1.8 * (np.sin(2 * np.pi * f * tt) + 0.4 * signal.sawtooth(2 * np.pi * f * tt)))
    s = lpf(s, 900) * np.minimum(1, tt / 0.005) * np.clip((length - tt) / 0.02, 0, 1)
    add("music", s, t, 0, g)
def pad(notes, t, length, g=0.1, cutoff=2500):
    n = int(length * SR); tt = T(n); s = np.zeros(n)
    for m in notes:
        for d in (-0.1, 0.0, 0.1): s += signal.sawtooth(2 * np.pi * hz(m) * 2 ** (d / 12) * tt + rng.uniform(0, 6))
    s = lpf(s / (len(notes) * 3), cutoff) * np.minimum(1, tt / 0.5) * np.clip((length - tt) / 0.5, 0, 1)
    add("music", np.stack([s, np.roll(s, 300)], 1), t, 0, g)

S = P["sections"]          # {"intro_end", "drop", "break_start", "break_end", "cut", "hit", "outro", "end_hit"}
def section(t):
    if t < S["intro_end"]: return "intro"
    if t < S["drop"]: return "build"
    if S["break_start"] <= t < S["break_end"]: return "break"
    if S["cut"] <= t < S["hit"]: return "cut"
    if t >= S["outro"]: return "outro"
    return "full"

t = S["intro_end"]
while t < S["outro"] - 1e-6:
    bar = int((t - S["intro_end"]) // 2); root, ch = prog[bar % 4]
    for i in range(4):
        bt = t + i * BEAT; sec = section(bt)
        if sec in ("cut", "outro") or bt >= S["outro"]: continue
        if sec in ("full",): kick(bt)
        elif sec == "build" and i % 2 == 0: kick(bt, 0.7)
        elif sec == "break" and i == 0: kick(bt, 0.6)
        if sec == "full" and i % 2 == 1: snare(bt)
        for h in range(4):
            ht = bt + h * BEAT / 4 + (0.012 if h % 2 else 0)        # léger swing
            if sec == "full" or (sec == "build" and h % 2 == 0) or (sec == "break" and h == 2):
                hat(ht, 0.13 if h == 2 else 0.07)
        if sec == "full": hat(bt + BEAT / 2, 0.06, open_=True)
        if sec in ("full", "build"):
            for e, ln in ((0, 0.2), (0.25, 0.1), (0.375, 0.1)): bass(root - 12, bt + e, ln, 0.3 if sec == "full" else 0.16)
    for k in range(8):
        at = t + k * BEAT / 2; sec = section(at)
        if sec in ("cut", "outro") or at >= S["outro"]: continue
        cut = {"build": 1400 + 2000 * (at - S["intro_end"]) / (S["drop"] - S["intro_end"]), "break": 1800}.get(sec, 5500)
        motif = [0, 1, 2, 1, 0, 2, 1, 2]
        pluck(ch[motif[k]] + (12 if k in (3, 7) else 0), at, 0.13, -.4 + .1 * k, cut)
    if section(t) not in ("cut", "outro"):
        pad([n - 12 for n in ch], t, 2.0, 0.07 if section(t) == "full" else 0.09, 2600 if section(t) != "break" else 1200)
    t += 2.0
# intro : nappe sombre
pad([45, 52, 57, 60], 0, S["intro_end"] + 0.3, 0.09, 900)
# outro : accords tenus, plucks ouverts
pad([45, 57, 64, 69, 72], S["outro"], DUR - S["outro"], 0.12, 1800)
for i, m in enumerate([69, 72, 76, 81, 76]): pluck(m, S["outro"] + 0.1 + i * 0.36, 0.13, -.3 + .15 * i, 3200)

# ================================================================ événements
E = P["events"]
for k, fn in (("tap", sfx_tap), ("key", sfx_key), ("pop", sfx_pop), ("notif", sfx_notif), ("sent", sfx_sent),
              ("received", sfx_received), ("success", sfx_success), ("beep", sfx_beep), ("glitch", sfx_glitch),
              ("thud", sfx_thud), ("slam", sfx_slam), ("impact", sfx_impact), ("heart", sfx_heart), ("flash", sfx_flash)):
    for x in E.get(k, []): fn(x)
for x in E.get("whoosh", []): sfx_whoosh(x[0], 0.5, 0.5, x[1])
for x in E.get("whoosh_low", []): sfx_whoosh(x, 0.45, 0.7, 1, hi=False)
for x in E.get("swish", []): sfx_swish(x)
for a, b in E.get("riser", []): sfx_riser(a, b)
for a, b in E.get("tickroll", []): sfx_tickroll(a, b)
for a, b in E.get("rumble", []): sfx_rumble(a, b - a)
for x in E.get("shimmer", []): sfx_shimmer(x)
for x in E.get("revcym", []): sfx_revcym(x)

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
