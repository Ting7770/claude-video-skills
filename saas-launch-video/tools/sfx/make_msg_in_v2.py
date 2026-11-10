"""msg_in v2: snappier, glassier text-received sound in the iPhone style (original, not Apple's)."""
import numpy as np, soundfile as sf
SR = 48000
def blip(f0, f1, dur, decay, bright=0.35):
    t = np.arange(int(dur * SR)) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.012)              # tiny upward/downward glide into the note
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) + bright * np.sin(2 * ph) + 0.12 * np.sin(3.01 * ph)
    return x * np.exp(-t / decay) * np.minimum(1, t / 0.0008)
out = np.zeros(int(0.42 * SR))
a = blip(1100, 1480, 0.20, 0.045)                      # first glassy blip
b = blip(1700, 1975, 0.32, 0.075, 0.28)                # brighter answer, a touch longer
out[:len(a)] += a; i = int(0.072 * SR); out[i:i+len(b)] += b[:len(out)-i]
click = np.random.default_rng(5).standard_normal(int(0.004 * SR)) * 0.25   # soft tap transient
out[:len(click)] += click
out = out / np.abs(out).max() * 0.55
sf.write("msg_in.wav", np.stack([out, out], 1).astype(np.float32), SR)
print("ok")
