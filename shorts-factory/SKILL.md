---
name: shorts-factory
description: Plan, write and render a whole season of YouTube Shorts for one channel (30 to 90 days, one a day) - topic calendar with hooks and tags, fact-checked scripts written in parallel batches, a shared 3D asset list, and an overnight render queue on the Mac mini, ending in a review list for the user. Built on /toon-short. Use for "write shorts for the next 90 days", "a month of Shorts", "plan a season", "batch the Orbit/TENANT Shorts", "render overnight on a second Mac", or a client who wants Shorts every day.
---

# shorts-factory

One channel, one season, one Short a day. `/toon-short` makes a single Short; this skill runs the whole line around it. Proven on Orbit's Logbook on 2026-11-09 (89 scripts in about 2 hours).

Never upload, schedule or post. the user reviews and uploads.

## 0. Inputs
- Channel, its format and voice (read the channel's memory note and series bible).
- What already exists: finished Shorts, scripts in progress, the last Studio numbers (run `/youtube-audit` if they're stale).
- Season length and start date. Default: 90 days, 1 a day.

## 1. Calendar
Write `<channel folder>/SHORTS-<N>-DAYS.md`: a table of Day | Date | Title (the hook) | Story / payoff | Tag | Status.
- Put already-finished Shorts first, then new topics.
- Each topic must be true and checkable (for fiction channels: each story must stand alone and open on its own hook).
- Tag every topic (e.g. Apollo, Robots, ISS, Soviet, Myth). The Sunday check compares subscribers by tag.
- Pin holidays to their dates (Dec 16 Gemini 6, Dec 24 Apollo 8, Dec 25 Skylab worked for Orbit).
- Keep a bench of spare topics for swaps.
- No two near-identical topics on back-to-back days.

## 2. Pilot batch first
Write 7 scripts with one `video-studio` agent before anything else. Check them against the channel's best Short (hook, deadpan, length, sources, loop ending). Fix the brief once here instead of in 80 scripts.

## 3. Fan out
Split the rest into about 6 groups **by setting** (each writer learns one set of scenes and reuses it), 11 to 14 scripts each, one `video-studio` agent per group, all launched in one message, in the background. Give each a topic file (day, folder `short-NN-slug`, title, story) and the brief:
- Templates: the channel's best `script.md` files. Engine: `tools/toon-short/` (prefer existing scenes and props).
- Every fact from a primary or reputable source, with the URL and the exact quote. Soften or cut what can't be verified. If a story falls apart, stop and report (it becomes a myth-buster or a bench swap).
- 15 to 18 shot lines, 130 to 155 words (2.7 words/s = 45 to 60 s). Hook states the funniest true fact. Last line loops to the first frame.
- `{spoken|caption}` numbers, no em or en dashes, no teasers, no "follow for more", no conspiracy framing, family-friendly.
- `## New assets needed` per script; scripts only, no rendering.

Budget: about 250k to 300k agent tokens and 20 to 30 minutes per 11 to 14 scripts.

## 4. Reconcile
- Sync the calendar from the files: real titles, the verified first sentence of each description, folder, status.
- Fix clashes the writers report (e.g. two pen stories on consecutive days).
- Report to the user: what the fact check changed, stories that turned into myth-busters, names the voice may mispronounce.

## 5. Trim the asset list
Merge every script's `## New assets needed`. Build reusable pieces, not one-offs: a generic astronaut and cosmonaut with a name patch instead of a model per person, about 10 shared sets. Rank assets by how many Shorts each unlocks and build in that order. Assets are built on the MacBook in `tools/toon-short/blender/`, then synced to the mini.

## 6. Render queue on the Mac mini
Optional: run renders on a second Mac over SSH (copy the engine and scripts, render one Short at a time, copy MP4s back). Render the scripts whose assets exist, oldest calendar day first, one at a time (EEVEE fights itself in parallel). Each Short leaves `<folder>.mp4`, `up/<folder>.mp4` (under 10 MB), `upload.md` and `build/contact.jpg`. Copy finished files back to the MacBook folder.

## 7. Review
Show the user the contact sheets and the upload files due in the next 7 days. They approve and upload. After each upload, delete that Short's `build/` cache.

## Weekly loop (Sundays)
Pull the numbers (`/youtube-audit`), compare subscribers and average % viewed by tag, move the next weeks' topics toward the winning tags, swap in bench topics for the losing ones.
