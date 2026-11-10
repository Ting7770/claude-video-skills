"""Clean procedural music bed (no samples, no AI): pads, pluck arpeggio, sub bass, soft drums.
Usage: python compose.py <out.wav> <key_root_midi> <bpm> <style: air|tech> [seconds]"""
import sys, numpy as np, soundfile as sf
SR = 48000
out_path, root, bpm, style = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
DUR = float(sys.argv[5]) if len(sys.argv) > 5 else 30.0
N = int(DUR * SR); beat = 60 / bpm; bar = 4 * beat
rng = np.random.default_rng(3)
def hz(m): return 440 * 2 ** ((m - 69) / 12)
def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR); y = np.zeros_like(x); acc = 0.0
    for i in range(len(x)): acc = (1 - a) * x[i] + a * acc; y[i] = acc
    return y
def adsr(n, a, d, s, r):
    e = np.ones(n) * s; A = int(a*SR); D = int(d*SR); R = int(r*SR)
    e[:A] = np.linspace(0, 1, A); e[A:A+D] = np.linspace(1, s, D)[:max(0, min(D, n-A))]
    if R: e[-R:] *= np.linspace(1, 0, R)
    return e
def saw(f, n, detune=0.0):
    t = np.arange(n) / SR; x = 0
    for d in (-detune, 0, detune):
        x = x + 2 * ((t * f * (1 + d)) % 1) - 1
    return x / 3
mix = np.zeros((N, 2))
def add(x, start, gain, pan=0.0):
    i = int(start * SR); x = x[: max(0, N - i)]
    mix[i:i+len(x), 0] += x * gain * (1 - pan) ; mix[i:i+len(x), 1] += x * gain * (1 + pan)
# progression: I - V - vi - IV  (airy) or vi - IV - I - V (tech)
prog = [(0, 4, 7), (7, 11, 14), (9, 12, 16), (5, 9, 12)] if style == "air" else [(9, 12, 16), (5, 9, 12), (0, 4, 7), (7, 11, 14)]
bars = int(np.ceil(DUR / bar))
for b in range(bars):
    t0 = b * bar; ch = prog[b % 4]; n = int(bar * SR) + int(0.6 * SR)
    # warm pad (detuned saws, low-passed, slow attack)
    pad = sum(saw(hz(root + 12 + c), n, 0.004) for c in ch)
    pad = lowpass(pad, 1400 if style == "air" else 1100) * adsr(n, 0.6, 0.4, 0.8, 0.6)
    add(pad, t0, 0.10)
    # sub bass on the root, quarter-note pulse in the middle section
    for q in range(4):
        tq = t0 + q * beat; m = int(beat * SR)
        sub = np.sin(2 * np.pi * hz(root - 12 + ch[0]) * np.arange(m) / SR) * adsr(m, 0.005, 0.2, 0.6, 0.08)
        if 4.0 < tq < DUR - 3.5: add(sub, tq, 0.18)
    # pluck arpeggio (8ths), enters after the hook
    arp = [ch[0], ch[1], ch[2], ch[1] + 12, ch[2], ch[1], ch[0] + 12, ch[2]]
    for k, c in enumerate(arp):
        tk = t0 + k * beat / 2
        if tk < 3.6 or tk > DUR - 1.2: continue
        m = int(0.35 * SR); f = hz(root + 24 + c)
        pl = (np.sin(2*np.pi*f*np.arange(m)/SR) + 0.3*np.sin(4*np.pi*f*np.arange(m)/SR)) * np.exp(-np.arange(m)/SR/0.09)
        add(pl, tk, 0.07, pan=0.35 if k % 2 else -0.35)
# drums: soft kick on 1 and 3, light clap on 2 and 4, closed hat 8ths (middle section only)
kick_n = int(0.3 * SR); kt = np.arange(kick_n) / SR
kick = np.sin(2 * np.pi * np.cumsum(50 + 90 * np.exp(-kt / 0.03)) / SR) * np.exp(-kt / 0.12)
clap = lowpass(rng.standard_normal(int(0.2 * SR)), 2500) * np.exp(-np.arange(int(0.2*SR)) / SR / 0.05)
hat = rng.standard_normal(int(0.05 * SR)); hat = (hat - lowpass(hat, 6000)) * np.exp(-np.arange(len(hat)) / SR / 0.012)
t = 0.0; step = beat / 2; k = 0
while t < DUR:
    if 7.0 < t < DUR - 3.0:
        if k % 4 == 0: add(kick, t, 0.55)
        if k % 4 == 2: add(clap, t, 0.12)
        add(hat, t, 0.05, pan=0.2)
    t += step; k += 1
# simple stereo reverb (feedback delays) and gentle master
wet = np.zeros_like(mix)
for d, g in ((0.031, .35), (0.047, .3), (0.071, .25), (0.113, .2)):
    s = int(d * SR); w = np.zeros_like(mix)
    for i in range(s, N, s): w[i:i+s] += (mix[i-s:i] + w[i-s:i] * g)[: min(s, N - i)] * g
    wet += w
mix = mix + 0.35 * wet
fade = np.ones(N); fi = int(1.2 * SR); fo = int(2.0 * SR)
fade[:fi] = np.linspace(0, 1, fi); fade[-fo:] = np.linspace(1, 0, fo)
mix *= fade[:, None]
mix = np.tanh(mix / np.abs(mix).max() * 1.6) * 0.8
sf.write(out_path, mix.astype(np.float32), SR); print("wrote", out_path)
