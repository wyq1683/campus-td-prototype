# m30_morning_mist.py — 里程碑 M30：清晨薄雾校园（Morning Mist Dawn Campus · OptiX）
# 非破坏：不删/不改任何既有物体。仅新建 M30_ 前缀临时世界/雾盒/材质（结束恢复），仅落盘 PNG。
# 思路：在已收官校园上叠加"清晨薄雾"——
#   ① 柔和破晓天光（深蓝穹顶 → 柔蓝中段 → 暖桃地平线，strength 0.5）
#   ② 低角柔粉朝阳（低仰角、暖粉、软阴影）
#   ③ 贴地晨雾（两层体积雾盒：底层浓 z∈[-1,4] / 高层薄 z∈[3,17]，偏冷白）
#   ④ 微提曝光，抓拍两张电影级清晨校园帧。
#   与 day/dusk/night(M24)/golden(M26)/snow(M27)/rain(M28)/lightning(M29) 形成第 8 种时段/天气氛围。
#   复用已验证 M19C_HeroDay(英雄) / M11_CamAerial(鸟瞰) 机位。
# 渲染 Cycles GPU OptiX / 256 samples / 2560×1440 / AgX。结束恢复白昼基线（world/sun/exposure/fog）。
import bpy, mathutils, importlib.util, os, time

BASE = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
M06 = BASE + r"/build/m06_lighting.py"
OUT_DIR = BASE + r"/previews"
PREFIX = "M30_"

HERO_LOC = (-52.0, -58.0, 48.0)
HERO_TGT = (0.0, -2.0, 6.0)
AERIAL_LOC = (0.0, -2.0, 120.0)
AERIAL_TGT = (0.0, 0.0, 0.0)

MIST_LOW_DENSITY = 0.030
MIST_HIGH_DENSITY = 0.012
DAWN_EXPOSURE = 0.05


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ---- 0) 幂等清理旧 M30_ 数据（防异常残留）----
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


# ---- 3) 破晓柔和天光 ----
def make_dawn_world():
    w = bpy.data.worlds.new("M30_DawnWorld")
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
    # 深蓝穹顶 → 柔蓝中段 → 暖桃地平线（破晓）
    ramp.color_ramp.elements[0].color = (0.20, 0.32, 0.58, 1.0)
    e1 = ramp.color_ramp.elements.new(0.5)
    e1.color = (0.45, 0.55, 0.74, 1.0)
    ramp.color_ramp.elements[1].color = (0.96, 0.72, 0.56, 1.0)
    bg.inputs["Strength"].default_value = 0.5
    return w


sc.world = make_dawn_world()

sun = bpy.data.objects.get("M6_Sun")
if sun:
    sun.location = (60.0, -40.0, 16.0)   # 低仰角，近地平线
    sun.data.energy = 2.2
    sun.data.color = (1.0, 0.68, 0.48)     # 柔粉朝阳
    sun.data.angle = 0.02
    sun.data.shadow_soft_size = 5.0        # 柔长阴影
    direction = mathutils.Vector((0.0, 0.0, 0.0)) - sun.location
    sun.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

sc.view_settings.view_transform = 'AgX'
sc.view_settings.exposure = DAWN_EXPOSURE


# ---- 4) 贴地晨雾（两层体积雾盒：底层浓、高层薄）----
def make_mist_material(density, color):
    mat = bpy.data.materials.new(PREFIX + "MistMat")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    nt.links.new(vol.outputs["Volume"], out.inputs["Volume"])
    vol.inputs["Density"].default_value = density
    vol.inputs["Anisotropy"].default_value = 0.30
    vol.inputs["Color"].default_value = color
    vol.inputs["Emission Strength"].default_value = 0.0
    return mat


mist_low_mat = make_mist_material(MIST_LOW_DENSITY, (0.82, 0.87, 0.92, 1.0))
mist_high_mat = make_mist_material(MIST_HIGH_DENSITY, (0.80, 0.85, 0.92, 1.0))

# 底层浓雾：贴地，z 跨 -1..4
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 1.5))
mist_low = bpy.context.active_object
mist_low.name = PREFIX + "MistLow"
mist_low.scale = (92.0, 92.0, 5.0)
mist_low.hide_viewport = True      # 不污染艺术家视口
mist_low.hide_render = False        # 但参与渲染
if mist_low.data.materials:
    mist_low.data.materials[0] = mist_low_mat
else:
    mist_low.data.materials.append(mist_low_mat)

# 高层薄霭：z 跨 3..17
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 10.0))
mist_high = bpy.context.active_object
mist_high.name = PREFIX + "MistHigh"
mist_high.scale = (92.0, 92.0, 14.0)
mist_high.hide_viewport = True
mist_high.hide_render = False
if mist_high.data.materials:
    mist_high.data.materials[0] = mist_high_mat
else:
    mist_high.data.materials.append(mist_high_mat)

# 体积步进取样：适度精度让雾过渡平滑（不显著增负）
try:
    sc.cycles.volume_step_rate = 1.8
except Exception:
    pass


# ---- 5) 相机复用 ----
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


# ---- 6) 渲染配置 + 出图 ----
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
    shots["hero"] = (os.path.join(OUT_DIR, "m30_morning_mist_hero.png"),
                     render_shot(hero_cam, os.path.join(OUT_DIR, "m30_morning_mist_hero.png")))
    shots["aerial"] = (os.path.join(OUT_DIR, "m30_morning_mist_aerial.png"),
                       render_shot(aerial_cam, os.path.join(OUT_DIR, "m30_morning_mist_aerial.png")))
finally:
    show(hidden_stack)


# ---- 7) 恢复白昼基线（不残留 M30_ 物体 / 世界 / 材质 / 网格 / 灯光）----
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
    "milestone": "M30",
    "device": sc.cycles.device,
    "compute_device_type": cpref.compute_device_type,
    "denoiser": sc.cycles.denoiser,
    "samples": sc.cycles.samples,
    "resolution": [2560, 1440],
    "dawn_exposure": DAWN_EXPOSURE,
    "mist_low_density": MIST_LOW_DENSITY,
    "mist_high_density": MIST_HIGH_DENSITY,
    "shots": {k: {
        "out": v[0],
        "size": _os.path.getsize(v[0]) if _os.path.exists(v[0]) else None,
        "time_s": round(v[1], 1),
    } for k, v in shots.items()},
    "hero_cam_reused": ("M19C_HeroDay" if not hero_built else "M30_M19C_HeroDay"),
    "aerial_cam_reused": ("M11_CamAerial" if not aerial_built else "M30_M11_CamAerial"),
    "n_obj_after_restore": len(bpy.data.objects),
    "restored_world": sc.world.name,
}
print("M30_RESULT=" + repr(result))
