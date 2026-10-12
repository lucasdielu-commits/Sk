"""Bande-son originale du motion design Sorienka : électro douce à 120 BPM + bruitages d'interface.

Usage : python3 music_motion.py sortie.wav '<json>'
json = {"dur": 24.5, "drop": 8.0, "end": 21.0, "collapse": 23.6,
        "whoosh": [..], "pop": [..], "type": [..], "ding": [..], "slam": [..]}
"""
import json, sys, wave
import numpy as np

SR = 44100
P = json.loads(sys.argv[2]); DUR = P["dur"]; N = int(SR * DUR)
rng = np.random.default_rng(21)
MUS = np.zeros((N, 2)); KICK = np.zeros((N, 2)); FX = np.zeros((N, 2))
BEAT = 0.5

def hz(m): return 440.0 * 2 ** ((m - 69) / 12)
def env_t(n): return np.arange(n) / SR

def add(bus, sig, start, pan=0.0, gain=1.0):
    i = int(round(start * SR)); j = min(N, i + len(sig))
    if j <= i or i < 0: return
    s = sig[: j - i] * gain
    bus[i:j, 0] += s * np.sqrt((1 - pan) / 2); bus[i:j, 1] += s * np.sqrt((1 + pan) / 2)

def hp(x, k=3):          # passe-haut grossier
    return x - np.convolve(x, np.ones(k) / k, "same")
def lp(x, k=8):
    return np.convolve(x, np.ones(k) / k, "same")

def kick(start, g=0.9):
    tt = env_t(int(0.45 * SR)); f = 45 + 95 * np.exp(-tt * 28)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 7.5)
    s[:200] += rng.standard_normal(200) * np.linspace(0.4, 0, 200)
    add(KICK, s, start, 0, g)

def clap(start, g=0.32):
    n = int(0.22 * SR); tt = env_t(n); s = np.zeros(n)
    for d in (0, 0.011, 0.022):
        k = int(d * SR); m = n - k
        s[k:] += hp(rng.standard_normal(m), 6) * np.exp(-np.arange(m) / SR * 38)
    add(MUS, s, start, 0.05, g)

def hat(start, g=0.08, open_=False):
    n = int((0.16 if open_ else 0.04) * SR)
    s = hp(hp(rng.standard_normal(n), 2), 2) * np.exp(-env_t(n) * (18 if open_ else 90))
    add(MUS, s, start, 0.3, g)

def pluck(m, start, g=0.12, pan=0.0, dec=6.0):
    tt = env_t(int(0.9 * SR)); f = hz(m)
    s = sum(np.sin(2 * np.pi * f * k * tt) / k * np.exp(-tt * dec * k * 0.6) for k in (1, 2, 3, 4))
    add(MUS, s * (1 - np.exp(-tt * 600)), start, pan, g)

def bass(m, start, length, g=0.22):
    tt = env_t(int(length * SR)); f = hz(m)
    s = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt) + 0.12 * np.sin(6 * np.pi * f * tt))
    s *= np.minimum(1, tt / 0.01) * np.clip((length - tt) / 0.03, 0, 1)
    add(MUS, s, start, 0, g)

def pad(notes, start, length, g=0.1):
    tt = env_t(int(length * SR)); s = np.zeros(len(tt))
    for m in notes:
        for d in (-0.08, 0.09):
            s += np.sin(2 * np.pi * hz(m) * 2 ** (d / 12) * tt + rng.uniform(0, 6))
    s *= np.minimum(1, tt / 0.6) * np.clip((length - tt) / 0.6, 0, 1)
    add(MUS, s / len(notes), start, 0, g)

def noise_sweep(start, length, g, up=True):
    n = int(length * SR); tt = env_t(n); x = rng.standard_normal(n)
    a = hp(x, 3) if up else lp(x, 12)
    e = (tt / length) ** 2.2 if up else np.exp(-tt * 5)
    add(FX, a * e, start, 0, g)

def whoosh(start, g=0.16):
    n = int(0.45 * SR); tt = env_t(n); x = rng.standard_normal(n)
    a = lp(x, 5) - lp(x, 40)
    add(FX, a * np.sin(np.pi * tt / 0.45) ** 3, start - 0.22, rng.uniform(-.4, .4), g)

def impact(start, g=0.8):
    tt = env_t(int(1.6 * SR)); f = 38 + 70 * np.exp(-tt * 12)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 2.6)
    add(FX, s, start, 0, g); noise_sweep(start, 1.2, 0.18, up=False)

def pop(start, g=0.13):
    tt = env_t(int(0.08 * SR)); f = 900 + 1400 * np.exp(-tt * 60)
    add(FX, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 55), start, rng.uniform(-.3, .3), g)

def click(start, g=0.06):
    n = int(0.012 * SR)
    add(FX, hp(rng.standard_normal(n), 2) * np.exp(-env_t(n) * 400), start, rng.uniform(-.2, .2), g)

def ding(start, g=0.16):
    tt = env_t(int(1.6 * SR)); s = np.zeros(len(tt))
    for m, a in ((88, 1), (95, .5)):
        for r, ra, d in ((1, 1, 3), (2.76, .4, 5)):
            s += a * ra * np.sin(2 * np.pi * hz(m) * r * tt) * np.exp(-tt * d)
    add(FX, s, start, 0.1, g)

def slam(start, g=0.4):
    kick(start, 0.7); noise_sweep(start - 0.25, 0.25, 0.08, up=True)

# --------------------------------------------------------------- arrangement
prog = [(57, [69, 72, 76]), (53, [69, 72, 77]), (60, [67, 72, 76]), (55, [67, 71, 74])]   # Am F C G
DROP, END, COL = P["drop"], P["end"], P["collapse"]

# intro : battement de cœur sur le point lumineux
for b in (0.0, 0.32, 1.0, 1.32, 2.0, 2.32):
    tt = env_t(int(0.3 * SR)); f = 50 + 30 * np.exp(-tt * 20)
    add(KICK, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 12), b, 0, 0.55 if b % 1 == 0 else 0.35)
pad([57, 64, 69, 72], 0.0, 3.4, 0.08)
noise_sweep(2.2, 0.8, 0.1, up=True)
impact(3.0, 0.45)

t = 3.0
while t < END - 1e-6:
    bar = int((t - 3.0) // 2); root, ch = prog[bar % 4]
    for i in range(4):                               # temps
        bt = t + i * BEAT
        if bt >= END: break
        full = bt >= DROP
        if full or i % 2 == 0: kick(bt, 0.85 if full else 0.6)
        if full and i % 2 == 1: clap(bt)
        for h in range(4 if full else 2):
            hat(bt + h * BEAT / (4 if full else 2), 0.06 if h % 2 else 0.09)
        if full: hat(bt + BEAT / 2, 0.05, open_=True)
        for e in (0, 0.25, 0.375):                   # basse syncopée
            if not (DROP - 0.5 < bt < DROP): bass(root - 24, bt + e, 0.11, 0.22 if full else 0.14)
    # arpège / accords
    for k in range(8):
        at = t + k * BEAT / 2
        if at >= END or (DROP - 0.2 < at < DROP): continue
        pluck(ch[k % 3] + (12 if k % 4 == 3 else 0), at, 0.09 if at < DROP else 0.11, -.35 + .1 * k)
    pad([n - 12 for n in ch], t, 2.0, 0.06 if t < DROP else 0.09)
    t += 2.0

noise_sweep(DROP - 1.6, 1.55, 0.16, up=True)        # montée avant le drop
impact(DROP, 0.9)
# fin : nappe, plucks lents, puis effondrement vers le point
pad([57, 64, 69, 72, 76], END, COL - END + 0.4, 0.1)
for i, m in enumerate([69, 72, 76, 81, 76, 72]): pluck(m, END + i * 0.4, 0.12, -.3 + .12 * i, 3.0)
noise_sweep(COL - 0.9, 0.9, 0.12, up=True)
impact(COL, 0.55); ding(COL + 0.05, 0.12)

for s in P.get("whoosh", []): whoosh(s)
for s in P.get("pop", []): pop(s)
for s in P.get("type", []): click(s)
for s in P.get("ding", []): ding(s)
for s in P.get("slam", []): slam(s)

# sidechain : la musique s'efface brièvement sous chaque kick (pompe house)
duck = np.ones(N); kenv = np.abs(KICK[:, 0])
peaks = np.where(kenv > 0.3)[0]
last = -10 ** 9
for p in peaks:
    if p - last > SR * 0.2:
        n = int(0.28 * SR); seg = 1 - 0.6 * np.exp(-np.arange(n) / SR * 9)
        duck[p:p + n] = np.minimum(duck[p:p + n], seg[: len(duck[p:p + n])]); last = p
MUS *= duck[:, None]
# réverb légère sur la musique
for d, g in ((0.083, .22), (0.167, .15), (0.251, .1)):
    k = int(d * SR); MUS[k:] += MUS[:-k][:, ::-1] * g
mix = MUS * 0.9 + KICK * 0.8 + FX
mix = np.tanh(mix * 1.3) / np.tanh(1.3)            # saturation douce
tt = np.arange(N) / SR
mix *= np.clip((DUR - tt) / 0.8, 0, 1)[:, None]
mix /= np.abs(mix).max() / 0.9
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
