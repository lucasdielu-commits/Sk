"""Musique d'ambiance originale (synthèse) + bruitages, 25 s, stéréo 44,1 kHz."""
import sys, wave
import numpy as np

SR = 44100
DUR = float(sys.argv[2]) if len(sys.argv) > 2 else 25.0
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(7)
L = np.zeros(N); R = np.zeros(N)

def hz(m): return 440.0 * 2 ** ((m - 69) / 12)

def add(sig, start, pan=0.0, gain=1.0):
    i = int(start * SR); j = min(N, i + len(sig))
    if j <= i: return
    s = sig[: j - i] * gain
    L[i:j] += s * np.sqrt((1 - pan) / 2); R[i:j] += s * np.sqrt((1 + pan) / 2)

def pad(notes, start, length, gain):
    n = int(length * SR); tt = np.arange(n) / SR
    env = np.minimum(1, tt / 1.6) * np.minimum(1, (length - tt) / 1.8).clip(0)
    sig = np.zeros(n)
    for m in notes:
        f = hz(m)
        for d in (-0.12, 0.0, 0.13):
            ff = f * 2 ** (d / 12)
            sig += np.sin(2 * np.pi * ff * tt + rng.uniform(0, 6)) + 0.18 * np.sin(4 * np.pi * ff * tt)
    sig *= env * (1 + 0.08 * np.sin(2 * np.pi * 0.25 * tt))
    add(sig / (len(notes) * 3), start, rng.uniform(-.3, .3), gain)

def pluck(m, start, gain=0.22, pan=0.0, decay=1.6):
    n = int(3.0 * SR); tt = np.arange(n) / SR; f = hz(m)
    env = (1 - np.exp(-tt * 300)) * np.exp(-tt * decay)
    sig = (np.sin(2*np.pi*f*tt) + .35*np.sin(4*np.pi*f*tt)*np.exp(-tt*3) + .12*np.sin(6*np.pi*f*tt)*np.exp(-tt*5)) * env
    add(sig, start, pan, gain)

def bell(m, start, gain=0.25):
    n = int(4 * SR); tt = np.arange(n) / SR; f = hz(m); sig = np.zeros(n)
    for r, a, d in ((1, 1, 1.2), (2.76, .5, 2.2), (5.4, .25, 3.5), (8.9, .12, 5)):
        sig += a * np.sin(2*np.pi*f*r*tt) * np.exp(-tt*d)
    add(sig * (1 - np.exp(-tt*400)), start, 0.1, gain)

def whoosh(start, length=0.7, gain=0.12):
    n = int(length * SR); tt = np.arange(n) / SR
    noise = rng.standard_normal(n)
    # passe-bande grossier : différence de deux moyennes glissantes
    k1, k2 = 6, 60
    a = np.convolve(noise, np.ones(k1)/k1, 'same') - np.convolve(noise, np.ones(k2)/k2, 'same')
    env = np.sin(np.pi * tt / length) ** 2
    add(a * env, start, 0.0, gain)

def drop(start, gain=0.2):
    n = int(0.35 * SR); tt = np.arange(n) / SR
    f = 900 * np.exp(-tt * 9) + 500
    sig = np.sin(2*np.pi*np.cumsum(f)/SR) * np.exp(-tt*14)
    add(sig, start, -0.2, gain)

# Grille d'accords (fa majeur, doux) : Fmaj9 · Am7 · Dm9 · Bbmaj9 · Fmaj9
K = DUR / 25.0          # la version courte compresse la grille
END = DUR - 4.8         # moment de la résolution (packshot)
chords = [
    (0.0,  [53, 57, 60, 64, 67]),
    (6.0*K,  [57, 60, 64, 67]),
    (11.5*K, [50, 57, 60, 64, 65]),
    (16.0*K, [46, 57, 60, 62, 65]),
    (END, [41, 53, 57, 60, 64, 67]),
]
for k, (s, ns) in enumerate(chords):
    e = chords[k+1][0] + 1.5 if k + 1 < len(chords) else DUR
    pad(ns, max(0, s - 0.6), e - max(0, s - 0.6), 0.55)
    add(np.sin(2*np.pi*hz(ns[0]-12)*np.arange(int((e-s)*SR))/SR) * np.minimum(1, np.arange(int((e-s)*SR))/SR/1.0)
        * np.clip((e - s - np.arange(int((e-s)*SR))/SR)/1.2, 0, 1), s, 0, 0.10)

# Arpèges doux, ~72 BPM en croches
beat = 60 / 72 / 2
arp = {0: [72, 76, 79, 81, 79, 76], 1: [72, 76, 79, 76, 74, 76], 2: [74, 77, 81, 76, 77, 72], 3: [74, 77, 81, 77, 74, 70], 4: [72, 76, 79, 84]}
pluck(76, 0.0, 0.30, 0.0, 1.0)            # attaque immédiate du hook
pluck(81, 0.05, 0.12, 0.3, 1.0)
x = 1.2
while x < DUR - 3.5:
    ci = max(i for i, (s, _) in enumerate(chords) if s <= x)
    pat = arp[ci]; m = pat[int(round(x / beat)) % len(pat)]
    if ci < 4 and rng.random() > 0.18:
        pluck(m, x, 0.15 + 0.05 * rng.random(), rng.uniform(-.5, .5))
    x += beat
for i, m in enumerate([72, 76, 79, 84]):      # résolution finale
    pluck(m, END + 0.05 + i * 0.32, 0.2, -.3 + .2 * i, 0.8)

# Bruitages
import json
for s in json.loads(sys.argv[3]): whoosh(s - 0.35, 0.6, 0.10)
drop(float(sys.argv[4]), 0.18)
bell(84, END + 0.05, 0.18); bell(91, END + 0.15, 0.06)

# Réverbération légère (lignes de retard croisées)
for d, g in ((0.113, .30), (0.237, .22), (0.371, .16), (0.523, .11)):
    k = int(d * SR)
    L2 = L.copy(); R2 = R.copy()
    L[k:] += R2[:-k] * g; R[k:] += L2[:-k] * g

# Fondu de sortie, normalisation
fade = np.clip((DUR - t) / 1.2, 0, 1); L *= fade; R *= fade
st = np.stack([L, R], 1); st /= np.abs(st).max() / 0.85
with wave.open(sys.argv[1], 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype('<i2').tobytes())
