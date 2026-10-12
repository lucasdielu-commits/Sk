"""Musique originale pour « Elle s'était oubliée » : piano seul, puis nappe, puis ampleur, résolution.

Usage : python3 music_story.py sortie.wav '<json>'
json = {"dur": 39, "pad": 5.6, "arp": 11, "full": 16.5, "end": 32, "cuts": [..]}
"""
import json, sys, wave
import numpy as np

SR = 44100
P = json.loads(sys.argv[2]); DUR = P["dur"]; N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(11)
L = np.zeros(N); R = np.zeros(N)

def hz(m): return 440.0 * 2 ** ((m - 69) / 12)

def add(sig, start, pan=0.0, gain=1.0):
    i = int(start * SR); j = min(N, i + len(sig))
    if j <= i or i < 0: return
    s = sig[: j - i] * gain
    L[i:j] += s * np.sqrt((1 - pan) / 2); R[i:j] += s * np.sqrt((1 + pan) / 2)

def piano(m, start, gain=0.25, pan=0.0, decay=1.1):
    n = int(4.0 * SR); tt = np.arange(n) / SR; f = hz(m)
    env = (1 - np.exp(-tt * 250)) * np.exp(-tt * decay)
    sig = (np.sin(2*np.pi*f*tt) + .45*np.sin(4*np.pi*f*tt)*np.exp(-tt*2.5)
           + .2*np.sin(6*np.pi*f*tt)*np.exp(-tt*4) + .08*np.sin(8*np.pi*f*tt)*np.exp(-tt*6)) * env
    add(sig, start, pan, gain)

def pad(notes, start, length, gain, attack=2.0):
    n = int(length * SR); tt = np.arange(n) / SR
    env = np.minimum(1, tt / attack) * np.clip((length - tt) / 2.0, 0, 1)
    sig = np.zeros(n)
    for m in notes:
        for d in (-0.1, 0.0, 0.11):
            ff = hz(m) * 2 ** (d / 12)
            sig += np.sin(2*np.pi*ff*tt + rng.uniform(0, 6)) + 0.15*np.sin(4*np.pi*ff*tt)
    add(sig * env / (len(notes) * 3), start, rng.uniform(-.25, .25), gain)

def bell(m, start, gain):
    n = int(5 * SR); tt = np.arange(n) / SR; sig = np.zeros(n)
    for r, a, d in ((1, 1, 1.0), (2.76, .45, 2.0), (5.4, .2, 3.2), (8.9, .1, 4.5)):
        sig += a * np.sin(2*np.pi*hz(m)*r*tt) * np.exp(-tt*d)
    add(sig * (1 - np.exp(-tt*400)), start, 0.1, gain)

def swell(start, length, gain):
    n = int(length * SR); tt = np.arange(n) / SR
    noise = rng.standard_normal(n)
    a = np.convolve(noise, np.ones(8)/8, 'same') - np.convolve(noise, np.ones(80)/80, 'same')
    add(a * (tt / length) ** 2 * np.clip((length - tt) / 0.15, 0, 1), start, 0, gain)

# Progression en ré mineur → fa majeur : mélancolie qui s'ouvre
prog = [[50, 57, 60, 65], [46, 53, 57, 62], [41, 53, 57, 60], [48, 55, 60, 64]]   # Dm Bb F C
END = P["end"]; step = 60 / 66 * 2          # une blanche à 66 BPM
# 1. piano seul, très clairsemé
mel = [69, 65, 67, 64, 65, 62, 64, 60]
x = 0.0; k = 0
while x < P["pad"] + 0.5:
    piano(mel[k % len(mel)], x, 0.22, -0.1 + 0.2 * (k % 2), 0.9); x += step * 0.9; k += 1
# 2. nappe + basse
x = P["pad"]; c = 0
while x < END:
    ch = prog[c % 4]; g = 0.35 if x < P["full"] else 0.6
    pad(ch, x - 0.3, step * 2 + 1.5, g)
    add(np.sin(2*np.pi*hz(ch[0]-12)*np.arange(int(step*2*SR))/SR) * np.clip(np.arange(int(step*2*SR))/SR/0.8, 0, 1)
        * np.clip((step*2 - np.arange(int(step*2*SR))/SR)/0.6, 0, 1), x, 0, 0.08 if x < P["full"] else 0.13)
    x += step * 2; c += 1
# 3. arpèges au piano, plus denses à partir de "full"
x = P["arp"]
while x < END - 0.2:
    c = int((x - P["pad"]) // (step * 2)) % 4; ch = prog[c]
    tones = [ch[1] + 12, ch[2] + 12, ch[3] + 12, ch[2] + 24 - 12]
    sub = 4 if x >= P["full"] else 2
    for s in range(sub):
        if rng.random() > 0.15:
            piano(tones[(s + int(x)) % 4], x + s * step / sub, 0.12 + 0.06 * (x >= P["full"]), rng.uniform(-.5, .5), 1.4)
    x += step
# 4. montée puis résolution sur fa majeur
swell(END - 1.6, 1.6, 0.05)
pad([41, 53, 57, 60, 64, 69], END, DUR - END, 0.7, attack=0.4)
for i, m in enumerate([65, 69, 72, 77]): piano(m, END + 0.05 + i * 0.28, 0.24, -.3 + .2 * i, 0.7)
bell(84, END + 0.1, 0.16); bell(89, END + 1.3, 0.06)
# transitions : souffles très légers
for s in P.get("cuts", []): swell(s - 0.5, 0.6, 0.025)
# ambiance de pièce, au tout début
amb = np.convolve(rng.standard_normal(int(6 * SR)), np.ones(200)/200, 'same')
add(amb * np.clip((6 - np.arange(len(amb))/SR)/2, 0, 1) * 2.0, 0, 0, 0.6)

for d, g in ((0.127, .32), (0.251, .24), (0.389, .17), (0.557, .12), (0.733, .08)):
    k = int(d * SR); L2 = L.copy(); R2 = R.copy()
    L[k:] += R2[:-k] * g; R[k:] += L2[:-k] * g
L *= np.clip((DUR - t) / 1.5, 0, 1); R *= np.clip((DUR - t) / 1.5, 0, 1)
L *= np.clip(t / 0.05, 0, 1); R *= np.clip(t / 0.05, 0, 1)
st = np.stack([L, R], 1); st /= np.abs(st).max() / 0.85
with wave.open(sys.argv[1], 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype('<i2').tobytes())
