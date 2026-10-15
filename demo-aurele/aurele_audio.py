"""Bande-son AURÈLE (base : banque de bruitages ORVA v2) : musique 120 BPM produite (filtres, sidechain, coupures) + banque de bruitages d'interface.

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


# ================================================================ instruments cinéma
def strings(notes, t, length, g=0.12, attack=1.4, cutoff=2400):
    n = int(length * SR); tt = T(n); s = np.zeros((n, 2))
    for m in notes:
        for d, pan in ((-0.07, -0.6), (0.0, 0.0), (0.08, 0.6)):
            f = hz(m) * 2 ** (d / 12); vib = 1 + 0.003 * np.sin(2 * np.pi * 5.2 * tt + rng.uniform(0, 6))
            x = signal.sawtooth(2 * np.pi * np.cumsum(f * vib) / SR)
            s[:, 0] += x * np.sqrt((1 - pan) / 2); s[:, 1] += x * np.sqrt((1 + pan) / 2)
    s = np.stack([lpf(s[:, 0], cutoff), lpf(s[:, 1], cutoff)], 1) / (len(notes) * 2)
    env = np.minimum(1, tt / attack) * np.clip((length - tt) / 1.5, 0, 1)
    add("music", s * env[:, None], t, 0, g)
def choir(notes, t, length, g=0.08, vowel="a"):
    F = {"a": (800, 1150, 2900), "o": (450, 800, 2830), "u": (325, 700, 2530)}[vowel]
    n = int(length * SR); tt = T(n); src_ = np.zeros(n)
    for m in notes:
        for d in (-0.1, 0.1):
            src_ += signal.sawtooth(2 * np.pi * hz(m) * 2 ** (d / 12) * tt * (1 + 0.004 * np.sin(2 * np.pi * 4.6 * tt + d * 30)))
    v = sum(bp(src_, f * 0.9, f * 1.1) * a for f, a in zip(F, (1, 0.6, 0.25)))
    v *= np.minimum(1, tt / 2.0) * np.clip((length - tt) / 2.0, 0, 1)
    add("music", np.stack([v, np.roll(v, 400)], 1) / len(notes), t, 0, g)
def piano(m, t, g=0.2, pan=0.0, dec=1.0):
    n = int(4 * SR); tt = T(n); f = hz(m)
    s = (np.sin(2 * np.pi * f * tt) + .5 * np.sin(4 * np.pi * f * tt) * np.exp(-tt * 2.5) + .2 * np.sin(6 * np.pi * f * tt) * np.exp(-tt * 4)
         + .08 * np.sin(2 * np.pi * f * 4.02 * tt) * np.exp(-tt * 6)) * np.exp(-tt * dec) * (1 - np.exp(-tt * 300))
    add("music", s, t, pan, g)
def drone(t, length, g=0.2, root=38):
    n = int(length * SR); tt = T(n)
    s = sum(np.sin(2 * np.pi * hz(root + iv) * tt + k) * a for k, (iv, a) in enumerate(((0, 1), (-12, .7), (7, .35), (12, .2))))
    s *= (0.8 + 0.2 * np.sin(2 * np.pi * 0.13 * tt)) * np.minimum(1, tt / 2) * np.clip((length - tt) / 1.5, 0, 1)
    add("music", lpf(s, 500), t, 0, g)
def boom(t, g=0.7):
    n = int(4 * SR); tt = T(n); f = 30 + 40 * np.exp(-tt * 6)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 1.0) + lpf(noise(n), 300) * np.exp(-tt * 1.5) * 0.4
    add("fx", s, t, 0, g)
def swell(t0, t1, g=0.3):              # souffle qui gonfle (cymbale inversée + cordes)
    n = int((t1 - t0) * SR); tt = T(n); L = t1 - t0
    s = sweep_filter(noise(n), 600, 9000, 1.2) * (tt / L) ** 2.5
    add("fx", s, t0, 0, g * 2)
def glass(t, g=0.25, m=None):          # tintement de verre
    m = m or rng.choice([96, 100, 103, 108]); tt = T(int(3 * SR))
    s = sum(a * np.sin(2 * np.pi * hz(m) * r * tt) * np.exp(-tt * d) for r, a, d in ((1, 1, 1.4), (2.32, .5, 2.2), (4.1, .25, 3.4), (6.7, .1, 5)))
    add("fx", s * (1 - np.exp(-tt * 3000)), t, rng.uniform(-.4, .4), g)
def pour(t0, t1, g=0.25):              # or liquide : coulée sourde et bulles graves
    n = int((t1 - t0) * SR); tt = T(n); x = lpf(noise(n), 700) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.7 * tt)) * 3
    x *= np.minimum(1, tt / 0.8) * np.clip((t1 - t0 - tt) / 0.8, 0, 1)
    add("fx", np.stack([x, np.roll(x, 900)], 1), t0, 0, g)
    for k in range(int((t1 - t0) * 3)):
        tk = t0 + rng.uniform(0.3, t1 - t0 - 0.3); tb = T(int(0.18 * SR)); f = rng.uniform(140, 260) * (1 + 1.2 * tb / 0.18)
        add("fx", np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tb * 18), tk, rng.uniform(-.5, .5), g * 0.4)
def spritz(t, g=0.6):                  # vaporisateur : « tchhh » aérien
    n = int(0.55 * SR); tt = T(n); s = bp(noise(n), 3000, 14000) * np.minimum(1, tt / 0.01) * np.exp(-tt * 4)
    add("fx", np.stack([s, np.roll(s, 60)], 1), t, 0, g)
    n2 = int(0.04 * SR); add("fx", hpf(noise(n2), 2000) * np.exp(-T(n2) * 200), t - 0.02, 0, g * 0.6)
def pen(t0, t1, g=0.05):               # plume qui trace
    n = int((t1 - t0) * SR); tt = T(n); x = bp(noise(n), 3000, 9000) * (0.5 + 0.5 * np.sin(2 * np.pi * 7 * tt) ** 2)
    add("fx", x * np.sin(np.pi * tt / (t1 - t0)), t0, 0.1, g)

# ================================================================ partition (ré mineur → ré majeur)
D, Bb, F, C, Gm, A = [50, 57, 62, 65, 69], [46, 53, 58, 62, 65], [41, 53, 57, 60, 65], [48, 55, 60, 64, 67], [43, 55, 58, 62, 67], [45, 52, 57, 61, 64]
drone(0, DUR, 0.22, 38)
strings([62, 69], 0.2, 3.6, 0.07, 2.5, 1400)
for tt_, m in ((0.4, 74), (1.6, 69), (2.3, 77), (3.1, 76)): piano(m, tt_, 0.18, 0.1, 0.8)
swell(TM["burn"] - 0.9, TM["burn"] + 0.35, 0.32); boom(TM["burn"] + 0.45, 0.55); sfx_shimmer(TM["burn"] + 0.4, 1.4, 0.12)
strings(Bb, 3.4, 5.4, 0.11, 2.0, 1800); choir([58, 62, 65], 4.0, 5.0, 0.06, "o")
for tt_, m in ((4.6, 74), (5.6, 72), (6.2, 70), (7.2, 69)): piano(m, tt_, 0.16, -0.1, 0.7)
pour(TM["liquid"][0], TM["liquid"][1], 0.28)
sfx_whoosh(TM["smoke"][0] + 0.7, 0.35, 1.0, 1, hi=False)
strings(F, 8.6, 6.6, 0.12, 1.6, 2200); choir([53, 57, 60, 65], 9.2, 6.0, 0.08, "a")
boom(TM["rim"], 0.75); swell(TM["rim"] - 0.8, TM["rim"], 0.18)
for tt_, m in ((10.2, 69), (10.9, 72), (11.6, 77), (12.6, 76), (13.4, 72)): piano(m, tt_, 0.17, 0.0, 0.7)
glass(TM["sweep"][0] + 0.3, 0.22, 103); glass(TM["logo"] + 0.3, 0.16, 108)
swell(TM["rack"], TM["rack"] + 0.8, 0.2)
strings(Gm, 15.0, 3.4, 0.1, 1.2, 2000); strings(A, 18.2, 2.2, 0.11, 0.9, 2200)
for k, t0 in enumerate(TM["notes"]):
    pen(t0 + 0.2, t0 + 1.4); glass(t0 + 0.6, 0.15, [96, 100, 103][k])
    for j, m in enumerate([[74, 77, 81], [72, 77, 79], [69, 73, 76]][k]): piano(m, t0 + 0.6 + j * 0.28, 0.14, -.3 + .3 * j, 1.1)
for x in TM["rings"]: sfx_whoosh(x + 0.3, 0.25, 0.5, 1)
swell(TM["spritz"] - 0.7, TM["spritz"] + 0.1, 0.25); spritz(TM["spritz"] + 0.12, 0.6); sfx_shimmer(TM["spritz"] + 0.2, 1.4, 0.16)
boom(TM["hero"], 0.85)
strings(D, 20.3, 3.6, 0.15, 0.8, 3000); choir([62, 65, 69, 74], 20.3, 3.6, 0.1, "a")
for tt_, m in ((20.6, 81), (21.3, 77), (21.9, 74), (22.5, 76), (23.0, 77)): piano(m, tt_, 0.2, 0.0, 0.6)
sfx_whoosh(TM["smoke"][1] + 0.6, 0.25, 1.0, 1, hi=False)
# fin : tierce picarde (ré majeur), lumineuse
strings([50, 57, 62, 66, 69, 74], 23.4, DUR - 23.4, 0.15, 1.0, 3200); choir([62, 66, 69], 23.4, DUR - 23.4, 0.09, "o")
boom(TM["end"], 0.5); glass(TM["endlogo"] + 0.6, 0.22, 98); sfx_shimmer(TM["endlogo"] + 0.3, 1.8, 0.12)
for j, m in enumerate([74, 78, 81, 86]): piano(m, 24.0 + j * 0.42, 0.16, -.3 + .2 * j, 0.6)

# ================================================================ mixage
def reverb(x, mix=0.25, length=2.8):
    ir_n = int(length * SR); tt = T(ir_n)
    ir = noise(ir_n) * np.exp(-tt * 2.0); ir = lpf(ir, 6000); ir /= np.abs(ir).sum() / 30
    out = np.stack([signal.fftconvolve(x[:, 0], ir)[:N], signal.fftconvolve(x[:, 1], np.roll(ir, 331))[:N]], 1)
    return x + out * mix
music = reverb(BUS["music"], 0.55); fx = reverb(BUS["fx"] + BUS["ui"], 0.35)
mix = music * 1.0 + fx * 0.9 + BUS["kick"] * 0.8
mix = hpf(mix.T, 22).T; mix = np.tanh(mix * 0.9) / np.tanh(0.9)
tt = T(N); mix *= np.clip((DUR - tt) / 1.2, 0, 1)[:, None] * np.clip(tt / 0.05, 0, 1)[:, None]
mix /= np.abs(mix).max() / 0.92
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
