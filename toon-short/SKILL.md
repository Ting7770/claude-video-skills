---
name: toon-short
description: Make a funny 3D cartoon vertical Short (45 to 60 s, 1080x1920) from a true story or a business's story, fully local and free - Kokoro voice, Blender toon 3D, burned-in captions, music, mixed to -14 LUFS, plus an under-10 MB upload copy. The engine behind Orbit's "He Smuggled a Sandwich Into Space" Short. Use for "3D cartoon short", "Zack D Films style", "animated short about my business", "funny true story short", client video requests, or new Orbit Shorts.
---

# toon-short

The engine lives at `the bundled engine/ folder (this skill's directory)`. Read its `README.md` first (script.md format, shot vocabulary, scene/prop library in `blender/assets.py` and `blender/scenes.py`).

## Workflow
1. **Brief.** Who it's for (Orbit, a the user brand, or a client), the one absurd or surprising true detail, the platform (YouTube Shorts / Reels / TikTok; TikTok pays only for videos over 1 minute).
2. **Facts.** Verify every claim from primary sources; soften anything shaky. For a client, use only facts they gave you or that are public on their site/Google profile. Never invent proof numbers or reviews.
3. **Script** (`<folder>/script.md`): hook states the funniest/most surprising fact in the first 2 s (first word under 0.5 s), nonstop narration (~2.3 words/s), a visual change every ~1.5 s, payoff last, abrupt ending that loops into the hook. Spoken numbers as words. No em dashes. Deadpan tone works best.
4. **Assets.** If the story needs a set or prop the library lacks (a service truck, a house, a shop counter), add it to `blender/assets.py` / `scenes.py` as a reusable, modular piece. Characters are original cartoons, never likenesses.
5. **Render:** `python3 "<skill dir>/engine/make_short.py" "<folder>/script.md" --scale 75` (`--draft` for a fast check, `--only N,M` to redo shots). One render at a time; it is GPU-bound.
6. **Check** `build/contact.jpg` and fix anything ugly, unreadable, off-model or static before delivering. Then delete `build/` PNG frames if disk matters (they are cache).
7. **Deliver** the mp4, the `up/` copy and `upload.md`. Never upload, post or send; the user approves.

AI disclosure guidance: narration is a synthetic voice; visuals are original procedural 3D, not AI-generated.
