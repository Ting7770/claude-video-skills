#!/usr/bin/env python3
"""toon-short: script.md -> finished vertical Short (1080x1920, 30 fps), <10 MB upload copy, upload.md, contact sheet.
Usage: python3 make_short.py <path/to/script.md> [--only N,M] [--draft] [--jobs 1] [--scale 75]
Everything is local and free: Kokoro (voice), Blender EEVEE (3D), PIL (captions), numpy (music + sfx), ffmpeg."""
import argparse, hashlib, json, os, re, subprocess, sys, time, wave, shutil, math, random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
BLENDER = "/opt/homebrew/bin/blender"
KOKORO_PY = os.environ.get("TOON_TTS_PY", os.path.expanduser("~/kokoro-venv/bin/python"))
FPS, W, H = 30, 1080, 1920
XF = 6            # crossfade frames between shots
GAP = 0.07        # seconds of air between narration lines (nonstop feel)
TAIL = 0.25       # seconds after the last word (abrupt ending that loops)
FONT = "/System/Library/Fonts/Supplemental/Arial Black.ttf"
ORANGE, WHITE, INK = (247, 150, 40), (255, 255, 255), (14, 10, 22)

def sh(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode: sys.exit(f"FAILED: {' '.join(map(str, cmd))[:300]}\n{r.stderr[-2500:]}")
    return r

# ------------------------------------------------------------------ script parsing
SPLIT = re.compile(r"\{([^|}]+)\|([^}]+)\}")

def parse(path):
    raw = Path(path).read_text(encoding="utf-8")
    head, body = raw.split("\n---\n", 1)
    body = body.split("\n---\n")[0]
    meta = {}
    for ln in head.splitlines():
        m = re.match(r"^([a-z_]+):\s*(.+)$", ln.strip())
        if m: meta[m.group(1)] = m.group(2).strip()
    meta["sources"] = raw.split("## Sources", 1)[1].split("\n## ")[0].strip() if "## Sources" in raw else ""
    lines = []
    for blk in [b.strip() for b in body.split("\n\n") if b.strip()]:
        m = re.match(r"^\[(.+?)\]\s*\n(.+)$", blk, re.S)
        if not m: continue
        parts = [p.strip() for p in m.group(1).split("|")]
        # scene[:args][.view]; args is a cast name (studio:gus) or key=val;key=val (moon:who=al,ed;lm=back)
        scene, _, view = parts[0].rpartition(".")
        if not scene or not re.fullmatch(r"[a-z0-9_]+", view): scene, view = parts[0], ""
        scene, _, who = scene.partition(":")
        sargs = {}
        for seg in [x for x in who.split(";") if x]:
            k, eq, v = seg.partition("=")
            if eq: sargs[k] = v
            else: sargs["who"] = seg
        acts = []
        for a in [x.strip() for x in (parts[2] if len(parts) > 2 else "").split(",") if x.strip()]:
            name, _, when = a.partition("@"); name, _, arg = name.partition(":")
            s, _, e = (when or "0-1").partition("-")
            acts.append([name, arg or None, float(s or 0), float(e or 1)])
        text = " ".join(m.group(2).split())
        lines.append(dict(scene=scene, scene_args=sargs, view=view or None, cam=parts[1] if len(parts) > 1 else "push_in", actions=acts,
                          say=SPLIT.sub(lambda x: x.group(1), text), cap=SPLIT.sub(lambda x: x.group(2), text)))
    return meta, lines

# ------------------------------------------------------------------ voice
def voice(lines, meta, vo_dir):
    v, sp = (meta.get("voice", "bm_george 1.0").split() + ["1.0"])[:2]
    says = [l["say"] for l in lines]
    tag = hashlib.md5(json.dumps([says, v, sp]).encode()).hexdigest()[:10]
    stamp = vo_dir / "tag.txt"
    if not (stamp.exists() and stamp.read_text() == tag and (vo_dir / "durations.json").exists()):
        vo_dir.mkdir(parents=True, exist_ok=True)
        (vo_dir / "lines.json").write_text(json.dumps(says, ensure_ascii=False))
        print("voice: Kokoro", v, sp, flush=True)
        r = subprocess.run([KOKORO_PY, str(HERE / "tts.py"), str(vo_dir / "lines.json"), str(vo_dir), v, sp])
        if r.returncode: sys.exit("TTS failed")
        stamp.write_text(tag)
    return json.loads((vo_dir / "durations.json").read_text())

# ------------------------------------------------------------------ timeline
def timeline(lines, durs):
    t = 0.0; out = []
    for i, (l, d) in enumerate(zip(lines, durs)):
        last = i == len(lines) - 1
        seg = d + (TAIL if last else GAP)
        out.append(dict(start=t, speech=d, seg=seg)); t += seg
    # snap to frames
    acc = 0
    for o in out:
        o["f0"] = acc; o["nf"] = int(round((o["start"] + o["seg"]) * FPS)) - acc; acc += o["nf"]
    return out, acc / FPS

# ------------------------------------------------------------------ 3D render
def lib_hash(scene=None):
    """Hash of the shared Blender code plus only this scene's builder, so editing one scene re-renders only its shots."""
    h = hashlib.md5()
    for n in ("toon.py", "assets.py", "actions.py", "render_shot.py"): h.update((HERE / "blender" / n).read_bytes())
    src = (HERE / "blender" / "scenes.py").read_text()
    head = src.split("\ndef ", 1)[0]                     # imports + CAST
    h.update(head.encode())
    m = re.search(r"\ndef (_pad|build_%s)\(.*?(?=\ndef |\nSCENES)" % re.escape(scene or ""), src, re.S)
    for fn in re.findall(r"\ndef (?:build_%s|_pad)\(.*?(?=\ndef |\nSCENES)" % re.escape(scene or ""), src, re.S): h.update(fn.encode())
    return h.hexdigest()[:8]

def render_shots(lines, tl, build, draft, jobs, only, scale=100):
    specs = []
    for i, (l, t) in enumerate(zip(lines, tl)):
        nf = t["nf"] + XF   # every shot starts XF frames early (crossfade in)
        spec = dict(scene=l["scene"], scene_args=l["scene_args"], view=l["view"], cam=l["cam"], actions=l["actions"], frames=nf, seed=i + 1,
                    samples=4 if draft else 8, pct=50 if draft else scale)
        tag = hashlib.md5((json.dumps(spec, sort_keys=True) + lib_hash(l["scene"])).encode()).hexdigest()[:8]
        out = build / "shots" / f"{i:02d}_{l['scene']}_{tag}"
        spec["out"] = str(out); specs.append(spec)
    todo = [s for i, s in enumerate(specs) if not (Path(s["out"]) / f"f_{s['frames']:04d}.png").exists() and (not only or i in only)]
    print(f"render: {len(todo)} of {len(specs)} shots need frames", flush=True)
    def run(s):
        js = Path(s["out"] + ".json"); js.parent.mkdir(parents=True, exist_ok=True); js.write_text(json.dumps(s))
        t0 = time.time()
        r = subprocess.run([BLENDER, "-b", "--factory-startup", "-P", str(HERE / "blender" / "render_shot.py"), "--", str(js)], capture_output=True, text=True)
        if r.returncode or "SHOT DONE" not in r.stdout:
            print(r.stdout[-3000:], r.stderr[-2000:]); raise SystemExit(f"blender failed: {s['out']}")
        print(f"  {Path(s['out']).name}: {s['frames']} frames in {time.time() - t0:.0f}s", flush=True)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        list(ex.map(run, todo))
    return specs, time.time() - t0

# ------------------------------------------------------------------ captions
def _wrap(words, font, d, maxw=920):
    rows, cur = [], []
    for w in words:
        if cur and d.textlength(" ".join(cur + [w]), font=font) > maxw: rows.append(cur); cur = [w]
        else: cur.append(w)
    return rows + [cur]

def caption_png(words, hi, path, size=92, y=1300):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, size)
    rows = _wrap(words, f, d); k = 0; yy = y - (len(rows) - 1) * size * 0.6
    for row in rows:
        tw = d.textlength(" ".join(row), font=f); x = (W - tw) / 2
        for w in row:
            col = ORANGE if k == hi else WHITE
            d.text((x + 6, yy + 8), w, font=f, fill=(0, 0, 0, 120), stroke_width=12, stroke_fill=(0, 0, 0, 120))
            d.text((x, yy), w, font=f, fill=col, stroke_width=12, stroke_fill=INK)
            x += d.textlength(w + " ", font=f); k += 1
        yy += size * 1.2
    im.save(path)

def captions(lines, tl, total, build):
    cdir = build / "caps"; shutil.rmtree(cdir, ignore_errors=True); cdir.mkdir(parents=True)
    Image.new("RGBA", (W, H), (0, 0, 0, 0)).save(cdir / "blank.png")
    cues = []  # (start, end, words, hi)
    for l, t in zip(lines, tl):
        words = l["cap"].replace('"', "").split()
        wts = [len(re.sub(r"[^\w]", "", w)) + 2.5 for w in words]; tot = sum(wts)
        st, acc = [], t["start"] + 0.04
        for w in wts: st.append(acc); acc += t["speech"] * 0.97 * w / tot
        st.append(t["start"] + t["speech"])
        # groups of up to 3 words, break after punctuation
        groups, cur = [], []
        for j, w in enumerate(words):
            cur.append(j)
            if len(cur) == 3 or re.search(r"[.,?!:;]$", w) or (len(cur) == 2 and len(w) > 9): groups.append(cur); cur = []
        if cur: groups.append(cur)
        for g in groups:
            gw = [words[j].upper() for j in g]
            for k, j in enumerate(g):
                cues.append((st[j], st[j + 1] if k < len(g) - 1 else st[g[-1] + 1], gw, k))
    lst, cur = [], 0.0
    for n, (a, b, gw, hi) in enumerate(cues):
        if a > cur + 0.01: lst.append(("blank.png", a - cur)); cur = a
        p = f"c{n:04d}.png"; caption_png(gw, hi, cdir / p); lst.append((p, max(0.04, b - cur))); cur = max(cur, b)
    lst.append(("blank.png", max(0.1, total - cur + 0.5)))
    (cdir / "caps.txt").write_text("".join(f"file '{f}'\nduration {d:.4f}\n" for f, d in lst) + f"file '{lst[-1][0]}'\n")
    sh(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", "caps.txt", "-vf", f"fps={FPS},format=rgba",
        "-c:v", "png", "caps.mov"], cwd=cdir)
    return cdir / "caps.mov", cues

# ------------------------------------------------------------------ audio: original music bed + synthesized sfx
SR = 48000

def _env(n, a=0.005, d=0.3):
    t = np.arange(n) / SR; return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)

def _note(f, dur, kind="pluck", amp=0.3):
    n = int(dur * SR); t = np.arange(n) / SR
    if kind == "pluck":
        s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) * np.exp(-t / 0.08) + 0.12 * np.sin(6 * np.pi * f * t)
        return amp * s * _env(n, 0.003, 0.22)
    if kind == "bass":
        return amp * (np.sin(2 * np.pi * f * t) + 0.2 * np.sin(4 * np.pi * f * t)) * _env(n, 0.01, 0.35)
    if kind == "pad":
        s = sum(np.sin(2 * np.pi * f * (1 + dt) * t) for dt in (-0.004, 0, 0.005)) / 3
        return amp * s * np.minimum(1, t / 0.4) * np.minimum(1, (dur - t) / 0.4)
    if kind == "tick":
        return amp * np.random.randn(n) * _env(n, 0.0005, 0.012)

def music(total, seed=3):
    np.random.seed(seed); n = int((total + 1) * SR); out = np.zeros(n)
    bpm = 104; beat = 60 / bpm
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    prog = [(60, [60, 64, 67]), (57, [57, 60, 64]), (53, [53, 57, 60]), (55, [55, 59, 62])]   # C Am F G
    mel = [72, 76, 79, 76, 74, 72, 69, 72, 72, 77, 76, 74, 74, 71, 67, 71]
    t, bar = 0.0, 0
    def add(sig, at):
        i = int(at * SR); j = min(n, i + len(sig))
        if i < n: out[i:j] += sig[: j - i]
    while t < total + 1:
        root, chord = prog[bar % 4]
        add(_note(hz(root - 12), beat * 2, "bass", 0.32), t); add(_note(hz(root - 12), beat * 2, "bass", 0.26), t + beat * 2)
        for c in chord: add(_note(hz(c), beat * 4, "pad", 0.05), t)
        for k in range(8):
            add(_note(hz(chord[k % 3] + 12), beat * 0.6, "pluck", 0.10 if k % 2 else 0.14), t + k * beat / 2)
            add(_note(0, beat / 2, "tick", 0.05 if k % 2 else 0.025), t + k * beat / 2)
        if bar % 2 == 1:
            for k in range(4): add(_note(hz(mel[(bar * 4 + k) % 16]), beat, "pluck", 0.12), t + k * beat)
        t += beat * 4; bar += 1
    return out[: int(total * SR)]

def sfx(kind):
    np.random.seed(hash(kind) % 1000)
    if kind == "whoosh":
        n = int(0.42 * SR); x = np.random.randn(n); y = np.zeros(n); a = 0.0
        cut = np.linspace(0.02, 0.35, n) * np.sin(np.linspace(0, np.pi, n)) + 0.01
        for i in range(n): a += cut[i] * (x[i] - a); y[i] = a
        return 0.9 * y * np.sin(np.linspace(0, np.pi, n)) ** 2
    if kind == "pop":
        n = int(0.12 * SR); t = np.arange(n) / SR; f = 900 * np.exp(-t * 25) + 250
        return 0.5 * np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.001, 0.04)
    if kind == "thud":
        n = int(0.35 * SR); t = np.arange(n) / SR
        return 0.9 * (np.sin(2 * np.pi * 80 * t) * _env(n, 0.001, 0.09) + 0.4 * np.random.randn(n) * _env(n, 0.0005, 0.01))
    if kind == "rumble":
        n = int(3.0 * SR); x = np.random.randn(n); y = np.zeros(n); a = 0.0
        for i in range(n): a += 0.02 * (x[i] - a); y[i] = a
        return 3.0 * y * np.minimum(1, np.arange(n) / (0.4 * SR)) * np.minimum(1, (n - np.arange(n)) / (1.0 * SR))
    if kind == "buzz":
        n = int(0.35 * SR); t = np.arange(n) / SR
        return 0.22 * np.sign(np.sin(2 * np.pi * 110 * t)) * _env(n, 0.002, 0.2)
    if kind == "crunch":
        n = int(0.16 * SR); x = np.random.randn(n) * (np.random.rand(n) > 0.6)
        return 0.5 * x * _env(n, 0.001, 0.05)
    if kind == "sparkle":
        n = int(0.9 * SR); y = np.zeros(n)
        for _ in range(14):
            i = np.random.randint(0, n - 3000); f = np.random.uniform(1800, 3800); t = np.arange(2400) / SR
            y[i:i + 2400] += 0.12 * np.sin(2 * np.pi * f * t) * np.exp(-t / 0.015)
        return y
    if kind == "boing":
        n = int(0.3 * SR); t = np.arange(n) / SR; f = 220 + 300 * t / 0.3 + 30 * np.sin(2 * np.pi * 18 * t)
        return 0.25 * np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.005, 0.15)
    if kind == "zap":   # lightning crack: noise burst with a crackle tail
        n = int(0.9 * SR); t = np.arange(n) / SR
        crack = np.random.randn(n) * (np.random.rand(n) > 0.75) * np.exp(-t / 0.25)
        return 0.9 * (crack + 0.6 * np.sin(2 * np.pi * 55 * t) * np.exp(-t / 0.3))
    if kind == "splash":
        n = int(0.7 * SR); x = np.random.randn(n); y = np.zeros(n); a = 0.0
        for i in range(n): a += 0.25 * (x[i] - a); y[i] = a
        return 0.8 * y * _env(n, 0.01, 0.22)
    if kind == "clink":
        n = int(0.25 * SR); t = np.arange(n) / SR
        return 0.25 * (np.sin(2 * np.pi * 3100 * t) + 0.6 * np.sin(2 * np.pi * 4700 * t)) * np.exp(-t / 0.05)
    if kind == "click":
        n = int(0.06 * SR); t = np.arange(n) / SR
        return 0.6 * np.sin(2 * np.pi * 1800 * t) * np.exp(-t / 0.008)
    if kind == "beep":
        n = int(0.9 * SR); t = np.arange(n) / SR
        return 0.18 * np.sign(np.sin(2 * np.pi * 880 * t)) * (np.sin(2 * np.pi * 4 * t) > 0)
    if kind == "rip":   # tape tearing
        n = int(0.45 * SR); x = np.random.randn(n) * (np.random.rand(n) > 0.5)
        return 0.35 * x * np.minimum(1, np.arange(n) / (0.05 * SR)) * np.exp(-np.arange(n) / SR / 0.3)
    if kind == "thwack":
        n = int(0.15 * SR); t = np.arange(n) / SR
        return 0.7 * (np.sin(2 * np.pi * 600 * t) * np.exp(-t / 0.02) + 0.5 * np.random.randn(n) * np.exp(-t / 0.006))
    return np.zeros(10)

SFX_MAP = {"sandwich_out": [("pop", 0)], "pouch": [("pop", 0)], "xmark": [("pop", 0), ("buzz", 0.1)], "tortilla": [("pop", 0)],
           "clipboard": [("pop", 0)], "crumbs": [("sparkle", 0.05)], "crumbs_panel": [("sparkle", 0.2)], "bite": [("crunch", 0)],
           "gavel": [("thud", 0), ("thud", 12 / FPS)], "liftoff": [("rumble", 0)], "jump": [("boing", 0)], "pocket": [("pop", 0.3)],
           "surprise": [("boing", 0)],
           "word": [("pop", 0)], "lightning": [("zap", 0), ("thud", 0.02)], "flash": [("thud", 0)], "alarms": [("beep", 0)],
           "glitch": [("buzz", 0), ("buzz", 0.4)], "sce_switch": [("click", 0)], "hatch_blow": [("pop", 0), ("thud", 0.02), ("splash", 0.6)],
           "sink": [("splash", 0)], "lift_fail": [("splash", 0)], "dimes": [("clink", 0), ("clink", 0.12), ("clink", 0.25), ("splash", 0.5)],
           "dime_stack": [("clink", 0), ("clink", 0.13)], "club": [("pop", 0)], "swing": [("thwack", 0)], "dust": [("thud", 0)],
           "ladder_hop": [("thud", 10 / FPS)], "tumble": [("whoosh", 0)], "zoom_by": [("whoosh", 0.3)], "gauge": [("beep", 0.5)],
           "square_peg": [("thud", 0), ("thud", 22 / FPS)], "assemble": [("rip", 0.3), ("rip", 0.9)], "tape_spin": [("rip", 0)],
           "item_pop": [("pop", 0)], "cash": [("pop", 0)], "handshake": [("pop", 0.25)], "throw": [("whoosh", 0)], "surface": [("splash", 0.8)]}

def audio(lines, tl, total, specs, vo_dir, build):
    n = int(total * SR); vo = np.zeros(n)
    for i, t in enumerate(tl):
        p = build / "a48" / f"line_{i:02d}.wav"; p.parent.mkdir(exist_ok=True, parents=True)
        sh(["ffmpeg", "-loglevel", "error", "-y", "-i", str(vo_dir / f"line_{i:02d}.wav"), "-ar", str(SR), "-ac", "1", str(p)])
        with wave.open(str(p)) as w: a = np.frombuffer(w.readframes(w.getnframes()), np.int16) / 32768
        s = int(t["start"] * SR); vo[s:s + len(a)] += a[: max(0, n - s)]
    fx = np.zeros(n)
    def add(sig, at, g=1.0):
        s = int(at * SR)
        if 0 <= s < n: m = min(n, s + len(sig)); fx[s:m] += g * sig[: m - s]
    wh = sfx("whoosh")
    for t in tl[1:]: add(wh, t["start"] - 0.25, 0.5)
    for (l, t, sp) in zip(lines, tl, specs):
        for name, arg, a, b in l["actions"]:
            for kind, off in SFX_MAP.get(name, []):
                f0 = max(2, round(1 + a * (sp["frames"] - 1)))
                shot_start = (t["f0"] - (XF if t["f0"] > 0 else 0)) / FPS
                add(sfx(kind), shot_start + (f0 - 1) / FPS + off, 0.6)
    mus = music(total)
    rms = lambda x: np.sqrt(np.mean(x[np.abs(x) > 1e-4] ** 2)) if np.any(np.abs(x) > 1e-4) else 1
    mus *= rms(vo) / rms(mus) * 10 ** (-17 / 20)        # music ~17 dB under voice
    fx *= rms(vo) / max(rms(fx), 1e-6) * 10 ** (-9 / 20)  # effects ~9 dB under voice
    # duck music slightly under speech
    env = np.convolve(np.abs(vo), np.ones(2400) / 2400, "same"); duck = 1 - 0.35 * np.clip(env / (env.max() + 1e-9) * 4, 0, 1)
    mix = vo + mus * duck + fx
    mix /= max(1.0, np.abs(mix).max() / 0.95)
    raw = build / "mix_raw.wav"
    with wave.open(str(raw), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype(np.int16).tobytes())
    with wave.open(str(build / "vo_full.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(vo, -1, 1) * 32767).astype(np.int16).tobytes())
    # compress, then two-pass loudnorm to -14 LUFS
    pre = "acompressor=threshold=-20dB:ratio=3:attack=5:release=120:makeup=2"
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(raw), "-af", pre + ",loudnorm=I=-14:TP=-1.5:LRA=7:print_format=json", "-f", "null", "-"], capture_output=True, text=True)
    m = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    ln = (f"loudnorm=I=-14:TP=-1.5:LRA=7:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    out = build / "mix.wav"
    sh(["ffmpeg", "-loglevel", "error", "-y", "-i", str(raw), "-af", pre + "," + ln, "-ar", str(SR), "-ac", "2", str(out)])
    return out

# ------------------------------------------------------------------ assemble
def assemble(specs, tl, caps, mix, total, final):
    args, fc = ["ffmpeg", "-loglevel", "error", "-y"], []
    for s in specs: args += ["-framerate", str(FPS), "-i", str(Path(s["out"]) / "f_%04d.png")]
    k = len(specs); args += ["-i", str(caps), "-i", str(mix)]
    for i in range(k): fc.append(f"[{i}:v]scale={W}:{H}:flags=lanczos,format=yuv420p,setsar=1,fps={FPS},settb=AVTB[s{i}]")
    prev = "s0"
    for i in range(1, k):
        off = (tl[i]["f0"] - XF) / FPS
        tr = "fadewhite" if i == 1 else "fade"
        fc.append(f"[{prev}][s{i}]xfade=transition={tr}:duration={XF / FPS:.3f}:offset={off:.3f}[x{i}]"); prev = f"x{i}"
    fc.append(f"[{prev}]format=yuv420p,setsar=1[base];[base][{k}:v]overlay=0:0:shortest=0,trim=duration={total:.3f},format=yuv420p[v]")
    args += ["-filter_complex", ";".join(fc), "-map", "[v]", "-map", f"{k + 1}:a", "-t", f"{total:.3f}",
             "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", str(FPS),
             "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(final)]
    sh(args)

def small_copy(final, out, total, mb=9.3):
    out.parent.mkdir(parents=True, exist_ok=True)
    vk = int((mb * 8 * 1024 * 1024 / total - 128_000) / 1000)
    common = ["-c:v", "libx264", "-b:v", f"{vk}k", "-preset", "slow", "-pix_fmt", "yuv420p"]
    log = str(out.parent / "x264pass")
    sh(["ffmpeg", "-loglevel", "error", "-y", "-i", str(final), *common, "-pass", "1", "-passlogfile", log, "-an", "-f", "mp4", "/dev/null"])
    sh(["ffmpeg", "-loglevel", "error", "-y", "-i", str(final), *common, "-pass", "2", "-passlogfile", log, "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out)])
    for f in out.parent.glob("x264pass*"): f.unlink()

def contact_sheet(final, total, path, step=1.5):
    tmp = path.parent / "_cs"; shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir()
    times = [min(total - 0.05, 0.2 + i * step) for i in range(int(total / step) + 1)]
    for i, t in enumerate(times):
        sh(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{t:.2f}", "-i", str(final), "-frames:v", "1", "-vf", "scale=216:384", str(tmp / f"{i:03d}.png")])
    ims = sorted(tmp.glob("*.png")); cols = 10; rows = math.ceil(len(ims) / cols)
    sheet = Image.new("RGB", (cols * 216, rows * 400), (0, 0, 0)); d = ImageDraw.Draw(sheet)
    for i, p in enumerate(ims):
        sheet.paste(Image.open(p), ((i % cols) * 216, (i // cols) * 400)); d.text(((i % cols) * 216 + 4, (i // cols) * 400 + 385), f"{times[i]:.1f}s", fill=(255, 220, 0))
    sheet.save(path, quality=85); shutil.rmtree(tmp)

def upload_md(meta, lines, total, path):
    title = meta.get("title", "Untitled")
    if len(title) > 60: print("WARNING: title is over 60 characters")
    desc = meta.get("description", "")
    md = f"""# Upload sheet

**Title** ({len(title)} chars): {title}

**Description:**

{desc}

{meta.get('hashtags', '')}

{meta.get('source_line', 'Sources in the script.')}

**Length:** {total:.1f} s, 1080x1920, 30 fps. Upload `up/{Path(path).parent.name}.mp4` (under 10 MB) from the browser.

## AI disclosure (YouTube "Altered or synthetic content")
- The narration is a synthetic voice (Kokoro text-to-speech, voice {meta.get('voice', 'bm_george 1.0').split()[0]}). It does not imitate any real person.
- The visuals are our own procedural 3D (Blender, built in code), not AI-generated images or video. The characters are stylized cartoons, not likenesses of the real astronauts.
- Suggested setting: the video does not show a realistic person or event that did not happen, so the "altered or synthetic" toggle can stay **No**. If you prefer to be conservative, turn it on and note "synthetic narration voice".
- Put this line at the end of the description: "Narration: synthetic voice. Animation: original 3D, made by Orbit's Logbook."

## Sources
{meta.get('sources', '')}
"""
    Path(path).write_text(md, encoding="utf-8")

# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("script"); ap.add_argument("--draft", action="store_true")
    ap.add_argument("--jobs", type=int, default=1); ap.add_argument("--only", default="")
    ap.add_argument("--scale", type=int, default=100, help="render resolution percent; frames are upscaled to 1080x1920")
    a = ap.parse_args()
    sp = Path(a.script).resolve(); vid = sp.parent; name = vid.name
    build = vid / ("build-draft" if a.draft else "build"); build.mkdir(exist_ok=True)
    T0 = time.time()
    meta, lines = parse(sp)
    print(f"{len(lines)} lines", flush=True)
    durs = voice(lines, meta, vid / "vo")
    tl, total = timeline(lines, durs)
    print(f"length {total:.1f}s", flush=True)
    only = {int(x) for x in a.only.split(",") if x.strip()}
    specs, rtime = render_shots(lines, tl, build, a.draft, a.jobs, only, a.scale)
    if only: print("partial render done"); return
    caps, cues = captions(lines, tl, total, build)
    mix = audio(lines, tl, total, specs, vid / "vo", build)
    final = vid / (f"{name}-draft.mp4" if a.draft else f"{name}.mp4")
    assemble(specs, tl, caps, mix, total, final)
    if not a.draft:
        small_copy(final, vid / "up" / f"{name}.mp4", total)
        upload_md(meta, lines, total, vid / "upload.md")
    contact_sheet(final, total, build / "contact.jpg")
    info = dict(length=round(total, 2), render_seconds=round(rtime), total_seconds=round(time.time() - T0),
                final=str(final), size_mb=round(final.stat().st_size / 1e6, 2))
    if not a.draft:
        up = vid / "up" / f"{name}.mp4"; info["upload_copy_mb"] = round(up.stat().st_size / 1e6, 2)
    (build / "report.json").write_text(json.dumps(info, indent=1)); print(json.dumps(info, indent=1))

if __name__ == "__main__":
    main()
