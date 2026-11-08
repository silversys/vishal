"""Generate the reel's soundtrack (27 s, 44.1 kHz stereo WAV) with numpy only.

Layers: tanpura drone, bansuri-style melody, dholak (keherwa taal),
temple bells on scene changes, coin chimes, and cracker sounds whose
timing is read from the reel's firework schedule (fireworks.json).

usage: python3 soundtrack.py fireworks.json out.wav [hero_seconds]

fireworks.json times are absolute (video time); everything else is
scheduled on the story timeline and shifted by hero_seconds.
"""
import json
import sys
import wave

import numpy as np

SR = 44100
OFF = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0  # title-screen length
DUR = 27.0 + OFF
N = int(SR * DUR)
rng = np.random.default_rng(7)
SA = 146.83  # D3 as "Sa"

mix = np.zeros((N, 2))


def add(sig, t0, gain=1.0, pan=0.0):
    i = int(t0 * SR)
    if i < 0:
        sig, i = sig[-i:], 0
    if i >= N:
        return
    sig = sig[: N - i]
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    mix[i:i + len(sig), 0] += sig * gain * l * 1.414
    mix[i:i + len(sig), 1] += sig * gain * r * 1.414


def tt(d):
    return np.arange(int(d * SR)) / SR


def lowpass(x, fc):
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def semis(s, base=SA):
    return base * 2 ** (s / 12)


# ---------- tanpura ----------
def tanpura_pluck(f, d=3.2):
    t = tt(d)
    env = np.exp(-t / 1.4) * np.minimum(1, t / 0.01)
    s = np.zeros_like(t)
    for n in range(1, 16):
        amp = (1 / n) * (1 + 0.5 * np.sin(n))  # bright "jawari" spectrum
        s += amp * np.sin(2 * np.pi * f * n * t * (1 + 0.0007 * n) + n)
    return s * env


cycle = [(semis(-5), 0.0), (semis(0), 0.6), (semis(0), 1.2), (semis(-12), 1.8)]
t0 = 0.0
while t0 < DUR:
    for f, off in cycle:
        add(tanpura_pluck(f), t0 + off, 0.05, pan=-0.3 if f < SA else 0.3)
    t0 += 2.4


# ---------- temple bell ----------
def bell(f=880, d=3.5):
    t = tt(d)
    s = np.zeros_like(t)
    for ratio, amp, dec in [(1, 1, 1.6), (2.0, .6, 1.1), (2.76, .5, .8), (5.4, .3, .45), (8.93, .2, .3)]:
        s += amp * np.sin(2 * np.pi * f * ratio * t) * np.exp(-t / dec)
    return s * np.minimum(1, t / 0.002)


for tb in [0.15] + [OFF + x for x in [0.15, 4.6, 10.6, 15.6, 20.6]][1 if OFF == 0 else 0:]:
    add(bell(), tb, 0.10, pan=0.15)


# ---------- bansuri melody ----------
def flute(f, d):
    t = tt(d)
    vib = 1 + 0.006 * np.sin(2 * np.pi * 5.2 * t) * np.minimum(1, t / 0.25)
    ph = 2 * np.pi * np.cumsum(f * vib) / SR
    s = np.sin(ph) + 0.28 * np.sin(2 * ph) + 0.08 * np.sin(3 * ph)
    s += 0.05 * rng.standard_normal(len(t))  # breath
    env = np.minimum(1, t / 0.07) * np.minimum(1, (d - t) / 0.12)
    return s * np.clip(env, 0, 1)


# notes as (semitones above Sa4, beats); one beat = 0.3 s
B = 0.3
phrases = ([(-OFF + 0.25, [(0, 1), (4, 1), (7, 1), (12, 3)])] if OFF >= 1.8 else []) + [
    (0.4, [(0, 2), (2, 1), (4, 1), (7, 3), (9, 1), (7, 2), (4, 2), (2, 1), (4, 1), (0, 4)]),
    (4.9, [(7, 1), (9, 1), (11, 1), (12, 3), (11, 1), (9, 1), (7, 2), (9, 1), (7, 1), (4, 2), (2, 2), (4, 4),
           (4, 1), (7, 1), (9, 2), (7, 1), (9, 1), (12, 4)]),
    (10.9, [(12, 2), (14, 1), (12, 1), (11, 2), (9, 2), (7, 1), (9, 1), (11, 1), (12, 1), (9, 4),
            (7, 1), (9, 1), (7, 1), (4, 1), (2, 2), (4, 2), (0, 4)]),
    (15.8, [(0, 1), (4, 1), (7, 1), (12, 1), (11, 1), (12, 1), (14, 2), (12, 1), (11, 1), (9, 2), (7, 2),
            (9, 1), (11, 1), (12, 2), (7, 2), (4, 2), (7, 2)]),
    (21.0, [(12, 3), (11, 1), (12, 2), (14, 2), (16, 3), (14, 1), (12, 2), (11, 2), (9, 2), (7, 2),
            (9, 1), (11, 1), (12, 4), (7, 2), (12, 6)]),
]
for start, notes in phrases:
    t = start + OFF
    for s, beats in notes:
        add(flute(semis(s + 12), beats * B), t, 0.11, pan=0.1)
        t += beats * B


# ---------- dholak (keherwa: dha ge na ti | na ka dhi na) ----------
def dhol_low(d=0.35):
    t = tt(d)
    f = 70 + 60 * np.exp(-t / 0.04)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)


def dhol_high(f=520, d=0.18):
    t = tt(d)
    return (np.sin(2 * np.pi * f * t) * 0.7 + 0.5 * rng.standard_normal(len(t)) * np.exp(-t / 0.01)) * np.exp(-t / 0.05)


pattern = ['LH', 'L', 'H', 'h', 'H', 'h', 'LH', 'H']
t = 4.6 + OFF
i = 0
while t < DUR - 1.2:
    g = 0.16 if t < 15.6 + OFF else 0.24
    for c in pattern[i % 8]:
        if c == 'L':
            add(dhol_low(), t, g * 1.2, pan=-0.1)
        elif c == 'H':
            add(dhol_high(), t, g * 0.55, pan=0.2)
        else:
            add(dhol_high(820, .1), t, g * 0.35, pan=0.25)
    t += B
    i += 1


# ---------- coin chimes (Laxmi scene) ----------
def ping(f, d=0.6):
    t = tt(d)
    return (np.sin(2 * np.pi * f * t) + .4 * np.sin(2 * np.pi * f * 2.7 * t)) * np.exp(-t / 0.15)


for _ in range(38):
    add(ping(rng.uniform(2200, 4200)), OFF + rng.uniform(11.0, 15.2), 0.035, pan=rng.uniform(-.8, .8))


# ---------- crackers ----------
def whistle(d=0.8):
    t = tt(d)
    f = 900 + 1700 * (t / d) ** 1.4
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(1, t / 0.1) * (1 - t / d) ** .3


def boom(d=1.8):
    t = tt(d)
    nz = rng.standard_normal(len(t))
    low = lowpass(nz, 180) * np.exp(-t / 0.35) * 6
    crack = np.zeros_like(t)
    for _ in range(70):  # crackle
        c = int(rng.uniform(0.25, 1.6) * SR)
        ln = int(0.006 * SR)
        if c + ln < len(t):
            crack[c:c + ln] += rng.standard_normal(ln) * np.exp(-np.arange(ln) / 60) * rng.uniform(.2, .7)
    return low + crack * 0.6


fw = json.load(open(sys.argv[1]))
for f in fw:
    pan = (f['x'] - 540) / 600
    add(whistle(), f['t'] - 0.85, 0.035, pan)
    add(boom(), f['t'], 0.35, pan)

# anaar (fountain) hiss
for x, a, b in [(165, 16.4, 20.3), (915, 16.7, 20.3)]:
    d = b - a + 1.0
    t = tt(d)
    nz = rng.standard_normal(len(t))
    hiss = (nz - lowpass(nz, 2500)) * np.minimum(1, t / .3) * np.clip((d - t) / 1.0, 0, 1)
    add(hiss, a + OFF, 0.05, (x - 540) / 600)

# ---------- master ----------
tm = np.arange(N) / SR
mix *= np.minimum(1, tm / 0.4)[:, None] * np.clip((DUR - tm) / 1.5, 0, 1)[:, None]
mix = np.tanh(mix * 1.2)
mix /= np.max(np.abs(mix)) / 0.89
pcm = (mix * 32767).astype('<i2')
with wave.open(sys.argv[2], 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print('wrote', sys.argv[2])
