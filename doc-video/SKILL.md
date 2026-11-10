---
name: doc-video
description: Make a cinematic documentary or explainer video entirely in code - one continuous camera move over one big world (a map, a desk, a board), real photos dropping in as prints, eased camera moves, grain, glow, vignette, every visual landing on the spoken word - with a synthetic narrator, original music, 3 Shorts and 3 thumbnails, from one command. The engine behind Orbit's Voyager episode. Use for "Netflix-style documentary", "continuous camera explainer", "history/space/company story video", "explainer for my business", client documentary requests, or new Orbit long-form episodes.
---

# doc-video

The engine lives at `the bundled engine/ folder (this skill's directory)`. Read its `README.md` first: the episode folder contract (`episode.json`, script, `vo/vo.wav` + `vo/vo.json`, `beats.json`, `img/` + `credits.json`), the beats element and camera vocabulary, and the producer checklist. `~/Business/Orbit's Logbook/videos/ep02-voyager/` is the worked example (`author_beats.py` is the readable source for `beats.json`).

## Workflow
1. **Script**, one idea per line, sourced facts (for a client: only their facts), spoken numbers as words, no em dashes.
2. **Voice:** Kokoro (`engine/kokoro_say.py`, bm_george 1.0 for Orbit; pick a fitting voice for others) with per-line timings.
3. **Beat table first:** time, narration, the ONE hero on screen, any on-screen text (never both spoken and typed), camera move. Show it to the user and get a yes before rendering.
4. **Images:** real photos the client owns or public-domain sources with credits; drawn diagrams labeled "illustration" (or "illustration based on <source> data").
5. **Render:** `"$HOME/Business/YouTube Channel/videos/tenant-lying-bank-test/.venv/bin/python" "$HOME/Business/Orbit's Logbook/tools/orbit-doc/orbit_doc.py" "<episode_dir>"` (`--draft` 960x540 preview, `--stage` to run selected stages, `--workers` max 4 on the 16 GB MacBook; about 90 min for 11 minutes).
6. **Check** the contact sheets and camera-move strips in `build/check/`; fix clutter, unreadable type, jerks or dead stops before the final render.
7. **Deliver** the film, Shorts (`up/` copies under 10 MB), thumbnails and `upload.md`. Never upload or send; the user approves. Delete `build/chunks/` afterwards if disk matters.
