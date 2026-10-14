"""Bande-son ARCADIUM 84 (base : banque de bruitages ORVA v2) : musique 120 BPM produite (filtres, sidechain, coupures) + banque de bruitages d'interface.

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


# ================================================================ synthwave 118 BPM en la mineur
BPM = 118; BEAT = 60 / BPM; BAR = 4 * BEAT
def saw(f, tt, det=0.0): return signal.sawtooth(2 * np.pi * f * (1 + det) * tt)
def kick(t, g=0.9):
    n = int(0.45 * SR); tt = T(n); f = 48 + 140 * np.exp(-tt * 34)
    add("kick", np.tanh(2 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 6.5)), t, 0, g * 0.8)
def snare80(t, g=0.5):                 # caisse claire à réverbération « gated »
    n = int(0.5 * SR); tt = T(n); body = np.sin(2 * np.pi * 185 * tt) * np.exp(-tt * 25) * 0.6
    nz = bp(noise(n), 1200, 9000); gate = np.where(tt < 0.28, 1.0, np.exp(-(tt - 0.28) * 60)) * (0.6 + 0.4 * np.exp(-tt * 8))
    add("drums", np.stack([(body + nz * 0.8) * gate, (body + np.roll(nz, 300) * 0.8) * gate], 1), t, 0, g)
def hat(t, g=0.06): n = int(0.04 * SR); add("drums", hpf(noise(n), 8000, 3) * np.exp(-T(n) * 90), t, 0.3, g)
def arp_note(m, t, ln, g=0.1, cut=2600):
    n = int(ln * SR); tt = T(n); f = hz(m); s = saw(f, tt) * 0.5 + saw(f, tt, 0.006) * 0.5
    s = lpf(s, cut) * np.minimum(1, tt / 0.003) * np.exp(-tt * 8); add("music", s, t, rng.uniform(-.5, .5), g)
def pad(notes, t, ln, g=0.08):
    n = int(ln * SR); tt = T(n); s = np.zeros(n)
    for m in notes:
        for d in (-0.012, 0.0, 0.011): s += saw(hz(m), tt, d)
    s = lpf(s / (3 * len(notes)), 2200) * np.minimum(1, tt / 0.4) * np.clip((ln - tt) / 0.4, 0, 1)
    add("music", np.stack([s, np.roll(s, 500)], 1), t, 0, g)
def bass(m, t, ln, g=0.22):
    n = int(ln * SR); tt = T(n); s = lpf(saw(hz(m), tt) + np.sin(2 * np.pi * hz(m) * tt), 600) * np.minimum(1, tt / 0.004) * np.clip((ln - tt) / 0.01, 0, 1)
    add("music", s, t, 0, g)
def lead(m0, m1, t, ln, g=0.1):        # lead avec glissando
    n = int(ln * SR); tt = T(n); f = hz(m0) + (hz(m1) - hz(m0)) * np.clip(tt / 0.08, 0, 1)
    vib = 1 + 0.006 * np.sin(2 * np.pi * 5.5 * tt) * np.clip((tt - 0.15) / 0.2, 0, 1)
    s = signal.square(2 * np.pi * np.cumsum(f * vib) / SR, 0.4) * 0.5 + signal.sawtooth(2 * np.pi * np.cumsum(f * vib * 1.004) / SR) * 0.5
    s = lpf(s, 3500) * np.minimum(1, tt / 0.01) * np.clip((ln - tt) / 0.05, 0, 1); add("music", s, t, 0.1, g)
Am, F, C, G = [57, 64, 69, 72], [53, 60, 65, 69], [48, 55, 64, 67], [55, 62, 67, 71]
PROG = [(Am, 45), (F, 41), (C, 48), (G, 43)]
MEL = [(76, 1.0), (74, 0.5), (72, 0.5), (74, 1.0), (79, 1.0), (77, 1.5), (76, 0.5), (72, 1.0), (74, 1.0)]
t = 1.3; bar = 0
while t < DUR - 2.0:
    ch, root = PROG[bar % 4]; quiet = (TM["game"][0] - 0.1 <= t < TM["game"][1]) and False
    for i in range(16):
        bt = t + i * BEAT / 4
        if bt >= DUR - 2.0: break
        arp_note(ch[[0, 1, 2, 3, 2, 1, 3, 2][i % 8]] + 12, bt, BEAT / 4, 0.07, 1800 + 1800 * ((t - 1.3) / 20))
        if i % 2 == 0: bass(root - 12 + (12 if i % 4 == 2 else 0), bt, BEAT / 2.2)
        if t >= 2.5 and i % 2 == 1: hat(bt)
    if t >= 2.5:
        for i in range(4):
            kick(t + i * BEAT)
            if i % 2 == 1: snare80(t + i * BEAT)
    pad(ch, t, BAR, 0.07)
    t += BAR; bar += 1
# mélodie principale à partir du jeu
t = TM["game"][0]
for rep in range(2):
    prev = 76
    for m, d in MEL:
        if t > DUR - 2.5: break
        lead(prev, m, t, d * BEAT * 0.95, 0.09); prev = m; t += d * BEAT
# fin : accord tenu
pad([45, 57, 64, 69, 72, 76], DUR - 2.2, 2.2, 0.12); kick(DUR - 2.2); snare80(DUR - 2.2, 0.6)

# ================================================================ bruitages rétro
def tv_static(t0, t1, g=0.35):
    n = int((t1 - t0) * SR); add("fx", np.stack([hpf(noise(n), 500), hpf(noise(n), 500)], 1) * np.clip((t1 - t0 - T(n)) / 0.05, 0, 1)[:, None], t0, 0, g)
def crt_thunk(t, g=0.5):
    n = int(0.6 * SR); tt = T(n); f = 55 + 40 * np.exp(-tt * 20)
    add("fx", np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 7) + hpf(noise(n), 3000) * np.exp(-tt * 40) * 0.4, t, 0, g)
    n2 = int(1.0 * SR); tt2 = T(n2); add("fx", np.sin(2 * np.pi * 7800 * tt2) * 0.05 * np.exp(-tt2 * 3), t, 0, g)
def crt_off_s(t, g=0.5):
    n = int(0.7 * SR); tt = T(n); f = 300 * np.exp(-tt * 6) + 40
    add("fx", np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 4) + lpf(noise(n), 900) * np.exp(-tt * 8) * 0.3, t, 0, g)
def tape_rew(t, ln=0.6, g=0.4):        # bande qui rembobine : sifflement modulé qui monte
    n = int(ln * SR); tt = T(n); f = 600 + 2600 * tt / ln + 300 * np.sin(2 * np.pi * 23 * tt)
    s = signal.sawtooth(2 * np.pi * np.cumsum(f) / SR) * 0.3 + bp(noise(n), 2000, 8000) * 0.6
    add("fx", s * np.sin(np.pi * tt / ln), t, 0, g); add("fx", hpf(noise(int(0.03 * SR)), 1000), t, 0, g * 0.8)
def coin_s(t, g=0.32):                 # pièce de monnaie 8-bit
    for k, f in enumerate((988, 1319)):
        n = int(0.09 * SR if k == 0 else 0.35 * SR); tt = T(n)
        add("ui", signal.square(2 * np.pi * f * tt) * np.exp(-tt * (20 if k == 0 else 7)) * 0.4, t + k * 0.08, 0, g)
def coin_drop(t, g=0.3):
    for k in range(4):
        tt = T(int(0.25 * SR)); add("fx", bell(98 + (k % 2) * 3, 0.25, 12) * 0.7, t + k * 0.07 * (1 - k * 0.15), rng.uniform(-.3, .3), g * (1 - k * 0.2))
def blip(t, g=0.1):                    # tir laser 8-bit
    n = int(0.12 * SR); tt = T(n); f = 1800 * np.exp(-tt * 25) + 300
    add("ui", signal.square(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 18) * 0.4, t, rng.uniform(-.4, .4), g)
def boom8(t, g=0.12):
    n = int(0.3 * SR); x = noise(n); hold = 18; x = np.repeat(x[::hold], hold)[:n]
    add("ui", lpf(x, 3000) * np.exp(-T(n) * 10), t, rng.uniform(-.4, .4), g)
def buzz(t, g=0.07):                   # néon qui s'allume en grésillant
    n = int(0.6 * SR); tt = T(n); r = np.random.default_rng(int(t * 100))
    gate = np.repeat((r.random(int(0.6 * 30) + 1) > 0.4).astype(float), int(SR / 30) + 1)[:n]
    s = (signal.sawtooth(2 * np.pi * 100 * tt) * 0.4 + signal.sawtooth(2 * np.pi * 200 * tt) * 0.2 + hpf(noise(n), 4000) * 0.3) * gate
    add("fx", lpf(s, 3000) * np.exp(-tt * 1.5), t, rng.uniform(-.3, .3), g)
def channel_click(t, g=0.4):
    add("fx", hpf(noise(int(0.02 * SR)), 1500) * np.exp(-T(int(0.02 * SR)) * 200), t, 0, g); tv_static(t + 0.05, t + 0.25, 0.3)

tv_static(TM["static"][0], TM["static"][1] + 0.1); crt_thunk(TM["crt_on"][0]); crt_thunk(TM["crt_on"][1], 0.35)
sfx_riser(TM["logo"] - 0.4, TM["logo"] + 0.9, 0.25); sfx_impact(TM["logo"] + 1.0, 0.55); sfx_shimmer(TM["logo"] + 1.0, 1.0, 0.1)
for x in TM["neon"]: buzz(x)
tape_rew(TM["rewind"]); coin_s(TM["coin"]); coin_drop(TM["coin_drop"])
for x in TM["blips"]:
    if TM["game"][0] - 3.9 < x < TM["game"][1]: blip(x); boom8(x + 0.7)
channel_click(TM["channel"] + 0.1)
for x in TM["slam"]: sfx_slam(x, 0.5)
sfx_whoosh(TM["zoom"] + 0.35, 0.4, 0.5, 1); sfx_glitch(TM["glitch"] + 0.05, 0.4, 0.3)
for x in TM["glass"]: buzz(x, 0.06)
crt_off_s(TM["crt_off"]); coin_s(TM["end"] + 1.5, 0.22)

# ================================================================ mixage
def reverb(x, mix=0.25, length=2.0):
    ir_n = int(length * SR); tt = T(ir_n); ir = noise(ir_n) * np.exp(-tt * 3.0); ir = lpf(ir, 7000); ir /= np.abs(ir).sum() / 30
    return x + np.stack([signal.fftconvolve(x[:, 0], ir)[:N], signal.fftconvolve(x[:, 1], np.roll(ir, 301))[:N]], 1) * mix
env = np.abs(BUS["kick"][:, 0]); env = signal.lfilter([1], [1, -0.9995], env) / 2000; duck = 1 - np.clip(env * 6, 0, 0.55)
mix = reverb(BUS["music"], 0.35) * duck[:, None] + reverb(BUS["drums"], 0.3) + BUS["kick"] * 0.85 + reverb(BUS["fx"], 0.2) + reverb(BUS["ui"], 0.15)
# saturation de bande + petit pleurage
mix = hpf(mix.T, 28).T; mix = np.tanh(mix * 1.2) / np.tanh(1.2)
tt = T(N); mix *= np.clip((DUR - tt) / 0.5, 0, 1)[:, None]; mix /= np.abs(mix).max() / 0.92
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
