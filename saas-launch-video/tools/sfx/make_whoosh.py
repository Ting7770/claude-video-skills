"""Smooth airy swoosh: pink-ish noise through a sweeping resonant low-pass, soft swell, plus a faint low tonal sweep."""
import numpy as np, soundfile as sf
SR = 48000; D = 0.55; n = int(D * SR); t = np.arange(n) / SR
rng = np.random.default_rng(11)
white = rng.standard_normal(n)
b = np.zeros(n); acc = 0.0                       # gentle pink-ish tilt
for i in range(n): acc = 0.97 * acc + 0.03 * white[i]; b[i] = acc
cut = 250 + 2600 * np.sin(np.pi * t / D) ** 2     # cutoff rises then falls with the swell
y = np.zeros(n); y1 = y2 = 0.0
for i in range(n):                                # 2-pole resonant low-pass, time-varying
    w = 2 * np.pi * cut[i] / SR; a = min(0.99, w); r = 0.35
    y0 = y1 + a * (b[i] - y1) + r * (y1 - y2); y2, y1 = y1, y0; y[i] = y0
env = np.sin(np.pi * np.clip(t / D, 0, 1)) ** 1.6
tonal = np.sin(2 * np.pi * np.cumsum(180 + 220 * (t / D)) / SR) * 0.12
x = (y / (np.abs(y).max() + 1e-9) + tonal) * env
x = x / np.abs(x).max() * 0.45
# slight stereo motion left to right
pan = t / D
sf.write("whoosh.wav", np.stack([x * (1.1 - 0.6 * pan), x * (0.5 + 0.6 * pan)], 1).astype(np.float32), SR)
print("ok")
