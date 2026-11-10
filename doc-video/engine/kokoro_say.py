"""Read a script aloud with Kokoro. Usage: python kokoro_say.py <script.md> <out.wav> <voice> <speed>
Narration = every section after the first '---' rule, up to a '## Sources' section; quotes kept, `[...]` cue lines and headings skipped; blank line = 0.7 s pause."""
import re, sys, wave, numpy as np
from mlx_audio.tts.utils import load_model
src, out, voice, speed = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
parts = open(src, encoding="utf-8").read().split("\n---\n")[1:]
body = "\n\n".join(p for p in parts[: next((i for i, p in enumerate(parts) if "## Sources" in p), len(parts))])
paras = [p.strip() for p in body.split("\n\n") if p.strip() and not p.strip().startswith(("`", "#", "✂", "**"))]
model = load_model("mlx-community/Kokoro-82M-bf16"); gap = np.zeros(int(24000 * 0.7), dtype=np.float32); parts = []
for p in paras:
    parts += [np.concatenate([np.array(r.audio) for r in model.generate(text=p, voice=voice, lang_code=voice[0], speed=speed)]), gap]
pcm = (np.clip(np.concatenate(parts), -1, 1) * 32767).astype(np.int16)
with wave.open(out, "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm.tobytes())
print(out, round(len(pcm) / 24000, 1), "s")
