"""Kokoro per-line TTS (run with the Kokoro venv python, ~/kokoro-venv). Usage: tts.py lines.json outdir voice speed
lines.json = ["line one", "line two", ...]. Writes outdir/line_NN.wav (24 kHz mono, silence trimmed) + durations.json."""
import sys, json, os, wave, numpy as np
from mlx_audio.tts.utils import load_model
lines, out, voice, speed = json.load(open(sys.argv[1])), sys.argv[2], sys.argv[3], float(sys.argv[4])
os.makedirs(out, exist_ok=True)
model = load_model("mlx-community/Kokoro-82M-bf16"); durs = []
for i, text in enumerate(lines):
    a = np.concatenate([np.array(r.audio, dtype=np.float32).reshape(-1) for r in model.generate(text=text, voice=voice, lang_code=voice[0], speed=speed)])
    env = np.abs(a) > 0.01; idx = np.where(env)[0]
    s, e = (max(0, idx[0] - 240), min(len(a), idx[-1] + 700)) if len(idx) else (0, len(a))
    a = a[s:e]
    with wave.open(os.path.join(out, f"line_{i:02d}.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())
    durs.append(len(a) / 24000); print(i, round(durs[-1], 2), text, flush=True)
json.dump(durs, open(os.path.join(out, "durations.json"), "w"))
