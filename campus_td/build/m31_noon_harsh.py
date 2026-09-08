# m31_noon_harsh.py — 里程碑 M31：正午硬光校园（Midday Harsh Sunlight · OptiX）
# 非破坏：不删/不改任何既有物体。仅新建 M31_ 前缀临时世界/材质（结束恢复），仅落盘 PNG。
# 思路：在已收官校园上叠加"正午硬光"——第 9 种时段/天气氛围（继 day/dusk/night/golden/snow/rain/lightning/morning-mist 之后）：
#   ① 深蓝晴空（穹顶深蔚蓝 → 中段蔚蓝 → 地平线苍白，strength 1.0，明亮正午天光）
#   ② 高角硬光太阳（接近天顶、略偏、白偏暖、energy 高、太阳角极小 + shadow_soft_size 极小 = 锐利短硬阴影 → "硬光"）
#   ③ 曝光略压，抓拍两张高对比正午校园帧。
#   复用已验证 M19C_HeroDay(英雄) / M11_CamAerial(鸟瞰) 机位。
# 渲染 Cycles GPU OptiX / 256 samples / 2560×1440 / AgX。结束恢复白昼基线（world/sun/exposure）。
import bpy, mathutils, importlib.util, os, time

BASE = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
M06 = BASE + r"/build/m06_lighting.py"
OUT_DIR = BASE + r"/previews"
PREFIX = "M31_"

HERO_LOC = (-52.0, -58.0, 48.0)
HERO_TGT = (0.0, -2.0, 6.0)
AERIAL_LOC = (0.0, -2.0, 120.0)
AERIAL_TGT = (0.0, 0.0, 0.0)

# ---- 正午硬光参数（经验初值，外部 PIL 像素统计校准）----
WORLD_STRENGTH = 1.0
SUN_ENERGY = 4.0
SUN_COLOR = (1.0, 0.97, 0.92)      # 白偏暖
SUN_LOC = (28.0, 38.0, 92.0)        # 高角近天顶、略偏 → 短锐利阴影
SUN_ANGLE = 0.01                    # 太阳盘极小 → 锐边
SUN_SOFT = 0.05                     # 阴影边缘极硬 → "硬光"
NOON_EXPOSURE = -0.05               # 略压以控高光


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ---- 0) 幂等清理旧 M31_ 数据（防异常残留）----
def clear_prefix():
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
    for w in [w for w in bpy.data.worlds if w.name.startswith(PREFIX)]:
        bpy.data.worlds.remove(w)


clear_prefix()

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


# ---- 3) 深蓝晴空天光 ----
def make_noon_world():
    w = bpy.data.worlds.new("M31_NoonWorld")
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
    # 深蔚蓝穹顶 → 蔚蓝中段 → 苍白地平线（明亮正午晴空）
    ramp.color_ramp.elements[0].color = (0.10, 0.32, 0.78, 1.0)
    e1 = ramp.color_ramp.elements.new(0.45)
    e1.color = (0.28, 0.55, 0.92, 1.0)
    ramp.color_ramp.elements[1].color = (0.80, 0.90, 0.97, 1.0)
    bg.inputs["Strength"].default_value = WORLD_STRENGTH
    return w


sc.world = make_noon_world()

sun = bpy.data.objects.get("M6_Sun")
if sun:
    sun.location = SUN_LOC
    sun.data.energy = SUN_ENERGY
    sun.data.color = SUN_COLOR
    sun.data.angle = SUN_ANGLE
    sun.data.shadow_soft_size = SUN_SOFT
    direction = mathutils.Vector((0.0, 0.0, 0.0)) - sun.location
    sun.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

sc.view_settings.view_transform = 'AgX'
sc.view_settings.exposure = NOON_EXPOSURE


# ---- 4) 相机复用 ----
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


# ---- 5) 渲染配置 + 出图 ----
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
    shots["hero"] = (os.path.join(OUT_DIR, "m31_noon_harsh_hero.png"),
                     render_shot(hero_cam, os.path.join(OUT_DIR, "m31_noon_harsh_hero.png")))
    shots["aerial"] = (os.path.join(OUT_DIR, "m31_noon_harsh_aerial.png"),
                       render_shot(aerial_cam, os.path.join(OUT_DIR, "m31_noon_harsh_aerial.png")))
finally:
    show(hidden_stack)


# ---- 6) 恢复白昼基线（不残留 M31_ 物体 / 世界 / 材质 / 网格 / 灯光）----
def restore():
    clear_prefix()
    try:
        m06.build_lighting("day")
    except Exception as _e:
        print("restore build_lighting warning:", _e)


restore()

if sc.world is None:
    w = bpy.data.worlds.new("World")
    w.use_nodes = True
    sc.world = w


import os as _os
result = {
    "milestone": "M31",
    "device": sc.cycles.device,
    "compute_device_type": cpref.compute_device_type,
    "denoiser": sc.cycles.denoiser,
    "samples": sc.cycles.samples,
    "resolution": [2560, 1440],
    "world_strength": WORLD_STRENGTH,
    "sun_energy": SUN_ENERGY,
    "sun_color": list(SUN_COLOR),
    "sun_loc": list(SUN_LOC),
    "sun_angle": SUN_ANGLE,
    "sun_soft": SUN_SOFT,
    "noon_exposure": NOON_EXPOSURE,
    "shots": {k: {
        "out": v[0],
        "size": _os.path.getsize(v[0]) if _os.path.exists(v[0]) else None,
        "time_s": round(v[1], 1),
    } for k, v in shots.items()},
    "hero_cam_reused": ("M19C_HeroDay" if not hero_built else "M31_M19C_HeroDay"),
    "aerial_cam_reused": ("M11_CamAerial" if not aerial_built else "M31_M11_CamAerial"),
    "n_obj_after_restore": len(bpy.data.objects),
    "restored_world": sc.world.name,
}
print("M31_RESULT=" + repr(result))
