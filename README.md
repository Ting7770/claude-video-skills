# 7 video skills for Claude Code

Unzip, then copy the 7 folders into `~/.claude/skills/` and start a new Claude Code session. Ask in plain words, e.g. "make a funny 3D cartoon Short about the first sandwich in space".

| Skill | Makes |
|---|---|
| toon-short | Funny 3D cartoon vertical Shorts (Blender toon 3D, local voice, captions, music) |
| shorts-factory | A whole season of Shorts: calendar, fact-checked scripts in parallel, render queue |
| doc-video | Continuous-camera documentaries and explainers |
| saas-launch-video | SaaS / product launch videos and ad reels (HyperFrames: HTML + GSAP to MP4) |
| link-edit | Talking-head edits from a link or file: cut silences, add motion graphics |
| reverse-video | Copy the editing style of a reference reel |
| stickman | Stickman explainer animations |

## Requirements (Mac, Apple Silicon recommended)
- Claude Code
- ffmpeg, Node.js 22+, Python 3.12 (`brew install ffmpeg node python@3.12`)
- Blender 5.x for toon-short (`brew install --cask blender`, then make sure `/opt/homebrew/bin/blender` exists)
- Local voice (Kokoro, free): `uv venv -p 3.12 ~/kokoro-venv && uv pip install --python ~/kokoro-venv/bin/python mlx-audio misaki[en] soundfile numpy` (toon-short also reads `TOON_TTS_PY` if your venv is elsewhere)
- doc-video: a venv at `~/video-venv` with playwright, numpy, scipy, Pillow
- saas-launch-video: the HyperFrames plugin for Claude Code
- link-edit: run `npm install` inside `link-edit/fx` once

Easiest setup: open Claude Code and say "set up the video skills in ~/.claude/skills, install anything missing". It can read each skill's README and do it.

## Notes
- Everything renders locally and free. Nothing posts anywhere by itself.
- Every skill fact-checks true stories and refuses invented proof numbers.
- Want more looks? The free Nafay 3D Style Library (nafay3d.com) has 7 more motion-graphics styles made for Claude.
