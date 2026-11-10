"""Procedural asset library. Every function builds one reusable asset and returns its root
(and, for characters, a dict of named parts that actions can animate).
Characters face -Y (towards a camera placed at negative Y)."""
import math, random
from mathutils import Vector, noise
from toon import *

# ------------------------------------------------------------------ characters
def character(name, kind="astronaut", accent="#f08a24", suit="#f4f1ea", skin="#f2c39b", hair="#4a3222",
              seated=False, tie="#e2483d", glasses=False, hair_style="crop", helmet=True,
              face=(1.0, 0.95, 1.02), helmet_col="#f8f6f0", rim_col=None, brow=(0.12, 0.04, 0.035), brow_col=None, tuft=None):
    """face: head scale (wide/round vs long/narrow). tuft: hair colour for a fringe that shows inside the helmet."""
    """kind: astronaut | shirt | suit | polo. Chunky toy proportions, big head, simple face."""
    P = {}
    root = empty(name); P["root"] = root
    body = empty(name + "_body", (0, 0, 0), root); P["body"] = body
    mat_suit, mat_skin = toon(suit), toon(skin)
    ol = 0.014
    # legs
    if seated:
        for s in (-1, 1):
            box(f"{name}_thigh{s}", (0.24, 0.6, 0.26), (0.16 * s, -0.25, 0.48), mat_suit, parent=body, outline=ol)
            box(f"{name}_shin{s}", (0.22, 0.24, 0.5), (0.16 * s, -0.5, 0.25), mat_suit, parent=body, outline=ol)
    else:
        for s in (-1, 1):
            box(f"{name}_leg{s}", (0.24, 0.26, 0.62), (0.16 * s, 0, 0.36), mat_suit if kind == "astronaut" else toon("#2b3550" if kind != "suit" else suit), parent=body, outline=ol)
            box(f"{name}_boot{s}", (0.27, 0.36, 0.14), (0.16 * s, -0.05, 0.07), toon("#2a2a33" if kind != "astronaut" else "#d9d4ca"), parent=body, outline=ol)
    # torso
    torso_col = suit if kind in ("astronaut", "suit") else accent
    box(name + "_torso", (0.66, 0.44, 0.72), (0, 0, 0.98), toon(torso_col), parent=body, outline=ol)
    if kind == "astronaut":
        box(name + "_patch", (0.18, 0.05, 0.14), (-0.16, -0.22, 1.12), toon(accent), parent=body, outline=0.006, sub=1)
        box(name + "_stripe", (0.68, 0.46, 0.08), (0, 0, 0.78), toon(accent), parent=body, outline=0.0)
        box(name + "_pack", (0.3, 0.08, 0.2), (0.12, -0.23, 0.88), toon("#c9c3b8"), parent=body, outline=0.006)
        torus(name + "_collar", 0.25, 0.06, (0, 0, 1.36), toon("#9aa3ad"), parent=body)
    elif kind == "suit":
        box(name + "_shirt", (0.2, 0.05, 0.42), (0, -0.215, 1.12), toon("#f4f1ea"), parent=body, outline=0.0)
        box(name + "_tie", (0.08, 0.06, 0.36), (0, -0.235, 1.1), toon(tie), parent=body, outline=0.004)
    elif kind == "polo":
        box(name + "_collarp", (0.34, 0.08, 0.08), (0, -0.2, 1.33), toon(accent), parent=body, outline=0.004)
        box(name + "_logo", (0.1, 0.04, 0.1), (-0.16, -0.225, 1.14), toon("#f4f1ea"), parent=body, outline=0.0)
    # head group (pivot at neck)
    head = empty(name + "_head", (0, 0, 1.38), body); P["head"] = head
    hz = 0.32
    fx = face[0]
    ball(name + "_face", 0.34, (0, 0, hz), mat_skin, scale=face, parent=head, outline=ol)
    for s in (-1, 1):
        ball(f"{name}_ear{s}", 0.07, (0.34 * fx * s, 0, hz), mat_skin, scale=(0.6, 1, 1), parent=head, outline=0.008)
    eyes = []
    for s in (-1, 1):
        e = ball(f"{name}_eye{s}", 0.06, (0.12 * fx * s, -0.285, hz + 0.05), toon("#120d18", shadow="#120d18", hi=0.05), scale=(0.95, 0.5, 1.3), parent=head, outline=0.0)
        ball(f"{name}_glint{s}", 0.017, (0.02, -0.03, 0.03), emit("#ffffff"), parent=e, outline=0.0)
        eyes.append(e)
    P["eyes"] = eyes
    bcol = brow_col or (hair if kind != "astronaut" else "#5a3a26")
    brows = [box(f"{name}_brow{s}", brow, (0.12 * fx * s, -0.29, hz + 0.17), toon(bcol), parent=head, outline=0.0, sub=1) for s in (-1, 1)]
    P["brows"] = brows
    ball(name + "_nose", 0.05, (0, -0.33, hz - 0.03), toon("#e8a77f"), parent=head, outline=0.006)
    mouth = ball(name + "_mouth", 0.07, (0, -0.3, hz - 0.14), toon("#6b1f2a", shadow="#3a0f18"), scale=(1.1, 0.4, 0.45), parent=head, outline=0.0)
    P["mouth"] = mouth
    for s in (-1, 1):
        ball(f"{name}_cheek{s}", 0.05, (0.2 * fx * s, -0.265, hz - 0.07), toon("#f2a0a0"), scale=(1, 0.3, 0.6), parent=head, outline=0.0)
    if kind == "astronaut" and helmet:
        if tuft == "swoop":   # rounded fringe swept to one side
            ball(name + "_hair", 0.35, (0, 0.03, hz + 0.1), toon(hair), scale=(fx * 1.02, 1.0, 0.75), parent=head, outline=ol,
                 cut=lambda c: c.z < -0.04 or (c.y < -0.2 and c.z < 0.14))
            ball(name + "_tuft", 0.13, (-0.1, -0.24, hz + 0.25), toon(hair), scale=(1.5, 0.8, 0.6), rot=(0, -20, 0), parent=head, outline=ol)
        elif tuft == "flat":  # flat-top crew cut, square and dark
            box(name + "_hair", (0.58 * fx, 0.56, 0.14), (0, 0.0, hz + 0.27), toon(hair), parent=head, outline=ol, bevel=0.06)
        shell = ball(name + "_helmet", 0.44, (0, 0.02, hz + 0.02), toon(helmet_col), seg=32, parent=head, outline=ol,
                     cut=lambda c: c.y < -0.16 and c.z > -0.36)
        sol = shell.modifiers.new("thick", "SOLIDIFY"); sol.thickness = 0.04
        shell.modifiers.move(len(shell.modifiers) - 1, 0)
        torus(name + "_rim", 0.405, 0.035, (0, -0.16, hz + 0.02), toon(rim_col or accent), rot=(90, 0, 0), parent=head)
    else:
        if hair_style == "crop":
            ball(name + "_hair", 0.355, (0, 0.04, hz + 0.1), toon(hair), scale=(1.02, 1.0, 0.72), parent=head, outline=ol,
                 cut=lambda c: c.z < -0.06 or (c.y < -0.18 and c.z < 0.12))
        elif hair_style == "long":   # fringe plus hair down to the shoulders
            ball(name + "_hair", 0.36, (0, 0.04, hz + 0.1), toon(hair), scale=(1.04, 1.0, 0.74), parent=head, outline=ol,
                 cut=lambda c: c.z < -0.06 or (c.y < -0.2 and c.z < 0.16))
            box(name + "_hairback", (0.72, 0.3, 0.62), (0, 0.12, hz - 0.12), toon(hair), parent=head, outline=ol, bevel=0.1)
            ball(name + "_bangs", 0.14, (0.08, -0.25, hz + 0.24), toon(hair), scale=(1.8, 0.7, 0.55), rot=(0, 12, 0), parent=head, outline=ol)
        elif hair_style == "bald":
            ball(name + "_hair", 0.355, (0, 0.06, hz + 0.0), toon(hair), scale=(1.03, 1.0, 0.7), parent=head, outline=ol,
                 cut=lambda c: c.z > 0.05 or c.y < -0.1 or c.z < -0.2)
    if glasses:
        for s in (-1, 1):
            torus(f"{name}_glass{s}", 0.075, 0.012, (0.12 * s, -0.315, hz + 0.05), toon("#1a1a22"), rot=(90, 0, 0), parent=head)
    # arms: shoulder pivots; arm hangs along -Z
    arms, hands = [], []
    for s in (-1, 1):
        sh = empty(f"{name}_shoulder{s}", (0.4 * s, 0, 1.24), body)
        sleeve = suit if kind in ("astronaut", "suit") else accent
        box(f"{name}_arm{s}", (0.18, 0.2, 0.52), (0, 0, -0.24), toon(sleeve), parent=sh, outline=ol)
        hand = ball(f"{name}_hand{s}", 0.1, (0, 0, -0.52), toon("#e9e4da" if kind == "astronaut" else skin), parent=sh, outline=ol)
        sh.rotation_euler = (0, math.radians(-8 * s), 0)
        arms.append(sh); hands.append(hand)
    P["armL"], P["armR"] = arms[1], arms[0]   # L = character's left (screen right)
    P["handL"], P["handR"] = hands[1], hands[0]
    return root, P

# ------------------------------------------------------------------ props
def sandwich(name="sandwich", parent=None, loc=(0, 0, 0), scale=1.0):
    root = empty(name, loc, parent); root.scale = (scale,) * 3
    rye, crust = toon("#c58b52"), toon("#7a4a2a")
    for z in (-0.06, 0.06):
        box(f"{name}_bread{z}", (0.42, 0.34, 0.07), (0, 0, z), rye, parent=root, outline=0.01)
        box(f"{name}_crust{z}", (0.44, 0.36, 0.05), (0, 0, z), crust, parent=root, outline=0.0)
    box(name + "_beef", (0.44, 0.35, 0.06), (0.01, -0.005, 0), toon("#d0605a"), parent=root, outline=0.008, sub=2)
    box(name + "_mustard", (0.4, 0.33, 0.015), (0, -0.01, 0.033), toon("#e7b52a"), parent=root, outline=0.0)
    random.seed(3)
    for i in range(14):
        ball(f"{name}_seed{i}", 0.008, (random.uniform(-0.18, 0.18), random.uniform(-0.14, 0.14), 0.098), toon("#3b2414"), scale=(1.6, 1, 0.6), parent=root, outline=0.0, seg=6)
    return root

def crumbs(name, n, origin, spread=1.4, parent=None, size=0.022, seed=5):
    random.seed(seed); out = []
    m1, m2 = toon("#c58b52"), toon("#7a4a2a")
    for i in range(n):
        s = size * random.uniform(0.5, 1.4)
        c = box(f"{name}{i}", (s, s * random.uniform(0.6, 1.2), s * random.uniform(0.5, 1)), origin, m1 if i % 3 else m2, sub=0, bevel=s * 0.2, outline=0.0, parent=parent)
        c["vel"] = (random.uniform(-1, 1) * spread, random.uniform(-1, 0.4) * spread, random.uniform(-0.6, 1) * spread)
        c["spin"] = (random.uniform(-400, 400), random.uniform(-400, 400), random.uniform(-400, 400))
        out.append(c)
    return out

def food_pouch(name="pouch", loc=(0, 0, 0), parent=None):
    root = empty(name, loc, parent)
    box(name + "_bag", (0.26, 0.08, 0.34), (0, 0, 0), toon("#e8eef2"), parent=root, outline=0.008)
    box(name + "_label", (0.18, 0.02, 0.1), (0, -0.045, 0.04), toon("#5aa9e6"), parent=root, outline=0.0)
    for i, (x, z) in enumerate([(-0.05, -0.07), (0.05, -0.07), (0, -0.12)]):
        box(f"{name}_cube{i}", (0.06, 0.04, 0.06), (x, -0.03, z), toon("#d8b27a"), parent=root, outline=0.004)
    return root

def tortilla(name="tortilla", loc=(0, 0, 0), parent=None, r=0.28):
    root = empty(name, loc, parent)
    t = cyl(name + "_disc", r, 0.025, (0, 0, 0), toon("#ead39a"), parent=root, outline=0.008, seg=32)
    random.seed(9)
    for i in range(9):
        a, d = random.uniform(0, 6.28), random.uniform(0.03, r * 0.85)
        ball(f"{name}_spot{i}", 0.025, (math.cos(a) * d, math.sin(a) * d, 0.014), toon("#b8873f"), scale=(1, 1, 0.25), parent=root, outline=0.0, seg=8)
    return root

def red_x(name="redx", loc=(0, 0, 0), size=1.0, parent=None):
    root = empty(name, loc, parent)
    for a in (45, -45):
        box(f"{name}{a}", (size, 0.08, size * 0.18), (0, 0, 0), emit("#ff3b30", 1.4), rot=(0, a, 0), parent=root, outline=0.02)
    return root

def gavel(name="gavel", loc=(0, 0, 0), parent=None):
    root = empty(name, loc, parent)   # pivot at the hand end
    cyl(name + "_handle", 0.035, 0.6, (0.3, 0, 0), toon("#6b3e22"), rot=(0, 90, 0), parent=root, outline=0.008)
    cyl(name + "_head", 0.09, 0.32, (0.6, 0, 0), toon("#7a4a2a"), parent=root, outline=0.01)
    return root

def clipboard(name="clipboard", loc=(0, 0, 0), parent=None, rot=(0, 0, 0)):
    root = empty(name, loc, parent, rot)
    box(name + "_board", (0.5, 0.03, 0.66), (0, 0, 0), toon("#a8743f"), parent=root, outline=0.01)
    box(name + "_paper", (0.42, 0.02, 0.54), (0, -0.02, -0.02), toon("#f8f4ea"), parent=root, outline=0.0)
    box(name + "_clip", (0.2, 0.05, 0.07), (0, -0.03, 0.31), toon("#9aa3ad"), parent=root, outline=0.006)
    for i in range(6):
        box(f"{name}_line{i}", (0.28 - 0.04 * (i % 2), 0.01, 0.025), (0.03, -0.035, 0.18 - i * 0.075), toon("#5b6b8c"), parent=root, outline=0.0, sub=0, bevel=0.005)
        box(f"{name}_tick{i}", (0.035, 0.01, 0.035), (-0.15, -0.035, 0.18 - i * 0.075), toon("#5fb36a"), parent=root, outline=0.0, sub=0, bevel=0.005)
    return root

def microphone(name, loc, parent=None):
    root = empty(name, loc, parent)
    cyl(name + "_base", 0.07, 0.03, (0, 0, 0), toon("#22283a"), parent=root, outline=0.0)
    cyl(name + "_stem", 0.012, 0.3, (0, -0.05, 0.14), toon("#22283a"), rot=(-20, 0, 0), parent=root, outline=0.0)
    ball(name + "_head", 0.04, (0, -0.1, 0.29), toon("#3b4256"), parent=root, outline=0.006)
    return root

# ------------------------------------------------------------------ space
def earth(name="earth", r=5.0, loc=(0, 0, 0), clouds=True, atmosphere=True):
    """Low-poly toon Earth: flat icosphere faces coloured by noise (ocean, land, desert, ice)."""
    root = empty(name, loc)
    e = ball(name + "_globe", r, (0, 0, 0), None, ico=4, smooth=False, outline=0.0, parent=root)
    for c in ("#2f7fd6", "#4fae5b", "#d8b27a", "#f4f7fb", "#2a6fc2"):
        e.data.materials.append(toon(c, hi=0.3))
    def pick(c):
        n = noise.noise(Vector(c) * (1.6 / r) + Vector((3.1, 1.7, 0.3)))
        lat = abs(c.z) / r
        if lat > 0.86: return 3
        if n > 0.18: return 2 if (n > 0.42 and lat < 0.5) else 1
        return 0 if (int((c.x + c.y) * 7 / r) % 2) else 4
    faces_by(e, pick)
    if clouds:
        random.seed(11)
        cm = toon("#ffffff", shadow="#b9c6e6")
        for i in range(26):
            v = Vector((random.gauss(0, 1), random.gauss(0, 1), random.gauss(0, 0.7))).normalized() * (r * 1.04)
            cl = ball(f"{name}_cloud{i}", r * random.uniform(0.07, 0.13), v, cm, scale=(1.6, 1.6, 0.45), ico=2, smooth=False, outline=0.0, parent=root)
            cl.rotation_euler = v.to_track_quat("Z", "Y").to_euler()
    if atmosphere:
        ball(name + "_atmo", r * 1.09, (0, 0, 0), glow("#7fc4ff", 2.0, 2.2), seg=48, outline=0.0, parent=root)
    return root

def moon_surface(name="moon", size=40):
    root = empty(name)
    g = box(name + "_ground", (size, size, 1.0), (0, 0, -0.5), toon("#a7a9b4", shadow="#4b4e66"), sub=0, bevel=0.0, outline=0.0, parent=root)
    random.seed(4); m = toon("#8e909c", shadow="#41435a")
    for i in range(24):
        x, y = random.uniform(-10, 10), random.uniform(-2, 25); R = random.uniform(0.4, 1.6)
        torus(f"{name}_crater{i}", R, R * 0.18, (x, y, 0.0), m, parent=root)
        ball(f"{name}_rock{i}", random.uniform(0.08, 0.3), (random.uniform(-8, 8), random.uniform(-3, 14), 0.05), toon("#7f818d"), ico=1, smooth=False, scale=(1.3, 1, 0.7), outline=0.006, parent=root)
    return root

def gemini_capsule(name="gemini", loc=(0, 0, 0), rot=(0, 0, 0)):
    """Exterior: dark cone re-entry module + white adapter. Axis along +Z (nose up)."""
    root = empty(name, loc, rot=rot)
    dark, white = toon("#2c3142", shadow="#141826", hi=0.35), toon("#f4f1ea")
    cyl(name + "_adapter", 1.5, 1.6, (0, 0, -0.8), white, r2=1.1, parent=root, outline=0.03)
    cyl(name + "_cabin", 1.1, 1.5, (0, 0, 0.75), dark, r2=0.55, parent=root, outline=0.03)
    cyl(name + "_nose", 0.55, 0.9, (0, 0, 1.95), dark, r2=0.42, parent=root, outline=0.03)
    for s in (-1, 1):
        box(f"{name}_win{s}", (0.22, 0.1, 0.3), (0.28 * s, -0.86, 0.95), emit("#9fd3ff", 1.2), rot=(-20, 0, 0), parent=root, outline=0.01)
    for i in range(8):
        a = i * math.pi / 4
        box(f"{name}_rib{i}", (0.05, 0.05, 1.5), (math.cos(a) * 0.86, math.sin(a) * 0.86, 0.72), toon("#454b5e"), rot=(0, 0, 0), parent=root, outline=0.0)
    return root

def rocket(name="titan", loc=(0, 0, 0), with_capsule=True):
    """Titan II style two-stage booster with a Gemini capsule on top. Base at z=0."""
    root = empty(name, loc)
    body, band = toon("#e9e6de"), toon("#2c3142")
    cyl(name + "_s1", 0.62, 6.0, (0, 0, 3.2), body, parent=root, outline=0.03)
    cyl(name + "_s2", 0.62, 3.0, (0, 0, 7.75), body, parent=root, outline=0.03)
    for z in (1.0, 5.9, 6.3, 9.0):
        cyl(f"{name}_band{z}", 0.635, 0.18, (0, 0, z), band, parent=root, outline=0.0)
    text(name + "_usa", "GEMINI", 0.34, (0, -0.64, 4.6), toon("#2c3142"), rot=(90, 90, 0), parent=root)
    for s in (-1, 1):
        cyl(f"{name}_bell{s}", 0.26, 0.5, (0.28 * s, 0, 0.0), toon("#5b6170"), r2=0.14, parent=root, outline=0.015)
    if with_capsule:
        g = gemini_capsule(name + "_cap", (0, 0, 10.0)); g.scale = (0.42,) * 3; g.parent = root
    return root

def shuttle_stack(name="shuttle", loc=(0, 0, 0)):
    root = empty(name, loc)
    cyl(name + "_tank", 0.85, 8.0, (0, 0.2, 4.6), toon("#e07a2e"), r2=0.85, parent=root, outline=0.03)
    ball(name + "_tanknose", 0.85, (0, 0.2, 8.6), toon("#e07a2e"), scale=(1, 1, 1.3), parent=root, outline=0.03, cut=lambda c: c.z < 0)
    for s in (-1, 1):
        cyl(f"{name}_srb{s}", 0.38, 7.6, (1.25 * s, 0.2, 4.1), toon("#f4f1ea"), parent=root, outline=0.025)
        cyl(f"{name}_srbnose{s}", 0.38, 0.8, (1.25 * s, 0.2, 8.3), toon("#f4f1ea"), r2=0.05, parent=root, outline=0.025)
    orb = empty(name + "_orbiter", (0, -1.05, 0), root)
    box(name + "_body", (0.9, 0.9, 6.0), (0, 0, 4.0), toon("#f4f1ea"), parent=orb, outline=0.03)
    ball(name + "_onose", 0.45, (0, 0, 7.0), toon("#f4f1ea"), scale=(1, 1, 1.6), parent=orb, outline=0.03, cut=lambda c: c.z < 0)
    box(name + "_belly", (0.92, 0.3, 6.0), (0, -0.35, 4.0), toon("#2c3142"), parent=orb, outline=0.0)
    prism(name + "_wing", [(-2.2, 1.2), (2.2, 1.2), (0.45, 4.6), (-0.45, 4.6)], 0.2, (0, -0.1, 0), toon("#f4f1ea"), parent=orb, outline=0.025)
    prism(name + "_tail", [(-0.1, 1.2), (0.1, 1.2), (0.1, 2.6), (-0.1, 2.0)], 1.4, (0, 0.6, 0), toon("#f4f1ea"), rot=(0, 0, 90), parent=orb)
    for i, x in enumerate((-0.2, 0.2)):
        box(f"{name}_win{i}", (0.22, 0.05, 0.16), (x, -0.45, 6.9), toon("#1b2233"), parent=orb, outline=0.0)
    return root

def launch_tower(name="tower", loc=(0, 0, 0), h=12):
    root = empty(name, loc); m = toon("#d9573b")
    for x in (-0.7, 0.7):
        for y in (-0.7, 0.7):
            box(f"{name}_post{x}{y}", (0.12, 0.12, h), (x, y, h / 2), m, sub=0, bevel=0.02, parent=root, outline=0.01)
    for i in range(int(h / 1.5)):
        z = 0.8 + i * 1.5
        for (sx, sy, rx) in ((1.5, 0.1, 0), (0.1, 1.5, 0)):
            for o in (-0.7, 0.7):
                box(f"{name}_beam{i}{sx}{o}", (sx, sy, 0.1), (o if sx < 1 else 0, o if sy < 1 else 0, z), m, sub=0, bevel=0.02, parent=root, outline=0.008)
    for i, z in enumerate((h * 0.55, h * 0.78)):
        box(f"{name}_arm{i}", (2.4, 0.3, 0.25), (-1.5, 0, z), m, parent=root, sub=0, bevel=0.03, outline=0.01)
    return root

def flame(name, loc, parent=None, scale=1.0):
    root = empty(name, loc, parent); root.scale = (scale,) * 3
    cyl(name + "_outer", 0.45, 1.8, (0, 0, -0.9), emit("#ff8a2a", 3.0), r2=0.05, seg=16, parent=root, outline=0.0, rot=(180, 0, 0))
    cyl(name + "_inner", 0.25, 1.1, (0, 0, -0.55), emit("#fff1a8", 4.0), r2=0.03, seg=16, parent=root, outline=0.0, rot=(180, 0, 0))
    return root

def smoke_puffs(name, n, center, radius=3.0, seed=2):
    random.seed(seed); m = toon("#f1ede6", shadow="#a8a3b8"); out = []
    for i in range(n):
        a = random.uniform(0, 6.28)
        p = ball(f"{name}{i}", random.uniform(0.5, 1.1), (center[0] + math.cos(a) * radius * random.uniform(0.3, 1), center[1] + math.sin(a) * radius * 0.5, center[2] + random.uniform(0, 0.6)),
                 m, ico=2, smooth=True, outline=0.0)
        p["dir"] = (math.cos(a), math.sin(a) * 0.5); out.append(p)
    return out

# ------------------------------------------------------------------ rooms
def room_box(name, w, d, h, wall="#2f8f9d", floor="#5b6b8c", ceiling=None, back_only=False):
    root = empty(name)
    box(name + "_floor", (w, d, 0.2), (0, d / 2 - 1, -0.1), toon(floor), sub=0, bevel=0.0, outline=0.0, parent=root)
    box(name + "_back", (w, 0.2, h), (0, d - 1, h / 2), toon(wall), sub=0, bevel=0.0, outline=0.0, parent=root)
    if not back_only:
        for s in (-1, 1):
            box(f"{name}_side{s}", (0.2, d, h), (s * w / 2, d / 2 - 1, h / 2), toon(wall), sub=0, bevel=0.0, outline=0.0, parent=root)
    if ceiling:
        box(name + "_ceil", (w, d, 0.2), (0, d / 2 - 1, h), toon(ceiling), sub=0, bevel=0.0, outline=0.0, parent=root)
    return root

def console(name, loc, rot=(0, 0, 0), screen="#4fd1c5", w=1.4):
    root = empty(name, loc, rot=rot)
    box(name + "_desk", (w, 0.8, 0.75), (0, 0, 0.375), toon("#8a94a6"), parent=root, outline=0.012)
    box(name + "_top", (w, 0.5, 0.6), (0, 0.15, 1.0), toon("#6f7a8e"), rot=(-12, 0, 0), parent=root, outline=0.012)
    box(name + "_scr", (w * 0.36, 0.05, 0.3), (-w * 0.2, -0.12, 1.05), emit(screen, 1.3), rot=(-12, 0, 0), parent=root, outline=0.006)
    box(name + "_scr2", (w * 0.36, 0.05, 0.3), (w * 0.2, -0.12, 1.05), emit("#f6c35a", 1.1), rot=(-12, 0, 0), parent=root, outline=0.006)
    random.seed(hash(name) % 99)
    for i in range(6):
        ball(f"{name}_btn{i}", 0.03, (-w * 0.35 + i * w * 0.14, -0.33, 0.76), emit(random.choice(["#ff5a4f", "#5fd36a", "#ffd34f", "#7fc4ff"]), 1.5), outline=0.0, seg=8, parent=root)
    return root

# ------------------------------------------------------------------ helpers for the Apollo-era library
def rod(name, p0, p1, r, mat, parent=None, outline=0.0, seg=10):
    """Cylinder between two points (in parent space)."""
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0
    o = cyl(name, r, d.length, tuple((p0 + p1) / 2), mat, seg=seg, outline=outline, parent=parent, bevel=0.0)
    o.rotation_mode = "QUATERNION"; o.rotation_quaternion = d.to_track_quat("Z", "Y")
    return o

def word(name, body, loc=(0, 0, 0), size=0.5, color="#f08a24", parent=None, face_cam=True):
    """Big 3D word with a dark drop layer. face_cam: render_shot turns it to the camera."""
    root = empty(name, loc, parent)
    text(name + "_back", body, size, (0.025 * size, 0.0, -0.035 * size), toon("#120d18", shadow="#120d18"), rot=(0, 0, 0), extrude=0.03 * size, parent=root)
    text(name + "_front", body, size, (0, 0, 0.04 * size), emit(color, 1.3), rot=(0, 0, 0), extrude=0.03 * size, parent=root)
    if face_cam: root["face_cam"] = 1
    else: root.rotation_euler = (math.radians(90), 0, 0)
    return root

# ------------------------------------------------------------------ Apollo hardware
def saturn_v(name="saturn", loc=(0, 0, 0)):
    """Saturn V with the Apollo spacecraft and escape tower. Base at z=0, about 16.5 tall."""
    root = empty(name, loc)
    w, blk, sil = toon("#f1eee6"), toon("#1d2130", shadow="#0c0f18"), toon("#c9ced6")
    cyl(name + "_s1", 0.95, 4.6, (0, 0, 2.5), w, parent=root, outline=0.03)
    for a in (45, 225):
        r = math.radians(a)
        box(f"{name}_roll{a}", (0.66, 0.06, 1.7), (math.cos(r) * 0.95, math.sin(r) * 0.95, 1.25), blk, rot=(0, 0, a + 90), parent=root, outline=0.0, sub=0, bevel=0.0)
    cyl(name + "_ring1", 0.965, 0.3, (0, 0, 4.85), blk, parent=root, outline=0.0)
    cyl(name + "_s2", 0.95, 3.5, (0, 0, 6.75), w, parent=root, outline=0.03)
    cyl(name + "_ring2", 0.965, 0.2, (0, 0, 8.55), blk, parent=root, outline=0.0)
    cyl(name + "_taper", 0.95, 0.7, (0, 0, 9.0), w, r2=0.62, parent=root, outline=0.03)
    cyl(name + "_s3", 0.62, 2.2, (0, 0, 10.45), w, parent=root, outline=0.03)
    cyl(name + "_s3band", 0.635, 0.35, (0, 0, 9.6), blk, parent=root, outline=0.0)
    cyl(name + "_iu", 0.63, 0.18, (0, 0, 11.64), sil, parent=root, outline=0.0)
    cyl(name + "_sla", 0.62, 1.0, (0, 0, 12.23), w, r2=0.48, parent=root, outline=0.03)
    cyl(name + "_sm", 0.48, 0.8, (0, 0, 13.13), sil, parent=root, outline=0.025)
    cyl(name + "_cm", 0.48, 0.85, (0, 0, 13.95), w, r2=0.07, parent=root, outline=0.025)
    rod(name + "_les", (0, 0, 14.3), (0, 0, 15.6), 0.045, toon("#d9573b"), parent=root)
    cyl(name + "_lesr", 0.09, 0.7, (0, 0, 15.9), w, r2=0.03, parent=root, outline=0.01)
    text(name + "_usa", "USA", 0.62, (0, -0.97, 3.0), blk, rot=(90, 90, 0), parent=root)
    for i, (x, y) in enumerate([(0, 0), (0.48, 0.48), (-0.48, 0.48), (0.48, -0.48), (-0.48, -0.48)]):
        cyl(f"{name}_f1_{i}", 0.3, 0.6, (x, y, 0.0), toon("#5b6170"), r2=0.15, parent=root, outline=0.015)
    for a in (45, 135, 225, 315):
        r = math.radians(a)
        prism(f"{name}_fin{a}", [(0, 0), (0.55, 0), (0.0, 1.2)], 0.08, (math.cos(r) * 0.9, math.sin(r) * 0.9, -0.05), toon("#e9e6de"), rot=(0, 0, a - 90 + 90), parent=root, outline=0.015)
    return root

def apollo_csm(name="csm", loc=(0, 0, 0), rot=(0, 0, 0)):
    """Command + service module. Axis +Z (nose up). About 3 tall."""
    root = empty(name, loc, rot=rot)
    sil, cm, dark = toon("#c9ced6", hi=0.4), toon("#eef0f2", hi=0.4), toon("#3a3f4d")
    cyl(name + "_sm", 0.5, 1.4, (0, 0, 0), sil, parent=root, outline=0.02)
    for i in range(6):
        a = i * math.pi / 3
        box(f"{name}_rad{i}", (0.22, 0.03, 1.1), (math.cos(a) * 0.5, math.sin(a) * 0.5, 0), toon("#e8e8ea"), rot=(0, 0, math.degrees(a) + 90), parent=root, outline=0.0, sub=0, bevel=0.0)
    cyl(name + "_bell", 0.32, 0.75, (0, 0, -1.05), dark, r2=0.14, parent=root, outline=0.015)
    cyl(name + "_cm", 0.5, 0.78, (0, 0, 1.09), cm, r2=0.07, parent=root, outline=0.02)
    cyl(name + "_probe", 0.03, 0.25, (0, 0, 1.58), dark, parent=root, outline=0.0)
    for s in (-1, 1):
        box(f"{name}_win{s}", (0.1, 0.05, 0.1), (0.14 * s, -0.36, 1.12), emit("#9fd3ff", 1.0), rot=(-32, 0, 0), parent=root, outline=0.006)
    rod(name + "_hga", (0.45, 0.0, -0.55), (0.95, 0.0, -0.75), 0.025, dark, parent=root)
    for k, (dx, dz) in enumerate([(0.1, 0.1), (-0.1, 0.1), (0.1, -0.1), (-0.1, -0.1)]):
        cyl(f"{name}_dish{k}", 0.09, 0.03, (1.0, dx, -0.78 + dz), toon("#f4f1ea"), r2=0.02, rot=(0, 90, 0), parent=root, outline=0.006)
    for i in range(4):
        a = i * math.pi / 2 + math.pi / 4
        box(f"{name}_rcs{i}", (0.12, 0.12, 0.2), (math.cos(a) * 0.53, math.sin(a) * 0.53, 0.3), toon("#9aa3ad"), parent=root, outline=0.006)
    return root

def lunar_module(name="lm", loc=(0, 0, 0), rot=(0, 0, 0), legs=True):
    """LM: gold descent stage with four legs (ladder on the front leg, facing -Y) and a grey ascent stage.
    Returns (root, parts) with parts['ascent'] an empty that can fly away on its own."""
    root = empty(name, loc, rot=rot); P = {"root": root}
    gold, gold2, grey = toon("#e0ad3c", shadow="#7a5420", hi=0.35), toon("#c98f2a", shadow="#6a4418"), toon("#b9bdc6")
    dark = toon("#1b2233", shadow="#0b1020")
    desc = empty(name + "_descent", (0, 0, 0), root); P["descent"] = desc
    cyl(name + "_dbody", 0.95, 0.8, (0, 0, 1.0), gold, seg=8, parent=desc, outline=0.02, bevel=0.03)
    for i in range(4):
        a = math.radians(i * 90 + 22.5)
        box(f"{name}_foil{i}", (0.5, 0.04, 0.55), (math.cos(a) * 0.86, math.sin(a) * 0.86, 1.0), gold2, rot=(0, 0, math.degrees(a) + 90), parent=desc, outline=0.0, sub=0, bevel=0.0)
    cyl(name + "_dbell", 0.3, 0.35, (0, 0, 0.45), dark, r2=0.2, parent=desc, outline=0.01)
    if legs:
        for i, a in enumerate((270, 0, 90, 180)):
            r = math.radians(a); c, s = math.cos(r), math.sin(r)
            foot = Vector((c * 1.75, s * 1.75, 0.06))
            rod(f"{name}_leg{i}", (c * 0.85, s * 0.85, 1.25), foot + Vector((0, 0, 0.1)), 0.05, toon("#d9d4ca"), parent=desc, outline=0.0)
            rod(f"{name}_strut{i}", (c * 0.9, s * 0.9, 0.65), foot * 0.75 + Vector((0, 0, 0.35)), 0.03, toon("#9aa3ad"), parent=desc)
            cyl(f"{name}_pad{i}", 0.24, 0.08, tuple(foot), toon("#d9d4ca"), parent=desc, outline=0.01)
            if a == 270:   # ladder on the front leg
                for sx in (-0.17, 0.17):
                    rod(f"{name}_rail{sx}", (sx, -0.93, 1.0), (sx, -1.6, 0.42), 0.022, toon("#e9e6de"), parent=desc, outline=0.0)
                for k in range(5):
                    t = k / 4.0; y = -0.93 + (-1.6 + 0.93) * t; z = 1.0 + (0.42 - 1.0) * t
                    rod(f"{name}_rung{k}", (-0.17, y, z), (0.17, y, z), 0.018, toon("#e9e6de"), parent=desc)
                box(name + "_porch", (0.5, 0.35, 0.05), (0, -0.98, 1.38), toon("#d9d4ca"), parent=desc, outline=0.008)
    asc = empty(name + "_ascent", (0, 0, 1.4), root); P["ascent"] = asc
    box(name + "_abody", (1.3, 1.0, 0.95), (0, 0.15, 0.55), grey, parent=asc, outline=0.02)
    cyl(name + "_acab", 0.55, 1.15, (0, -0.25, 0.6), grey, rot=(0, 90, 0), parent=asc, outline=0.02)
    for s in (-1, 1):
        prism(f"{name}_win{s}", [(0, 0), (0.32, 0), (0.0, 0.3)] if s > 0 else [(0, 0), (-0.32, 0), (0.0, 0.3)], 0.06,
              (0.08 * s, -0.79, 0.7), dark, rot=(-12, 0, 0), parent=asc, outline=0.01)
    box(name + "_hatch", (0.36, 0.05, 0.36), (0, -0.8, 0.25), toon("#9aa3ad"), parent=asc, outline=0.008)
    for s in (-1, 1):
        box(f"{name}_quad{s}", (0.18, 0.18, 0.18), (0.75 * s, -0.1, 0.75), toon("#3a3f4d"), parent=asc, outline=0.008)
        for k, d in enumerate(((0, 0, 0.14), (0, 0, -0.14), (0.14 * s, 0, 0))):
            cyl(f"{name}_jet{s}{k}", 0.04, 0.1, (0.75 * s + d[0], -0.1, 0.75 + d[2]), toon("#5b6170"), r2=0.06, parent=asc, outline=0.0,
                rot=(0, 90, 0) if d[0] else (0, 0, 0))
    rod(name + "_ant", (0.3, 0.3, 1.0), (0.45, 0.45, 1.45), 0.02, toon("#9aa3ad"), parent=asc)
    cyl(name + "_dish", 0.16, 0.04, (0.47, 0.47, 1.5), toon("#f4f1ea"), r2=0.04, rot=(-30, 20, 0), parent=asc, outline=0.006)
    cyl(name + "_dock", 0.2, 0.15, (0, 0.15, 1.1), toon("#9aa3ad"), parent=asc, outline=0.008)
    return root, P

def moon_globe(name="moonglobe", r=10.0, loc=(0, 0, 0)):
    root = empty(name, loc)
    g = ball(name + "_g", r, (0, 0, 0), None, ico=4, smooth=False, outline=0.0, parent=root)
    for c in ("#b5b7c0", "#8d909c", "#cfd1d8"):
        g.data.materials.append(toon(c, shadow="#3a3d52", hi=0.25))
    def pick(c):
        n = noise.noise(Vector(c) * (1.3 / r) + Vector((1.3, 2.1, 0.7)))
        return 1 if n > 0.2 else (2 if n < -0.35 else 0)
    faces_by(g, pick)
    random.seed(17)
    for i in range(30):
        v = Vector((random.gauss(0, 1), random.gauss(0, 1), random.gauss(0, 1))).normalized() * r
        R = r * random.uniform(0.03, 0.08)
        t = torus(f"{name}_cr{i}", R, R * 0.2, tuple(v), toon("#9a9ca8", shadow="#3a3d52"), parent=root)
        t.rotation_euler = v.to_track_quat("Z", "Y").to_euler()
    return root

# ------------------------------------------------------------------ Mercury, ocean, helicopter
def mercury_capsule(name="mercury", loc=(0, 0, 0), rot=(0, 0, 0)):
    """Black bell-shaped Mercury capsule, axis +Z. Returns (root, hatch)."""
    root = empty(name, loc, rot=rot)
    blk = toon("#2a2d38", shadow="#10121a", hi=0.3)
    cyl(name + "_shield", 0.95, 0.16, (0, 0, 0.0), toon("#8a6a4a"), parent=root, outline=0.02)
    cyl(name + "_cone", 0.9, 1.4, (0, 0, 0.78), blk, r2=0.45, parent=root, outline=0.025)
    for i in range(16):
        a = i * math.pi / 8
        rod(f"{name}_rib{i}", (math.cos(a) * 0.9, math.sin(a) * 0.9, 0.1), (math.cos(a) * 0.46, math.sin(a) * 0.46, 1.46), 0.012, toon("#3d4150"), parent=root)
    cyl(name + "_neck", 0.45, 0.5, (0, 0, 1.73), blk, r2=0.34, parent=root, outline=0.02)
    cyl(name + "_can", 0.32, 0.45, (0, 0, 2.2), toon("#c9ced6"), parent=root, outline=0.02)
    box(name + "_win", (0.22, 0.05, 0.16), (0.0, -0.52, 1.25), emit("#9fd3ff", 0.9), rot=(-18, 0, 0), parent=root, outline=0.006)
    # painted crack, like the Liberty Bell
    pts = [(0.35, 1.3), (0.42, 1.05), (0.33, 0.85), (0.45, 0.6), (0.38, 0.35)]
    for k in range(len(pts) - 1):
        (x0, z0), (x1, z1) = pts[k], pts[k + 1]
        rad = lambda z: 0.9 - 0.45 * (z - 0.08) / 1.4
        a0, a1 = Vector((x0, -math.sqrt(max(0.01, rad(z0) ** 2 - x0 ** 2)), z0)), Vector((x1, -math.sqrt(max(0.01, rad(z1) ** 2 - x1 ** 2)), z1))
        rod(f"{name}_crack{k}", a0 * 1.01, a1 * 1.01, 0.014, toon("#f4f1ea"), parent=root)
    hatch = empty(name + "_hatchroot", (-0.25, -0.69, 0.7), root, rot=(-18, 0, 0))
    box(name + "_hatch", (0.42, 0.06, 0.55), (0, 0, 0), toon("#3d4150"), parent=hatch, outline=0.012)
    for s in (-1, 1):
        for z in (-0.2, 0.2):
            ball(f"{name}_bolt{s}{z}", 0.025, (0.17 * s, -0.035, z), toon("#c9ced6"), parent=hatch, outline=0.0, seg=8)
    return root, hatch

def helicopter(name="heli", loc=(0, 0, 0), rot=(0, 0, 0), cable=2.5, body_col="#6f7f5a"):
    """1960s utility helicopter, nose to -Y. Returns (root, parts: rotor, tailrotor, cable, hook)."""
    root = empty(name, loc, rot=rot); P = {"root": root}
    b = toon(body_col, shadow="#2c3424")
    ball(name + "_body", 0.9, (0, 0, 0), b, scale=(0.85, 1.4, 0.85), parent=root, outline=0.025)
    ball(name + "_nose", 0.6, (0, -0.95, -0.05), emit("#bfe3ff", 0.6), scale=(0.95, 0.8, 0.9), parent=root, outline=0.015, cut=lambda c: c.y > 0.1)
    rod(name + "_boom", (0, 0.9, 0.2), (0, 3.0, 0.55), 0.14, b, parent=root, outline=0.015)
    prism(name + "_fin", [(0, 0), (0.45, 0), (0.25, 0.7)], 0.06, (0, 3.0, 0.5), b, rot=(0, 0, 90), parent=root)
    tr = empty(name + "_tr", (0.08, 3.1, 0.95), root); P["tailrotor"] = tr
    for k in range(2):
        box(f"{name}_trb{k}", (0.04, 0.08, 0.7), (0, 0, 0), toon("#22283a"), rot=(0, 0, 0) if k else (90, 0, 0), parent=tr, outline=0.0)
    tr.rotation_euler = (0, math.radians(90), 0)
    cyl(name + "_mast", 0.08, 0.35, (0, 0, 0.85), toon("#22283a"), parent=root, outline=0.006)
    rot_ = empty(name + "_rotor", (0, 0, 1.05), root); P["rotor"] = rot_
    for k in range(4):
        box(f"{name}_blade{k}", (3.6, 0.2, 0.04), (1.8, 0, 0), toon("#22283a"), parent=empty(f"{name}_bh{k}", (0, 0, 0), rot_, rot=(0, 0, k * 90)), outline=0.0, sub=0, bevel=0.01)
    for s in (-1, 1):
        rod(f"{name}_strutw{s}", (0.45 * s, -0.3, -0.55), (0.75 * s, -0.3, -1.0), 0.03, toon("#22283a"), parent=root)
        cyl(f"{name}_wheel{s}", 0.13, 0.08, (0.78 * s, -0.3, -1.05), toon("#1a1a22"), rot=(0, 90, 0), parent=root, outline=0.006)
    box(name + "_stripe", (1.4, 0.4, 0.12), (0, 0.2, 0.1), toon("#f4f1ea"), parent=root, outline=0.0, sub=0, bevel=0.02)
    cab = rod(name + "_cable", (0, 0, -0.75), (0, 0, -0.75 - cable), 0.015, toon("#1a1a22"), parent=root); P["cable"] = cab
    P["hook"] = ball(name + "_hook", 0.06, (0, 0, -0.75 - cable), toon("#9aa3ad"), parent=root, outline=0.004)
    return root, P

def coin(name, loc=(0, 0, 0), parent=None, r=0.08):
    root = empty(name, loc, parent)
    cyl(name + "_c", r, 0.014, (0, 0, 0), toon("#d4d8e0", shadow="#6f7486", hi=0.5), parent=root, outline=0.004, bevel=0.003)
    torus(name + "_rim", r * 0.82, 0.005, (0, 0, 0.008), toon("#a9aeb9"), parent=root)
    return root

def lightning_bolt(name, p_top, p_bot, seed=1, width=0.12, branches=2):
    """Jagged emissive bolt from p_top to p_bot (world). Returns root."""
    random.seed(seed); root = empty(name, (0, 0, 0))
    a, b = Vector(p_top), Vector(p_bot); n = 9
    pts = [a.lerp(b, i / n) + (Vector((random.uniform(-1, 1), random.uniform(-0.3, 0.3), 0)) * (a - b).length * 0.06 if 0 < i < n else Vector()) for i in range(n + 1)]
    core = emit("#fff27a", 6.0)
    for i in range(n):
        rod(f"{name}_c{i}", pts[i], pts[i + 1], width * 0.45, core, parent=root)
        rod(f"{name}_h{i}", pts[i], pts[i + 1], width, glass("#8fc4ff", 0.6), parent=root)
    for k in range(branches):
        i = random.randint(2, n - 3); p = pts[i]
        q = p + Vector((random.uniform(-1, 1), 0, -0.6)) * (a - b).length * 0.15
        rod(f"{name}_br{k}", p, q, width * 0.3, core, parent=root)
    return root

# ------------------------------------------------------------------ small props for the Apollo stories
def golf_club(name="club", loc=(0, 0, 0), parent=None, rot=(0, 0, 0), length=0.95):
    """Sample-scoop handle with a 6-iron head clipped on. Grip at the origin, shaft down -Z."""
    root = empty(name, loc, parent, rot=rot)
    for k in range(3):   # segmented aluminium handle
        cyl(f"{name}_seg{k}", 0.028, length / 3 - 0.01, (0, 0, -(k + 0.5) * length / 3), toon("#c9ced6", hi=0.5), parent=root, outline=0.004)
        cyl(f"{name}_joint{k}", 0.04, 0.035, (0, 0, -k * length / 3 - 0.01), toon("#5b6170"), parent=root, outline=0.0)
    box(name + "_head", (0.24, 0.05, 0.1), (0.08, 0, -length - 0.02), toon("#e3e6ec", hi=0.6), rot=(0, -10, 0), parent=root, outline=0.006)
    return root

def golf_ball(name="ball", loc=(0, 0, 0), parent=None, r=0.06):
    return ball(name, r, loc, toon("#ffffff", shadow="#b9c6e6"), parent=parent, outline=0.006, seg=16)

def us_flag(name="flag", loc=(0, 0, 0), rot=(0, 0, 0), h=1.9):
    root = empty(name, loc, rot=rot)
    cyl(name + "_pole", 0.025, h, (0, 0, h / 2), toon("#d9d4ca"), parent=root, outline=0.004)
    rod(name + "_bar", (0, 0, h - 0.04), (0.95, 0, h - 0.04), 0.018, toon("#d9d4ca"), parent=root)
    for i in range(7):
        box(f"{name}_st{i}", (0.92, 0.02, 0.6 / 7), (0.48, 0, h - 0.1 - (i + 0.5) * 0.6 / 7), toon("#e2483d" if i % 2 == 0 else "#f4f1ea"), parent=root, outline=0.0, sub=0, bevel=0.0)
    box(name + "_canton", (0.4, 0.03, 0.32), (0.22, 0, h - 0.26), toon("#1f3a7a"), parent=root, outline=0.0, sub=0, bevel=0.0)
    return root

def lioh_canister(name, shape="square", loc=(0, 0, 0), parent=None, rot=(0, 0, 0), s=0.34):
    """CO2 scrubber cartridge. square = command module type, round = lunar module type."""
    root = empty(name, loc, parent, rot=rot)
    body, grille = toon("#b9bec8", hi=0.4), toon("#3a3f4d")
    if shape == "square":
        box(name + "_b", (s, s, s), (0, 0, 0), body, parent=root, outline=0.012)
        for k in range(4):
            box(f"{name}_g{k}", (s * 0.75, 0.01, 0.02), (0, -s / 2 - 0.005, -s * 0.3 + k * s * 0.2), grille, parent=root, outline=0.0, sub=0, bevel=0.0)
    else:
        cyl(name + "_b", s * 0.55, s, (0, 0, 0), body, parent=root, outline=0.012)
        for k in range(4):
            torus(f"{name}_g{k}", s * 0.56, 0.008, (0, 0, -s * 0.3 + k * s * 0.2), grille, parent=root)
    return root

def round_socket(name, loc=(0, 0, 0), parent=None, rot=(0, 0, 0), r=0.2):
    """A panel with a round opening (where a round canister goes)."""
    root = empty(name, loc, parent, rot=rot)
    box(name + "_plate", (0.75, 0.08, 0.75), (0, 0, 0), toon("#7d8698"), parent=root, outline=0.012)
    cyl(name + "_hole", r, 0.1, (0, -0.01, 0), toon("#120d18", shadow="#120d18"), rot=(90, 0, 0), parent=root, outline=0.0)
    torus(name + "_ring", r, 0.025, (0, -0.05, 0), toon("#f08a24"), rot=(90, 0, 0), parent=root)
    return root

def duct_tape(name="tape", loc=(0, 0, 0), parent=None, rot=(0, 0, 0)):
    root = empty(name, loc, parent, rot=rot)
    cyl(name + "_roll", 0.13, 0.08, (0, 0, 0), toon("#9aa3ad", hi=0.45), parent=root, outline=0.008)
    cyl(name + "_core", 0.075, 0.085, (0, 0, 0), toon("#c9a46a"), parent=root, outline=0.0)
    cyl(name + "_hole", 0.06, 0.09, (0, 0, 0), toon("#120d18", shadow="#120d18"), parent=root, outline=0.0)
    return root

def sock(name="sock", loc=(0, 0, 0), parent=None, rot=(0, 0, 0)):
    root = empty(name, loc, parent, rot=rot)
    w = toon("#f4f1ea")
    cyl(name + "_leg", 0.065, 0.36, (0, 0, 0.1), w, parent=root, outline=0.008)
    for z in (0.22, 0.25):
        cyl(f"{name}_band{z}", 0.067, 0.018, (0, 0, z), toon("#e2483d"), parent=root, outline=0.0)
    ball(name + "_foot", 0.075, (0, -0.07, -0.1), w, scale=(0.9, 1.6, 0.85), parent=root, outline=0.008)
    ball(name + "_toe", 0.06, (0, -0.17, -0.1), toon("#9aa3ad"), scale=(1.05, 0.7, 0.9), parent=root, outline=0.0)
    return root

def plastic_bag(name="bag", loc=(0, 0, 0), parent=None, rot=(0, 0, 0), size=(0.45, 0.3, 0.5)):
    root = empty(name, loc, parent, rot=rot)
    box(name + "_b", size, (0, 0, 0), glass("#dff1ff", 0.35), parent=root, outline=0.006, sub=2)
    return root

def cardboard(name="card", loc=(0, 0, 0), parent=None, rot=(0, 0, 0), size=(0.42, 0.012, 0.55)):
    root = empty(name, loc, parent, rot=rot)
    box(name + "_c", size, (0, 0, 0), toon("#c9a46a"), parent=root, outline=0.006, sub=0, bevel=0.004)
    for k in range(3):
        box(f"{name}_l{k}", (size[0] * 0.7, 0.004, 0.025), (0, -size[1] / 2 - 0.002, size[2] * 0.3 - k * 0.09), toon("#5b6b8c"), parent=root, outline=0.0, sub=0, bevel=0.0)
    return root

def hose(name="hose", p0=(0, 0, 0), p1=(0.5, 0, 0), parent=None, r=0.04):
    root = empty(name, (0, 0, 0), parent)
    p0, p1 = Vector(p0), Vector(p1); mid = (p0 + p1) / 2 + Vector((0, 0, 0.15))
    rod(name + "_a", p0, mid, r, toon("#2f5fa8"), parent=root, outline=0.006)
    rod(name + "_b", mid, p1, r, toon("#2f5fa8"), parent=root, outline=0.006)
    ball(name + "_j", r, tuple(mid), toon("#2f5fa8"), parent=root, outline=0.006, seg=12)
    return root

def mailbox(name="mailbox", loc=(0, 0, 0), parent=None):
    """The Apollo 13 CO2 adapter: square cartridge, cardboard, a plastic bag, tape and a suit hose.
    Every piece is a direct child so actions can fly the pieces in."""
    root = empty(name, loc, parent)
    lioh_canister(name + "_can", "square", (0, 0, 0), root)
    cardboard(name + "_card", (0, -0.2, 0.0), root, size=(0.44, 0.012, 0.44))
    plastic_bag(name + "_bag", (0, 0, 0.02), root, size=(0.5, 0.5, 0.52))
    for k, z in enumerate((-0.12, 0.12)):
        box(f"{name}_tape{k}", (0.53, 0.53, 0.07), (0, 0, z), toon("#9aa3ad", hi=0.45), parent=root, outline=0.006, sub=0, bevel=0.01)
    hose(name + "_hose", (0, 0.0, 0.26), (0.55, 0.1, 0.45), root)
    return root

def gauge(name="gauge", loc=(0, 0, 0), parent=None, label="CO2", scale=1.0):
    """Round dial with green / yellow / red zones. Returns (root, needle pivot). Needle angle: +60 = green, -60 = red."""
    root = empty(name, loc, parent); root.scale = (scale,) * 3
    cyl(name + "_body", 0.5, 0.12, (0, 0, 0), toon("#2c3142"), rot=(90, 0, 0), parent=root, outline=0.02)
    cyl(name + "_face", 0.43, 0.02, (0, -0.07, 0), toon("#f6ead8"), rot=(90, 0, 0), parent=root, outline=0.0)
    for k in range(9):
        a = math.radians(70 - k * 17.5)
        col = "#5fb36a" if k < 3 else ("#f7c548" if k < 6 else "#e2483d")
        box(f"{name}_z{k}", (0.12, 0.02, 0.06), (math.sin(-a) * -0.33, -0.085, math.cos(a) * 0.33), toon(col), rot=(0, math.degrees(a), 0), parent=root, outline=0.0, sub=0, bevel=0.005)
    text(name + "_lab", label, 0.13, (0, -0.09, -0.2), toon("#1f2a44"), rot=(90, 0, 0), parent=root)
    nd = empty(name + "_needle", (0, -0.1, 0), root)
    box(name + "_nd", (0.03, 0.02, 0.34), (0, 0, 0.15), toon("#e2483d"), parent=nd, outline=0.004, sub=0, bevel=0.005)
    ball(name + "_hub", 0.05, (0, -0.01, 0), toon("#2c3142"), parent=nd, outline=0.0)
    return root, nd

def big_switch(name="switch", loc=(0, 0, 0), parent=None, title="SCE", left="", right="AUX", rot=(0, 0, 0)):
    """Chunky labelled toggle switch on a plate. Returns (root, lever pivot). Lever rot y: -35 = left, +35 = right."""
    root = empty(name, loc, parent, rot=rot)
    box(name + "_plate", (0.9, 0.06, 0.75), (0, 0, 0), toon("#3a3f4d"), parent=root, outline=0.015)
    text(name + "_t", title, 0.18, (0, -0.04, 0.25), emit("#f6ead8", 1.2), rot=(90, 0, 0), parent=root)
    if left: text(name + "_l", left, 0.11, (-0.28, -0.04, -0.22), emit("#f6ead8", 1.0), rot=(90, 0, 0), parent=root)
    if right: text(name + "_r", right, 0.13, (0.28, -0.04, -0.22), emit("#f7c548", 1.3), rot=(90, 0, 0), parent=root)
    cyl(name + "_base", 0.09, 0.06, (0, -0.05, -0.05), toon("#9aa3ad"), rot=(90, 0, 0), parent=root, outline=0.006)
    lv = empty(name + "_lever", (0, -0.07, -0.05), root)
    rod(name + "_stick", (0, 0, 0), (0, -0.05, 0.19), 0.03, toon("#d9d4ca", hi=0.5), parent=lv)
    ball(name + "_tip", 0.05, (0, -0.05, 0.21), toon("#f4f1ea"), parent=lv, outline=0.006)
    return root, lv

def cash_stack(name="cash", loc=(0, 0, 0), parent=None, rot=(0, 0, 0), n=5):
    root = empty(name, loc, parent, rot=rot)
    for k in range(n):
        box(f"{name}_b{k}", (0.36, 0.17, 0.018), (0.01 * (k % 2), 0, k * 0.02), toon("#7bbf6a" if k % 2 else "#6aae5c"), parent=root, outline=0.004, sub=0, bevel=0.004)
    box(name + "_band", (0.07, 0.175, n * 0.02 + 0.006), (0, 0, (n - 1) * 0.01), toon("#f4f1ea"), parent=root, outline=0.0, sub=0, bevel=0.002)
    return root

def notepad(name="notepad", loc=(0, 0, 0), parent=None, rot=(0, 0, 0)):
    root = empty(name, loc, parent, rot=rot)
    box(name + "_p", (0.2, 0.02, 0.28), (0, 0, 0), toon("#f8f4ea"), parent=root, outline=0.006)
    box(name + "_top", (0.21, 0.03, 0.04), (0, 0, 0.14), toon("#e2483d"), parent=root, outline=0.0)
    for k in range(4):
        box(f"{name}_l{k}", (0.14, 0.01, 0.012), (0, -0.012, 0.07 - k * 0.05), toon("#5b6b8c"), parent=root, outline=0.0, sub=0, bevel=0.0)
    return root
