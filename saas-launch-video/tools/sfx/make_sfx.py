"""Synthesised UI sound kit (no samples, no licences): click, pop, whoosh, ding, tick, type."""
import numpy as np, soundfile as sf
SR = 48000
def env(n, a=0.002, r=0.08):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / r)
def save(name, x, gain=0.8):
    x = x / (np.abs(x).max() + 1e-9) * gain
    sf.write(f"{name}.wav", np.stack([x, x], 1).astype(np.float32), SR)
rng = np.random.default_rng(7)
def lp(x, k):  # simple low-pass
    return np.convolve(x, np.ones(k) / k, mode="same")
# click: short bright noise burst + body thump
n = int(0.05 * SR); t = np.arange(n) / SR
click = lp(rng.standard_normal(n), 3) * env(n, 0.0005, 0.006) + 0.6 * np.sin(2*np.pi*1800*t) * env(n, 0.0005, 0.01)
save("click", click, 0.7)
# pop: sine blip with a fast pitch drop
n = int(0.18 * SR); t = np.arange(n) / SR
f = 900 * np.exp(-t * 18) + 280
pop = np.sin(2*np.pi*np.cumsum(f)/SR) * env(n, 0.002, 0.05)
save("pop", pop, 0.6)
# whoosh: band-limited noise swelling then fading, slight stereo-free sweep
n = int(0.7 * SR); t = np.arange(n) / SR
noise = rng.standard_normal(n)
sweep = np.zeros(n); k = 3
for i in range(0, n, 2400):  # time-varying smoothing = moving cutoff
    k = int(40 - 34 * np.sin(np.pi * i / n)); sweep[i:i+2400] = lp(noise[max(0,i-200):i+2600], max(2,k))[200:2600][:len(sweep[i:i+2400])]
whoosh = sweep * np.sin(np.pi * t / t[-1]) ** 2
save("whoosh", whoosh, 0.5)
# ding: soft two-partial bell
n = int(0.9 * SR); t = np.arange(n) / SR
ding = (np.sin(2*np.pi*1320*t) + 0.5*np.sin(2*np.pi*1980*t) + 0.25*np.sin(2*np.pi*2640*t)) * env(n, 0.003, 0.25)
save("ding", ding, 0.5)
# tick: tiny high tick for counters and typing
n = int(0.025 * SR); t = np.arange(n) / SR
tick = np.sin(2*np.pi*3200*t) * env(n, 0.0003, 0.004)
save("tick", tick, 0.45)
print("ok")
