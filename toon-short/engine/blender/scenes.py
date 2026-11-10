"""Scene library. Each builder sets world + lights + assets and returns a ctx dict:
  ctx["views"][name] = (camera_loc, target, lens)
  ctx[<role>] = parts/objects that actions can drive (e.g. ctx["young"], ctx["sandwich"]).
Add a new scene: write build_<name>(ctx) and register it in SCENES."""
import math, random
from toon import *
from assets import *

CAST = {  # recurring characters, consistent across every shot and every story
    # Young: round wide face, orange-blond swoop fringe, thin light brows, white helmet with orange rim.
    # Gus: long narrow face, dark flat-top, thick dark brows, sky-blue helmet with navy rim. Readable at a glance.
    "young": dict(kind="astronaut", accent="#f08a24", skin="#f2c39b", face=(1.1, 0.95, 0.93), hair="#d9963a", tuft="swoop",
                  brow=(0.1, 0.035, 0.028), brow_col="#b8752e", helmet_col="#f8f6f0", rim_col="#f08a24"),
    "gus": dict(kind="astronaut", accent="#2f6fd0", skin="#e3a77e", face=(0.88, 0.95, 1.14), hair="#2b1d14", tuft="flat",
                brow=(0.14, 0.05, 0.05), brow_col="#2b1d14", helmet_col="#a9d4f5", rim_col="#1f2a44"),
    "wally": dict(kind="shirt", accent="#5fb36a", skin="#f0bf95", hair="#3b2a1e"),
    "member": dict(kind="suit", suit="#4a3a32", tie="#e2483d", hair="#c9c9c9", skin="#efb894", hair_style="bald"),
    "member2": dict(kind="suit", suit="#2f3b52", tie="#f7c548", hair="#6b4a2e", skin="#d99a6c"),
    "member3": dict(kind="suit", suit="#3d4a3a", tie="#5aa9e6", hair="#dcdcdc", skin="#f2c39b"),
    "boss": dict(kind="suit", suit="#1f2a44", tie="#f08a24", hair="#9b9b9b", skin="#efc19a", glasses=True),
    "crew": dict(kind="polo", accent="#2f5fa8", skin="#c98f63", hair="#1e1410"),
}

CAST.update({   # Apollo-era crews: stylized toys told apart by trim colour, face shape and fringe. Not likenesses.
    "pete": dict(kind="astronaut", accent="#e2483d", skin="#f0bf95", face=(1.12, 0.95, 0.9), hair="#c46a32", tuft="swoop",
                 brow=(0.11, 0.04, 0.03), brow_col="#a4532a", helmet_col="#f8f6f0", rim_col="#e2483d", height=0.86),
    "alan": dict(kind="astronaut", accent="#7a5cc8", skin="#f2c39b", face=(0.98, 0.95, 1.05), hair="#6b4a2e", tuft="flat",
                 brow=(0.11, 0.04, 0.03), brow_col="#4a3222", helmet_col="#f8f6f0", rim_col="#7a5cc8"),
    "dick": dict(kind="astronaut", accent="#5fb36a", skin="#e8b48a", face=(1.0, 0.95, 1.0), hair="#3b2a1e", tuft="flat",
                 brow=(0.12, 0.045, 0.035), brow_col="#2b1d14", helmet_col="#f8f6f0", rim_col="#3d8a4a"),
    "al": dict(kind="astronaut", accent="#2f8f9d", skin="#efc19a", face=(0.92, 0.95, 1.1), hair="#a9a9a9", tuft="flat",
               brow=(0.13, 0.045, 0.04), brow_col="#7a7a7a", helmet_col="#f8f6f0", rim_col="#2f8f9d"),
    "ed": dict(kind="astronaut", accent="#f7c548", skin="#f2c39b", face=(1.04, 0.95, 1.0), hair="#6b4a2e", tuft="swoop",
               brow=(0.1, 0.035, 0.03), brow_col="#4a3222", helmet_col="#f8f6f0", rim_col="#d9a020"),
    "tom": dict(kind="astronaut", accent="#2f8f9d", skin="#f0bf95", face=(0.95, 0.95, 1.08), hair="#4a3222", tuft="flat",
                brow=(0.12, 0.045, 0.035), brow_col="#2b1d14", helmet_col="#f8f6f0", rim_col="#2f8f9d"),
    "gene": dict(kind="astronaut", accent="#f7c548", skin="#efc19a", face=(1.06, 0.95, 0.98), hair="#2b1d14", tuft="swoop",
                 brow=(0.12, 0.045, 0.035), brow_col="#2b1d14", helmet_col="#f8f6f0", rim_col="#d9a020"),
    "jim": dict(kind="astronaut", accent="#5aa9e6", skin="#f2c39b", face=(1.0, 0.95, 1.04), hair="#8a6a4a", tuft="swoop",
                brow=(0.11, 0.04, 0.03), brow_col="#6b4a2e", helmet_col="#f8f6f0", rim_col="#2f6fd0"),
    "fred": dict(kind="astronaut", accent="#5fb36a", skin="#efc19a", face=(1.08, 0.95, 0.95), hair="#4a3222", tuft="flat",
                 brow=(0.12, 0.045, 0.035), brow_col="#2b1d14", helmet_col="#f8f6f0", rim_col="#3d8a4a"),
    "jack": dict(kind="astronaut", accent="#e86a8a", skin="#f2c39b", face=(0.94, 0.95, 1.08), hair="#c9a46a", tuft="swoop",
                 brow=(0.1, 0.035, 0.03), brow_col="#a07a4a", helmet_col="#f8f6f0", rim_col="#c0486a"),
    "reporter": dict(kind="shirt", accent="#c0392b", skin="#f0bf95", hair="#2b1d14", hair_style="long"),
    "eng": dict(kind="suit", suit="#f4f1ea", tie="#2f5fa8", hair="#3b2a1e", skin="#f2c39b", glasses=True),
    "eng2": dict(kind="suit", suit="#e8eef6", tie="#e2483d", hair="#8a6a4a", skin="#d99a6c"),
    "eecom": dict(kind="suit", suit="#f4f1ea", tie="#1f2a44", hair="#2b1d14", skin="#efc19a"),
})

def cast(role, name=None, **kw):
    a = dict(CAST[role]); a.update(kw)
    h = a.pop("height", 1.0)
    r, P = character(name or role, **a)
    if h != 1.0: r.scale = (h,) * 3
    return r, P

def suit_up(P):
    """Lunar-surface kit on an astronaut: bubble visor and backpack."""
    ball(P["root"].name + "_bubble", 0.5, (0, 0, 0.32), glass("#dff1ff", 0.18), parent=P["head"], outline=0.008, seg=32)
    box(P["root"].name + "_lifepack", (0.55, 0.3, 0.7), (0, 0.32, 1.0), toon("#f4f1ea"), parent=P["body"], outline=0.014)

def _names(who, default):
    if who == "none": return []
    return [w for w in (who or default).split(",") if w]

# ---------------------------------------------------------------- capsule interior
def build_capsule(ctx, who="young,gus"):
    names = _names(who, "young,gus")
    world("#0b1228", 0.6, stars=True)
    sun((62, 0, 205), 2.6, "#fff0d6"); area((-1.6, -3.4, 3.2), (55, 0, -25), 260, "#ffd9b0", 2, shadow=True); area((2.5, -1.5, 1.5), (70, 0, 60), 120, "#8fa8ff", 3)
    area((0, 0.5, 3.0), (0, 0, 0), 90, "#ffe2b8", 2)
    wall, trim = toon("#6a7896", shadow="#2a3150"), toon("#e9dfcc")
    # back wall with porthole (boolean cut)
    bw = box("cap_back", (3.6 * (1.0 if len(names) < 3 else 1.18) + 0.6, 0.25, 3.4), (0, 1.25, 1.7), wall, sub=0, bevel=0.0, outline=0.0)
    cutter = cyl("cap_cut", 0.55, 1.0, (0, 1.25, 2.72), None, rot=(90, 0, 0), outline=0.0, bevel=0.0); cutter.hide_render = True; cutter.hide_viewport = True
    b = bw.modifiers.new("hole", "BOOLEAN"); b.object = cutter; b.operation = "DIFFERENCE"
    torus("cap_porthole", 0.57, 0.08, (0, 1.1, 2.72), toon("#f08a24"), rot=(90, 0, 0))
    xs = {1: [0.0], 2: [-0.58, 0.58]}.get(len(names), [-0.86, 0.0, 0.86])
    wide = 1.0 if len(names) < 3 else 1.18
    for i, x in enumerate(xs):
        box(f"cap_seat{i}", (0.8, 0.22, 1.25), (x, 0.32, 1.05), toon("#2a2f3f"), outline=0.012)
        box(f"cap_cush{i}", (0.76, 0.6, 0.18), (x, -0.02, 0.42), toon("#2a2f3f"), outline=0.012)
    for s in (-1, 1):
        box(f"cap_side{s}", (0.25, 4.0, 3.4), (1.75 * s * wide, -0.5, 1.7), wall, rot=(0, -12 * s, 0), sub=0, bevel=0.0, outline=0.0)
        for k in range(3):
            box(f"cap_panelw{s}{k}", (0.08, 0.6, 0.45), (1.6 * s * wide, -0.4 - k * 0.7, 2.0), trim, rot=(0, -12 * s, 0), outline=0.006)
        cyl(f"cap_pipe{s}", 0.05, 3.0, (1.45 * s * wide, 0.9, 1.6), toon("#9aa3ad"), outline=0.0)
    box("cap_ceiling", (3.6 * wide + 0.4, 4.0, 0.25), (0, -0.5, 3.15), wall, sub=0, bevel=0.0, outline=0.0, rot=(-8, 0, 0))
    box("cap_floor", (3.6 * wide + 0.6, 4.0, 0.2), (0, -0.5, -0.1), toon("#2a2f3f"), sub=0, bevel=0.0, outline=0.0)
    for k, x in enumerate((-1.1, 1.1)):
        box(f"cap_backpanel{k}", (0.6, 0.06, 0.8), (x, 1.1, 2.1), trim, outline=0.008)
        for j in range(3):
            ball(f"cap_bl{k}{j}", 0.035, (x - 0.15 + j * 0.15, 1.06, 2.35), emit(["#ff5a4f", "#5fd36a", "#ffd34f"][j], 1.6), outline=0.0, seg=8)
    # instrument panel in front of the crew (faces +Y, toward them)
    pnl = empty("panel", (0, -1.05, 0.78), rot=(28, 0, 0))
    box("panel_body", (2.6, 0.22, 0.8), (0, 0, 0), toon("#8a94a6"), parent=pnl, outline=0.015)
    for i in range(5):
        cyl(f"panel_knob{i}", 0.028, 0.05, (-0.9 + i * 0.45, -0.1, 0.42), toon("#f08a24"), parent=pnl, outline=0.006)
    box("panel_face", (2.4, 0.05, 0.66), (0, 0.12, 0), trim, parent=pnl, outline=0.0)
    random.seed(8)
    for i in range(7):
        x = -1.0 + i * 0.33
        cyl(f"panel_dial{i}", 0.09, 0.05, (x, 0.16, 0.12), toon("#f4f1ea"), rot=(90, 0, 0), parent=pnl, outline=0.006)
        box(f"panel_needle{i}", (0.012, 0.01, 0.08), (x, 0.19, 0.14), toon("#e2483d"), rot=(0, random.uniform(-50, 50), 0), parent=pnl, outline=0.0, sub=0, bevel=0.003)
        ball(f"panel_lamp{i}", 0.03, (x, 0.15, -0.14), emit(random.choice(["#ff5a4f", "#5fd36a", "#ffd34f", "#7fc4ff"]), 1.8), parent=pnl, outline=0.0, seg=8)
        box(f"panel_sw{i}", (0.03, 0.06, 0.08), (x + 0.12, 0.16, -0.16), toon("#9aa3ad"), rot=(30, 0, 0), parent=pnl, outline=0.004)
    ctx["panel"] = pnl
    earth("earth", 14.0, (4, 40, 0.5))
    ctx["views"] = {
        "two": ((0, -2.7, 1.5), (0, 0, 1.75), 22),
        "three": ((0, -3.6, 1.95), (0, 0, 1.95), 22),
        "panel": ((0.0, -0.3, 1.95), (0, -1.05, 0.8), 26),
        "window": ((0.2, -2.4, 1.6), (0, 1.25, 2.6), 24),
    }
    for n, x in zip(names, xs):
        r, ctx[n] = cast(n, seated=True); r.location = (x, 0, 0.42)
        ctx["views"][n] = ((x * 0.26, -1.75, 2.0), (x * 0.86, 0, 1.95), 30)
    ctx["switch_home"] = (0.0, -0.95, 1.12)
    ctx["prop_home"] = (0, -0.75, 1.85)

# ---------------------------------------------------------------- launch pads
def _pad(ctx, vehicle, storm=""):
    if storm:
        world("#5d6a80", 0.75)
        sun((58, 0, 35), 1.4, "#dfe6f2"); area((-6, -10, 6), (60, 0, -30), 1800, "#aab8d6", 10)
    else:
        world("#8fc7ef", 0.9)
        sun((58, 0, 35), 3.2, "#fff2dc"); area((-6, -10, 6), (60, 0, -30), 2500, "#bcd2ff", 10)
    box("ground", (80, 80, 0.2), (0, 20, -0.1), toon("#c9bea2" if storm else "#d8c9a6", shadow="#6a6680" if storm else "#8a7f9a"), sub=0, bevel=0.0, outline=0.0)
    box("ocean", (200, 40, 0.1), (0, 70, -0.05), toon("#356f9e" if storm else "#3f8fd0"), sub=0, bevel=0.0, outline=0.0)
    cyl("pad", 4.0, 0.6, (0, 0, 0.3), toon("#b9b4aa"), outline=0.02, bevel=0.1)
    random.seed(1)
    for i in range(10):
        ball(f"bush{i}", random.uniform(0.6, 1.4), (random.uniform(-25, 25), random.uniform(8, 40), 0.2), toon("#5fa35e"), ico=2, smooth=False, scale=(1.3, 1.3, 0.8), outline=0.0)
    if storm:   # low, heavy grey ceiling
        cm = toon("#7d8699", shadow="#3d4458")
        for i in range(40):
            ball(f"scloud{i}", random.uniform(4, 7), (random.uniform(-45, 45), random.uniform(-10, 70), random.uniform(34, 40)), cm, ico=2, smooth=True, scale=(2.0, 1.4, 0.7), outline=0.0)
    else:
        for i in range(6):
            ball(f"cloud{i}", random.uniform(1.5, 3), (random.uniform(-30, 30), 60, random.uniform(14, 30)), toon("#ffffff", shadow="#c5d4ee"), ico=2, smooth=True, scale=(2.2, 1, 0.9), outline=0.0)
    if vehicle == "gemini":
        rk = rocket("rocket", (0, 0, 0.6)); launch_tower("tower", (2.5, 0.4, 0.6), h=11)
        fl = [flame(f"fl{s}", (0.28 * s, 0, 0.0), rk, 1.0) for s in (-1, 1)]
        top = 11.0
    elif vehicle == "saturn":
        rk = saturn_v("rocket", (0, 0, 0.6)); launch_tower("tower", (2.6, 0.4, 0.6), h=15)
        fl = [flame(f"fl{i}", (x, y, -0.25), rk, 1.15) for i, (x, y) in enumerate([(0, 0), (0.48, 0.48), (-0.48, 0.48), (0.48, -0.48), (-0.48, -0.48)])]
        top = 16.0
    else:
        rk = shuttle_stack("rocket", (0, 0, 0.6)); launch_tower("tower", (3.6, 1.0, 0.6), h=10)
        fl = [flame(f"fl{s}", (1.25 * s, 0.2, 0.2), rk, 1.4) for s in (-1, 1)] + [flame("flm", (0, -1.05, 1.0), rk, 0.9)]
        top = 9.5
    for f in fl: f.scale = (0.001,) * 3
    ctx["rocket"], ctx["flames"], ctx["rocket_top"] = rk, fl, top
    ctx["smoke"] = smoke_puffs("smoke", 22, (0, 0, 0.6), 3.0 if vehicle != "saturn" else 4.0)
    for p in ctx["smoke"]: p.scale = (0.01,) * 3
    ctx["views"] = {
        "wide": ((0, -24 * top / 11, 3.5), (0, 0, top * 0.55), 30),
        "low": ((3.2, -7.5 * top / 11, 1.2), (0, 0, top * 0.62), 20),
        "top": ((1.5, -6, top - 0.5), (0, 0, top - 0.3), 30),
        "strike": ((6, -36, 2.0), (0, 0, 17), 24),
    }
    if storm:   # rain streaks, looping
        random.seed(31); m = emit("#dfe8ff", 0.9); drops = []
        for i in range(90):
            d = cyl(f"rain{i}", 0.012, 0.9, (random.uniform(-9, 9), random.uniform(-14, 6), random.uniform(0, 22)), m, seg=4, outline=0.0, bevel=0.0, rot=(0, 8, 0))
            drops.append((d, d.location.z, random.uniform(0, 22)))
        def rain(N):
            for d, z0, ph in drops:
                for fr in range(1, N + 1):   # every frame, so the wrap-around never streaks upward
                    key(d, fr, loc=(d.location.x, d.location.y, (z0 - ph - fr * 0.9) % 22))
        ctx.setdefault("anim", []).append(rain)

def build_launch(ctx): _pad(ctx, "gemini")
def build_shuttle(ctx): _pad(ctx, "shuttle")
def build_saturn(ctx, storm=""): _pad(ctx, "saturn", storm)

# ---------------------------------------------------------------- orbit
def build_orbit(ctx, craft="gemini", body="earth", labels=""):
    """craft: gemini | csm | lm | pair (LM just undocked from the CSM) | stack (docked).  body: earth | moon."""
    world("#070b1c", 1.0, stars=True)
    sun((40, 0, 120), 3.0, "#fff4e0")
    if body == "moon": moon_globe("moonglobe", 16.0, (0, 14, -19))
    elif body == "sun":
        ball("sunball", 3.0, (-9, 40, 6), emit("#fff1c8", 4.0), outline=0.0); ball("sunglow", 4.4, (-9, 40, 6), glow("#ffb347", 2.5, 1.5), outline=0.0)
    elif body != "none": earth("earth", 16.0, (0, 14, -19))
    ctx["views"] = {"hero": ((3.2, -6.5, 1.2), (0, 0, 0.2), 32), "wide": ((6, -14, 3), (0, 2, -2), 26)}
    if craft == "gemini":
        g = gemini_capsule("gemini", (0, 0, 0), rot=(0, 72, 18)); ctx["gemini"] = g
    if craft == "mercury":
        ctx["capsule"], _ = mercury_capsule("mercury", (0, 0, 0), rot=(0, -110, 20))
    if craft == "ascent":   # only the LM's top half
        lr, P = lunar_module("lm", (0, 0, -1.4), rot=(0, 0, 0)); P["descent"].scale = (0.001,) * 3; ctx["lm"] = P
        piv = empty("lm_pivot", (0, 0, 0)); lr.parent = piv; piv.rotation_euler = (math.radians(15), math.radians(-20), math.radians(-30)); ctx["lm_root"] = piv
    if craft in ("csm", "pair", "stack"):
        ctx["csm"] = apollo_csm("csm", (-0.9 if craft == "pair" else 0, 0, 0.6 if craft == "pair" else 0), rot=(0, 70, 15))
    if craft in ("lm", "pair", "stack"):
        if craft == "stack":   # LM docked on the CSM nose
            lr, ctx["lm"] = lunar_module("lm", (0, 0, 0), rot=(0, 0, 0)); lr.parent = ctx["csm"]
            lr.location = (0, 0, 3.9); lr.rotation_euler = (math.radians(180), 0, 0); lr.scale = (0.8,) * 3
        else:
            lr, ctx["lm"] = lunar_module("lm", (1.3 if craft == "pair" else 0, 0.5, -0.9 if craft == "pair" else -1.0), rot=(10, -8, -20))
            lr.scale = (0.75,) * 3
        ctx["lm_root"] = lr
    if craft == "ascent": ctx["views"]["close"] = ((1.4, -3.4, 0.7), (0, 0, 0.5), 30)
    if craft == "pair":
        ctx["views"]["hero"] = ((2.6, -9.5, 1.0), (0.2, 0, 0.2), 30)
    if craft == "stack":
        ctx["views"]["hero"] = ((4.0, -11.0, 1.6), (1.7, 0.3, 0.6), 28)
    if labels:   # call signs floating by each craft
        if "csm" in ctx: ctx["csm_label"] = word("csm_label", labels.split("/")[0].replace("_", " "), (-0.4, -0.6, 2.9) if craft == "pair" else (0, -0.6, 2.3), 0.55, "#f6ead8")
        if "lm" in ctx and "/" in labels: ctx["lm_label"] = word("lm_label", labels.split("/")[1].replace("_", " "), (0.6, -0.6, -3.1), 0.7, "#f08a24")   # below the captions
    ctx["prop_home"] = (0, -1.5, 0.4)

# ---------------------------------------------------------------- deli
def build_deli(ctx):
    world("#2a1d18", 0.5)
    sun((55, 0, 20), 1.6, "#ffe6c4"); area((0, -4, 3.5), (50, 0, 0), 500, "#ffd29a", 5); area((3, -1, 2), (70, 0, 70), 120, "#9fb4ff", 3)
    room_box("deli", 8, 6, 4, wall="#f3dfc1", floor="#b9895a", ceiling="#e8cfa8")
    box("tiles", (8, 0.1, 1.2), (0, 4.9, 0.6), toon("#2f8f9d"), sub=0, bevel=0.0, outline=0.0)
    plank = box("sign", (2.6, 0.12, 0.8), (0, 4.8, 3.0), toon("#0d1630"), outline=0.02)
    text("sign_t", "DELI", 0.55, (0, 4.72, 3.0), emit("#f08a24", 1.6), rot=(90, 0, 0))
    for i in range(4):
        box(f"menu{i}", (1.0, 0.06, 0.12), (2.4, 4.85, 2.6 - i * 0.3), toon("#f4f1ea"), outline=0.0)
        box(f"menuL{i}", (1.0, 0.06, 0.12), (-2.4, 4.85, 2.6 - i * 0.3), toon("#f4f1ea"), outline=0.0)
    box("menuboard", (1.3, 0.05, 1.4), (2.4, 4.88, 2.15), toon("#22283a"), outline=0.01)
    box("menuboardL", (1.3, 0.05, 1.4), (-2.4, 4.88, 2.15), toon("#22283a"), outline=0.01)
    for x in (-2, 0, 2):
        cyl(f"lampc{x}", 0.01, 1.0, (x, 0.6, 3.6), toon("#222222"), outline=0.0)
        cyl(f"lamp{x}", 0.32, 0.3, (x, 0.6, 3.0), toon("#f08a24"), r2=0.08, outline=0.01)
        ball(f"bulb{x}", 0.1, (x, 0.6, 2.85), emit("#fff1c8", 3.0), outline=0.0)
    box("counter", (5.0, 0.9, 1.05), (0, -0.6, 0.525), toon("#2f8f9d"), outline=0.02)
    box("countertop", (5.2, 1.0, 0.1), (0, -0.6, 1.08), toon("#f4f1ea"), outline=0.015)
    box("register", (0.5, 0.4, 0.35), (1.6, -0.6, 1.3), toon("#9aa3ad"), outline=0.012)
    cyl("jar", 0.14, 0.4, (-1.6, -0.6, 1.33), glass("#ffe7b0", 0.35), outline=0.008)
    box("step", (2, 1, 0.4), (0, 0.4, 0.2), toon("#8a5a36"), outline=0.0)
    wr, ctx["wally"] = cast("wally"); wr.location = (0, 0.4, 0.4)
    ctx["views"] = {"wide": ((0.6, -5.0, 1.9), (0, 0.6, 1.6), 24), "counter": ((0.5, -2.6, 1.85), (0, 0.4, 1.75), 32)}
    ctx["prop_home"] = (0, -0.5, 1.6)

# ---------------------------------------------------------------- studio (any character on a coloured backdrop)
BACKDROPS = {"orange": ("#f08a24", "#e07a1a"), "blue": ("#5aa9e6", "#4a95d6"), "navy": ("#1f2a44", "#18223a"),
             "green": ("#5fb36a", "#4fa35a"), "red": ("#e2483d", "#c93a30"), "cream": ("#f6ead8", "#e8d8c0")}

def build_studio(ctx, who="young", bg="orange", floor=None):
    bg, floor = BACKDROPS.get(bg, (bg, floor or bg))
    world("#1b1430", 0.6)
    sun((50, 0, 25), 2.8, "#fff0d8"); area((2.5, -2, 2), (70, 0, 55), 220, "#9fb4ff", 3)
    box("bd_floor", (12, 12, 0.2), (0, 3, -0.1), toon(floor), sub=0, bevel=0.0, outline=0.0)
    box("bd_back", (12, 0.2, 8), (0, 2.5, 4), toon(bg), sub=0, bevel=0.0, outline=0.0)
    random.seed(6)
    for i in range(14):
        ball(f"bd_dot{i}", 0.12, (random.uniform(-3, 3), 2.38, random.uniform(0.6, 4.5)), toon("#ffffff"), outline=0.0, scale=(1, 0.2, 1), seg=12)
    names = _names(who, "young"); xs = [0.0] if len(names) == 1 else [-0.62, 0.62]
    ctx["views"] = {"close": ((0.25, -2.7, 1.75), (0, 0, 1.55), 30), "med": ((0.4, -4.0, 1.4), (0, 0, 1.2), 28),
                    "two": ((0.2, -3.6, 1.6), (0, 0, 1.45), 28)}
    for n, x in zip(names, xs):
        r, ctx[n] = cast(n); r.location = (x, 0, 0)
        if len(names) > 1:
            r.rotation_euler = (0, 0, math.radians(-14 if x < 0 else 14))
            ctx["views"][n] = ((x * 0.55 + 0.1, -2.6, 1.75), (x, 0, 1.55), 30)
    ctx["prop_home"] = (0, -0.6, 1.3)

# ---------------------------------------------------------------- congressional hearing
def build_hearing(ctx):
    world("#6b4a34", 1.0)
    sun((50, 0, 15), 3.4, "#fff0d8"); area((0, -5, 4), (50, 0, 0), 1400, "#ffe2b8", 6); area((4, -1, 2), (70, 0, 70), 260, "#b8c8ff", 3)
    area((0, 2, 4.6), (0, 0, 0), 500, "#ffe9cc", 6)
    room_box("hear", 10, 6, 5, wall="#b07a4f", floor="#7a5236", ceiling="#e8d2b4")
    for i in range(9):
        box(f"strip{i}", (0.12, 0.1, 5), (-4 + i, 4.88, 2.5), toon("#8a5a36"), sub=0, bevel=0.0, outline=0.0)
    cyl("seal", 0.75, 0.08, (0, 4.82, 3.3), toon("#e8c35a"), rot=(90, 0, 0), outline=0.02)
    cyl("seal_in", 0.55, 0.1, (0, 4.8, 3.3), toon("#1f2a44"), rot=(90, 0, 0), outline=0.0)
    ball("seal_star", 0.18, (0, 4.74, 3.3), toon("#f4f1ea"), scale=(1, 0.3, 1), outline=0.0, ico=1, smooth=False)
    box("dais", (7.5, 1.2, 1.5), (0, 0.6, 0.75), toon("#a8703f"), outline=0.025)
    box("daistop", (7.7, 1.4, 0.12), (0, 0.6, 1.53), toon("#7a4a2a"), outline=0.015)
    box("daisfront", (7.0, 0.05, 0.9), (0, -0.02, 0.8), toon("#c08a55"), outline=0.0)
    for i, (role, x) in enumerate((("member2", -2.0), ("member", 0.0), ("member3", 2.0))):
        r, P = cast(role, seated=True); r.location = (x, 1.3, 0.62); ctx[role] = P
        box(f"plate{i}", (0.7, 0.12, 0.18), (x, 0.0, 1.68), toon("#f4f1ea"), outline=0.008)
        microphone(f"mic{i}", (x + 0.35, 0.2, 1.6))
    ctx["gavel"] = gavel("gavel", (0.55, 0.25, 1.62)); ctx["gavel"].rotation_euler = (0, math.radians(-10), math.radians(200))
    cyl("block", 0.12, 0.05, (-0.05, 0.2, 1.6), toon("#5e3720"), outline=0.006)
    box("witness", (2.6, 0.9, 0.85), (1.6, -3.0, 0.425), toon("#8a5a36"), outline=0.02)
    microphone("micw", (2.0, -3.0, 0.86))
    ctx["views"] = {"wide": ((0.3, -4.3, 2.3), (0, 0.8, 1.95), 24), "member": ((0.35, -2.4, 2.25), (0, 1.3, 2.2), 30),
                    "low": ((-1.2, -3.2, 0.8), (0, 1.0, 2.0), 20)}

# ---------------------------------------------------------------- mission control
def build_mission(ctx, label="GEMINI 3", who="boss"):
    world("#0b1024", 0.5)
    sun((55, 0, 25), 1.6, "#ffe9cc"); area((0, -4, 4), (45, 0, 0), 500, "#ffd6a0", 6); area((0, 5, 3), (-70, 0, 0), 200, "#5fa8ff", 5)
    room_box("mc", 12, 9, 5, wall="#1f2a44", floor="#2b3550")
    scr = box("screen", (6.5, 0.1, 2.8), (0, 7.85, 2.9), emit("#10264a", 1.0), sub=0, bevel=0.0, outline=0.03)
    for i in range(3):
        torus(f"orbitline{i}", 1.2 + i * 0.6, 0.025, (0, 7.75, 2.9), emit("#f08a24", 1.8), rot=(90, 0, 0))
    ball("scr_earth", 0.6, (0, 7.75, 2.9), emit("#3f8fd0", 1.2), scale=(1, 0.2, 1), outline=0.0)
    text("scr_t", label.replace("_", " "), 0.38, (-1.9, 7.74, 4.0), emit("#f6ead8", 1.4), rot=(90, 0, 0), align="LEFT")
    ctx["screen_c"] = (0, 7.6, 2.9); ctx["screen_size"] = (6.0, 2.5)
    for row, y in enumerate((2.6, 4.6)):
        for x in (-3.2, -1.6, 0, 1.6, 3.2):
            console(f"con{row}{x}", (x, y, row * 0.35), rot=(0, 0, 180))
        box(f"tier{row}", (12, 1.6, row * 0.35 + 0.01), (0, y, row * 0.175), toon("#2b3550"), sub=0, bevel=0.0, outline=0.0)
    random.seed(12)
    for i, x in enumerate((-2.4, 0.8, 2.4)):
        r, _ = character(f"ctl{i}", kind="shirt", accent=random.choice(["#f4f1ea", "#dfe8ff", "#f6ead8"]), skin=random.choice(["#f2c39b", "#d99a6c"]), hair="#3b2a1e")
        r.location = (x, 3.2, 0); r.rotation_euler = (0, 0, math.radians(180))
    br, ctx[who] = cast(who); br.location = (0.0, 0.6, 0)
    ctx["views"] = {"wide": ((2.6, -5.2, 2.6), (0, 2.5, 1.8), 22), "boss": ((0.35, -1.8, 1.8), (0, 0.6, 1.62), 30),
                    "screen": ((0.0, 1.0, 2.6), (0, 7.8, 2.9), 26)}
    ctx["prop_home"] = (0, 7.3, 2.7)

# ---------------------------------------------------------------- moon
def build_moon(ctx, who="young", lm="", flag=""):
    world("#04060f", 1.0, stars=True, star_density=0.03)
    sun((30, 0, 40), 3.6, "#fffaf0"); area((3, -4, 3), (60, 0, 40), 150, "#8fa8ff", 4)
    moon_surface("moon")
    earth("earth", 1.6, (-3.5, 26, 9.5), clouds=True)
    names = _names(who, "young")
    ctx["views"] = {"wide": ((0.7, -2.9, 1.35), (0, 0, 1.4), 26), "low": ((0.8, -3.0, 0.4), (0, 0, 1.4), 20)}
    for i, n in enumerate(names):
        r, P = cast(n); ctx[n] = P; suit_up(P)
        r.location = (0, 0, 0) if i == 0 else (1.5 * i, 1.6, 0); r.rotation_euler = (0, 0, math.radians(-25 * i))
        ctx["views"][n] = ((r.location[0] + 0.6, r.location[1] - 2.8, 1.35), (r.location[0], r.location[1], 1.4), 26)
    if lm == "back":
        lr, ctx["lm"] = lunar_module("lm", (-2.4, 5.0, 0), rot=(0, 0, 25))
        ctx["views"]["lm"] = ((1.2, -5.5, 1.6), (-1.2, 3.0, 1.6), 22)
    elif lm == "ladder":   # lander right behind; the first crew member starts on the bottom rung
        lr, ctx["lm"] = lunar_module("lm", (0, 1.75, 0))
        ctx["views"]["ladder"] = ((1.1, -2.6, 1.0), (0, 0.1, 1.15), 26)
        ctx["views"]["lm"] = ((1.6, -5.6, 1.4), (0, 1.2, 1.7), 24)
        ctx["views"]["boot"] = ((0.5, -1.4, 0.35), (0, 0.0, 0.2), 30)
    if flag == "1":
        us_flag("flag", (-1.5, 2.2, 0), rot=(0, 0, 15))
    ctx["prop_home"] = (0, -0.6, 1.3)

# ---------------------------------------------------------------- space station module
def build_station(ctx):
    world("#cfd8e6", 0.8)
    sun((40, 0, 20), 2.2, "#fff4e4"); area((0, -3, 2.5), (60, 0, 0), 300, "#ffe4c4", 4); area((2, 1, 1), (90, 0, 80), 120, "#9fc0ff", 3)
    room_box("mod", 4.2, 6, 3.6, wall="#e9e6de", floor="#c9d0dc", ceiling="#dfe3ea")
    random.seed(5)
    cols = ["#f4f1ea", "#cfd8e6", "#dfe8ff", "#e9dfcc"]
    for i in range(6):
        x = -1.5 + (i % 3) * 1.5; z = 0.9 + (i // 3) * 1.3
        box(f"stp{i}", (1.3, 0.12, 1.1), (x, 4.85, z), toon(random.choice(cols)), outline=0.01)
        for k in range(3):
            ball(f"stl{i}{k}", 0.04, (x - 0.3 + k * 0.3, 4.78, z + 0.35), emit(random.choice(["#5fd36a", "#7fc4ff", "#ffd34f"]), 1.6), seg=8, outline=0.0)
    for s_ in (-1, 1):
        for k in range(3):
            box(f"sts{s_}{k}", (0.12, 1.4, 1.2), (2.0 * s_, 0.8 + k * 1.5, 1.9), toon(random.choice(cols)), outline=0.01)
        cyl(f"rail{s_}", 0.045, 5, (1.85 * s_, 2.0, 1.0), toon("#f7c548"), rot=(90, 0, 0), outline=0.006)
        box(f"bag{s_}", (0.5, 0.4, 0.5), (1.7 * s_, 3.2, 2.7), toon("#5b6b8c" if s_ < 0 else "#f08a24"), outline=0.01)
    box("laptop", (0.6, 0.4, 0.04), (-1.3, 1.6, 1.2), toon("#3b4256"), rot=(0, 0, 20), outline=0.008)
    box("laptopscr", (0.55, 0.03, 0.36), (-1.35, 1.8, 1.4), emit("#7fc4ff", 1.3), rot=(-10, 0, 20), outline=0.006)
    cyl("window", 0.4, 0.1, (1.9, 2.6, 2.3), emit("#0b1228", 1.0), rot=(0, 90, 0), outline=0.02)   # side-wall porthole, clear of the head
    ball("winearth", 0.24, (1.84, 2.5, 2.2), emit("#3f8fd0", 1.2), scale=(0.2, 1, 1), outline=0.0)
    r, ctx["crew"] = cast("crew"); r.location = (0, 0.8, 0.35); r.rotation_euler = (math.radians(5), 0, math.radians(-8))
    ctx["views"] = {"close": ((0.25, -1.9, 1.95), (0, 0.8, 1.85), 28), "wide": ((0.6, -3.4, 1.8), (0, 1.0, 1.5), 22)}
    ctx["prop_home"] = (0.42, 0.2, 1.55)

# ---------------------------------------------------------------- lunar module cabin (standing crew, triangle windows)
def build_lm(ctx, who="tom,gene", outside="moon"):
    names = _names(who, "tom,gene")
    world("#04060f", 1.0, stars=True, star_density=0.03)
    sun((50, 0, 200), 2.4, "#fff0d6"); area((0, -2.0, 2.6), (40, 0, 0), 240, "#ffd9b0", 2.5, shadow=True); area((2.0, 0.5, 1.6), (70, 0, 70), 90, "#8fa8ff", 3)
    wall, trim = toon("#8a93a3", shadow="#353b52"), toon("#d9d4ca")
    room_box("lmc", 3.4, 4.0, 2.9, wall="#8a93a3", floor="#4a4f5e", ceiling="#7a8293")
    # front wall (behind the camera in crew shots) with two triangular windows
    fw = box("lm_front", (3.4, 0.2, 2.9), (0, -2.9, 1.45), wall, sub=0, bevel=0.0, outline=0.0)
    for s_ in (-1, 1):
        pts = [(0.15 * s_, 1.2), (0.95 * s_, 1.2), (0.15 * s_, 2.2)]
        c = prism(f"lm_cut{s_}", pts, 1.0, (0, -2.9, 0), None, outline=0.0, bevel=0.0); c.hide_render = True; c.hide_viewport = True
        b = fw.modifiers.new(f"win{s_}", "BOOLEAN"); b.object = c; b.operation = "DIFFERENCE"
        for k in range(3):
            (x0, z0), (x1, z1) = pts[k], pts[(k + 1) % 3]
            rod(f"lm_frame{s_}{k}", (x0, -2.78, z0), (x1, -2.78, z1), 0.04, toon("#f08a24"))
    # side and back panels, lamps, a handhold rail
    random.seed(14)
    for s_ in (-1, 1):
        for k in range(2):
            box(f"lm_sp{s_}{k}", (0.1, 0.9, 0.7), (1.62 * s_, -0.6 + k * 1.1, 1.7), trim, outline=0.008)
            for j in range(4):
                ball(f"lm_sl{s_}{k}{j}", 0.03, (1.56 * s_, -0.85 + k * 1.1 + j * 0.15, 1.95), emit(random.choice(["#ff5a4f", "#5fd36a", "#ffd34f", "#7fc4ff"]), 1.6), outline=0.0, seg=8)
        rod(f"lm_rail{s_}", (1.5 * s_, -1.2, 1.2), (1.5 * s_, 1.0, 1.2), 0.03, toon("#f7c548"))
    box("lm_backpanel", (2.2, 0.1, 1.1), (0, 2.9, 1.8), trim, outline=0.01)
    for j in range(8):
        ball(f"lm_bl{j}", 0.035, (-0.9 + j * 0.26, 2.83, 2.15), emit(random.choice(["#ff5a4f", "#5fd36a", "#ffd34f"]), 1.6), outline=0.0, seg=8)
        cyl(f"lm_bd{j}", 0.07, 0.04, (-0.9 + j * 0.26, 2.83, 1.75), toon("#f4f1ea"), rot=(90, 0, 0), outline=0.004)
    box("lm_console", (1.1, 0.5, 0.6), (0, -2.5, 0.3), toon("#6f7a8e"), outline=0.012)
    pnl = empty("panel", (0, -1.1, 1.05), rot=(-20, 0, 180))   # small panel between the crew, faces them
    ctx["panel"] = pnl; ctx["switch_home"] = (0, -1.25, 1.3)
    if outside == "moon":
        mr = moon_surface("moonout"); mr.location = (0, -16, -5); mr.rotation_euler = (0, 0, math.pi)
    else:
        earth("earth", 3.0, (-2, -26, 4))
    ctx["views"] = {"two": ((0, -2.45, 1.75), (0, 0, 1.6), 20), "three": ((0, -2.7, 1.85), (0, 0, 1.65), 16),
                    "window": ((0.0, -0.7, 2.3), (0.0, -2.9, 1.45), 24)}
    xs = [0.0] if len(names) == 1 else ([-0.55, 0.55] if len(names) == 2 else [-0.85, 0.0, 0.85])
    for n, x in zip(names, xs):
        r, ctx[n] = cast(n); r.location = (x, 0, 0)
        ctx["views"][n] = ((x * 0.4, -1.8, 1.85), (x, 0, 1.75), 28)
    ctx["prop_home"] = (0, -0.9, 1.5)

# ---------------------------------------------------------------- open ocean (splashdown)
def build_ocean(ctx, who="gus", heli="1"):
    world("#8fc7ef", 0.9)
    sun((55, 0, 30), 3.0, "#fff2dc"); area((-5, -8, 5), (60, 0, -30), 1500, "#bcd2ff", 8)
    box("sea", (300, 300, 0.2), (0, 60, -0.1), toon("#2f7fc4", shadow="#1a4a80", hi=0.15), sub=0, bevel=0.0, outline=0.0)
    random.seed(23); foam = toon("#e8f4ff", shadow="#9ec4e6"); caps = []
    for i in range(70):
        f = ball(f"foam{i}", random.uniform(0.15, 0.4), (random.uniform(-14, 14), random.uniform(-4, 40), 0.0), foam, scale=(2.2, 0.6, 0.15), outline=0.0, seg=10)
        caps.append((f, random.uniform(0, 6.28)))
    for i in range(5):
        ball(f"skycloud{i}", random.uniform(2, 4), (random.uniform(-30, 30), 80, random.uniform(10, 22)), toon("#ffffff", shadow="#c5d4ee"), ico=2, scale=(2.2, 1, 0.8), outline=0.0)
    cap, ctx["hatch"] = mercury_capsule("capsule", (1.3, 2.6, -0.45), rot=(-8, 12, 0)); ctx["capsule"] = cap
    ctx["cap_base"] = tuple(cap.location)
    ring = [torus(f"ripple{k}", 1.0 + k * 0.3, 0.03, (1.3, 2.6, 0.02), toon("#e8f4ff"), rot=(0, 0, 0)) for k in range(2)]
    names = _names(who, "gus"); bodies = []
    for i, n in enumerate(names):
        r, ctx[n] = cast(n); r.location = (-0.6 - i * 1.2, 0, -1.05); bodies.append(r)
    if heli == "1":
        hr, H = helicopter("heli", (1.3, 2.6, 6.2), rot=(0, 0, 25), cable=3.75); ctx["heli"] = H; ctx["heli_root"] = hr
    ctx["views"] = {"wide": ((-0.2, -8.5, 2.0), (0.4, 2.0, 2.2), 24),
                    "low": ((-1.0, -4.5, 0.35), (0.8, 2.6, 3.2), 22),
                    "capsule": ((0.6, -1.7, 0.75), (1.3, 2.6, 0.55), 30),
                    "heli": ((-0.6, -3.5, 0.6), (1.3, 2.6, 5.2), 24)}
    for n, r in zip(names, bodies):
        ctx["views"][n] = ((r.location[0] + 0.35, -2.3, 0.75), (r.location[0], 0, 0.55), 30)
    ctx["prop_home"] = (-0.6, -0.45, 0.4)
    def waves(N):
        for f, ph in caps:
            for fr in range(1, N + 1, 4):
                key(f, fr, loc=(f.location.x + 0.004 * fr * 0, f.location.y, 0.03 * math.sin(fr / 9 + ph)))
        for r in bodies:
            for fr in range(1, N + 1, 4):
                key(r, fr, loc=(r.location.x, r.location.y, -1.05 + 0.06 * math.sin(fr / 11)), rot=(0, 3 * math.sin(fr / 13), 0))
        if not ctx.get("cap_animated"):
            for fr in range(1, N + 1, 4):
                key(cap, fr, loc=(ctx["cap_base"][0], ctx["cap_base"][1], ctx["cap_base"][2] + 0.07 * math.sin(fr / 12)),
                    rot=(-8 + 4 * math.sin(fr / 15), 12 + 3 * math.sin(fr / 17), 0))
        for k, t in enumerate(ring):
            for fr in range(1, N + 1, 3):
                u = ((fr / 45.0) + k * 0.5) % 1.0
                key(t, fr, scale=(0.8 + 1.4 * u, 0.8 + 1.4 * u, 1))
        if "heli" in ctx:
            for fr in range(1, N + 1):
                key(ctx["heli"]["rotor"], fr, rot=(0, 0, fr * 47)); key(ctx["heli"]["tailrotor"], fr, rot=(fr * 61, 90, 0))
    ctx.setdefault("anim", []).append(waves)

# ---------------------------------------------------------------- engineers' table (1970 Houston)
def build_workshop(ctx, who="eng,eng2"):
    world("#2a2f3f", 0.5)
    sun((55, 0, 20), 2.0, "#fff0dc"); area((0, -3.5, 3.5), (45, 0, 0), 700, "#ffe6c4", 6); area((3, 0, 2), (70, 0, 70), 150, "#9fb4ff", 3)
    room_box("ws", 9, 6, 3.6, wall="#d9d2c0", floor="#8a8f99", ceiling="#eae6dc")
    box("chalk", (3.2, 0.08, 1.4), (0, 4.88, 2.1), toon("#2f4a3a"), outline=0.02)
    text("chalk_t", "CO2", 0.45, (-0.8, 4.82, 2.3), toon("#f4f1ea"), rot=(90, 0, 0))
    torus("chalk_o", 0.28, 0.025, (0.6, 4.82, 2.2), toon("#f4f1ea"), rot=(90, 0, 0))
    box("chalk_sq", (0.5, 0.02, 0.5), (1.3, 4.82, 2.2), toon("#f4f1ea"), outline=0.0, sub=0, bevel=0.0)
    for x in (-2.5, 0, 2.5):
        box(f"tube{x}", (1.6, 0.25, 0.08), (x, 1.0, 3.5), emit("#fffbe8", 2.0), outline=0.0)
    box("table", (3.0, 1.4, 0.08), (0, 0.6, 0.95), toon("#a8743f"), outline=0.015)
    for x in (-1.4, 1.4):
        for y in (0.0, 1.2):
            box(f"tleg{x}{y}", (0.08, 0.08, 0.95), (x, y, 0.47), toon("#5e3720"), outline=0.008)
    I = ctx["items"] = {}
    I["square"] = lioh_canister("t_square", "square", (-0.9, 0.5, 1.16))
    I["round"] = lioh_canister("t_round", "round", (-0.3, 0.75, 1.16))
    I["tape"] = duct_tape("t_tape", (0.35, 0.35, 1.03))
    I["bag"] = plastic_bag("t_bag", (0.95, 0.75, 1.05), size=(0.45, 0.3, 0.12))
    I["card"] = cardboard("t_card", (0.2, 0.9, 1.0), rot=(90, 0, 15))
    I["hose"] = hose("t_hose", (0.7, 0.2, 1.02), (1.25, 0.3, 1.02))
    I["sock"] = sock("t_sock", (-0.6, 0.15, 1.04), rot=(90, 0, 70))
    names = _names(who, "eng,eng2"); xs = [0.0] if len(names) == 1 else [-0.8, 0.8]
    ctx["views"] = {"wide": ((0.3, -3.6, 2.4), (0, 0.8, 1.35), 24), "table": ((0.05, -0.35, 2.75), (0, 0.55, 1.0), 26), "peg": ((0.45, -1.7, 1.75), (0, 0.0, 1.55), 30)}
    for n, x in zip(names, xs):
        r, ctx[n] = cast(n); r.location = (x, 1.75, 0)
        ctx["views"][n] = ((x * 0.5, -1.0, 2.0), (x, 1.75, 1.75), 30)
    ctx["prop_home"] = (0, -0.1, 1.55)

SCENES = dict(capsule=build_capsule, launch=build_launch, shuttle=build_shuttle, orbit=build_orbit, deli=build_deli,
              studio=build_studio, hearing=build_hearing, mission=build_mission, moon=build_moon, station=build_station,
              saturn=build_saturn, lm=build_lm, ocean=build_ocean, workshop=build_workshop)
