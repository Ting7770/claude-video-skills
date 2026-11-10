"""Core helpers: render setup, toon materials, rounded primitives, outlines, parenting.
Everything is procedural. Colours are sRGB hex; converted to linear here."""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, noise

# ---- palette (Orbit's Logbook: navy, orange, cream, pale blue) ----
PAL = dict(
    navy="#0d1630", deep="#070b1c", orange="#f08a24", cream="#f6ead8", white="#f4f1ea",
    paleblue="#dfe8ff", sky="#5aa9e6", teal="#2f8f9d", slate="#5b6b8c", red="#e2483d",
    yellow="#f7c548", green="#5fb36a", brown="#7a4a2a", wood="#8a5a36", rye="#b07a45",
    beef="#c9574f", skin="#f2c39b", skin2="#d99a6c", hair="#4a3222", gray="#9aa3ad",
    dark="#22283a", ink="#120d18", pink="#f29aa0", mustard="#e0b020", tan="#d8b27a",
)

def lin(c):
    if isinstance(c, str):
        c = c.lstrip("#"); c = tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c[:3])

def srgb(c):
    if isinstance(c, str):
        c = c.lstrip("#"); return tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return c

# ---- scene / render ----
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    random.seed(7)

def setup_render(w=1080, h=1920, fps=30, samples=8):
    s = bpy.context.scene
    for e in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try: s.render.engine = e; break
        except Exception: pass
    s.eevee.taa_render_samples = samples
    for k, v in (("use_shadows", True), ("shadow_step_count", 2), ("shadow_ray_count", 1), ("shadow_resolution_scale", 0.5),
                 ("use_raytracing", False), ("use_volumetric_shadows", False), ("fast_gi_method", "GLOBAL_ILLUMINATION")):
        try: setattr(s.eevee, k, v)
        except Exception: pass
    try: s.render.filter_size = 1.2
    except Exception: pass
    s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = w, h, 100
    s.render.fps = fps
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_mode = "RGB"
    s.render.image_settings.compression = 10
    s.view_settings.view_transform = "Standard"
    s.view_settings.look = "None"
    s.render.film_transparent = False
    return s

def world(color="#0d1630", strength=1.0, stars=False, star_density=0.035):
    w = bpy.data.worlds.new("World"); bpy.context.scene.world = w
    nt = w.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld"); bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (*lin(color), 1); bg.inputs["Strength"].default_value = strength
    if stars:
        tc = nt.nodes.new("ShaderNodeTexCoord"); vor = nt.nodes.new("ShaderNodeTexVoronoi")
        vor.inputs["Scale"].default_value = 160
        nt.links.new(tc.outputs["Generated"], vor.inputs["Vector"])
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs[1].default_value = star_density; mr.inputs[2].default_value = 0.0
        nt.links.new(vor.outputs["Distance"], mr.inputs[0])
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
        nt.links.new(mr.outputs[0], mix.inputs[0])
        mix.inputs[6].default_value = (*lin(color), 1); mix.inputs[7].default_value = (1, 0.97, 0.9, 1)
        nt.links.new(mix.outputs[2], bg.inputs["Color"])
    nt.links.new(bg.outputs[0], out.inputs[0])
    return w

def sun(rot=(50, 10, 30), energy=3.0, color="#fff1dc", soft=0.6):
    l = bpy.data.lights.new("sun", "SUN"); l.energy = energy; l.color = srgb(color); l.angle = math.radians(soft)
    o = bpy.data.objects.new("sun", l); bpy.context.collection.objects.link(o)
    o.rotation_euler = [math.radians(a) for a in rot]; return o

def area(loc, rot, energy=200, color="#9fb4ff", size=4, shadow=False):
    l = bpy.data.lights.new("area", "AREA"); l.energy = energy; l.color = srgb(color); l.size = size; l.use_shadow = shadow
    o = bpy.data.objects.new("area", l); bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = [math.radians(a) for a in rot]; return o

def point(loc, energy=100, color="#ffd8a8", radius=0.3):
    l = bpy.data.lights.new("pt", "POINT"); l.energy = energy; l.color = srgb(color); l.shadow_soft_size = radius
    o = bpy.data.objects.new("pt", l); bpy.context.collection.objects.link(o); o.location = loc; return o

# ---- materials ----
_mat_cache = {}

def toon(color, name=None, shadow=None, hi=0.22, soft=True):
    """Cel material: diffuse -> Shader to RGB -> colour ramp (cool shadow, base, warm highlight) -> emission."""
    key = ("toon", color, shadow, hi)
    if key in _mat_cache: return _mat_cache[key]
    base = srgb(color)
    sh = shadow and srgb(shadow) or tuple(b * 0.5 * 0.65 + c * 0.35 for b, c in zip(base, (0.20, 0.17, 0.38)))
    hl = tuple(min(1, b + (1 - b) * hi + d) for b, d in zip(base, (0.02, 0.01, -0.02)))
    m = bpy.data.materials.new(name or f"toon_{color}")
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); dif = nt.nodes.new("ShaderNodeBsdfDiffuse")
    s2r = nt.nodes.new("ShaderNodeShaderToRGB"); ramp = nt.nodes.new("ShaderNodeValToRGB"); em = nt.nodes.new("ShaderNodeEmission")
    cr = ramp.color_ramp; cr.interpolation = "EASE" if soft else "CONSTANT"
    cr.elements[0].position = 0.0; cr.elements[0].color = (*lin(sh), 1)
    cr.elements[1].position = 0.95; cr.elements[1].color = (*lin(hl), 1)
    e = cr.elements.new(0.16); e.color = (*lin(sh), 1)
    e = cr.elements.new(0.40); e.color = (*lin(base), 1)
    e = cr.elements.new(0.78); e.color = (*lin(base), 1)
    nt.links.new(dif.outputs[0], s2r.inputs[0]); nt.links.new(s2r.outputs[0], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], em.inputs[0]); nt.links.new(em.outputs[0], out.inputs[0])
    m.diffuse_color = (*lin(base), 1)
    _mat_cache[key] = m; return m

def emit(color, strength=1.0, name=None):
    key = ("emit", color, strength)
    if key in _mat_cache: return _mat_cache[key]
    m = bpy.data.materials.new(name or f"emit_{color}")
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[0].default_value = (*lin(color), 1); em.inputs[1].default_value = strength
    nt.links.new(em.outputs[0], out.inputs[0]); _mat_cache[key] = m; return m

def glow(color, strength=1.5, power=2.0):
    """Fresnel rim glow (atmosphere). Transparent in the middle."""
    m = bpy.data.materials.new("glow"); nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission"); tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    lw = nt.nodes.new("ShaderNodeLayerWeight"); mix = nt.nodes.new("ShaderNodeMixShader"); pw = nt.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"; pw.inputs[1].default_value = power; lw.inputs[0].default_value = 0.5
    em.inputs[0].default_value = (*lin(color), 1); em.inputs[1].default_value = strength
    nt.links.new(lw.outputs["Facing"], pw.inputs[0]); nt.links.new(pw.outputs[0], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], out.inputs[0])
    try: m.surface_render_method = "BLENDED"
    except Exception: pass
    return m

def glass(color="#cfe6ff", alpha=0.25):
    m = bpy.data.materials.new("glass"); nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission"); tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader"); mix.inputs[0].default_value = alpha
    em.inputs[0].default_value = (*lin(color), 1)
    nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], out.inputs[0])
    try: m.surface_render_method = "BLENDED"
    except Exception: pass
    return m

def outline_mat(color="#120d18"):
    key = ("outline", color)
    if key in _mat_cache: return _mat_cache[key]
    m = emit(color, 1.0, name="outline"); m = m.copy(); m.use_backface_culling = True
    try: m.use_backface_culling_shadow = True
    except Exception: pass
    _mat_cache[key] = m; return m

# ---- objects ----
def _link(name, mesh):
    o = bpy.data.objects.new(name, mesh); bpy.context.collection.objects.link(o); return o

def _finish(o, mat, bevel=0.0, seg=3, sub=0, outline=0.0, smooth=True, parent=None, loc=(0, 0, 0), rot=(0, 0, 0)):
    if mat is not None:
        o.data.materials.append(mat)
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    if bevel > 0:
        b = o.modifiers.new("bevel", "BEVEL"); b.width = bevel; b.segments = seg; b.limit_method = "ANGLE"
    if sub > 0:
        s = o.modifiers.new("sub", "SUBSURF"); s.levels = sub; s.render_levels = sub
    if outline > 0:
        o.data.materials.append(outline_mat())
        so = o.modifiers.new("outline", "SOLIDIFY"); so.thickness = outline; so.offset = 1
        so.use_flip_normals = True; so.use_rim = False; so.material_offset = 1
    o.location = loc; o.rotation_euler = [math.radians(a) for a in rot]
    if parent is not None: o.parent = parent
    return o

def box(name, size, loc=(0, 0, 0), mat=None, bevel=None, sub=1, outline=0.012, rot=(0, 0, 0), parent=None, smooth=True):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if bevel is None: bevel = min(size) * 0.22
    return _finish(_link(name, me), mat, bevel=bevel, sub=sub, outline=outline, parent=parent, loc=loc, rot=rot, smooth=smooth)

def ball(name, r, loc=(0, 0, 0), mat=None, scale=(1, 1, 1), seg=24, outline=0.012, rot=(0, 0, 0), parent=None, ico=0, smooth=True, cut=None):
    """cut: function(co)->bool, verts to delete (e.g. open helmet)."""
    bm = bmesh.new()
    if ico: bmesh.ops.create_icosphere(bm, subdivisions=ico, radius=r)
    else: bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(8, seg * 2 // 3), radius=r)
    for v in bm.verts: v.co = Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2]))
    if cut:
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if cut(v.co)], context="VERTS")
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return _finish(_link(name, me), mat, outline=outline, parent=parent, loc=loc, rot=rot, smooth=smooth)

def cyl(name, r, h, loc=(0, 0, 0), mat=None, r2=None, seg=24, bevel=None, sub=0, outline=0.012, rot=(0, 0, 0), parent=None, smooth=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=h)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if bevel is None: bevel = min(r, h) * 0.12
    o = _finish(_link(name, me), mat, bevel=bevel, seg=2, sub=sub, outline=outline, parent=parent, loc=loc, rot=rot, smooth=smooth)
    return o

def torus(name, R, r, loc=(0, 0, 0), mat=None, rot=(0, 0, 0), parent=None, outline=0.0, seg=32):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=seg, minor_segments=12)
    o = bpy.context.active_object; o.name = name
    return _finish(o, mat, outline=outline, parent=parent, loc=loc, rot=rot)

def prism(name, pts, depth, loc=(0, 0, 0), mat=None, rot=(0, 0, 0), parent=None, outline=0.012, bevel=0.02):
    """Extrude a 2D polygon (x,z points) along y by depth."""
    bm = bmesh.new()
    f = bm.faces.new([bm.verts.new((x, -depth / 2, z)) for x, z in pts])
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    for v in [e for e in r["geom"] if isinstance(e, bmesh.types.BMVert)]: v.co.y += depth
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return _finish(_link(name, me), mat, bevel=bevel, seg=2, outline=outline, parent=parent, loc=loc, rot=rot, smooth=False)

def text(name, body, size=0.5, loc=(0, 0, 0), mat=None, rot=(90, 0, 0), extrude=0.02, parent=None, align="CENTER"):
    cu = bpy.data.curves.new(name, "FONT"); cu.body = body; cu.size = size; cu.extrude = extrude
    cu.align_x = align; cu.align_y = "CENTER"
    try:
        cu.font = bpy.data.fonts.load("/System/Library/Fonts/Supplemental/Arial Black.ttf")
    except Exception: pass
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o)
    if mat: o.data.materials.append(mat)
    o.location = loc; o.rotation_euler = [math.radians(a) for a in rot]
    if parent is not None: o.parent = parent
    return o

def empty(name, loc=(0, 0, 0), parent=None, rot=(0, 0, 0)):
    o = bpy.data.objects.new(name, None); bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = [math.radians(a) for a in rot]
    if parent is not None: o.parent = parent
    return o

def faces_by(obj, fn):
    """Assign material index per face: fn(center)->index; materials must already be on obj."""
    for p in obj.data.polygons: p.material_index = fn(p.center)

def ease_out(t):
    t = max(0.0, min(1.0, t)); return 1 - (1 - t) ** 3

def ease_in_out(t):
    t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)

def key(o, frame, loc=None, rot=None, scale=None):
    if loc is not None: o.location = loc; o.keyframe_insert("location", frame=frame)
    if rot is not None: o.rotation_euler = [math.radians(a) for a in rot]; o.keyframe_insert("rotation_euler", frame=frame)
    if scale is not None:
        o.scale = (scale,) * 3 if isinstance(scale, (int, float)) else scale; o.keyframe_insert("scale", frame=frame)

def hide_at(o, frame, hidden=True):
    o.hide_render = not hidden; o.keyframe_insert("hide_render", frame=frame - 1)
    o.hide_render = hidden; o.keyframe_insert("hide_render", frame=frame)
    for c in o.children: hide_at(c, frame, hidden)
