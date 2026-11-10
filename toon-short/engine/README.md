# toon-short

Turns one `script.md` into a finished 3D cartoon YouTube Short: 1080x1920, 30 fps, original toon 3D, synthetic voice, burned-in captions, music and sound effects, all made locally for free. Nothing is uploaded.

## One command

```bash
python3 "<skill dir>/engine/make_short.py" "<video folder>/script.md"
```

What it does, in order:

1. Kokoro reads each narration line (`vo/line_NN.wav` and `vo/durations.json`).
2. The line lengths set the shot timings.
3. Blender renders one shot per line (`build/shots/`).
4. PIL draws the captions.
5. numpy makes the music and sound effects, mixed to -14 LUFS.
6. ffmpeg joins it all into:
   - `<folder>.mp4`
   - `up/<folder>.mp4`, the under-10 MB copy (two-pass x264, aac 128k)
   - `upload.md`
   - `build/contact.jpg`, one frame every 1.5 s
   - `build/report.json`

Options:

- `--draft`: half resolution and 4 samples, written to `build-draft/` and `<folder>-draft.mp4`. Use it to check timing and blocking fast.
- `--jobs N`: how many Blender renders run at once. Default 1. EEVEE is GPU-bound on the M1 Pro (about 1.4 s a frame at 1080x1920 and 8 samples), and parallel renders fight over the GPU and run several times slower. More than 1 only helps for `--draft`.
- `--scale 75`: render at 75% (810x1440) and upscale with lanczos to 1080x1920. Toon shading survives this well, and it is about twice as fast. Use it when the GPU is busy.
- `--only 3,7`: render only those shots (0-based), for example after fixing one shot.

Each shot is cached by a hash of its spec plus the Blender library, so a re-run renders only what changed. The voice is re-made only when the text changes.

Requirements: Blender at `/opt/homebrew/bin/blender`, Kokoro in `~/kokoro-venv` (mlx_audio; or set TOON_TTS_PY to your venv python), system `python3` with numpy and Pillow, and ffmpeg (no drawtext needed).

## script.md format

```
# Title for humans
title: Under 60 chars, curiosity first
description: One or two sentences.
hashtags: #space #NASA #history
voice: bm_george 1.0
source_line: Sources: NASA History Office, ...

---

[capsule.two | crash | sandwich_float, crumbs_drift, surprise:all@0.08]
An astronaut smuggled a corned beef sandwich into space, and Congress got involved.

[launch.low | follow_up | liftoff@0.03]
{Nineteen sixty-five|1965}, {Gemini Three|Gemini 3}. Grissom and Young blast off.

---

## Sources
- ...
```

- Each block is one shot: a `[scene.view | camera | actions]` line, then the narration it covers.
- Scene options go after a colon: a cast name (`studio:gus.close`) or `key=value` pairs split by `;` (`moon:who=al,ed;lm=back;flag=1.wide`, `mission:label=APOLLO_12;who=eecom.screen`). Use `_` for spaces in labels, and `who=none` for an empty set. Values cannot contain `.` or `,` inside an action.
- `{spoken|caption}`: the voice says the left side and the caption shows the right side (numbers are spoken as words and shown as digits).
- An action is written `name`, `name:arg`, `name:arg@start` or `name:arg@start-end`. Start and end are fractions of the shot (0 to 1).
- Keep it 45 to 60 s, about 150 to 170 words with bm_george at 1.0. Put the hook in line one and end abruptly so the last line loops back into the first.

## Library

**Scenes and views** (`blender/scenes.py`):

| scene | views | what is in it |
|---|---|---|
| capsule | two, young, gus, panel, window | Gemini-style two-seat cabin, instrument panel, porthole with Earth |
| launch | wide, low, top | Titan-style rocket, gantry, pad, ocean |
| shuttle | wide, low, top | Shuttle stack on the same pad |
| orbit | hero, wide | capsule exterior over a low-poly Earth |
| deli | wide, counter | sandwich shop counter with Wally behind it |
| studio | close, med | any cast member on an orange backdrop; pick who with `studio:gus.close` (default young) |
| hearing | wide, member, low | wood-panelled hearing room, three members, gavel |
| mission | wide, boss, screen | mission control consoles, big screen, NASA boss |
| moon | wide, low | lunar surface, Earth in the sky, astronaut with a bubble helmet |
| station | close, wide | modern station module, crew member in a polo |
| saturn | wide, low, top, strike | Saturn V on the pad; `storm=1` adds a low grey ceiling and rain (`strike` is the wide view for lightning) |
| lm | two, three, window, \<name\> | lunar module cabin, standing crew, two triangle windows; `outside=moon` or `space` |
| ocean | wide, low, capsule, heli, \<name\> | open sea, Mercury capsule bobbing, crew treading water; `heli=0` drops the helicopter |
| workshop | wide, table, peg, \<name\> | 1970 engineers' table with CO2 cartridges, tape, bags, cardboard, hose, sock |

Scene options added for the Apollo set: `capsule:who=a,b,c` (one to three seats, views `two`, `three` and one per name), `studio:who=a,b;bg=blue` (two-shot `two`, backdrops orange, blue, navy, green, red, cream), `mission:label=..;who=..`, `moon:who=a,b;lm=back|ladder;flag=1` (ladder adds views `ladder`, `lm`, `boot`), `orbit:craft=gemini|csm|lm|pair|stack|mercury|ascent;body=earth|moon|sun|none;labels=CHARLIE_BROWN/SNOOPY`.

**Cast** (`CAST` in `scenes.py`): young (orange trim), gus (blue trim), wally, member, member2, member3, boss and crew. Apollo crews: pete (red, short), alan, dick, al, ed, tom, gene, jim, fred, jack; plus reporter, eng, eng2 and eecom. A `height` entry scales a character. They are deliberately not likenesses of real people: chunky toy bodies, big heads and simple faces.

**Camera moves** (`render_shot.py`): `push_in`, `pull_out`, `orbit_l`, `orbit_r`, `pan_l`, `pan_r`, `tilt_up`, `follow_up` (for launches), `crash` (zoom burst), `rise`, `dutch` and `shake`. Every move eases out fast and then drifts, with a little handheld sway and an impact shake on hits.

**Actions** (`blender/actions.py`):

- Faces: `talk:who`, `surprise:who|all`, `angry`, `frown`, `grin`, `wink`
- Body: `point`, `shrug`, `arms_crossed`, `jump`, `float`
- Props: `sandwich_float`, `sandwich_hold:who`, `sandwich_out:who`, `give:young>gus`, `bite:who`, `crumbs:N`, `crumbs_drift`, `crumbs_panel`, `pocket:who`, `pouch`, `xmark:scale`, `clipboard:who`, `tortilla:who`
- Effects: `liftoff`, `gavel`
- Apollo set: `word:TEXT` (big 3D word pinned to the top third of the frame; `_` = space, `~` = cream instead of orange, `*0.3` = size), `flash`, `lightning` (`:2` strikes twice), `alarms`, `glitch` (junk on the mission screen), `sce_switch`, `laugh`, `hatch_blow`, `sink`, `surface`, `lift_fail`, `swim`, `dimes:N`, `dime_stack:N`, `club`, `swing:who>dud|far` (contact at the start time), `throw`, `dust`, `ladder_hop`, `tumble`, `undock`, `descend`, `zoom_by`, `gauge:up|down`, `square_peg`, `assemble` (the Apollo 13 mailbox builds itself), `tape_spin`, `item_pop:sock|tape|bag|card|square|round|hose`, `cash`, `notepad`, `handshake:a>b`

Blinks and idle sway run on their own. The capsule and station scenes also get a zero-g bob.

**Assets** (`blender/assets.py`): `character()` (hair styles crop, bald, long), Saturn V, Apollo CSM, lunar module (separable ascent stage), Moon globe, Mercury capsule (with hatch), helicopter, coin, lightning bolt, golf club and ball, US flag, LiOH canisters (square and round), round socket, duct tape, sock, plastic bag, cardboard, hose, the "mailbox" adapter, gauge, big labelled switch, cash stack, notepad, `word()` and `rod()`, sandwich, crumbs, food pouch, tortilla, red X, gavel, clipboard, microphone, low-poly Earth (with clouds and an atmosphere), moon surface, Gemini capsule, Titan rocket, shuttle stack, launch tower, flames, smoke, room box and console.

**Look** (`blender/toon.py`): every material is a cel ramp (Diffuse, Shader to RGB, a ramp from a cool shadow through the base colour to a warm highlight, into Emission). Outlines are inverted hulls. Shapes are beveled and subdivided rounded boxes. The world colour comes from the world Background node, and EEVEE renders with the Standard view transform. The palette follows the Orbit's Logbook brand: navy, orange, cream and pale blue.

## Adding to the library for a new story

- **New prop**: write a function in `assets.py` built from `box()`, `ball()`, `cyl()`, `torus()`, `prism()` and `text()` with `toon()` colours.
- **New scene**: write `build_<name>(ctx)` in `scenes.py`. It sets `world()` and the lights, places assets, stores animatable parts in `ctx[...]` and sets `ctx["views"] = {name: (cam_loc, target, lens)}`. Register it in `SCENES`.
- **Ambient animation** (waves, rain, rotors): append a function `fn(N)` to `ctx["anim"]` in the scene builder; it runs after the actions.
- **New action**: write `fn(ctx, f0, f1, N, arg)` in `actions.py` that keyframes things, and register it in `ACTIONS`. To give it a sound, add it to `SFX_MAP` in `make_short.py`.
- **Test one scene quickly**: write a shot JSON with `"still": 0.5, "pct": 50` and run `blender -b --factory-startup -P blender/render_shot.py -- shot.json`.

## Sound

The music is original and generated in code (a C-Am-F-G pluck, pad and bass loop at 104 BPM), so there are no rights issues. The effects are synthesized too: whoosh on every cut, pop, crunch, sparkle, thud, rumble, buzz and boing. Music sits about 17 dB under the voice and ducks while the voice is speaking. The effects sit about 9 dB under the voice. A compressor and a two-pass loudnorm bring the mix to -14 LUFS with a -1.5 dBTP ceiling.

## Quality bar (2026-11 teardown)
Full checklist: `~/Business/YouTube Channel/research/viral-teardown-2026.md`, section 3, rules O1 to O10. Check every render with `python3 "$HOME/Business/YouTube Channel/tools/pace.py" <short.mp4>`.
Headline numbers: average shot 2.0 s or less (sandwich was 3.5 s; Ricks Clips 1.2 to 2.2 s, Zack D 0.7 to 1.5 s); 3+ cuts in the first 5 s; 40% close-ups; narration 3.0 to 3.6 words a second; no date or proper name in the first 8 s; one "You see," turn; end on the payoff word with no outro; small white 1 to 3 word captions that never cover a face; true stories only, sourced.
