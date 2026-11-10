"""Render one shot. blender -b --factory-startup -P render_shot.py -- shot.json
shot.json: {scene, view, cam, actions:[[name,arg,a,b],...], frames, out, samples, still (optional fraction), pct}"""
import sys, os, json, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector, Quaternion
import toon, scenes, actions

spec = json.load(open(sys.argv[sys.argv.index("--") + 1]))
N = int(spec["frames"])
toon.reset()
S = toon.setup_render(samples=spec.get("samples", 8))
S.render.resolution_percentage = spec.get("pct", 100)
ctx = {}
scenes.SCENES[spec["scene"]](ctx, **spec.get("scene_args", {}))
actions.auto_life(ctx, N, zero_g=spec["scene"] in ("capsule", "station"), seed=spec.get("seed", 1))
for name, arg, a, b in spec.get("actions", []):
    f0 = max(2, int(round(1 + a * (N - 1)))); f1 = max(f0 + 1, int(round(1 + b * (N - 1))))
    actions.ACTIONS[name](ctx, f0, f1, N, arg)
for fn in ctx.get("anim", []):   # scene-level ambient animation (waves, rain, rotors), after actions so they can opt out
    fn(N)

# ---------------------------------------------------------------- camera
loc0, tgt0, lens = ctx["views"][spec.get("view") or next(iter(ctx["views"]))]
loc0, tgt0 = Vector(loc0), Vector(tgt0)
cd = bpy.data.cameras.new("cam"); cd.lens = lens; cd.clip_start = 0.05; cd.clip_end = 400; cd.sensor_width = 36
cam = bpy.data.objects.new("cam", cd); S.collection.objects.link(cam); S.camera = cam
move = spec.get("cam", "push_in"); dist = (loc0 - tgt0).length
hits = list(ctx.get("hits", [])) + ([ctx["bite_frame"]] if "bite_frame" in ctx else [])
if any(n == "liftoff" for n, *_ in spec.get("actions", [])):
    hits += list(range(int(N * 0.15), N, 5))
random.seed(spec.get("seed", 1))

def prog(fr):  # ease-out burst on the first frames, then a slow steady drift
    return 0.35 * (1 - math.exp(-fr / 4.0)) + 0.65 * (fr / N)

def rot_z(v, deg):
    a = math.radians(deg); return Vector((v.x * math.cos(a) - v.y * math.sin(a), v.x * math.sin(a) + v.y * math.cos(a), v.z))

for fr in range(1, N + 1):
    p = prog(fr); loc, tgt, roll, ln = loc0.copy(), tgt0.copy(), 0.0, lens
    off = loc - tgt
    side = off.cross(Vector((0, 0, 1))).normalized()
    if move in ("push_in", "dutch", "shake"):
        loc = tgt + off * (1 - 0.2 * p)
    elif move == "pull_out":
        loc = tgt + off * (0.85 + 0.25 * p)
    elif move in ("orbit_l", "orbit_r"):
        loc = tgt + rot_z(off, (14 if move == "orbit_l" else -14) * p) * (1 - 0.06 * p)
    elif move in ("pan_l", "pan_r"):
        d = side * (0.16 * dist * p) * (1 if move == "pan_r" else -1); loc += d; tgt += d
    elif move == "tilt_up":
        up = 0.55 * dist; tgt.z += up * p; loc.z += up * 0.35 * p
    elif move == "follow_up":   # for launches: track the rising rocket (liftoff sets follow_z)
        up = ctx["follow_z"](fr) if "follow_z" in ctx else dist * 0.9 * (fr / N) ** 2
        tgt.z += up * 0.9; loc.z += up * 0.75; loc = tgt + (loc - tgt) * (1 - 0.1 * p)
    elif move == "crash":
        ln = lens * (0.7 + 0.3 * (1 - math.exp(-fr / 3.0))) * (1 + 0.08 * fr / N)
    elif move == "rise":
        loc.z += 0.25 * dist * p
    if move == "dutch":
        roll = 8.0 + 2.0 * p
    # handheld sway
    tgt += Vector((math.sin(fr / 23.0) * 0.006, 0, math.sin(fr / 29.0) * 0.006)) * dist
    # impact shake
    for h in hits:
        if 0 <= fr - h < 10:
            k = (1 - (fr - h) / 10) * 0.02 * dist
            loc += Vector((random.uniform(-k, k), 0, random.uniform(-k, k)))
    q = (tgt - loc).to_track_quat("-Z", "Y") @ Quaternion((0, 0, 1), math.radians(roll))
    cam.location = loc; cam.rotation_mode = "QUATERNION"; cam.rotation_quaternion = q
    cam.keyframe_insert("location", frame=fr); cam.keyframe_insert("rotation_quaternion", frame=fr)
    cd.lens = ln; cd.keyframe_insert("lens", frame=fr)

for o in list(bpy.data.objects):   # labels and words that should always read straight to camera
    if o.get("cam_word"):            # pinned to the upper third of the frame, just past the lens so nothing can cover it
        k = 0.25; d = lens / 20.25 * 1.9 * k
        o.parent = cam; o.location = (0, 0.95 * k, -d); o.scale = (k, k, k)
    elif o.get("face_cam"):
        c = o.constraints.new("TRACK_TO"); c.target = cam; c.track_axis = "TRACK_Z"; c.up_axis = "UP_Y"
S.frame_start, S.frame_end = 1, N
out = spec["out"]
if "still" in spec:
    S.frame_set(max(1, int(spec["still"] * N)))
    S.render.filepath = out; bpy.ops.render.render(write_still=True)
else:
    os.makedirs(out, exist_ok=True)
    S.render.filepath = os.path.join(out, "f_####")
    bpy.ops.render.render(animation=True)
print("SHOT DONE", out)
