# m35_tree_snow.py — 里程碑 M35：树积雪帽（Tree Snow Caps · OptiX）
# 非破坏：不删/不改任何既有物体。仅新建 M35_ 前缀临时世界/雪盖/树积雪/飘雪（结束恢复），仅落盘 PNG。
# 思路：M27 已在收官校园上叠加"冬季雪天"（屋顶雪盖 + 地面积雪 + 飘雪），但树木（M5_TreeFoliage* 10 株 ×
#   主球+2 卫星球共 30 个树冠）仍是光秃绿叶。本里程碑把 M27 的雪天环境原样复用，并额外在每棵树冠顶部
#   放置一块白色雪帽（压扁 icosphere，仅上半球露出），让雪景里的树也"积了雪"。复用 M19C/M11 机位。
# 渲染 Cycles GPU OptiX / 256 samples / 2560×1440 / AgX。结束恢复白昼基线（world/sun/exposure）。
import bpy, mathutils, importlib.util, os, time

BASE = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
M06 = BASE + r"/build/m06_lighting.py"
OUT_DIR = BASE + r"/previews"
PREFIX = "M35_"

HERO_LOC = (-52.0, -58.0, 48.0)
HERO_TGT = (0.0, -2.0, 6.0)
AERIAL_LOC = (0.0, -2.0, 120.0)
AERIAL_TGT = (0.0, 0.0, 0.0)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ---- 1) 配置 Cycles GPU (OptiX) ----
cpref = bpy.context.preferences.addons['cycles'].preferences
cpref.compute_device_type = 'OPTIX'
cpref.get_devices()
for d in cpref.devices:
    if d.type in ('OPTIX', 'CUDA'):
        d.use = True

sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.view_settings.view_transform = 'AgX'

m06 = load(M06, "m06l")


def hide_previews():
    h = []
    for o in bpy.data.objects:
        if o.name.startswith("Mat_Preview_"):
            h.append((o, o.hide_render))
            o.hide_render = True
    return h


def show(h):
    for o, was in h:
        o.hide_render = was


# ---- 2) 以 day 为已知基线 ----
m06.build_lighting("day")


# ---- 3) 原状态交给 m06.build_lighting('day') 在 restore 时重建，避免长运行时 world 引用失效 ----
sun = bpy.data.objects.get("M6_Sun")


# ---- 4) 冬季冷调明亮天光 ----
def make_snow_world():
    w = bpy.data.worlds.new("M35_SnowWorld")
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    tex = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    bg = nt.nodes.new("ShaderNodeBackground")
    outn = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(tex.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], outn.inputs["Surface"])
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[0].color = (0.55, 0.68, 0.90, 1.0)
    e1 = ramp.color_ramp.elements.new(0.45)
    e1.color = (0.78, 0.85, 0.93, 1.0)
    ramp.color_ramp.elements[1].color = (0.93, 0.95, 0.98, 1.0)
    bg.inputs["Strength"].default_value = 0.95
    return w


sc.world = make_snow_world()

if sun:
    sun.location = (52.0, -38.0, 58.0)
    sun.data.energy = 2.8
    sun.data.color = (0.92, 0.95, 1.0)
    sun.data.angle = 0.008
    sun.data.shadow_soft_size = 4.0
    direction = mathutils.Vector((0.0, 0.0, 0.0)) - sun.location
    sun.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

sc.view_settings.view_transform = 'AgX'
sc.view_settings.exposure = 0.0


# ---- 5) 积雪材质 ----
def make_snow_material():
    mat = bpy.data.materials.new(PREFIX + "SnowMat")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    outn = nt.nodes.new("ShaderNodeBsdfPrincipled")
    outp = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(outn.outputs["BSDF"], outp.inputs["Surface"])
    outn.inputs["Base Color"].default_value = (0.93, 0.95, 0.99, 1.0)
    outn.inputs["Roughness"].default_value = 0.82
    outn.inputs["Metallic"].default_value = 0.0
    if "Emission Color" in outn.inputs:
        outn.inputs["Emission Color"].default_value = (0.30, 0.36, 0.46, 1.0)
        outn.inputs["Emission Strength"].default_value = 0.10
    return mat


snow_mat = make_snow_material()


# ---- 6) 屋顶积雪盖（按 roof AABB 动态放置，不硬编码）----
def world_aabb(o):
    mw = o.matrix_world
    xs = []; ys = []; zs = []
    for c in o.bound_box:
        v = mw @ mathutils.Vector(c)
        xs.append(v.x); ys.append(v.y); zs.append(v.z)
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)


n_caps = 0
for o in list(bpy.data.objects):
    if not (o.type == "MESH" and o.name.lower().endswith("_roof")):
        continue
    mn_x, mx_x, mn_y, mx_y, mn_z, mx_z = world_aabb(o)
    sx = (mx_x - mn_x) * 0.96
    sy = (mx_y - mn_y) * 0.96
    cz = mx_z + 0.09
    cx = (mn_x + mx_x) * 0.5
    cy = (mn_y + mx_y) * 0.5
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
    cap = bpy.context.active_object
    cap.name = PREFIX + "SnowCap_" + o.name
    cap.scale = (sx, sy, 0.18)
    cap.data.materials.clear()
    cap.data.materials.append(snow_mat)
    cap.hide_viewport = False
    n_caps += 1


# ---- 6.5) 树冠积雪帽（M35 新增）：每棵 M5_TreeFoliage* 树冠顶部压一块白色雪帽 ----
n_tree = 0
for o in list(bpy.data.objects):
    # M11 总平重排后树冠改名为 M11_Tree{N}_Canopy / _Sat0 / _Sat1（M5_TreeFoliage 已被重命名）
    if not (o.type == "MESH" and o.name.startswith("M11_Tree") and ("_Canopy" in o.name or "_Sat" in o.name)):
        continue
    mn_x, mx_x, mn_y, mx_y, mn_z, mx_z = world_aabb(o)
    cx = (mn_x + mx_x) * 0.5
    cy = (mn_y + mx_y) * 0.5
    cz = (mn_z + mx_z) * 0.5
    R = (mx_z - mn_z) / 2.0
    if R < 0.3:
        continue
    # 压扁 icosphere：半径 1，scale 成略大于树冠的椭球，仅上半球(顶)露出 -> 像雪积在树顶
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.0, location=(cx, cy, cz + R * 0.15))
    cap = bpy.context.active_object
    cap.name = PREFIX + "TreeSnow_" + o.name.replace("M11_Tree", "T")
    cap.scale = (R * 1.02, R * 1.02, R * 0.60)
    cap.data.materials.clear()
    cap.data.materials.append(snow_mat)
    cap.hide_viewport = False
    n_tree += 1


# ---- 7) 地面积雪（复制 Ground 网格，完美贴合地形，略上移防 z-fight）----
n_ground = 0
ground = bpy.data.objects.get("Ground")
if ground is not None:
    gsn = ground.copy()
    gsn.data = ground.data.copy()
    gsn.name = PREFIX + "GroundSnow"
    gsn.location.z += 0.05
    bpy.context.collection.objects.link(gsn)
    gsn.data.materials.clear()
    gsn.data.materials.append(snow_mat)
    n_ground = 1


# ---- 8) 空中飘雪粒子 ----
flake = bpy.data.meshes.new(PREFIX + "FlakeMesh")
bfl = bpy.data.objects.new(PREFIX + "SnowFlake", flake)
bpy.context.collection.objects.link(bfl)
bpy.context.view_layer.objects.active = bfl
bfl.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.primitive_ico_sphere_add(radius=1.0, subdivisions=1, location=(0, 0, 0))
bpy.ops.object.mode_set(mode='OBJECT')
bfl.data.materials.clear()
bfl.data.materials.append(snow_mat)
bfl.scale = (0.06, 0.06, 0.06)
bfl.location = (0.0, 0.0, -500.0)
bfl.hide_viewport = True
bfl.hide_render = True

emit = bpy.data.objects.new(PREFIX + "SnowEmitter", bpy.data.meshes.new(PREFIX + "EmitMesh"))
bpy.context.collection.objects.link(emit)
bpy.context.view_layer.objects.active = emit
emit.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0))
bpy.ops.object.mode_set(mode='OBJECT')
emit.scale = (110.0, 110.0, 26.0)
emit.location = (0.0, 0.0, 13.0)
mod = emit.modifiers.new(PREFIX + "SnowPS", 'PARTICLE_SYSTEM')
ps = emit.particle_systems[0]
pset = ps.settings
pset.count = 1400
pset.frame_start = 1
pset.frame_end = 1
pset.lifetime = 2000
pset.emit_from = 'VOLUME'
pset.distribution = 'RAND'
pset.physics_type = 'NO'
pset.particle_size = 1.0
pset.render_type = 'OBJECT'
pset.instance_object = bfl
pset.brownian_factor = 0.0
pset.normal_factor = 0.0
pset.use_modifier_stack = False
n_particles = pset.count

eminvis = bpy.data.materials.new(PREFIX + "EmitInvis")
eminvis.use_nodes = True
ent = eminvis.node_tree
ent.nodes.clear()
tn = ent.nodes.new("ShaderNodeBsdfTransparent")
ep = ent.nodes.new("ShaderNodeOutputMaterial")
ent.links.new(tn.outputs["BSDF"], ep.inputs["Surface"])
emit.data.materials.clear()
emit.data.materials.append(eminvis)
sc.frame_set(1)


# ---- 9) 相机复用 ----
def get_cam(name, loc, tgt, lens=35.0, fallback=True):
    c = bpy.data.objects.get(name)
    if c is not None:
        return c, False
    if not fallback:
        return None, False
    cam_data = bpy.data.cameras.new(PREFIX + name)
    cam_data.sensor_width = 36.0
    cam_data.lens = lens
    cam_data.clip_start = 0.1
    cam_data.clip_end = 1000.0
    cam = bpy.data.objects.new(PREFIX + name, cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = mathutils.Vector(loc)
    cam.rotation_euler = (mathutils.Vector(tgt) - mathutils.Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return cam, True


hero_cam, hero_built = get_cam("M19C_HeroDay", HERO_LOC, HERO_TGT, 35.0)
aerial_cam, aerial_built = get_cam("M11_CamAerial", AERIAL_LOC, AERIAL_TGT, 35.0)


# ---- 10) 渲染配置 + 出图 ----
def cfg_samples():
    sc.cycles.device = 'GPU'
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = 'OPTIX'
    sc.cycles.samples = 256
    sc.cycles.max_bounces = 12
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.view_settings.view_transform = 'AgX'


def render_shot(cam, out_path):
    sc.camera = cam
    sc.render.resolution_x = 2560
    sc.render.resolution_y = 1440
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.render.image_settings.color_depth = '8'
    sc.render.filepath = out_path
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    return time.time() - t0


hidden_stack = []
shots = {}
try:
    hidden_stack += hide_previews()
    cfg_samples()
    shots["hero"] = (os.path.join(OUT_DIR, "m35_tree_snow_hero.png"),
                     render_shot(hero_cam, os.path.join(OUT_DIR, "m35_tree_snow_hero.png")))
    shots["aerial"] = (os.path.join(OUT_DIR, "m35_tree_snow_aerial.png"),
                       render_shot(aerial_cam, os.path.join(OUT_DIR, "m35_tree_snow_aerial.png")))
finally:
    show(hidden_stack)


# ---- 11) 恢复白昼基线（不残留 M35_ 物体 / 雪世界 / 雪材质）----
def restore():
    for o in list(bpy.data.objects):
        if o.name.startswith(PREFIX):
            bpy.data.objects.remove(o, do_unlink=True)
    for c in [c for c in bpy.data.cameras if c.name.startswith(PREFIX)]:
        bpy.data.cameras.remove(c)
    for me in [me for me in bpy.data.meshes if me.name.startswith(PREFIX)]:
        bpy.data.meshes.remove(me)
    for m in [m for m in bpy.data.materials if m.name.startswith(PREFIX)]:
        bpy.data.materials.remove(m)
    try:
        m06.build_lighting("day")
    except Exception as _e:
        print("restore build_lighting warning:", _e)
    for w in [w for w in bpy.data.worlds if w.name.startswith(PREFIX)]:
        bpy.data.worlds.remove(w)


restore()

if sc.world is None:
    w = bpy.data.worlds.new("World")
    w.use_nodes = True
    sc.world = w


import os as _os
result = {
    "milestone": "M35",
    "device": sc.cycles.device,
    "compute_device_type": cpref.compute_device_type,
    "denoiser": sc.cycles.denoiser,
    "samples": sc.cycles.samples,
    "resolution": [2560, 1440],
    "roof_snow_caps": n_caps,
    "tree_snow_caps": n_tree,
    "ground_snow": n_ground,
    "snow_particles": n_particles,
    "shots": {k: {
        "out": v[0],
        "size": _os.path.getsize(v[0]) if _os.path.exists(v[0]) else None,
        "time_s": round(v[1], 1),
    } for k, v in shots.items()},
    "hero_cam_reused": ("M19C_HeroDay" if not hero_built else "M35_M19C_HeroDay"),
    "aerial_cam_reused": ("M11_CamAerial" if not aerial_built else "M35_M11_CamAerial"),
    "n_obj_after_restore": len(bpy.data.objects),
    "restored_world": sc.world.name,
}
print("M35_RESULT=" + repr(result))
