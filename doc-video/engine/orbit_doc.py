#!/usr/bin/env python3
"""orbit-doc: render an Orbit's Logbook episode (continuous-camera documentary) from an episode folder.

usage:  PY orbit_doc.py <episode_dir> [--stage STAGES] [--workers N] [--draft]
  PY  = ~/video-venv/bin/python  (playwright + numpy + scipy + PIL)
  STAGES (comma list, default all): validate,audio,check,main,shorts,thumbs,upload
  --draft renders the main film at 960x540 for a quick look (build/draft.mp4)
See README.md for the input contract."""
import argparse, base64, functools, http.server, json, math, multiprocessing as mp, os, re, shutil, socketserver, subprocess, sys, threading, time, wave
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ENGINE = HERE / "engine"
THUMB_PY = Path.home() / "Business/YouTube Channel/tools/thumbs/thumb.py"
LOG = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------- inputs
def narration_lines(script):
    """Same rule as kokoro_say/kokoro_cast: sections after the first '---' up to '## Sources'; skip cue/heading lines."""
    parts = Path(script).read_text(encoding="utf-8").split("\n---\n")[1:]
    stop = next((i for i, p in enumerate(parts) if "## Sources" in p), len(parts))
    body = "\n\n".join(parts[:stop])
    return [p.strip() for p in body.split("\n\n") if p.strip() and not p.strip().startswith(("`", "#", "✂", "**"))]


def load(ep_dir):
    ep_dir = Path(ep_dir).resolve(); E = json.loads((ep_dir / "episode.json").read_text())
    E["_dir"] = ep_dir
    E["_script"] = (ep_dir / E["script"]).resolve()
    lines = narration_lines(E["_script"]); tim = json.loads((ep_dir / E["timings"]).read_text())
    E["_lines"] = [{"t0": x["t0"], "t1": x["t1"], "text": l} for l, x in zip(lines, tim)]
    E["_nlines"], E["_ntim"] = len(lines), len(tim)
    E["_beats"] = json.loads((ep_dir / E["beats"]).read_text())
    w = wave.open(str(ep_dir / E["vo"])); E["_vo_dur"] = w.getnframes() / w.getframerate(); w.close()
    E["fps"] = E.get("fps", 30); E["_frames"] = int(round(E["_vo_dur"] * E["fps"]))
    return E


def validate(E):
    errs, warn = [], []
    bt = E["_beats"]; beats, world = bt["beats"], bt["world"]
    if not (E["_nlines"] == E["_ntim"] == len(beats)):
        errs.append(f"count mismatch: script lines {E['_nlines']}, timings {E['_ntim']}, beats {len(beats)}")
    ids = {e["id"] for e in world["elements"]}
    for e in world["elements"]:
        if e.get("img") and not (E["_dir"] / E.get("img", "img") / e["img"]).exists(): errs.append(f"missing image {e['img']}")
        if e.get("type") == "card" and "illustration" not in (e.get("note") or "").lower(): errs.append(f"card {e['id']} needs an 'illustration ...' note")
    texts = [b.get("text") for b in beats if b.get("text")]
    for t in set(texts):
        if texts.count(t) > 1: errs.append(f"on-screen text repeated: {t!r}")
    for k, b in enumerate(beats):
        for h in ([b["hero"]] if isinstance(b.get("hero"), str) else b.get("hero", [])):
            if h not in ids: errs.append(f"beat {k}: hero {h} not an element")
        c = b.get("cam") or {}
        for o in ([c["on"]] if isinstance(c.get("on"), str) else c.get("on", [])):
            if o not in ids: errs.append(f"beat {k}: cam.on {o} not an element")
        if k < len(E["_lines"]) and b.get("on") and b["on"].lower() not in E["_lines"][k]["text"].lower():
            errs.append(f"beat {k}: on-word {b['on']!r} not in line")
        for o in b.get("set", []):
            if len(o) > 3 and o[3] and k < len(E["_lines"]) and str(o[3]).lower() not in E["_lines"][k]["text"].lower(): errs.append(f"beat {k}: set word {o[3]!r} not in line")
            if o[0].split(".")[0] not in ids: errs.append(f"beat {k}: set on unknown element {o[0]}")
        if b.get("text") and len(b["text"]) > 34: warn.append(f"beat {k}: text over 34 chars, may not read in one second: {b['text']}")
    s = E["_script"].read_text()
    if "\u2014" in s or "\u2013" in s: errs.append("script contains an em/en dash")
    return errs, warn


# ---------------------------------------------------------------- page server + workers
class _H(http.server.SimpleHTTPRequestHandler):
    roots = {}
    def log_message(self, *a): pass
    def translate_path(self, path):
        path = path.split("?")[0].split("#")[0]; from urllib.parse import unquote; path = unquote(path)
        for pre, root in self.roots.items():
            if path.startswith(pre): return str(Path(root) / path[len(pre):])
        return str(ENGINE / "missing")


def serve(ep_dir):
    _H.roots = {"/engine/": str(ENGINE), "/ep/": str(ep_dir)}
    class _S(socketserver.ThreadingTCPServer): request_queue_size = 256; daemon_threads = True; allow_reuse_address = True
    srv = _S(("127.0.0.1", 0), _H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def cfg_for(E, W, H, rng=None):
    return {"W": W, "H": H, "fps": E["fps"], "frames": E["_frames"], "base": "/ep/" + E.get("img_base", ""), "world": E["_beats"]["world"],
            "beats": E["_beats"]["beats"], "lines": E["_lines"], "seed": E.get("seed", 1), "brand": E.get("brand"),
            "range": rng, "handheld": E.get("handheld", 1)}


def _page(pw, port, cfg):
    b = pw.chromium.launch(args=["--disable-web-security", "--enable-gpu-rasterization", "--ignore-gpu-blocklist"])
    pg = b.new_page(viewport={"width": cfg["W"], "height": cfg["H"]})
    pg.on("pageerror", lambda e: print("PAGE ERROR", e, flush=True))
    pg.goto(f"http://127.0.0.1:{port}/engine/engine.html"); pg.wait_for_function("window.init !== undefined")
    info = pg.evaluate("c => init(c)", cfg)
    return b, pg, info


def _worker(args):
    try: return _work(args)
    except Exception:
        import traceback; traceback.print_exc(); sys.stdout.flush(); raise


def _work(args):
    """Render one segment [f0, f1) to out (written to .part, renamed when complete, so a rerun resumes)."""
    port, cfg, f0, f1, out, q, idx = args
    out = Path(out)
    if out.exists(): return str(out)
    time.sleep(1.0 * (idx % 8))  # stagger page loads
    from playwright.sync_api import sync_playwright
    t0 = time.time(); part = out.with_suffix(".part.mp4")
    with sync_playwright() as pw:
        b, pg, _ = _page(pw, port, cfg)
        ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(cfg["fps"]), "-c:v", "mjpeg", "-i", "-",
                               "-c:v", "libx264", "-preset", "fast", "-threads", "3", "-crf", "17", "-pix_fmt", "yuv420p", "-r", str(cfg["fps"]), str(part)], stdin=subprocess.PIPE)
        for f in range(f0, f1):
            d = pg.evaluate("([f,q]) => frame(f,q)", [f, q]); ff.stdin.write(base64.b64decode(d.split(",", 1)[1]))
        ff.stdin.close(); ff.wait(); b.close()
    part.rename(out); LOG(f"  segment {out.name} frames {f0}-{f1} in {time.time() - t0:.0f}s")
    return str(out)


def render_range(E, port, W, H, f0, f1, out, workers, rng=None, q=0.93, seg=600):
    """Split [f0, f1) into segments of about `seg` frames, render them on `workers` browsers, concat. Finished segments are reused on rerun."""
    cfg = cfg_for(E, W, H, rng); build = E["_dir"] / "build" / "chunks"; build.mkdir(parents=True, exist_ok=True)
    n = f1 - f0; k = max(1, math.ceil(n / seg)); cuts = [f0 + round(n * i / k) for i in range(k + 1)]
    tag = f"{out.stem}-{W}x{H}"; jobs = [(port, cfg, cuts[i], cuts[i + 1], build / f"{tag}-{cuts[i]:06d}-{cuts[i + 1]:06d}.mp4", q, i) for i in range(k)]
    with mp.get_context("spawn").Pool(max(1, min(workers, k)), maxtasksperchild=1) as pool: parts = list(pool.imap(_worker, jobs))
    lst = build / f"{tag}.txt"; lst.write_text("".join("file '" + str(p).replace("'", "'\\''") + "'\n" for p in parts))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)], check=True)
    return out


# ---------------------------------------------------------------- audio
SR = 48000
def wread(p):
    w = wave.open(str(p)); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768; ch = w.getnchannels(); sr = w.getframerate(); w.close()
    return (a.reshape(-1, ch) if ch > 1 else a), sr
def wwrite(p, a, sr=SR):
    x = (np.clip(a, -1, 1) * 32767).astype(np.int16); w = wave.open(str(p), "wb"); w.setnchannels(1 if x.ndim == 1 else x.shape[1]); w.setsampwidth(2); w.setframerate(sr); w.writeframes(x.tobytes()); w.close()


def music_bed(N, seed, root=50):
    """Original synthesized ambient bed: slow pad chords + low drone + sparse bells + noise-IR reverb. Ours, made per episode."""
    from scipy.signal import fftconvolve, butter, sosfilt
    rng = np.random.default_rng(seed); t = np.arange(N) / SR; T = N / SR
    mtof = lambda m: 440 * 2 ** ((m - 69) / 12)
    shapes = [[0, 7, 14, 16, 19], [-3, 4, 12, 16, 19], [-7, 0, 9, 12, 16], [-5, 2, 11, 14, 18], [0, 7, 12, 14, 19], [-7, 0, 7, 12, 21], [-3, 4, 9, 12, 16], [-5, 2, 7, 11, 14]]
    order = rng.permutation(len(shapes)); CH = 16.0; L = np.zeros(N, np.float32); R = np.zeros(N, np.float32)
    for k in range(int(np.ceil(T / CH)) + 1):
        c = [root + x for x in shapes[order[k % len(shapes)]]]; a0, a1 = k * CH - 4, (k + 1) * CH + 4
        i0, i1 = max(0, int(a0 * SR)), min(N, int(a1 * SR))
        if i1 <= i0: continue
        tt = t[i0:i1]; env = np.sin(np.pi * np.clip((tt - a0) / (a1 - a0), 0, 1)) ** 1.5
        for j, m in enumerate(c):
            f = mtof(m); g = (0.16 if j == 0 else 0.10) / (1 + 0.15 * j); lfo = 0.75 + 0.25 * np.sin(2 * np.pi * (0.05 + 0.013 * j) * tt + j)
            for side, det in ((L, -1.8), (R, 1.8)):
                ff = f * 2 ** (det / 1200); side[i0:i1] += (g * env * lfo * (np.sin(2 * np.pi * ff * tt + j) + 0.18 * np.sin(4 * np.pi * ff * tt + 2 * j))).astype(np.float32)
    dr = 0.10 * (np.sin(2 * np.pi * mtof(root - 12) * t) + 0.5 * np.sin(2 * np.pi * mtof(root - 5) * t)) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.021 * t))
    L += dr.astype(np.float32); R += dr.astype(np.float32)
    pent = [root + 24 + x for x in (0, 2, 4, 7, 9, 12, 14)]; tb = 3.0
    while tb < T - 4:
        f = mtof(pent[rng.integers(len(pent))]); i0 = int(tb * SR); tt = np.arange(min(int(5 * SR), N - i0)) / SR
        b = 0.05 * np.exp(-tt / 1.4) * (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2.01 * f * tt)) * np.minimum(1, tt / .01); pan = rng.uniform(.25, .75)
        L[i0:i0 + len(b)] += (b * (1 - pan)).astype(np.float32); R[i0:i0 + len(b)] += (b * pan).astype(np.float32); tb += rng.uniform(5, 11)
    sos = butter(2, 2400, "low", fs=SR, output="sos"); L = sosfilt(sos, L).astype(np.float32); R = sosfilt(sos, R).astype(np.float32)
    n = int(3.5 * SR); it = np.arange(n) / SR
    ir = [(rng.standard_normal(n) * np.exp(-it / 0.9)).astype(np.float32) for _ in range(2)]; ir = [x / np.sqrt((x ** 2).sum()) for x in ir]
    mL = 0.55 * L + 0.8 * fftconvolve(L, ir[0])[:N]; mR = 0.55 * R + 0.8 * fftconvolve(R, ir[1])[:N]
    pk = max(np.abs(mL).max(), np.abs(mR).max()); fade = np.minimum(1, t / 3.0) * np.minimum(1, (T - t) / 3.0)
    return (mL / pk * fade).astype(np.float32), (mR / pk * fade).astype(np.float32)


def loudnorm(src, dst, lufs=-14.0, tp=-1.0):
    def measure(p):
        o = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(p), "-af", f"loudnorm=I={lufs}:TP={tp}:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True).stderr
        return json.loads(o[o.rindex("{"):o.rindex("}") + 1])
    m = measure(src)
    af = (f"loudnorm=I={lufs}:TP={tp}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,aresample={SR}")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", af, "-ar", str(SR), str(dst)], check=True)
    o = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(dst), "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    I = re.findall(r"I:\s+(-?[\d.]+) LUFS", o)[-1]; P = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", o)[-1]
    return float(I), float(P)


def make_audio(E):
    from scipy.signal import resample_poly
    b = E["_dir"] / "build"; b.mkdir(exist_ok=True)
    vo, sr = wread(E["_dir"] / E["vo"]); vo = resample_poly(vo, SR, sr).astype(np.float32)
    N = int(round(E["_frames"] / E["fps"] * SR)); vo = np.pad(vo, (0, max(0, N - len(vo))))[:N]
    mL, mR = music_bed(N, E.get("music", {}).get("seed", 7), E.get("music", {}).get("root", 50))
    wwrite(b / "music.wav", np.stack([mL, mR], 1))
    win = int(0.05 * SR); rms = np.sqrt(np.convolve(vo ** 2, np.ones(win) / win, "same")); sp = (rms > 0.01).astype(np.float32)
    step = SR // 100; ctl = sp[::step]; sm = np.zeros_like(ctl); v = 0.0
    for i, x in enumerate(ctl): v += (x - v) * (0.04 if x > v else 0.0085); sm[i] = v
    sm = np.interp(np.arange(N), np.arange(len(sm)) * step, sm).astype(np.float32)
    mu = E.get("music", {}); gdb = mu.get("gap_db", -19.0) + (mu.get("speech_db", -28.0) - mu.get("gap_db", -19.0)) * sm
    g = (10 ** (gdb / 20)).astype(np.float32); mix = np.stack([vo + mL * g, vo + mR * g], 1)
    wwrite(b / "mix_pre.wav", mix); I, P = loudnorm(b / "mix_pre.wav", b / "mix.wav", E.get("lufs", -14))
    LOG(f"audio: {N / SR:.2f}s  {I} LUFS  peak {P} dBFS"); return {"lufs": I, "peak": P}


# ---------------------------------------------------------------- checks
def check(E, port):
    from playwright.sync_api import sync_playwright
    from PIL import Image, ImageDraw, ImageFont
    out = E["_dir"] / "build" / "check"; shutil.rmtree(out, ignore_errors=True); (out / "stills").mkdir(parents=True, exist_ok=True); (out / "moves").mkdir(exist_ok=True)
    fps = E["fps"]; L = E["_lines"]; rep = {}
    with sync_playwright() as pw:
        b, pg, info = _page(pw, port, cfg_for(E, 1920, 1080)); st = pg.evaluate("() => stats()")
        def grab(f, path, size=None):
            d = pg.evaluate("([f,q]) => frame(f,q)", [f, 0.9]); path.write_bytes(base64.b64decode(d.split(",", 1)[1]))
        stills = []
        for k, ln in enumerate(L):
            tw = st["beats"][k]["hit"]; t = min(max(tw + 0.8, (ln["t0"] + ln["t1"]) / 2), ln["t1"] + 0.3)
            p = out / "stills" / f"b{k:03d}.jpg"; grab(int(t * fps), p); stills.append(p)
        spd = np.array(st["speed"]); moves = []; f = 0
        while f < len(spd):  # contiguous runs of fast camera
            if spd[f] > 4:
                g = f
                while g < len(spd) and spd[g] > 1.0: g += 1
                moves.append((float(spd[f:g].max()), f, g)); f = g
            else: f += 1
        moves.sort(reverse=True)
        for i, (_, a, z) in enumerate(moves[:10]):
            fr = [int(a - 6 + (z - a + 12) * j / 7) for j in range(8)]; ims = []
            for j, ff in enumerate(fr):
                p = out / "moves" / f"_m{i}_{j}.jpg"; grab(max(0, min(ff, E["_frames"] - 1)), p); ims.append(Image.open(p).resize((480, 270)))
            strip = Image.new("RGB", (480 * 4, 270 * 2)); [strip.paste(im, (480 * (j % 4), 270 * (j // 4))) for j, im in enumerate(ims)]
            strip.save(out / "moves" / f"move{i:02d}_f{a}-{z}.jpg", quality=85); [ (out / "moves" / f"_m{i}_{j}.jpg").unlink() for j in range(8)]
        b.close()
    cols = 6; tw_, th_ = 400, 225
    for s0 in range(0, len(stills), 36):
        chunk = stills[s0:s0 + 36]; rows = math.ceil(len(chunk) / cols); sheet = Image.new("RGB", (cols * tw_, rows * (th_ + 26)), (20, 20, 24)); d = ImageDraw.Draw(sheet)
        for i, p in enumerate(chunk):
            k = s0 + i; x, y = (i % cols) * tw_, (i // cols) * (th_ + 26); sheet.paste(Image.open(p).resize((tw_, th_)), (x, y + 26))
            d.text((x + 6, y + 6), f"{k}  {L[k]['t0']:.1f}s  {L[k]['text'][:46]}", fill=(230, 230, 230))
        sheet.save(out / f"sheet-{s0 // 36 + 1}.jpg", quality=82)
    rep = {k: st[k] for k in ("maxSpeed", "maxAccel", "deadFrames", "deadSample", "blurFrames")}
    rep["moves"] = [{"maxSpeed": round(m[0], 1), "frames": [m[1], m[2]]} for m in moves[:10]]
    (out / "check.json").write_text(json.dumps(rep, indent=1)); LOG("check:", rep["maxSpeed"], rep["maxAccel"], "dead frames", rep["deadFrames"])
    return rep


# ---------------------------------------------------------------- outputs
def mux(video, audio, out, a_from=None, a_dur=None):
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(video)]
    if a_from is not None: cmd += ["-ss", f"{a_from:.3f}", "-t", f"{a_dur:.3f}"]
    cmd += ["-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart", "-shortest", str(out)]
    subprocess.run(cmd, check=True)


def probe(p):
    o = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=width,height,nb_frames", "-of", "json", str(p)], capture_output=True, text=True).stdout
    return json.loads(o)


def small_copy(src, dst, limit=10_000_000):
    dur = float(probe(src)["format"]["duration"]); br = int((limit * 0.92 * 8 / dur - 128_000))
    for _ in range(4):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-c:v", "libx264", "-preset", "slow", "-b:v", str(br), "-maxrate", str(int(br * 1.3)), "-bufsize", str(br * 2),
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(dst)], check=True)
        if dst.stat().st_size < limit: return dst
        br = int(br * 0.85)
    return dst


def shorts(E, port, workers):
    b = E["_dir"] / "build"; up = E["_dir"] / "up"; up.mkdir(exist_ok=True); L = E["_lines"]; fps = E["fps"]; res = []
    for s in E.get("shorts", []):
        t0 = max(0.0, L[s["from"]]["t0"] - 0.35); t1 = min(E["_frames"] / fps, L[s["to"]]["t1"] + 0.9)
        f0, f1 = int(t0 * fps), int(t1 * fps); vid = b / f"{s['name']}-video.mp4"
        render_range(E, port, 1080, 1920, f0, f1, vid, workers, rng=[f0 / fps, f1 / fps])
        mix_pre, _ = wread(b / "mix_pre.wav"); seg = mix_pre[int(f0 / fps * SR):int(f1 / fps * SR)].copy(); n = len(seg)
        fade = np.minimum(1, np.arange(n) / (0.25 * SR)) * np.minimum(1, (n - np.arange(n)) / (0.6 * SR)); seg *= fade[:, None]
        wwrite(b / f"{s['name']}-pre.wav", seg); loudnorm(b / f"{s['name']}-pre.wav", b / f"{s['name']}.wav", E.get("lufs", -14))
        out = E["_dir"] / f"{s['name']}.mp4"; mux(vid, b / f"{s['name']}.wav", out); small_copy(out, up / f"{s['name']}.mp4")
        res.append({"name": s["name"], "seconds": round((f1 - f0) / fps, 2), "up_mb": round((up / f"{s['name']}.mp4").stat().st_size / 1e6, 2)}); LOG("short", res[-1])
    return res


def thumbs(E):
    T = E.get("thumbs");
    if not T: return []
    cfgp = E["_dir"] / "thumbs.json"; cfgp.write_text(json.dumps({"out_dir": "thumbs", "base": T["base"], "variants": T["variants"]}, indent=1))
    subprocess.run([sys.executable, str(THUMB_PY), str(cfgp)], check=True); return [v["name"] for v in T["variants"]]


def fmt(t): t = int(t); return f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}" if t >= 3600 else f"{t // 60}:{t % 60:02d}"


def upload_md(E):
    U = E.get("upload", {}); L = E["_lines"]; beats = E["_beats"]["beats"]
    ch = [(0 if not i else L[k]["t0"], b["chapter"]) for i, (k, b) in enumerate((k, b) for k, b in enumerate(beats) if b.get("chapter"))]
    src = E["_script"].read_text().split("## Sources", 1)[1].split("\n", 1)[1]
    src = "\n".join(l for l in src.split("\n**Fact-check")[0].strip().splitlines() if l.startswith("- "))
    cred = json.loads((E["_dir"] / E.get("credits", "img/credits.json")).read_text()) if (E["_dir"] / E.get("credits", "img/credits.json")).exists() else {}
    used = {e["img"] for e in E["_beats"]["world"]["elements"] if e.get("img")}
    credits = "; ".join(sorted({(v.get("nasa_id") or v.get("title", k)) for k, v in cred.items() if k in used}))
    md = [f"# {E['brand']}: upload sheet", "", f"**Publish:** {U.get('publish', '')}", "", "## Title", E["title"], "", "Alternates: " + " / ".join(E.get("titles", [])), "", "## Description"]
    md += U.get("description", []) + ["", "Chapters"] + [f"{fmt(t)} {n}" for t, n in ch] + ["", "Sources", src, "",
           f"Image credits: NASA/JPL-Caltech, public domain ({credits}). Some images are NASA artist concepts. Diagrams marked \"illustration based on NASA data\" are drawn by Orbit's Logbook. Narration: synthetic voice (Kokoro TTS). Music: original, made for this channel.",
           "", "## YouTube settings", U.get("ai", ""), "", f"## Tags ({len(U.get('tags', []))})", ", ".join(U.get("tags", [])), "", "## Shorts"]
    md += [f"{i + 1}. {s['name']}.mp4 (upload copy in up/): {s.get('title', '')}" for i, s in enumerate(E.get("shorts", []))]
    md += ["", "## Thumbnails"] + [f"thumbs/{v['name']}.png" + (" (pick)" if i == 0 else "") for i, v in enumerate(E.get("thumbs", {}).get("variants", []))]
    (E["_dir"] / "upload.md").write_text("\n".join(md) + "\n"); return E["_dir"] / "upload.md"


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("episode"); ap.add_argument("--stage", default="all"); ap.add_argument("--workers", type=int, default=4); ap.add_argument("--draft", action="store_true")
    a = ap.parse_args(); E = load(a.episode); stages = {"validate", "audio", "check", "main", "shorts", "thumbs", "upload"} if a.stage == "all" else set(a.stage.split(","))
    t_start = time.time(); report = {"episode": E["slug"], "frames": E["_frames"], "vo_seconds": round(E["_vo_dur"], 3)}
    errs, warn = validate(E); [LOG("warn:", w) for w in warn]
    if errs: [LOG("ERROR:", e) for e in errs]; sys.exit(1)
    LOG(f"valid: {len(E['_lines'])} beats, {E['_frames']} frames ({E['_vo_dur']:.2f}s)")
    srv, port = serve(E["_dir"]); (E["_dir"] / "build").mkdir(exist_ok=True)
    if "audio" in stages: report["audio"] = make_audio(E)
    if "check" in stages: report["check"] = check(E, port)
    if "main" in stages:
        t0 = time.time(); W, H = (960, 540) if a.draft else tuple(E.get("size", [1920, 1080]))
        vid = E["_dir"] / "build" / ("draft-video.mp4" if a.draft else "main-video.mp4")
        render_range(E, port, W, H, 0, E["_frames"], vid, a.workers, q=0.85 if a.draft else 0.93)
        out = E["_dir"] / ("build/draft.mp4" if a.draft else f"orbit-{E['slug']}.mp4"); mux(vid, E["_dir"] / "build" / "mix.wav", out)
        p = probe(out); report["main"] = {"file": str(out), "seconds": float(p["format"]["duration"]), "frames": int(p["streams"][0].get("nb_frames", 0)), "render_s": round(time.time() - t0)}
        LOG("main", report["main"])
    if "shorts" in stages: report["shorts"] = shorts(E, port, a.workers)
    if "thumbs" in stages: report["thumbs"] = thumbs(E)
    if "upload" in stages: report["upload"] = str(upload_md(E))
    report["total_s"] = round(time.time() - t_start)
    rp = E["_dir"] / "build" / "report.json"; old = json.loads(rp.read_text()) if rp.exists() else {}
    report = {**old, **report}; rp.write_text(json.dumps(report, indent=1))  # partial runs update, never erase; LOG("done", json.dumps({k: v for k, v in report.items() if k != "check"}))
    srv.shutdown()


if __name__ == "__main__":
    main()
