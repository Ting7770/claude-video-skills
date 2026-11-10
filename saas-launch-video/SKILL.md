---
name: saas-launch-video
description: Make SaaS / tech launch videos and short ad reels as motion graphics in code (HyperFrames: HTML + GSAP rendered to MP4 locally), with a Problem-Agitate-Solve script, voice-synced kinetic captions, silk-ribbon backgrounds, phone/browser/UI mockups and a free local voiceover. Use for "SaaS launch video", "tech launch motion graphic", "product demo video", "ad creatives / reels for Rooted in Leads (or any of the user's brands)", "make it like the Sentient Desk / Yustudio video", or turning a script into a vertical ad.
---

# SaaS launch video

the user's house method for launch videos and ad reels. It merges four sources:
the **launch-motion** skill (Sanji Chien, Higgsfield guide; motion rules, brief and storyboard templates, installed at `~/.claude/skills/launch-motion`),
the **Sentient Desk** reel by Yustudio (reverse-engineered beat sheet),
**noamdorr/saas-product-demo-video** (beat-synced cuts, SFX on events, UI rebuilt as components; not installed, Remotion),
and the Rooted in Leads ad system built on 2026-10-31.

Engine: **HyperFrames**, not Remotion (the user chose HyperFrames: plain HTML/GSAP, no team-size license). Load `/hyperframes` for the render contract when building something new. Every frame is a pure function of time: one paused GSAP timeline, `fromTo()` entrances, count-ups and typing through proxies (`onUpdate`), no `Math.random()`/`Date.now()`.

## The fastest path: reuse the generator

- `gen.py` holds every scene type and the `ADS` dict of scripts. One ad = a list of `(scene type, voiceover line, args)`.
- `template.html` holds the look (CSS tokens, silk ribbons, captions, all scene styles).
- `python3 gen.py --voice f --only <id>` builds one ad; `VOICES=f ./render-all.sh` builds and renders all to `renders/`.
- `python3 gen.py --clips` builds silent looping website feature clips (`../site-clips/`).
- `python3 gen.py --export scripts.json` feeds the scripts board artifact (https://claude.ai/artifact/EujDSmhjo8wL2ekh7qTT72).
- For a new brand: copy the folder, swap the CSS tokens, logo and copy; scene code stays.

Scene types: `text` (caption only), `walk` (leads pop around a ringing phone, line up, walk into the competitor's house), `stat` (10 people, answered ones go green, sourced number), `meet` (logo reveal + silk swell), `phone_lock`, `phone_chat`, `browser` (mock site + quote form), `realsite` (real client site scrolling in a browser), `realmaps` (real Google listing with rating highlight), `orb` (glowing AI ring that types), `cards` (glass system cards), `stars`, `calendar`, `timer`, `step`, `rank` (you climb to #1), `ai_chat` (AI assistant answer), `blog`, `pipeline` (CRM card moves New lead → Won), `end` (logo + close line + CTA). Any scene can take `"dark": True`.

## 1. Script: Problem → Agitate → Solve (the Sentient Desk beat sheet)

1. **Problem** (0–5s): name the pain in money. "Every missed call is money going straight to your competitor."
2. **Agitate** (5–14s): make it hurt with a number or a story. Numbers must be real and sourced on screen (e.g. 411 Locals: small businesses answer about 4 in 10 calls), or framed as "if" maths ("Miss 3 calls a week on $500 jobs = $78,000 a year"). Story version: "It's 2 AM. A pipe just burst. They call you. You're asleep. The next plumber picks up."
3. **The turn**: "Meet Rooted." Short brand name only; long names slow the turn.
4. **Solve**: give the AI a face (orb types "Hi! How can I help?"), show the product doing the job, then the twist: "It doesn't just reply. It books the estimate."
5. **Close**: one line the whole brand repeats. Rooted in Leads closes on "Fill your calendar with booked estimates."
Keep each voiceover line 3–10 words, one idea per beat. Cold ads: aim for 20–30 s.

## 2. Motion rules (launch-motion + what worked)

- Nothing moves linearly; nothing ever fully stops. Each scene's content does a slow camera pull-back (scale 1.07 → 1, x drift) for its whole duration; silk ribbons drift the whole video and a ribbon sweeps diagonally through on every cut.
- Entrances ~0.5 s with slight overshoot (`back.out`, or blur 16px → 0 with `expo.out`). Exits faster (~60%), ease-in, sliding sideways with motion blur (x -90, blur 16px). No hard cuts.
- Stagger repeated elements 2–4 frames apart (cards, people, stars); overlap the next move during the last ~20% of the previous one.
- Counters run ~1 s, ease-out, never jump. Clicks get a press (1 → 0.96 → 1). Cursors travel on arcs and settle with a tiny overshoot.
- Captions are the voiceover, word for word: each word blurs in when spoken, the centred line grows so it slides across, phrases of up to 4 words roll on with a sideways blur exit. Caption font: **Inter Tight 500**, accents bold in brand colour.
- Icons bold and filled (people, house, phone at stroke 3 / solid fill), never thin outlines.
- Anything important holds ≥ 1.5 s. Dark palette is a scene (AI moment, night story), the brand stays light.

## 3. Voice and sound

- Free local voice: Kokoro via `npx hyperframes tts` with `HYPERFRAMES_PYTHON=~/kokoro-venv/bin/python`. the user approved **af_heart at speed 0.9** (calm female narrator, ~138 wpm like the reference). He disliked am_michael.
- Money and numbers are spoken in words, shown in digits: `speakable()` in gen.py turns "$500 jobs" into "five hundred dollar jobs" and "$78,000 a year" into "seventy-eight thousand dollars a year". Check any new number pattern by ear.
- Paid voices (ElevenLabs, HeyGen) only with the user's key and OK. No paid AI video services unless the user asks.
- Music: compose it in code with `tools/music/compose.py <out.wav> <root_midi> <bpm> <air|tech> [seconds]` (clean pads, pluck arpeggio, sub bass, soft drums; builds after the hook, resolves on the logo). the user disliked MusicGen's hissy output, so MusicGen is a last resort. Mix with ffmpeg sidechain ducking under the voice (music volume ~0.5).
- Older option: local MusicGen bed (not included, ~2.5 min for 30 s) mixed under the voice with ffmpeg sidechain ducking; or a track the user supplies; or Meta's library at upload.
- Sound effects (the user wants these, like Sanji's launch videos): synthesized kit at `tools/sfx/` (click, pop, whoosh, ding, tick; `make_sfx.py`). Place each on the frame its animation lands: whoosh ~0.4 s before every cut, click on cursor clicks/buttons, pop when cards/phones/logos land, ding on results and the logo, ticks while numbers count or text types. Ads: `sfx_events()` in the RIL gen.py does it automatically. Finished films: build a placed track like `plume-demo/music/sfx_track.py` and mix it on top.

## 4. Real over mock

When showing the website or Google, use real footage of a real client (captured with Playwright via `channel: "chrome"` for full-page site shots; Google Maps via Claude in Chrome), cropped to name, rating and photo. Crop out street addresses, reviewer names and the user's own Google account. Label it "Real client site" / "Real client · Google Maps". Ask before featuring a new client.

## 5. Copy rules (house rules)

No em dashes. No "Free", pricing, timelines or "month to month" in RIL creative. No invented client numbers or stats; real numbers only with a source. Don't add client proof scenes unless asked. Trade-neutral wording for multi-trade ads ("job site", "contractor", "estimate"); a single-trade story ad may name the trade. Competitors are "Competitor #1/#2/#3", never a real-sounding name. Avoid "good jobs". Generic phone/AI mockups, no Apple or OpenAI marks.

## 6. Checks before render

- `npx hyperframes check` passes in each project; read the contact sheet, and look at the frame inside the scene you changed (snapshot `frame-00`, the last file is the auto final frame).
- No overlapping text, nothing clipped, first frame not empty (it's the thumbnail), AA contrast including mid-transition.
- Confirm length, then render: `npx hyperframes render . -q high -o <file>.mp4` with `PRODUCER_BROWSER_GPU_MODE=hardware`.
- Deliverables: 9:16 for Reels/Stories by default; offer 16:9 (website hero, YouTube) and 1:1 / 4:5 (feed) cuts.

## References

- `~/.claude/skills/launch-motion/` for the brief template, 5-scene storyboard template (hook, problem, product, payoff, logo + CTA) and the Upwork pitch template.
