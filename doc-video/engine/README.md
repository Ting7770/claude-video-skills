# orbit-doc: the Orbit's Logbook episode engine

This engine turns one episode folder into a finished long-form documentary, three vertical Shorts, three thumbnails and an upload sheet. The film is one continuous code-drawn camera moving over one big illustrated world. Real NASA prints and drawn diagram cards drop onto that world where the story happens. Each narration line has one hero, and everything else dims. Type is huge and lands on the spoken word.

Episode 2 (Voyager) was built by running this engine. The reference episode folder is `videos/ep02-voyager/`.

## One command

```bash
PY="$HOME/Business/YouTube Channel/videos/tenant-lying-bank-test/.venv/bin/python"
"$PY" "$HOME/Business/Orbit's Logbook/tools/orbit-doc/orbit_doc.py" "<episode_dir>"
```

The default runs every stage in order: `validate, audio, check, main, shorts, thumbs, upload`. To run only some stages, pass `--stage check` or `--stage main,shorts`. Use `--workers N` to set the number of parallel Chromium renderers (default 4). Use `--draft` for a quick 960x540 cut at `build/draft.mp4`.

`build/report.json` has the summary: frames, length, loudness, render time, camera check and Shorts sizes.

Rendering is split into 600-frame segments (20 s of film each). A finished segment is kept in `build/chunks/`, so if a run is interrupted, rerunning the same command resumes where it stopped. To force a fresh render, delete `build/chunks/`. Speed on the MacBook: about 13 frames per second with 4 workers, so an 11-minute film takes about 25 minutes. The default is 4 workers; with 6, the 16 GB machine runs out of memory and gets slower.

## Input contract (everything lives in the episode folder)

| File | What it is |
|---|---|
| `episode.json` | Metadata: slug, brand line, title(s), paths, fps, size, music seed, LUFS, Shorts, thumbnails, upload text. See `videos/ep02-voyager/episode.json`. |
| script (`episode.json.script`) | The narration markdown. Lines are read the same way `kokoro_say.py` / `kokoro_cast.py` read them: sections after the first `---`, up to `## Sources`, skipping cue, heading, `✂` and `**` lines. The `## Sources` list is copied into the upload sheet. |
| `vo/vo.wav` + `vo/vo.json` | The voiceover and per-line times. Make them with `~/Business/YouTube Channel/tools/kokoro_cast.py <script> vo/vo.wav bm_george 1.0 cast.json`, using cast.json `{"voices":{},"lines":{}}`. **Video length = VO length, to the frame.** |
| `beats.json` | The world, plus one beat per narration line (schema below). The beat count must equal the line count. |
| `img/` + `img/credits.json` | NASA/JPL public-domain images (data only) and their metadata (`nasa_id`, `title`, `page`). |

For an editable source of `beats.json`, use a small Python authoring script, like `videos/ep02-voyager/author_beats.py`. The engine reads only the JSON.

### beats.json

```json
{"world": {"size": [30000, 12000], "bg": "#04060D", "stars": 4500, "elements": [ ... ]},
 "beats": [ {one object per narration line, in order} ]}
```

**Elements.** Each element has an `id` and a `type`. A numeric property can be animated from beats. `a` (opacity) exists on every element.

| type | fields | animatable |
|---|---|---|
| `sun` | x, y, r | a |
| `planet` | x, y, r, color [light, dark], bands?, ring? (css color), haze? | a |
| `orbits` | cx, cy, radii[], flat | a |
| `bubble` (heliosphere-style) | cx, cy, rx, ry | a, glow |
| `ring` | cx, cy, rx, ry, dash?, color, width | a, glow |
| `label` (big world text, Anton) | x, y, w, h, size, text, color | a |
| `glow` | x, y, r, color | a |
| `path` | points [[x,y]...] (Catmull-Rom), color, width, dash?, `dot` (drawn up to that dot) or `reveal` | a, reveal |
| `dot` (craft marker) | path, size, color, label? | k (float index along the path points), vis, glow, rot, flash |
| `thread` (signal line) | from (element), to (dot) | a, static (0..1), pulse (0..1 along the line; -1 = none) |
| `wind`, `burst`, `drape`, `ripples` | see engine.js DRAW | a, p (burst) |
| `print` (real photo, paper border, credit) | img, x, y, w, rot, credit, `drop` (beat index), `dropOn` (word), hires? | a |
| `card` (drawn diagram) | kind: gauge, tone, trace, memory, craft; x, y, w, h, drop, **note** (must contain "illustration") | kind props: p1/p2, p, hi, red/chip/scatter, gen/lit/plasma/heat/thr |
| `mark` (yellow circle on a print) | on (print id), at [fx, fy], r | a |

**Beats.** There is one object per narration line. Every field is optional.

- `hero`: an element id or a list of ids. The hero is redrawn bright over a dark veil. `dim` sets the veil strength (default 0.58 with a hero, 0.6 with text alone, 0 with neither).
- `text`: on-screen type, shown with `on` (a word of the spoken line; the type lands on it). With a hero it is a caption at the bottom (7.8% of the short side). Without one it is a centered hero word (13.5%, or `textSize`). The validator refuses repeated text anywhere in the episode.
- `cam`: the camera target for the line:
  - `{"x","y","r"}`: r is half the visible span on the short side, in world units.
  - `{"on": id | [ids], "fill": 0.8}`: frames the element(s).
  - `{"on": printId, "at": [fx, fy], "r": R}`: pushes into a point on a photo.
  - `{"on": dotId, "r": R, "follow": true}`: rides along with a moving craft.
  - `{"same": true}`: keeps the previous shot.
  - Extras: `push` (zoom drift per second, default 0.014; negative pulls back), `drift`, `dur` (seconds or `"beat"`), `lead` (how early the move starts, default 0.35 s), `dx`/`dy`.
- `set`: a list of `[ "id.prop", value, duration|"beat"|"next", "word", linear? ]` property animations. They start on that spoken word.
- `chapter`: a chapter name for the upload sheet (the first one is 0:00).
- `brand`: true shows the series mark (`episode.json.brand`) small in the corner for that line.

### Camera and look (all automatic)

- **Camera path:** moves use the van Wijk-Nuij zoom-pan, so a long move pulls out, travels, then pushes in. Easing is cubic plus sine, and the whole track is Gaussian-smoothed (0.16 s). Holds keep a slow push and drift, so the camera never stops dead.
- **Motion blur:** shutter-accumulated subframes, used whenever the camera moves faster than 10 px/frame.
- **Finish:** subtle handheld jitter, bloom, film grain and a vignette.
- **Fades and Shorts framing:** fade in from black and out at the end. Shorts are rendered from the same beats at 1080x1920, with their own camera track.

### Audio

The voiceover is mixed with an original synthesized ambient bed (seeded per episode, so it is ours). The bed ducks under speech (-28 dB) and rises in the pauses (-19 dB). The mix is then two-pass loudnormed to **-14 LUFS, -1 dBTP**. Shorts get their own slice, normalized the same way.

## Outputs (in the episode folder)

| File | What it is |
|---|---|
| `orbit-<slug>.mp4` | 1920x1080, 30 fps, H.264 CRF 16, AAC 256k |
| `short-N.mp4` + `up/short-N.mp4` | 1080x1920 Shorts; the upload copies are under 10 MB |
| `thumbs/*.png` + `thumbs/preview.jpg` | Made by `tools/thumbs/thumb.py`, orbit style |
| `upload.md` | Title, description, chapters, sources, credits, AI-disclosure guidance, tags, Shorts, thumbnails |
| `build/check/` | `sheet-*.jpg` (a still of every beat at its hit), `moves/*.jpg` (8-frame strips of the 10 fastest moves), `check.json` (max speed and acceleration, dead frames) |

## Making the next episode (Producer agent checklist)

1. Write `scripts/epNN-<topic>.md` in the ep02 format: one idea per paragraph, numbers spoken as words, no em dashes, `## Sources` at the end. Every fact needs a NASA/JPL or peer-review source.
2. Make the voiceover with kokoro_cast (bm_george 1.0) into `videos/epNN-<topic>/vo/`.
3. Download NASA/JPL public-domain images into a new `img/` folder (images-api.nasa.gov `nasa_id` lookups), and write `credits.json`.
4. Copy `videos/ep02-voyager/author_beats.py` and `episode.json`, then lay out the new world and beats. Rules:
   - one hero per line;
   - a spoken phrase is either shown on a real document or typed, never both;
   - text is 34 characters or fewer;
   - drawn diagrams carry "illustration based on NASA data".
5. Run `--stage validate,audio,check`. Look at `build/check/sheet-*.jpg` and `moves/`, fix anything empty, cluttered or jerky, and repeat.
6. Run the one command for everything else. Then compare `build/report.json` with the VO length.

## Quality bar (2026-11 teardown)
Full checklist: `~/Business/YouTube Channel/research/viral-teardown-2026.md`, section 3, rules D1 to D7 (and O1, O3, O5 for Shorts cut from a doc). Check pacing with `python3 "$HOME/Business/YouTube Channel/tools/pace.py" <video.mp4>`.
Headline numbers: 60% of frames are full-screen hero imagery, not black space with small labels (the Voyager grid fails this; NullSpace and SEA pass); a 45 to 90 s image-led cold open; narration 1.8 to 2.4 words a second; no fully static frame over 6 s; flagships 15 to 25 min; doc Shorts are re-cut to 2.0 s shots, never a 30 s crop of one camera move.
