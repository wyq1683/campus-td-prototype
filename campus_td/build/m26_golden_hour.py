# m26_golden_hour.py — 里程碑 M26：黄金时刻暖调渲染（Golden Hour Cinematic）
# 非破坏：不删/不改任何既有物体。仅新建 M26_ 前缀临时世界/相机（结束恢复），仅落盘 PNG。
# 思路：把已验证的白昼英雄机位 / 鸟瞰机位，在"低角度暖色阳光 + 暖色天穹渐变"下重拍成黄金时刻，
#   与既有 day / dusk(M6) / night(M24) 形成第 4 种时段氛围；复用 M25 持久化体积雾做暖色大气薄霭。
# 渲染 Cycles GPU OptiX / 256 samples / 2560×1440 / AgX。结束恢复白昼基线（world/sun/exposure/glow/halo）。
import bpy, mathutils, importlib.util, os, time

BASE = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
M06 = BASE + r"/build/m06_lighting.py"
OUT_DIR = BASE + r"/previews"
PREFIX = "M26_"

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


# ---- 2) 以 day 为已知基线（确保 M6_Sun / 天穹 / 辉光壳 存在）----
m06.build_lighting("day")


# ---- 3) 保存原状态（用于结束恢复）----
old_world = sc.world
sun = bpy.data.objects.get("M6_Sun")
saved = {}
if sun:
    saved["sun_energy"] = sun.data.energy
    saved["sun_color"] = tuple(sun.data.color)
    saved["sun_loc"] = tuple(sun.location)
saved["exposure"] = sc.view_settings.exposure
saved["view_transform"] = sc.view_settings.view_transform

glow_saved = []
for mat in bpy.data.materials:
    if "glow" in mat.name.lower() and mat.use_nodes:
        for n in mat.node_tree.nodes:
            if n.type == "EMISSION":
                glow_saved.append((mat.name, n.inputs["Strength"].default_value))

halo_saved = []
for mat in bpy.data.materials:
    if mat.name.startswith("M6_HaloMat"):
        for n in mat.node_tree.nodes:
            if n.type == "EMISSION":
                halo_saved.append((mat.name, n.inputs["Strength"].default_value))


# ---- 4) 黄金时刻布光 ----
def make_golden_world():
    w = bpy.data.worlds.new("M26_GoldenWorld")
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
    # 暖橙地平线 → 蜜桃 → 柔蓝中高 → 深蓝顶
    ramp.color_ramp.elements[0].color = (0.98, 0.62, 0.30, 1.0)
    e1 = ramp.color_ramp.elements.new(0.40)
    e1.color = (0.96, 0.76, 0.55, 1.0)
    e2 = ramp.color_ramp.elements.new(0.70)
    e2.color = (0.55, 0.66, 0.82, 1.0)
    ramp.color_ramp.elements[1].color = (0.24, 0.40, 0.72, 1.0)
    bg.inputs["Strength"].default_value = 0.55
    return w


sc.world = make_golden_world()

if sun:
    # 低角度暖色阳光，落在校园远端 (+x,+y) 做逆光/边缘光，制造金色轮廓
    sun.location = (78.0, 58.0, 22.0)
    sun.data.energy = 4.5
    sun.data.color = (1.0, 0.52, 0.22)
    sun.data.angle = 0.010
    sun.data.shadow_soft_size = 3.0
    direction = mathutils.Vector((0.0, 0.0, 0.0)) - sun.location
    sun.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

sc.view_settings.view_transform = 'AgX'
sc.view_settings.exposure = 0.05


# ---- 5) 相机：复用已验证英雄机位 / 鸟瞰机位，缺失则自建 ----
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
    shots["hero"] = (os.path.join(OUT_DIR, "m26_golden_hour_hero.png"),
                     render_shot(hero_cam, os.path.join(OUT_DIR, "m26_golden_hour_hero.png")))
    shots["aerial"] = (os.path.join(OUT_DIR, "m26_golden_hour_aerial.png"),
                       render_shot(aerial_cam, os.path.join(OUT_DIR, "m26_golden_hour_aerial.png")))
finally:
    show(hidden_stack)


# ---- 7) 恢复白昼基线（仅落盘 PNG，不残留 M26_ 物体 / 金世界）----
def restore():
    for o in list(bpy.data.objects):
        if o.name.startswith(PREFIX):
            bpy.data.objects.remove(o, do_unlink=True)
    for c in [c for c in bpy.data.cameras if c.name.startswith(PREFIX)]:
        bpy.data.cameras.remove(c)
    if "M26_GoldenWorld" in bpy.data.worlds:
        bpy.data.worlds.remove(bpy.data.worlds["M26_GoldenWorld"])
    sc.world = old_world
    if sun:
        sun.data.energy = saved["sun_energy"]
        sun.data.color = saved["sun_color"]
        sun.location = saved["sun_loc"]
    sc.view_settings.exposure = saved["exposure"]
    sc.view_settings.view_transform = saved["view_transform"]
    for mn, val in glow_saved:
        m = bpy.data.materials.get(mn)
        if m and m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == "EMISSION":
                    n.inputs["Strength"].default_value = val
    for mn, val in halo_saved:
        m = bpy.data.materials.get(mn)
        if m and m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == "EMISSION":
                    n.inputs["Strength"].default_value = val


restore()

import os as _os
result = {
    "milestone": "M26",
    "device": sc.cycles.device,
    "compute_device_type": cpref.compute_device_type,
    "denoiser": sc.cycles.denoiser,
    "samples": sc.cycles.samples,
    "resolution": [2560, 1440],
    "shots": {k: {
        "out": v[0],
        "size": _os.path.getsize(v[0]) if _os.path.exists(v[0]) else None,
        "time_s": round(v[1], 1),
    } for k, v in shots.items()},
    "hero_cam_reused": ("M19C_HeroDay" if not hero_built else "M26_M19C_HeroDay"),
    "aerial_cam_reused": ("M11_CamAerial" if not aerial_built else "M26_M11_CamAerial"),
    "n_obj_after_restore": len(bpy.data.objects),
    "restored_world": sc.world.name,
}
print("M26_RESULT=" + repr(result))
