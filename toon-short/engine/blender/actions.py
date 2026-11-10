"""Action library. Each action: fn(ctx, f0, f1, N, arg) keyframes objects between frames f0..f1 of a shot of N frames.
In a shot line they are written name, name:arg, name@0.3 (start at 30%) or name:arg@0.2-0.7."""
import math, random
from mathutils import Vector
from toon import *
from assets import sandwich, crumbs as make_crumbs, tortilla, red_x, food_pouch, clipboard
import assets as A

def _chars(ctx):
    return {k: v for k, v in ctx.items() if isinstance(v, dict) and "mouth" in v}

def _who(ctx, arg, default="young"):
    c = _chars(ctx)
    return c.get(arg or default) or (next(iter(c.values())) if c else None)

def _eul(o):
    return [math.degrees(a) for a in o.rotation_euler]

def _arm(P, side, f, rx=0, ry=None, rz=0):
    a = P["armR" if side == "R" else "armL"]
    s = -1 if side == "R" else 1
    key(a, f, rot=(rx, -8 * s if ry is None else ry, rz))

# ---------------------------------------------------------------- always-on life
def auto_life(ctx, N, zero_g=False, seed=1):
    random.seed(seed)
    for name, P in _chars(ctx).items():
        f = random.randint(10, 40)
        while f < N - 4:
            for e in P["eyes"]:
                key(e, f - 1, scale=(1, 1, 1)); key(e, f + 1, scale=(1, 1, 0.12)); key(e, f + 3, scale=(1, 1, 1))
            f += random.randint(50, 95)
        b = P["body"]; ph = random.uniform(0, 6)
        for fr in range(1, N + 1, 6):
            key(b, fr, rot=(1.5 * math.sin(fr / 22 + ph), 1.2 * math.sin(fr / 27 + ph), 3 * math.sin(fr / 31 + ph)))
        if zero_g:
            b = P["body"]
            for fr in range(1, N + 1, 6):
                key(b, fr, loc=(0, 0, 0.025 * math.sin(fr / 18 + ph)))

# ---------------------------------------------------------------- faces
def talk(ctx, f0, f1, N, arg):
    P = _who(ctx, arg); m = P["mouth"]; random.seed(f0)
    key(m, f0 - 1, scale=(1, 1, 1)); fr = f0
    while fr < f1:
        key(m, fr, scale=(random.uniform(0.85, 1.15), 1, random.uniform(1.6, 2.6))); fr += 3
        key(m, fr, scale=(1, 1, random.uniform(0.6, 1.0))); fr += random.choice((2, 3))
    key(m, f1 + 1, scale=(1, 1, 1))
    h = P["head"]
    for fr in range(f0, f1, 9):
        key(h, fr, rot=(-4, 0, random.uniform(-6, 6))); key(h, fr + 4, rot=(3, 0, random.uniform(-4, 4)))

def surprise(ctx, f0, f1, N, arg):
    for name, P in (_chars(ctx).items() if arg in (None, "all") else [(arg, _who(ctx, arg))]):
        for b in P["brows"]:
            z = b.location.z
            key(b, f0 - 1, loc=tuple(b.location)); key(b, f0 + 3, loc=(b.location.x, b.location.y, z + 0.07)); b.location.z = z
        for e in P["eyes"]:
            key(e, f0 - 1, scale=(1, 1, 1)); key(e, f0 + 3, scale=(1.35, 1, 1.4)); key(e, f1, scale=(1.25, 1, 1.3))
        key(P["mouth"], f0 - 1, scale=(1, 1, 1)); key(P["mouth"], f0 + 4, scale=(0.75, 1, 2.6))
        key(P["head"], f0 - 1, rot=(0, 0, 0)); key(P["head"], f0 + 4, rot=(-8, 0, 0))

def angry(ctx, f0, f1, N, arg):
    P = _who(ctx, arg)
    for i, b in enumerate(P["brows"]):
        s = -1 if i == 0 else 1
        key(b, f0 - 1, rot=(0, 0, 0)); key(b, f0 + 3, rot=(0, 25 * s, 0))
        key(b, f0 - 1, loc=tuple(b.location)); key(b, f0 + 3, loc=(b.location.x, b.location.y, b.location.z - 0.03))
    key(P["mouth"], f0 - 1, scale=(1, 1, 1)); key(P["mouth"], f0 + 3, scale=(1.5, 1, 0.5))

def frown(ctx, f0, f1, N, arg):
    P = _who(ctx, arg)
    for i, b in enumerate(P["brows"]):
        s = -1 if i == 0 else 1
        key(b, f0 - 1, rot=(0, 0, 0)); key(b, f0 + 4, rot=(0, -18 * s, 0))
    key(P["mouth"], f0 - 1, scale=(1, 1, 1)); key(P["mouth"], f0 + 4, scale=(1.3, 1, 0.45))
    key(P["head"], f0 - 1, rot=(0, 0, 0)); key(P["head"], f0 + 6, rot=(8, 0, 0))

def grin(ctx, f0, f1, N, arg):
    P = _who(ctx, arg)
    key(P["mouth"], f0 - 1, scale=(1, 1, 1)); key(P["mouth"], f0 + 4, scale=(1.7, 1, 1.25))
    for b in P["brows"]:
        key(b, f0 - 1, loc=tuple(b.location)); key(b, f0 + 4, loc=(b.location.x, b.location.y, b.location.z + 0.04))

def wink(ctx, f0, f1, N, arg):
    P = _who(ctx, arg); e = P["eyes"][1]
    key(e, f0 - 1, scale=(1, 1, 1)); key(e, f0 + 2, scale=(1.1, 1, 0.1)); key(e, f0 + 14, scale=(1.1, 1, 0.1)); key(e, f0 + 17, scale=(1, 1, 1))
    grin(ctx, f0, f1, N, arg)

# ---------------------------------------------------------------- body
def point(ctx, f0, f1, N, arg):
    P = _who(ctx, arg)
    _arm(P, "R", f0 - 1); _arm(P, "R", f0 + 4, rx=-100)
    for fr in range(f0 + 6, f1, 8):
        _arm(P, "R", fr, rx=-92); _arm(P, "R", fr + 4, rx=-104)

def shrug(ctx, f0, f1, N, arg):
    P = _who(ctx, arg)
    for side, s in (("R", -1), ("L", 1)):
        _arm(P, side, f0 - 1); _arm(P, side, f0 + 5, rx=-30, ry=45 * s, rz=0)
    key(P["head"], f0 - 1, rot=(0, 0, 0)); key(P["head"], f0 + 5, rot=(0, 10, 0))
    grin(ctx, f0, f1, N, arg)

def arms_crossed(ctx, f0, f1, N, arg):
    P = _who(ctx, arg)
    _arm(P, "R", f0, rx=-80, ry=0, rz=62); _arm(P, "L", f0, rx=-75, ry=0, rz=-62)

def jump(ctx, f0, f1, N, arg):
    P = _who(ctx, arg); b = P["body"]; L = 24
    fr = f0
    while fr + L <= f1 + 1:
        for k in range(0, L + 1, 2):
            t = k / L; key(b, fr + k, loc=(0, 0, 0.9 * 4 * t * (1 - t)))
        fr += L + 4
    _arm(P, "L", f0, rx=-150, ry=10)

def float_(ctx, f0, f1, N, arg):
    P = _who(ctx, arg); b = P["body"]
    for fr in range(f0, f1 + 1, 4):
        key(b, fr, loc=(0.04 * math.sin(fr / 14), 0, 0.08 * math.sin(fr / 20)))

# ---------------------------------------------------------------- the sandwich and friends
def _get_sandwich(ctx, scale=1.0):
    if "sandwich" not in ctx:
        ctx["sandwich"] = sandwich("sandwich", loc=ctx.get("prop_home", (0, -0.6, 1.6)), scale=scale)
    return ctx["sandwich"]

def sandwich_float(ctx, f0, f1, N, arg):
    s = _get_sandwich(ctx, float(arg) if arg else 1.0); base = Vector(s.location)
    for fr in range(1, N + 1, 3):
        key(s, fr, loc=base + Vector((0.03 * math.sin(fr / 13), 0, 0.05 * math.sin(fr / 17))), rot=(15 * math.sin(fr / 21), 8 * math.sin(fr / 15), fr * 1.2))

def sandwich_hold(ctx, f0, f1, N, arg):
    """Sandwich in the character's right hand, held up in front of the chest."""
    P = _who(ctx, arg); s = _get_sandwich(ctx, 0.85)
    s.parent = P["handR"]; s.location = (0.0, -0.12, 0.05); s.rotation_euler = (math.radians(70), 0, math.radians(10))
    _arm(P, "R", 1, rx=-68, rz=62)

def sandwich_out(ctx, f0, f1, N, arg):
    """Pull the sandwich out of the suit pocket and lift it up with a pop."""
    P = _who(ctx, arg); s = _get_sandwich(ctx, 0.85)
    s.parent = P["handR"]; s.location = (0.0, -0.12, 0.05); s.rotation_euler = (math.radians(70), 0, math.radians(10))
    key(s, 1, scale=0.001); key(s, f0, scale=0.001); key(s, f0 + 5, scale=1.15); key(s, f0 + 9, scale=1.0)
    _arm(P, "R", 1, rx=-10, rz=0); _arm(P, "R", f0, rx=-15, rz=0); _arm(P, "R", f0 + 8, rx=-74, rz=64); _arm(P, "R", min(N, f0 + 30), rx=-68, rz=62)

def give(ctx, f0, f1, N, arg):
    """young hands the sandwich across to gus (capsule)."""
    a, b = (arg or "young>gus").split(">")
    Pa, Pb = _who(ctx, a), _who(ctx, b); s = _get_sandwich(ctx, 0.85)
    s.parent = None
    pa, pb = Vector((-0.2, -0.6, 1.5)), Vector((0.35, -0.55, 1.55))
    if a == "gus": pa, pb = pb, pa
    for fr in range(1, N + 1, 2):
        t = ease_in_out((fr - f0) / max(1, f1 - f0))
        key(s, fr, loc=pa.lerp(pb, t) + Vector((0, 0, 0.12 * math.sin(t * math.pi))), rot=(70, 0, 10 + 20 * t))
    _arm(Pa, "R", f0, rx=-60, rz=20); _arm(Pa, "R", f1, rx=-10)
    _arm(Pb, "L" if b == "gus" else "R", f0, rx=-10); _arm(Pb, "L" if b == "gus" else "R", f1, rx=-60, rz=-20 if b == "gus" else 20)

def bite(ctx, f0, f1, N, arg):
    """Sandwich at the mouth; chomp at f0 leaves a bite mark."""
    P = _who(ctx, arg); s = _get_sandwich(ctx, 0.85)
    s.parent = P["head"]; s.location = (0.05, -0.55, 0.12); s.rotation_euler = (math.radians(12), 0, math.radians(-25))
    key(s, 1, loc=(0.08, -0.7, 0.05)); key(s, f0 - 4, loc=(0.06, -0.48, 0.1)); key(s, f0, loc=(0.05, -0.4, 0.14)); key(s, f0 + 4, loc=(0.08, -0.62, 0.08))
    cut = ball("bitecut", 0.13, (0.6, 0.6, 0), None, parent=s, outline=0.0); cut.hide_render = True; cut.hide_viewport = True
    key(cut, f0 - 1, loc=(1.5, 1.5, 0)); key(cut, f0, loc=(0.22, -0.2, 0))
    for c in s.children:
        if c.type == "MESH" and c != cut:
            m = c.modifiers.new("bite", "BOOLEAN"); m.object = cut; m.operation = "DIFFERENCE"
            c.modifiers.move(len(c.modifiers) - 1, 0)
    m = P["mouth"]; key(m, f0 - 6, scale=(1, 1, 1)); key(m, f0 - 2, scale=(1.2, 1, 3.0)); key(m, f0 + 1, scale=(1.1, 1, 0.5)); key(m, f0 + 5, scale=(1, 1, 1.2)); key(m, f0 + 8, scale=(1, 1, 0.6)); key(m, f0 + 11, scale=(1, 1, 1))
    _arm(P, "R", 1, rx=-80, rz=25)
    ctx["bite_frame"] = f0

def crumbs(ctx, f0, f1, N, arg):
    """Burst of rye crumbs from the sandwich (or prop_home) at f0, then zero-g drift."""
    n = int(arg) if arg else 60
    import bpy
    bpy.context.view_layer.update()
    s = ctx.get("sandwich"); o = Vector(s.matrix_world.translation) if s else Vector(ctx.get("prop_home", (0, -0.6, 1.6)))
    cs = make_crumbs("crumb", n, o, spread=0.9, size=0.03)
    for c in cs:
        v = Vector(c["vel"]); sp = c["spin"]
        key(c, 1, scale=0.001); key(c, max(1, f0 - 1), scale=0.001, loc=o)
        for fr in range(f0, N + 1, 2):
            t = (fr - f0) / 30
            p = o + v * (1 - math.exp(-t * 2.2)) * 0.9 + Vector((0.03 * math.sin(t * 2 + v.x * 5), 0, 0.04 * t))
            key(c, fr, loc=p, rot=(sp[0] * t, sp[1] * t, sp[2] * t), scale=1.0)

def crumbs_drift(ctx, f0, f1, N, arg):
    """Crumbs already floating around the frame."""
    n = int(arg) if arg else 40
    o = Vector(ctx.get("prop_home", (0, -0.6, 1.6)))
    cs = make_crumbs("dcrumb", n, o, spread=1.0, size=0.028, seed=9)
    random.seed(4)
    for c in cs:
        p0 = o + Vector((random.uniform(-1.1, 1.1), random.uniform(-0.8, 0.6), random.uniform(-0.6, 0.8)))
        v = Vector(c["vel"]) * 0.05; sp = c["spin"]
        for fr in range(1, N + 1, 3):
            t = fr / 30; key(c, fr, loc=p0 + v * t * 3, rot=(sp[0] * t * 0.3, sp[1] * t * 0.3, sp[2] * t * 0.3))

def crumbs_panel(ctx, f0, f1, N, arg):
    """Crumbs drift down into the instrument panel and slip into the gaps."""
    pnl = ctx["panel"]; target = Vector(pnl.location)
    cs = make_crumbs("pcrumb", 45, target, spread=1.0, size=0.03, seed=13)
    random.seed(21)
    for c in cs:
        a = Vector((random.uniform(-1.3, 1.3), random.uniform(-0.6, -0.1), random.uniform(1.0, 1.6))) + Vector((0, 0, 0))
        a = Vector((a.x, -0.3 + a.y, a.z))
        b = target + Vector((random.uniform(-1.1, 1.1), 0.05, random.uniform(-0.25, 0.25)))
        sp = c["spin"]; d = random.uniform(0.5, 1.0)
        for fr in range(1, N + 1, 2):
            t = ease_out(fr / (N * d)); key(c, fr, loc=a.lerp(b, t), rot=(sp[0] * fr / 60, sp[1] * fr / 60, sp[2] * fr / 60))

def pocket(ctx, f0, f1, N, arg):
    """Stuff the sandwich into the suit pocket (shrinks into the chest)."""
    P = _who(ctx, arg); s = _get_sandwich(ctx, 0.85)
    s.parent = P["handR"]; s.location = (0.0, -0.12, 0.05); s.rotation_euler = (math.radians(70), 0, math.radians(10))
    _arm(P, "R", 1, rx=-68, rz=40); _arm(P, "R", f0, rx=-68, rz=40); _arm(P, "R", f0 + 10, rx=-25, rz=10)
    key(s, f0 + 4, scale=1.0); key(s, f0 + 11, scale=0.001)

def pouch(ctx, f0, f1, N, arg):
    o = Vector(ctx.get("prop_home", (0, -0.6, 1.6))) + Vector((float(arg or 0.0), 0, -0.15))
    p = food_pouch("pouch", o); p.scale = (0.7,) * 3
    for fr in range(1, N + 1, 3):
        key(p, fr, loc=o + Vector((0, 0, 0.05 * math.sin(fr / 15))), rot=(10 * math.sin(fr / 20), 0, fr * 1.5))
    key(p, f0, scale=0.001); key(p, f0 + 5, scale=0.8); key(p, f0 + 8, scale=0.7)

def xmark(ctx, f0, f1, N, arg):
    """Big sandwich with a red X that slams on at f0 (works in any scene; uses prop_home)."""
    o = Vector(ctx.get("prop_home", (0, -0.6, 1.6)))
    s = sandwich("bigsandwich", loc=o + Vector((0, -0.4, 0)), scale=float(arg) if arg else 4.0)
    for fr in range(1, N + 1, 3):
        key(s, fr, rot=(18, 0, 10 * math.sin(fr / 18)))
    x = red_x("redx", o + Vector((0, -1.2, 0)), size=(float(arg) if arg else 4.0) * 0.55)
    x.rotation_euler = (0, 0, 0)
    key(x, 1, scale=0.001); key(x, f0, scale=0.001); key(x, f0 + 4, scale=1.25); key(x, f0 + 8, scale=1.0)

def clip(ctx, f0, f1, N, arg):
    P = _who(ctx, arg)
    c = clipboard("clipboard", (0.0, -0.18, 0.12), parent=P["handR"], rot=(0, 0, 0))
    _arm(P, "R", 1, rx=-58, rz=20)
    key(c, f0, scale=0.001); key(c, f0 + 5, scale=1.1); key(c, f0 + 8, scale=1.0)

def tortilla_(ctx, f0, f1, N, arg):
    """Tortilla floats in front of the crew member, spinning like a frisbee, then gets caught."""
    P = _who(ctx, arg or "crew"); o = Vector(ctx.get("prop_home", (0, -0.4, 0.6)))
    t = tortilla("tortilla", o)
    for fr in range(1, N + 1, 2):
        u = ease_out(fr / max(2, f1))
        key(t, fr, loc=o + Vector((0.5 * (1 - u), -0.1, 0.06 * math.sin(fr / 10))), rot=(75, 10 * math.sin(fr / 12), fr * 6))
    _arm(P, "R", 1, rx=-10); _arm(P, "R", f1, rx=-70, rz=20)

def liftoff(ctx, f0, f1, N, arg):
    rk = ctx["rocket"]; base = Vector(rk.location); ctx["rocket_base"] = base.copy()
    for f in ctx["flames"]:
        key(f, 1, scale=0.001); key(f, f0, scale=0.001); key(f, f0 + 4, scale=1.2)
        for fr in range(f0 + 6, N + 1, 2):
            key(f, fr, scale=(1 + 0.12 * math.sin(fr * 2.1), 1 + 0.12 * math.sin(fr * 2.1), 1 + 0.25 * math.sin(fr * 1.7)))
    rise0 = f0 + 10
    ctx["follow_z"] = lambda fr: 0.9 * (max(0, fr - rise0) / 30) ** 2
    for fr in range(1, N + 1, 2):
        key(rk, fr, loc=base + Vector((0.02 * math.sin(fr * 3) * (fr > f0), 0, ctx["follow_z"](fr))))
    for p in ctx["smoke"]:
        p0 = Vector(p.location); d = Vector((p["dir"][0], p["dir"][1], 0.15))
        for fr in range(1, N + 1, 3):
            t = max(0, fr - f0) / 30
            key(p, fr, loc=p0 + d * (3.5 * (1 - math.exp(-t * 1.2))), scale=0.001 if fr < f0 else min(1.7, 0.3 + t * 1.2))

def gavel_bang(ctx, f0, f1, N, arg):
    g = ctx["gavel"]; base = _eul(g); P = ctx.get("member")
    hits = [f0, f0 + 12]
    key(g, 1, rot=base)
    for h in hits:
        key(g, h - 6, rot=(base[0], base[1] - 50, base[2])); key(g, h, rot=(base[0], base[1] + 8, base[2])); key(g, h + 3, rot=base)
        if P:
            _arm(P, "R", h - 6, rx=-110, rz=-20); _arm(P, "R", h, rx=-60, rz=-25)
    ctx["hits"] = hits

# ---------------------------------------------------------------- Apollo-era library
def _home(ctx, k="prop_home", d=(0, -0.6, 1.6)):
    return Vector(ctx.get(k, d))

def _hit(ctx, f):
    ctx.setdefault("hits", []).append(f)

def _pop_in(o, f0, s=1.0):
    key(o, 1, scale=0.001); key(o, max(1, f0 - 1), scale=0.001); key(o, f0 + 4, scale=s * 1.2); key(o, f0 + 8, scale=s)

def word_(ctx, f0, f1, N, arg):
    """word:WHOOPIE!  Big 3D word pops in at prop_home (use _ for spaces, ~ for an orange/cream swap)."""
    t = (arg or "WOW").replace("_", " "); col = "#f08a24"
    t, _, sz = t.partition("*")
    if t.startswith("~"): t, col = t[1:], "#f6ead8"
    size = float(sz) if sz else min(0.34, 1.55 / (0.78 * max(1, len(t))))
    w = A.word("word_" + str(f0), t, (0, 0, 0), size, col, face_cam=False); w.rotation_euler = (0, 0, 0); w["cam_word"] = 1
    inner = empty(w.name + "_pop", (0, 0, 0), w)
    for c in list(w.children):
        if c is not inner: c.parent = inner
    _pop_in(inner, f0)
    for fr in range(f0 + 8, N + 1, 4): key(inner, fr, scale=1.0 + 0.03 * math.sin(fr / 4))

def flash(ctx, f0, f1, N, arg):
    """White flash: world and every light spike for a few frames at f0 (and again at f0+5 if arg=2)."""
    import bpy
    w = bpy.context.scene.world; bg = next((n for n in w.node_tree.nodes if n.type == "BACKGROUND"), None)
    lights = [o for o in bpy.data.objects if o.type == "LIGHT"]
    hits = [f0] + ([f0 + 6] if (arg or "").startswith("2") else []); soft = "soft" in (arg or "")
    for L in lights:
        e = L.data.energy; L.data.keyframe_insert("energy", frame=1)
        for h in hits:
            L.data.keyframe_insert("energy", frame=h - 1); L.data.energy = e * 6; L.data.keyframe_insert("energy", frame=h)
            L.data.energy = e; L.data.keyframe_insert("energy", frame=h + 3)
    if bg and not soft:
        v = bg.inputs[1].default_value; c = tuple(bg.inputs[0].default_value)
        for h in hits:
            bg.inputs[1].keyframe_insert("default_value", frame=h - 1); bg.inputs[1].default_value = 9.0
            bg.inputs[1].keyframe_insert("default_value", frame=h); bg.inputs[1].default_value = v; bg.inputs[1].keyframe_insert("default_value", frame=h + 3)
    for h in hits: _hit(ctx, h)

def lightning(ctx, f0, f1, N, arg):
    """Bolt from the clouds into the rocket's nose at f0 (pad scenes). arg=2 strikes twice."""
    rk = ctx.get("rocket"); top = ctx.get("rocket_top", 11)
    hits = [f0] + ([f0 + 6] if arg == "2" else [])
    for k, h in enumerate(hits):
        z = ctx.get("rocket_base", rk.location).z + top + (ctx["follow_z"](h) if "follow_z" in ctx else 0)
        b = A.lightning_bolt(f"bolt{k}", (rk.location.x - 5 + 9 * k, rk.location.y + 1, z + 17), (rk.location.x, rk.location.y - 0.3, z - 0.2), seed=7 + k, width=0.6)
        for c in [b] + list(b.children_recursive):
            c.hide_render = True; c.keyframe_insert("hide_render", frame=1); c.keyframe_insert("hide_render", frame=h - 1)
            c.hide_render = False; c.keyframe_insert("hide_render", frame=h)
            c.hide_render = True; c.keyframe_insert("hide_render", frame=h + 4)
    flash(ctx, f0, f1, N, (arg or "") + "soft")

def alarms(ctx, f0, f1, N, arg):
    """Warning lamps blink red/amber all over the panel from f0."""
    random.seed(41)
    import bpy; bpy.context.view_layer.update()
    pnl = ctx.get("panel"); M = pnl.matrix_world if pnl else None
    for i in range(16):
        q = Vector((random.uniform(-1.1, 1.1), 0.2, random.uniform(-0.3, 0.32)))
        p = (M @ q) if M else _home(ctx) + q
        l = ball(f"alarm{i}", 0.065, tuple(p), emit("#ff3b30" if i % 3 else "#ffb020", 3.0), outline=0.0, seg=10)
        key(l, 1, scale=0.001); key(l, f0 - 1, scale=0.001)
        fr = f0 + random.randint(0, 4)
        while fr < N:
            key(l, fr, scale=1.4); key(l, fr + 4, scale=1.4); key(l, fr + 5, scale=0.4); fr += 9

def glitch(ctx, f0, f1, N, arg):
    """Mission-control screen fills with junk data: flickering coloured blocks and zigzags from f0."""
    c = Vector(ctx.get("screen_c", (0, 7.6, 2.9))); w, h = ctx.get("screen_size", (6.0, 2.5)); random.seed(43)
    cols = ["#ff3b30", "#5fd36a", "#ffd34f", "#7fc4ff", "#f4f1ea"]
    for i in range(34):
        b = box(f"junk{i}", (random.uniform(0.2, 1.1), 0.02, random.uniform(0.08, 0.35)), tuple(c + Vector((random.uniform(-w / 2, w / 2), -0.05, random.uniform(-h / 2, h / 2)))),
                emit(random.choice(cols), 1.6), outline=0.0, sub=0, bevel=0.0)
        key(b, 1, scale=0.001); key(b, f0 - 1, scale=0.001)
        for fr in range(f0, N + 1, 3):
            key(b, fr, scale=(random.uniform(0.3, 1.4), 1, 1) if random.random() > 0.3 else 0.001)
    for k in range(3):
        pts = [c + Vector((-w / 2 + j * w / 12, -0.07, random.uniform(-h / 3, h / 3))) for j in range(13)]
        for j in range(12):
            r = A.rod(f"zig{k}{j}", pts[j], pts[j + 1], 0.025, emit("#ffd34f", 2.0))
            key(r, 1, scale=0.001); key(r, f0 - 1, scale=0.001); key(r, f0, scale=1.0)

def sce_switch(ctx, f0, f1, N, arg):
    """Big SCE switch on the panel flips to AUX at f0."""
    home = _home(ctx, "switch_home", (0, -0.95, 1.12))
    holder = empty("sce_holder", tuple(home)); holder["face_cam"] = 1   # plate front (-Y) turned to +Z, which tracks the camera
    root, lv = A.big_switch("sce", (0, 0, 0), holder, title="SCE", right="AUX", rot=(-90, 0, 0))
    holder.scale = (0.75,) * 3
    key(lv, 1, rot=(0, -35, 0)); key(lv, f0 - 1, rot=(0, -35, 0)); key(lv, f0 + 2, rot=(0, 40, 0)); key(lv, f0 + 5, rot=(0, 33, 0))
    _hit(ctx, f0)

def laugh(ctx, f0, f1, N, arg):
    """Big open-mouth laugh with head bobs (who or all)."""
    who = list(_chars(ctx).items()) if arg in (None, "all") else [(arg, _who(ctx, arg))]
    for name, P in who:
        m, h = P["mouth"], P["head"]
        key(m, f0 - 1, scale=(1, 1, 1))
        for fr in range(f0, f1, 6):
            key(m, fr, scale=(1.6, 1, 2.4)); key(m, fr + 3, scale=(1.5, 1, 1.2))
            key(h, fr, rot=(-10, 0, 3)); key(h, fr + 3, rot=(-4, 0, -3))
        key(m, f1 + 2, scale=(1.4, 1, 1.0)); key(h, f1 + 2, rot=(0, 0, 0))
        for e in P["eyes"]:
            key(e, f0 - 1, scale=(1, 1, 1)); key(e, f0 + 2, scale=(1.1, 1, 0.25)); key(e, f1, scale=(1.1, 1, 0.25)); key(e, f1 + 3, scale=(1, 1, 1))

def hatch_blow(ctx, f0, f1, N, arg):
    """Mercury hatch pops off at f0 and splashes down nearby."""
    hz = ctx["hatch"]; p0 = Vector(hz.location)
    key(hz, 1, loc=p0); key(hz, f0 - 1, loc=p0)
    for fr in range(f0, min(N, f0 + 30) + 1, 2):
        t = (fr - f0) / 30.0
        key(hz, fr, loc=p0 + Vector((-1.6 * t, -2.2 * t, 1.6 * t - 2.4 * t * t)), rot=(-18 + 540 * t, 200 * t, 0))
    for k in range(10):   # puff from the bolts
        p = ball(f"hpuff{k}", 0.12, (0, 0, 0), toon("#f1ede6"), outline=0.0, seg=10)
        p.parent = hz.parent; d = Vector((random.uniform(-1, 1), -1, random.uniform(-0.3, 1))).normalized()
        key(p, 1, scale=0.001); key(p, f0 - 1, scale=0.001, loc=p0)
        key(p, f0 + 6, scale=1.6, loc=p0 + d * 0.4); key(p, f0 + 20, scale=0.001, loc=p0 + d * 0.8)
    _hit(ctx, f0)

def nohatch(ctx, f0, f1, N, arg):
    """The Mercury hatch is already gone (for shots after hatch_blow)."""
    h = ctx["hatch"]; key(h, 1, scale=0.001); key(h, N, scale=0.001)

def sink(ctx, f0, f1, N, arg):
    """The capsule (or ctx[arg]) slowly sinks below the waves between f0 and f1."""
    o = ctx[arg or "capsule"]; ctx["cap_animated"] = True; b = Vector(o.location)
    for fr in range(1, N + 1, 2):
        t = ease_in_out((fr - f0) / max(1, f1 - f0)) if fr > f0 else 0
        key(o, fr, loc=b + Vector((0, 0, -2.8 * t + 0.06 * math.sin(fr / 10))), rot=(-8 - 25 * t, 12 + 10 * t, 0))

def lift_fail(ctx, f0, f1, N, arg):
    """Helicopter hauls the flooded capsule half out of the water, strains, then lets it go at f1."""
    o = ctx["capsule"]; ctx["cap_animated"] = True; b = Vector(o.location); H = ctx.get("heli"); hr = ctx.get("heli_root")
    for fr in range(1, N + 1, 2):
        if fr < f0: z = 0
        elif fr < f1: z = 0.9 * ease_out((fr - f0) / max(1, f1 - f0)) + 0.05 * math.sin(fr * 1.3)
        else: z = 0.9 - 1.4 * ease_in_out((fr - f1) / 20.0)
        key(o, fr, loc=b + Vector((0.05 * math.sin(fr * 0.9) * (f0 < fr < f1), 0, z)), rot=(-8 + 6 * math.sin(fr / 7), 12, 0))
        if hr:
            sag = -0.5 * ease_out((fr - f0) / max(1, f1 - f0)) if f0 < fr < f1 else (0 if fr <= f0 else -0.5 + 0.9 * ease_out((fr - f1) / 15.0))
            key(hr, fr, loc=(hr.location.x, hr.location.y, 6.2 + sag), rot=(5 * math.sin(fr / 5) * (f0 < fr < f1), 0, 25))
    if H:
        key(H["cable"], 1, scale=1.0); key(H["cable"], f1 - 1, scale=1.0); key(H["cable"], f1, scale=(1, 1, 0.3))
        key(H["hook"], 1, scale=1.0); key(H["hook"], f1 - 1, scale=1.0); key(H["hook"], f1, scale=0.001)
    _hit(ctx, f1)

def swim(ctx, f0, f1, N, arg):
    """Treading water: arms paddle, head tilts back."""
    P = _who(ctx, arg)
    for fr in range(f0, f1 + 1, 4):
        a = math.sin(fr / 3.0)
        _arm(P, "R", fr, rx=-40 + 35 * a, rz=-30); _arm(P, "L", fr, rx=-40 - 35 * a, rz=30)
    key(P["head"], f0, rot=(-12, 0, 0))

def dimes(ctx, f0, f1, N, arg):
    """A cascade of dimes spills from prop_home at f0 and drops (they sink below the water line)."""
    n = int(arg or 24); o = _home(ctx); random.seed(51)
    for i in range(n):
        c = A.coin(f"dime{i}", tuple(o)); d = Vector((random.uniform(-0.5, 0.5), random.uniform(-0.6, 0.1), random.uniform(0.3, 1.0)))
        st = f0 + i % 8; sp = [random.uniform(-600, 600) for _ in range(3)]
        key(c, 1, scale=0.001); key(c, st - 1, scale=0.001, loc=o)
        for fr in range(st, N + 1, 2):
            t = (fr - st) / 30.0
            key(c, fr, loc=o + Vector((d.x * t, d.y * t, d.z * t - 2.6 * t * t)), rot=(sp[0] * t, sp[1] * t, sp[2] * t), scale=1.0)

def dime_stack(ctx, f0, f1, N, arg):
    """Rolls of dimes pop up in front of the character (a souvenir stack)."""
    o = _home(ctx) + Vector((0, -0.1, 0.1)); n = int(arg or 3)
    for k in range(n):
        root = empty(f"roll{k}", tuple(o + Vector(((k - (n - 1) / 2) * 0.24, 0, 0))))
        for j in range(10):
            A.coin(f"roll{k}_{j}", (0, 0, j * 0.017), root)
        root.rotation_euler = (math.radians(70), 0, math.radians(10 * k))
        _pop_in(root, f0 + 4 * k, 0.9)

def swing(ctx, f0, f1, N, arg):
    """One-handed golf swing in the picture plane; contact at f0. arg 'who', 'who>dud' (ball dribbles) or 'who>far' (ball sails)."""
    import bpy
    who, _, how = (arg or "al>far").partition(">"); P = _who(ctx, who); how = how or "far"
    A.golf_club("club", (0, -0.02, -0.02), P["handR"], length=0.72)
    P["root"].rotation_euler = (0, 0, math.radians(62))   # side-on: the swing arc reads across the frame, club on the camera side
    arm = P["armR"]
    key(arm, 1, rot=(-8, -8, 0)); key(arm, f0 - 18, rot=(-8, -8, 0))
    key(arm, f0 - 7, rot=(115, -8, 0))      # backswing
    key(arm, f0, rot=(-6, -8, 0))           # contact
    key(arm, f0 + 7, rot=(-135, -8, 0)); key(arm, min(N, f0 + 30), rot=(-120, -8, 0))
    S = bpy.context.scene; S.frame_set(f0); bpy.context.view_layer.update()
    hp = Vector(bpy.data.objects["club_head"].matrix_world.translation); S.frame_set(1)
    bl = Vector((hp.x + 0.1, hp.y - 0.02, 0.085))
    b = A.golf_ball("gball", tuple(bl), r=0.085)
    key(b, 1, loc=bl); key(b, f0, loc=bl)
    if how == "dud":
        for fr in range(f0, min(N, f0 + 24) + 1, 2):
            t = (fr - f0) / 24.0; key(b, fr, loc=bl + Vector((0.6 * t, 0.25 * t, 0.2 * math.sin(t * math.pi))))
    else:
        for fr in range(f0, N + 1, 2):
            t = (fr - f0) / 30.0; key(b, fr, loc=bl + Vector((3.0 * t, 6.0 * t, 3.4 * t - 0.25 * t * t)))
    random.seed(f0)
    for k in range(10):
        p = ball(f"gdust{k}", 0.07, tuple(bl), toon("#b5b7c0", shadow="#5b5e72"), outline=0.0, seg=8); d = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(0.3, 1))).normalized()
        key(p, 1, scale=0.001); key(p, f0 - 1, scale=0.001, loc=bl); key(p, f0 + 5, scale=1.8 if how == "dud" else 1.0, loc=bl + d * 0.3); key(p, f0 + 24, scale=0.001, loc=bl + d * 0.55)
    _hit(ctx, f0)

def club(ctx, f0, f1, N, arg):
    """Hold up the golf club (scoop handle + 6-iron head), popping in at f0."""
    P = _who(ctx, arg or "al"); c = A.golf_club("club", (0, -0.05, 0.0), P["handR"], rot=(180, 0, 0), length=0.8)
    _arm(P, "R", 1, rx=-20); _arm(P, "R", f0, rx=-20); _arm(P, "R", f0 + 6, rx=-150, rz=10)
    _pop_in(c, f0)

def surface(ctx, f0, f1, N, arg):
    """The sunken capsule rises back up out of the sea, f0..f1 (1999 recovery)."""
    o = ctx["capsule"]; ctx["cap_animated"] = True; b = Vector(o.location)
    for fr in range(1, N + 1, 2):
        t = ease_out((fr - f0) / max(1, f1 - f0)) if fr > f0 else 0
        key(o, fr, loc=b + Vector((0, 0, -3.0 + 3.6 * t)), rot=(-8, 12 + 20 * t, 0))
    H = ctx.get("heli")
    if H: key(H["cable"], 1, scale=1.0)

def dust(ctx, f0, f1, N, arg):
    """Moon-dust puff around a character's feet (or prop_home) at f0."""
    P = _who(ctx, arg) if arg else None
    import bpy; bpy.context.view_layer.update()
    o = Vector(P["root"].matrix_world.translation) + Vector((0, -0.1, 0.05)) if P else _home(ctx)
    random.seed(f0)
    for k in range(14):
        p = ball(f"dust{f0}_{k}", 0.09, tuple(o), toon("#b5b7c0", shadow="#5b5e72"), outline=0.0, seg=8)
        d = Vector((random.uniform(-1, 1), random.uniform(-0.6, 0.6), random.uniform(0.05, 0.5))).normalized()
        key(p, 1, scale=0.001); key(p, f0 - 1, scale=0.001, loc=o); key(p, f0 + 6, scale=1.5, loc=o + d * 0.45); key(p, f0 + 30, scale=0.001, loc=o + d * 0.8 - Vector((0, 0, 0.1)))
    _hit(ctx, f0)

def ladder_hop(ctx, f0, f1, N, arg):
    """Character waits on the bottom rung, then hops down onto the footpad; lands at f0+10."""
    P = _who(ctx, arg); b = P["body"]; P["root"].location = (0, 0.12, 0)
    up, down = Vector((0, 0.12, 0.62)), Vector((0, -0.05, 0.08))
    key(b, 1, loc=up); key(b, f0, loc=up)
    for k in range(0, 11):
        t = k / 10.0; key(b, f0 + k, loc=up.lerp(down, t) + Vector((0, 0, 0.35 * math.sin(t * math.pi))))
    key(b, f0 + 13, loc=down + Vector((0, 0, -0.04))); key(b, f0 + 17, loc=down)
    _arm(P, "R", f0, rx=-150, ry=10); _arm(P, "L", f0, rx=-150, ry=-10); _arm(P, "R", f0 + 12, rx=-40); _arm(P, "L", f0 + 12, rx=-40)
    dust(ctx, f0 + 10, f1, N, arg)

def tumble(ctx, f0, f1, N, arg):
    """ctx[arg] (default lm_root) spins and wobbles out of control between f0 and f1."""
    o = ctx.get(arg or "lm_root"); r0 = Vector(o.rotation_euler); random.seed(61)
    ax = [random.choice((-1, 1)) * random.uniform(200, 420) for _ in range(3)]
    for fr in range(1, N + 1, 2):
        t = max(0, min(fr, f1) - f0) / 30.0
        key(o, fr, rot=(math.degrees(r0.x) + ax[0] * t, math.degrees(r0.y) + ax[1] * t * 0.6, math.degrees(r0.z) + ax[2] * t * 0.4))

def undock(ctx, f0, f1, N, arg):
    """LM drifts away from the CSM (and slightly down), f0..f1."""
    o = ctx["lm_root"]; b = Vector(o.location)
    for fr in range(1, N + 1, 2):
        t = ease_in_out((fr - f0) / max(1, f1 - f0)); key(o, fr, loc=b + Vector((1.2 * t, 0.3 * t, -1.0 * t)))
    if "lm_label" in ctx:   # the call sign drifts a little with it but stays clear of the captions and the frame edge
        L = ctx["lm_label"]; lb = Vector(L.location)
        for fr in range(1, N + 1, 2):
            t = ease_in_out((fr - f0) / max(1, f1 - f0)); key(L, fr, loc=lb + Vector((0.4 * t, 0.0, 0.0)))

def descend(ctx, f0, f1, N, arg):
    """ctx[arg] (default lm_root) glides down/away toward the surface over f0..f1."""
    o = ctx.get(arg or "lm_root"); b = Vector(o.location)
    for fr in range(1, N + 1, 2):
        t = ease_in_out((fr - f0) / max(1, f1 - f0)); key(o, fr, loc=b + Vector((0.5 * t, 3.0 * t, -2.6 * t)))

def zoom_by(ctx, f0, f1, N, arg):
    """ctx[arg] (default csm) rockets across frame with speed lines."""
    o = ctx.get(arg or "csm"); b = Vector(o.location); random.seed(71)
    for fr in range(1, N + 1, 2):
        t = (fr - f0) / max(1, f1 - f0); key(o, fr, loc=b + Vector((-6 + 12 * t, 0, 1.5 - 3 * t)))
    for i in range(22):
        y = random.uniform(-2, 3); z = random.uniform(-3, 3); L = random.uniform(1.5, 4)
        r = cyl(f"speed{i}", 0.02, L, (0, y, z), emit("#f6ead8", 2.0), rot=(0, 90 - 26, 0), outline=0.0, bevel=0.0)
        x0 = random.uniform(-8, 8)
        for fr in range(1, N + 1, 2):
            key(r, fr, loc=(((x0 - fr * 0.9) + 10) % 20 - 10, y, z + ((x0 - fr * 0.9) % 20) * 0.0))

def gauge_(ctx, f0, f1, N, arg):
    """CO2 gauge at prop_home; arg up = needle climbs into the red, down = falls back to green (f0..f1)."""
    root, nd = A.gauge("co2", tuple(_home(ctx) + Vector((0, -0.2, 0.15))), label="CO2", scale=1.15)
    a, b = (60, -55) if arg != "down" else (-55, 60)
    for fr in range(1, N + 1, 2):
        t = ease_in_out((fr - f0) / max(1, f1 - f0)); key(nd, fr, rot=(0, -(a + (b - a) * t) + 3 * math.sin(fr * 1.7) * (arg != "down"), 0))

def square_peg(ctx, f0, f1, N, arg):
    """Square cartridge slides in from the left, bonks a plate with a smaller round hole at f0, and again at f0+22."""
    o = _home(ctx) + Vector((0, 0, 0.05))
    A.round_socket("socket", tuple(o + Vector((0.18, 0.25, 0))), r=0.15)
    can = A.lioh_canister("peg", "square", tuple(o), s=0.36)
    p_far, p_hit = o + Vector((-0.75, -0.35, 0.02)), o + Vector((0.1, 0.0, 0.0))
    hits = [f0, f0 + 22]
    key(can, 1, loc=p_far)
    for h in hits:
        key(can, h - 10, loc=p_far, rot=(0, 0, 0)); key(can, h, loc=p_hit, rot=(0, 0, 0))
        key(can, h + 3, loc=p_hit + Vector((-0.12, -0.1, 0)), rot=(0, 10, 0)); key(can, h + 9, loc=p_far + Vector((0.2, 0.1, 0)), rot=(0, -5, 0))
        _hit(ctx, h)

def assemble(ctx, f0, f1, N, arg):
    """The 'mailbox' builds itself: each part flies in from off to the side and snaps on, f0..f1."""
    root = A.mailbox("mailbox", tuple(_home(ctx) + Vector((0, 0, -0.05))))
    parts = list(root.children); random.seed(81); n = len(parts)
    for i, p in enumerate(parts):
        home = Vector(p.location); off = Vector((random.choice((-1.5, 1.5)), -0.5, random.uniform(-0.4, 0.8)))
        a = f0 + int(i * (f1 - f0) / max(1, n)); bnd = a + 8
        key(p, 1, loc=home + off, scale=0.001); key(p, a - 1, loc=home + off, scale=0.001)
        key(p, a, loc=home + off, scale=1.0); key(p, bnd, loc=home, scale=1.08); key(p, bnd + 3, loc=home, scale=1.0)
    for fr in range(1, N + 1, 3): key(root, fr, rot=(0, 0, 20 * math.sin(fr / 25) + 15))

def tape_spin(ctx, f0, f1, N, arg):
    """A duct tape roll whirls around prop_home."""
    t = A.duct_tape("tapefly", tuple(_home(ctx))); o = _home(ctx)
    key(t, 1, scale=0.001); key(t, f0 - 1, scale=0.001)
    for fr in range(f0, N + 1, 2):
        a = (fr - f0) / 8.0; key(t, fr, loc=o + Vector((0.45 * math.cos(a), -0.2 + 0.25 * math.sin(a), 0.15 * math.sin(a * 0.5))), rot=(90, fr * 25, 0), scale=1.2)

def item_pop(ctx, f0, f1, N, arg):
    """Pop one workshop item up and spin it: item_pop:sock (sock, tape, bag, card, square, round, hose)."""
    o = ctx["items"][arg]; b = Vector(o.location)
    key(o, 1, loc=b); key(o, f0 - 1, loc=b)
    for fr in range(f0, N + 1, 2):
        t = ease_out((fr - f0) / 10.0); key(o, fr, loc=b + Vector((0, -0.25 * t, 0.45 * t + 0.03 * math.sin(fr / 6))), rot=(math.degrees(o.rotation_euler.x), 0, 10 * (fr - f0)), scale=1 + 0.4 * t)

def cash(ctx, f0, f1, N, arg):
    """A banded stack of cash: in a character's hand (cash:pete) or floating at prop_home (cash)."""
    if arg and arg in _chars(ctx):
        P = _who(ctx, arg); c = A.cash_stack("cash", (0, -0.1, -0.02), P["handR"], rot=(70, 0, 0)); _arm(P, "R", f0, rx=-70, rz=30)
        _pop_in(c, f0, 1.3)
    else:
        c = A.cash_stack("cash", tuple(_home(ctx))); c.scale = (2.2,) * 3
        key(c, 1, scale=0.001); key(c, f0 - 1, scale=0.001); key(c, f0 + 4, scale=2.6); key(c, f0 + 8, scale=2.2)
        for fr in range(f0, N + 1, 3): key(c, fr, rot=(60, 0, 10 * math.sin(fr / 10)))

def notepad_(ctx, f0, f1, N, arg):
    P = _who(ctx, arg); A.notepad("notepad", (0.0, -0.12, 0.0), P["handR"], rot=(-20, 0, 0)); _arm(P, "R", 1, rx=-60, rz=25)

def handshake(ctx, f0, f1, N, arg):
    """a>b shake hands (studio two-shot): both reach to the middle and pump."""
    a, b = (arg or "pete>reporter").split(">"); Pa, Pb = _who(ctx, a), _who(ctx, b)
    for P, side, rz in ((Pa, "L", -40), (Pb, "R", 40)):
        _arm(P, side, f0 - 1); _arm(P, side, f0 + 5, rx=-70, rz=rz)
        for fr in range(f0 + 8, f1, 8):
            _arm(P, side, fr, rx=-62, rz=rz); _arm(P, side, fr + 4, rx=-78, rz=rz)

def throw(ctx, f0, f1, N, arg):
    """Javelin throw of a long handle; release at f0."""
    P = _who(ctx, arg); import bpy; bpy.context.view_layer.update()
    o = Vector(P["root"].matrix_world.translation) + Vector((0.3, -0.1, 1.6))
    pole = cyl("javelin", 0.02, 1.4, tuple(o), toon("#c9ced6", hi=0.5), rot=(0, 70, 0), outline=0.004)
    _arm(P, "R", f0 - 10, rx=40); _arm(P, "R", f0, rx=-140)
    key(pole, 1, loc=o); key(pole, f0, loc=o)
    for fr in range(f0, N + 1, 2):
        t = (fr - f0) / 30.0; key(pole, fr, loc=o + Vector((-2.5 * t, 4.0 * t, 1.6 * t - 0.25 * t * t)), rot=(0, 70 + 25 * t, 0))

ACTIONS = dict(talk=talk, surprise=surprise, angry=angry, frown=frown, grin=grin, wink=wink, point=point, shrug=shrug,
               arms_crossed=arms_crossed, jump=jump, float=float_, sandwich_float=sandwich_float, sandwich_hold=sandwich_hold,
               sandwich_out=sandwich_out, give=give, bite=bite, crumbs=crumbs, crumbs_drift=crumbs_drift, crumbs_panel=crumbs_panel,
               pocket=pocket, pouch=pouch, xmark=xmark, clipboard=clip, tortilla=tortilla_, liftoff=liftoff, gavel=gavel_bang,
               word=word_, flash=flash, lightning=lightning, alarms=alarms, glitch=glitch, sce_switch=sce_switch, laugh=laugh,
               hatch_blow=hatch_blow, sink=sink, lift_fail=lift_fail, swim=swim, dimes=dimes, dime_stack=dime_stack, swing=swing,
               dust=dust, ladder_hop=ladder_hop, tumble=tumble, undock=undock, descend=descend, zoom_by=zoom_by, gauge=gauge_,
               square_peg=square_peg, assemble=assemble, tape_spin=tape_spin, item_pop=item_pop, cash=cash, notepad=notepad_,
               handshake=handshake, throw=throw, club=club, surface=surface, nohatch=nohatch)
