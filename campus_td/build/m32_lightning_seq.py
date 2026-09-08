# m32_lightning_seq.py — 里程碑 M32：多帧闪电序列（Lightning Flash Sequence · OptiX）
# 非破坏：不删/不改任何既有物体。仅新建 M32_ 前缀临时世界/物体（结束恢复），仅落盘 PNG/MP4。
# 思路：在 M28/M29 已验证的"雨夜 + 闪电"之上，把"单帧抓拍"升级为"多帧戏剧化序列"——
#   按真实闪电的时间线（预放电→蓄能→主闪峰→余辉→二次闪→残光）逐帧渲染，
#   叠加一道程序化可见电弧（M32_BoltSeg_*，仅峰/二次帧可见），最终外部合成可循环 MP4。
#   与 day/dusk/night(M24)/golden(M26)/snow(M27)/rain(M28)/lightning(M29)/mist(M30)/noon(M31) 形成第 10 种氛围。
# 渲染 Cycles GPU OptiX / 256 samples / 1920×1080(英雄序列) 或 2560×1440(鸟瞰峰) / AgX。
# 结束恢复白昼基线（world/sun/exposure/flash/bolt）。复用 M19C_HeroDay / M11_CamAerial 机位。
import bpy, mathutils, importlib.util, os, time, random

BASE = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
M06 = BASE + r"/build/m06_lighting.py"
OUT_DIR = BASE + r"/previews"
PREFIX = "M32_"

HERO_LOC = (-52.0, -58.0, 48.0)
HERO_TGT = (0.0, -2.0, 6.0)
AERIAL_LOC = (0.0, -2.0, 120.0)
AERIAL_TGT = (0.0, 0.0, 0.0)

# 闪电序列：每帧 (tag, flash_sun_energy, world_strength, exposure, bolt_visible)
# 时间线：预暗 → 蓄能(微亮) → 主闪峰(采用 M29 获胜参数 energy90/world0.06/exp-0.34) → 余辉 → 二次闪 → 残光
FRAMES = [
    ("pre",    0.0, 0.04, -0.36, False),
    ("charge", 18.0, 0.05, -0.34, False),
    ("peak",   90.0, 0.06, -0.34, True),
    ("glow",   28.0, 0.10, -0.28, False),
    ("flick",  55.0, 0.06, -0.32, True),
    ("resid",  8.0,  0.05, -0.33, False),
]


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


# ---- 3) 雨夜暴风冷蓝天光（闪电各帧在此基础上调 world strength / exposure / flash）----
def make_rain_world():
    w = bpy.data.worlds.new("M32_RainWorld")
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
    ramp.color_ramp.elements[0].color = (0.09, 0.12, 0.17, 1.0)
    e1 = ramp.color_ramp.elements.new(0.5)
    e1.color = (0.18, 0.22, 0.28, 1.0)
    ramp.color_ramp.elements[1].color = (0.30, 0.34, 0.38, 1.0)
    bg.inputs["Strength"].default_value = 0.04
    return w


rain_world = make_rain_world()
sc.world = rain_world

sun = bpy.data.objects.get("M6_Sun")
if sun:
    sun.location = (40.0, -30.0, 50.0)
    sun.data.energy = 0.6
    sun.data.color = (0.60, 0.70, 0.90)
    sun.data.angle = 0.02
    sun.data.shadow_soft_size = 8.0
    direction = mathutils.Vector((0.0, 0.0, 0.0)) - sun.location
    sun.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

sc.view_settings.view_transform = 'AgX'
sc.view_settings.exposure = -0.36


# ---- 4) 闪电闪光灯（强方向性 SUN，置于场地一角高空）----
flash_lamp = bpy.data.lights.new(PREFIX + "FlashLamp", 'SUN')
flash_lamp.energy = 0.0
flash_lamp.color = (0.80, 0.86, 1.0)
flash_lamp.angle = 0.015
flash_lamp.shadow_soft_size = 2.0
flash_obj = bpy.data.objects.new(PREFIX + "FlashSun", flash_lamp)
bpy.context.collection.objects.link(flash_obj)
flash_obj.location = (55.0, 45.0, 95.0)
flash_obj.rotation_euler = (mathutils.Vector((0.0, 0.0, 0.0)) - flash_obj.location).to_track_quat("-Z", "Y").to_euler()


# ---- 5) 湿润反光地面材质 + 覆盖层 ----
def make_wet_material():
    mat = bpy.data.materials.new(PREFIX + "WetMat")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    outn = nt.nodes.new("ShaderNodeBsdfPrincipled")
    outp = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(outn.outputs["BSDF"], outp.inputs["Surface"])
    outn.inputs["Base Color"].default_value = (0.04, 0.05, 0.07, 1.0)
    outn.inputs["Roughness"].default_value = 0.32
    outn.inputs["Metallic"].default_value = 0.0
    if "Emission Color" in outn.inputs:
        outn.inputs["Emission Color"].default_value = (0.02, 0.03, 0.05, 1.0)
        outn.inputs["Emission Strength"].default_value = 0.0
    if "Clearcoat" in outn.inputs:
        outn.inputs["Clearcoat"].default_value = 0.35
    if "Clearcoat Roughness" in outn.inputs:
        outn.inputs["Clearcoat Roughness"].default_value = 0.3
    return mat


wet_mat = make_wet_material()
n_ground = 0
ground = bpy.data.objects.get("Ground")
if ground is not None:
    gsn = ground.copy()
    gsn.data = ground.data.copy()
    gsn.name = PREFIX + "GroundWet"
    gsn.location.z += 0.05
    bpy.context.collection.objects.link(gsn)
    gsn.data.materials.clear()
    gsn.data.materials.append(wet_mat)
    n_ground = 1


# ---- 6) 雨丝材质（冷色微自发光）----
def make_rain_material():
    mat = bpy.data.materials.new(PREFIX + "RainMat")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    outn = nt.nodes.new("ShaderNodeBsdfPrincipled")
    outp = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(outn.outputs["BSDF"], outp.inputs["Surface"])
    outn.inputs["Base Color"].default_value = (0.62, 0.72, 0.90, 1.0)
    outn.inputs["Roughness"].default_value = 0.4
    outn.inputs["Metallic"].default_value = 0.0
    outn.inputs["Alpha"].default_value = 0.55
    if "Emission Color" in outn.inputs:
        outn.inputs["Emission Color"].default_value = (0.35, 0.45, 0.65, 1.0)
        outn.inputs["Emission Strength"].default_value = 0.5
    mat.blend_method = 'BLEND'
    return mat


rain_mat = make_rain_material()


# ---- 7) 雨丝实例模板（细长圆柱，略带风斜）----
streak = bpy.data.meshes.new(PREFIX + "StreakMesh")
bstreak = bpy.data.objects.new(PREFIX + "RainStreak", streak)
bpy.context.collection.objects.link(bstreak)
bpy.context.view_layer.objects.active = bstreak
bstreak.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.primitive_cylinder_add(radius=0.012, depth=1.8, location=(0, 0, 0))
bpy.ops.object.mode_set(mode='OBJECT')
bstreak.data.materials.clear()
bstreak.data.materials.append(rain_mat)
bstreak.rotation_euler = (0.18, 0.0, 0.05)
bstreak.scale = (1.0, 1.0, 1.0)
bstreak.location = (0.0, 0.0, -500.0)
bstreak.hide_viewport = True
bstreak.hide_render = True


# ---- 8) 雨丝粒子发射体（覆盖全校园的体积）----
emit = bpy.data.objects.new(PREFIX + "RainEmitter", bpy.data.meshes.new(PREFIX + "EmitMesh"))
bpy.context.collection.objects.link(emit)
bpy.context.view_layer.objects.active = emit
emit.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0))
bpy.ops.object.mode_set(mode='OBJECT')
emit.scale = (110.0, 110.0, 30.0)
emit.location = (0.0, 0.0, 15.0)
mod = emit.modifiers.new(PREFIX + "RainPS", 'PARTICLE_SYSTEM')
ps = emit.particle_systems[0]
pset = ps.settings
pset.count = 1600
pset.frame_start = 1
pset.frame_end = 1
pset.lifetime = 2000
pset.emit_from = 'VOLUME'
pset.distribution = 'RAND'
pset.physics_type = 'NO'
pset.particle_size = 1.0
pset.render_type = 'OBJECT'
pset.instance_object = bstreak
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


# ---- 9) 程序化可见电弧（仅峰/二次帧可见）----
def make_bolt_material():
    mat = bpy.data.materials.new(PREFIX + "BoltMat")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    outn = nt.nodes.new("ShaderNodeBsdfPrincipled")
    outp = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(outn.outputs["BSDF"], outp.inputs["Surface"])
    outn.inputs["Base Color"].default_value = (0.70, 0.85, 1.0, 1.0)
    outn.inputs["Roughness"].default_value = 1.0
    outn.inputs["Metallic"].default_value = 0.0
    if "Emission Color" in outn.inputs:
        outn.inputs["Emission Color"].default_value = (0.80, 0.90, 1.0, 1.0)
        outn.inputs["Emission Strength"].default_value = 25.0
    mat.blend_method = 'OPAQUE'
    return mat


def add_bolt_segment(a, b, mat, r):
    mid = (a + b) / 2.0
    vec = b - a
    length = vec.length
    m = bpy.data.meshes.new(PREFIX + "BoltSeg")
    o = bpy.data.objects.new(PREFIX + "BoltSeg", m)
    bpy.context.collection.objects.link(o)
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=length, location=(0, 0, 0))
    bpy.ops.object.mode_set(mode='OBJECT')
    o.location = mid
    o.rotation_euler = vec.to_track_quat("-Z", "Y").to_euler()
    o.data.materials.clear()
    o.data.materials.append(mat)
    o.hide_render = True
    o.hide_viewport = True
    return o


def build_bolt():
    rng = random.Random(32)
    top = mathutils.Vector((40.0, 30.0, 78.0))
    bot = mathutils.Vector((6.0, -10.0, 13.0))
    n = 12
    pts = []
    for i in range(n + 1):
        t = i / n
        p = top.lerp(bot, t)
        if 0 < i < n:
            p.x += rng.uniform(-4.0, 4.0)
            p.y += rng.uniform(-4.0, 4.0)
            p.z += rng.uniform(-3.0, 3.0)
        pts.append(p)
    mat = make_bolt_material()
    objs = []
    for i in range(len(pts) - 1):
        r = 0.13 - 0.06 * (i / len(pts))
        objs.append(add_bolt_segment(pts[i], pts[i + 1], mat, r))
    return objs


bolt_objs = build_bolt()


# ---- 10) 相机复用 ----
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


# ---- 11) 渲染配置 + 出图 ----
def cfg_samples():
    sc.cycles.device = 'GPU'
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = 'OPTIX'
    sc.cycles.samples = 256
    sc.cycles.max_bounces = 12
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.view_settings.view_transform = 'AgX'


def set_frame(f):
    tag, energy, world_strength, exp, bolt = f
    flash_lamp.energy = energy
    for n in rain_world.node_tree.nodes:
        if n.type == 'BACKGROUND':
            n.inputs["Strength"].default_value = world_strength
    sc.view_settings.exposure = exp
    for o in bolt_objs:
        o.hide_render = not bolt
        o.hide_viewport = not bolt


def render_shot(cam, out_path, w, h):
    sc.camera = cam
    sc.render.resolution_x = w
    sc.render.resolution_y = h
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
frame_order = []
try:
    hidden_stack += hide_previews()
    cfg_samples()
    for f in FRAMES:
        tag = f[0]
        set_frame(f)
        out = os.path.join(OUT_DIR, "m32_lightning_%s.png" % tag)
        dt = render_shot(hero_cam, out, 1920, 1080)
        shots[tag] = {"out": out, "time_s": round(dt, 1), "size": os.path.getsize(out) if os.path.exists(out) else None}
        frame_order.append((tag, out))
    # 鸟瞰峰帧（额外 still）
    set_frame(("peak", 90.0, 0.06, -0.34, True))
    out_a = os.path.join(OUT_DIR, "m32_lightning_aerial_peak.png")
    dt = render_shot(aerial_cam, out_a, 2560, 1440)
    shots["aerial_peak"] = {"out": out_a, "time_s": round(dt, 1), "size": os.path.getsize(out_a) if os.path.exists(out_a) else None}
finally:
    show(hidden_stack)


# ---- 12) 恢复白昼基线 ----
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
    for lt in [lt for lt in bpy.data.lights if lt.name.startswith(PREFIX)]:
        bpy.data.lights.remove(lt)
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
    "milestone": "M32",
    "device": sc.cycles.device,
    "compute_device_type": cpref.compute_device_type,
    "denoiser": sc.cycles.denoiser,
    "samples": sc.cycles.samples,
    "frames": len(FRAMES),
    "wet_ground_overlay": n_ground,
    "rain_particles": n_particles,
    "bolt_segments": len(bolt_objs),
    "shots": {k: {
        "out": v["out"],
        "size": v["size"],
        "time_s": v["time_s"],
    } for k, v in shots.items()},
    "hero_cam_reused": ("M19C_HeroDay" if not hero_built else "M32_M19C_HeroDay"),
    "aerial_cam_reused": ("M11_CamAerial" if not aerial_built else "M32_M11_CamAerial"),
    "n_obj_after_restore": len(bpy.data.objects),
    "restored_world": sc.world.name,
}
print("M32_RESULT=" + repr(result))
