"""Bande-son KUMO (base : banque de bruitages ORVA v2) : musique 120 BPM produite (filtres, sidechain, coupures) + banque de bruitages d'interface.

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


# ================================================================ instruments japonais (synthèse)
def koto(m, t, g=0.25, pan=0.0, length=3.0):
    """Corde pincée claire (Karplus-Strong) avec léger « pitch bend » d'attaque."""
    f = hz(m); n = int(length * SR); p = max(2, int(SR / f)); prev = rng.uniform(-1, 1, p); reps = n // p + 1; y = np.zeros(reps * p)
    for r_ in range(reps): y[r_ * p:(r_ + 1) * p] = prev; prev = 0.997 * 0.5 * (prev + np.roll(prev, -1))
    s = y[:n] * np.exp(-T(n) * 0.9); s = s + 0.3 * hpf(s, 1500)
    add("music", s, t, pan, g)
def shaku(m, t, ln, g=0.12, bend=0.0):  # flûte shakuhachi : souffle + note avec vibrato et glissé
    n = int(ln * SR); tt = T(n); f = hz(m) * 2 ** ((bend * np.clip(1 - tt / 0.35, 0, 1)) / 12)
    vib = 1 + 0.008 * np.sin(2 * np.pi * 5.0 * tt) * np.clip((tt - 0.3) / 0.4, 0, 1)
    ph = 2 * np.pi * np.cumsum(f * vib) / SR; tone = np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.08 * np.sin(3 * ph)
    breath = bp(noise(n), 700, 4000) * 0.35
    env = np.minimum(1, tt / 0.25) * np.clip((ln - tt) / 0.5, 0, 1) * (1 + 0.15 * np.sin(2 * np.pi * 0.7 * tt))
    add("music", (tone * 0.7 + breath) * env, t, -0.15, g)
def taiko(t, g=0.6):
    n = int(1.6 * SR); tt = T(n); f = 62 + 50 * np.exp(-tt * 18)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 3.2) + lpf(noise(n), 700) * np.exp(-tt * 25) * 0.5
    add("kick", s, t, 0, g)
def tok(t, g=0.45):                     # shishi-odoshi : le bambou qui frappe la pierre
    n = int(0.5 * SR); tt = T(n)
    s = sum(a * np.sin(2 * np.pi * f * tt) * np.exp(-tt * d) for f, a, d in ((420, 1, 26), (980, 0.5, 40), (1630, 0.25, 55)))
    add("fx", s + bp(noise(n), 600, 3000) * np.exp(-tt * 80) * 0.4, t, 0.25, g)
def drip(t, g=0.3):
    n = int(0.25 * SR); tt = T(n); f = 900 + 1500 * (tt / 0.25) ** 0.5
    add("fx", np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 28), t, 0, g)
def brush_s(t0, t1, g=0.12):            # pinceau sur papier
    n = int((t1 - t0) * SR); tt = T(n); x = bp(noise(n), 1500, 7000) * (0.6 + 0.4 * np.sin(2 * np.pi * 3 * tt) ** 2)
    add("fx", x * np.sin(np.pi * tt / (t1 - t0)) ** 0.6, t0, rng.uniform(-.3, .3), g)
def wind(t0, t1, g=0.12):
    n = int((t1 - t0) * SR); tt = T(n); x = sweep_filter(noise(n), 300, 900, 1.5) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.2 * tt))
    x *= np.minimum(1, tt / 1.0) * np.clip((t1 - t0 - tt) / 1.0, 0, 1); add("fx", np.stack([x, np.roll(x, 3000)], 1), t0, 0, g)
def chime(t, g=0.08):
    for k in range(5): add("fx", bell(rng.choice([86, 89, 91, 93, 98]), 1.6, 2.5) * 0.6, t + rng.uniform(0, 0.6), rng.uniform(-.7, .7), g)
def pour_s(t0, t1, g=0.2):
    n = int((t1 - t0) * SR); tt = T(n); x = bp(noise(n), 400, 3500) * (0.7 + 0.3 * np.sin(2 * np.pi * 9 * tt)) * np.minimum(1, tt / 0.1) * np.clip((t1 - t0 - tt) / 0.2, 0, 1)
    add("fx", x * 2, t0, -0.1, g)
def whisk_s(t0, t1, g=0.18):            # fouet en bambou : va-et-vient rapide
    n = int((t1 - t0) * SR); tt = T(n); mod = (0.5 + 0.5 * np.sin(2 * np.pi * 6 * tt)) ** 2
    add("fx", bp(noise(n), 2000, 9000) * mod * np.minimum(1, tt / 0.1) * np.clip((t1 - t0 - tt) / 0.2, 0, 1) * 2, t0, 0.15, g)
def stampseal(t, g=0.4):
    n = int(0.25 * SR); tt = T(n); f = 120 + 60 * np.exp(-tt * 40)
    add("fx", np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 18) + lpf(noise(n), 1500) * np.exp(-tt * 40) * 0.5, t, 0, g)

# ================================================================ partition (gamme hirajoshi en ré)
SC = [62, 64, 65, 69, 70, 74, 76, 77, 81, 82]          # ré mi fa la si♭ …
wind(0, DUR, 0.10)
for i, (st, m) in enumerate(((0.9, 74), (1.6, 70), (2.2, 69), (2.9, 65))): koto(m, st, 0.2, -0.2 + 0.15 * i)
shaku(69, 4.4, 2.6, 0.12, -1.5); shaku(70, 7.0, 1.4, 0.1); shaku(65, 8.4, 1.6, 0.1, -1)
# motif de koto récurrent
pattern = [0, 3, 4, 3, 5, 4, 2, 3]; step = 0.48
t = 4.3; k = 0
while t < DUR - 3.2:
    if not (14.2 <= t < 14.9):
        koto(SC[pattern[k % 8]] - (12 if k % 8 == 0 else 0), t, 0.16 if t < 14 else 0.19, -0.4 + 0.1 * (k % 8))
    t += step if (k % 8) not in (3, 7) else step * 2; k += 1
for st, m, ln, b in ((10.2, 74, 2.0, -1.5), (12.4, 76, 1.2, 0), (13.4, 74, 1.0, 0), (15.6, 69, 2.2, -1.5), (18.2, 70, 1.4, 0), (20.6, 74, 2.4, -2), (23.8, 69, 2.6, -1.5)):
    shaku(m, st, ln, 0.11, b)
koto(50, DUR - 2.8, 0.25, 0, 3.0); koto(62, DUR - 2.7, 0.2, 0.2); koto(69, DUR - 2.55, 0.16, -0.2)

# ================================================================ événements
drip(TM["drip"]); brush_s(*TM["enso"], 0.16); brush_s(*TM["ensoend"], 0.16)
for x in TM["seal"]: stampseal(x + 0.08)
for x in TM["brush"]: brush_s(x, x + 0.75, 0.25); taiko(x + 0.05, 0.55)
tok(TM["land"] + 0.3); chime(TM["land"] + 0.8)
for x in TM["mist"]: sfx_whoosh(x + 0.5, 0.18, 1.0, 1, hi=False); chime(x + 0.3, 0.05)
tok(TM["bamboo"] + 1.8); chime(TM["bamboo"] + 0.5, 0.06)
for k in range(10): brush_s(TM["bamboo"] + 0.1 + k * 0.3, TM["bamboo"] + 0.4 + k * 0.3, 0.06)
drip(TM["drop"]); taiko(TM["drop"] + 0.1, 0.5); sfx_whoosh(TM["drop"] + 0.5, 0.2, 0.8, 1, hi=False)
pour_s(*TM["pour"]); whisk_s(*TM["whisk"])
tok(TM["tin"] + 1.0, 0.35); taiko(TM["end"], 0.45); tok(DUR - 2.0, 0.4)
for x in TM["texts"]: brush_s(x, x + 0.4, 0.05)

# ================================================================ mixage
def reverb(x, mix=0.3, length=3.2):
    ir_n = int(length * SR); tt = T(ir_n); ir = noise(ir_n) * np.exp(-tt * 1.8); ir = lpf(ir, 7000); ir /= np.abs(ir).sum() / 30
    return x + np.stack([signal.fftconvolve(x[:, 0], ir)[:N], signal.fftconvolve(x[:, 1], np.roll(ir, 377))[:N]], 1) * mix
mix = reverb(BUS["music"], 0.5) + reverb(BUS["fx"] + BUS["ui"], 0.35) + reverb(BUS["kick"], 0.4) * 0.9
mix = hpf(mix.T, 25).T; mix = np.tanh(mix * 0.8) / np.tanh(0.8)
tt = T(N); mix *= np.clip((DUR - tt) / 1.2, 0, 1)[:, None]; mix /= np.abs(mix).max() / 0.92
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
