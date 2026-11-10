"""Original phone-style sounds (not Apple's): text received, text sent, notification."""
import numpy as np, soundfile as sf
SR = 48000
def tone(f, dur, decay, partials=((1, 1), (2.76, .35), (5.4, .12))):  # marimba-like bar partials
    t = np.arange(int(dur * SR)) / SR
    x = sum(a * np.sin(2*np.pi*f*m*t) * np.exp(-t / (decay / m**0.5)) for m, a in partials)
    return x * np.minimum(1, t / 0.0015)
def place(parts, total):
    out = np.zeros(int(total * SR))
    for start, x in parts:
        i = int(start * SR); out[i:i+len(x)] += x[:len(out)-i]
    return out
def save(name, x, gain):
    x = x / np.abs(x).max() * gain
    sf.write(f"{name}.wav", np.stack([x, x], 1).astype(np.float32), SR)
# text received: two quick rising bar notes (E6 -> B6)
save("msg_in", place([(0, tone(1318.5, .45, .16)), (0.085, tone(1975.5, .55, .2))], .65), .55)
# text sent: soft pitched "bloop" sliding up, with a breathy tail
t = np.arange(int(.22 * SR)) / SR
f = 520 + 900 * (t / t[-1]) ** 0.6
bloop = np.sin(2*np.pi*np.cumsum(f)/SR) * np.exp(-t / .06) * np.minimum(1, t / .003)
noise = np.convolve(np.random.default_rng(3).standard_normal(len(t)), np.ones(30)/30, "same") * np.exp(-t/.03) * .25
save("msg_out", bloop + noise, .5)
# notification: glassy two-note "ding-ding" (A6 then D7), softer and longer
save("notify", place([(0, tone(1760, .8, .3, ((1,1),(3,.2),(4.2,.08)))), (0.13, tone(2349.3, 1.0, .38, ((1,1),(3,.2),(4.2,.08))))], 1.2), .5)
print("ok")
