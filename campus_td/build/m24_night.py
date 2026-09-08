# m24_night.py — 里程碑 M24：夜间塔防作战渲染（Night Defense Render）
# 非破坏：不删/不改任何既有物体。仅新建 M24_ 前缀相机（复刻已验证的 M19C_HeroDay 英雄机位）
#   与 M24_ 临时点光（塔基补光）；结束恢复光照状态，仅落盘一张 PNG。
# 思路：把"白昼英雄 3/4 俯角"复拍成"夜间作战"——压暗天光 + 冷蓝月光 + 防御塔发光环/辉光壳提亮
#   + 塔基补点光，让 4 座防御塔在夜色中清晰可辨，凸显塔防主题。
# 渲染 Cycles GPU OptiX / 256 samples / 2560×1440 / AgX。
import bpy, mathutils, importlib.util, os, time

BASE = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
M06 = BASE + r"/build/m06_lighting.py"
OUT = BASE + r"/previews/m24_night_defense.png"
PREFIX = "M24_"

HERO_LOC = (-52.0, -58.0, 48.0)
HERO_TGT = (0.0, -2.0, 6.0)


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


# ---- 4) 夜间布光 ----
def make_night_world():
    w = bpy.data.worlds.new("M24_NightWorld")
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
    ramp.color_ramp.elements[0].color = (0.06, 0.07, 0.13, 1.0)
    e1 = ramp.color_ramp.elements.new(0.5)
    e1.color = (0.03, 0.04, 0.10, 1.0)
    ramp.color_ramp.elements[1].color = (0.01, 0.015, 0.04, 1.0)
    bg.inputs["Strength"].default_value = 0.28
    return w


sc.world = make_night_world()

if sun:
    sun.data.energy = 0.8
    sun.data.color = (0.55, 0.68, 1.0)
    sun.data.shadow_soft_size = 5.0

# 提亮塔防发光环 + 辉光壳（夜间主视觉）
for mat in bpy.data.materials:
    if "glow" in mat.name.lower() and mat.use_nodes:
        for n in mat.node_tree.nodes:
            if n.type == "EMISSION":
                n.inputs["Strength"].default_value = 9.0
for mat in bpy.data.materials:
    if mat.name.startswith("M6_HaloMat"):
        for n in mat.node_tree.nodes:
            if n.type == "EMISSION":
                n.inputs["Strength"].default_value = 6.0

# 塔基补点光，让塔在地面投出冷光池
towers = [o for o in bpy.data.objects if o.name.startswith("Tower_") and o.type == 'MESH']
for i, o in enumerate(towers):
    bb = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
    cx = sum(v.x for v in bb) / 8.0
    cy = sum(v.y for v in bb) / 8.0
    cz = sum(v.z for v in bb) / 8.0
    bpy.ops.object.light_add(type='POINT')
    pl = bpy.context.object
    pl.name = f"{PREFIX}TLight_{i}"
    pl.data.name = f"{PREFIX}TLight_{i}"
    pl.location = (cx, cy, cz + 0.5)
    pl.data.energy = 120.0
    pl.data.color = (0.7, 0.8, 1.0)
    pl.data.shadow_soft_size = 2.0
    try:
        pl.data.cutoff_distance = 45.0
    except Exception:
        pass

sc.view_settings.view_transform = 'AgX'
sc.view_settings.exposure = -0.05

# ---- 5) 相机：复刻已验证英雄机位 ----
for o in list(bpy.data.objects):
    if o.name.startswith(PREFIX):
        bpy.data.objects.remove(o, do_unlink=True)
for c in [c for c in bpy.data.cameras if c.name.startswith(PREFIX)]:
    bpy.data.cameras.remove(c)

cam_data = bpy.data.cameras.new(PREFIX + "NightCam")
cam_data.sensor_width = 36.0
cam_data.lens = 35.0
cam_data.clip_start = 0.1
cam_data.clip_end = 1000.0
cam = bpy.data.objects.new(PREFIX + "NightCam", cam_data)
bpy.context.collection.objects.link(cam)
cam.location = mathutils.Vector(HERO_LOC)
cam.rotation_euler = (mathutils.Vector(HERO_TGT) - mathutils.Vector(HERO_LOC)).to_track_quat("-Z", "Y").to_euler()
sc.camera = cam


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


hidden_stack = []
try:
    hidden_stack += hide_previews()
    cfg_samples()
    sc.render.resolution_x = 2560
    sc.render.resolution_y = 1440
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.render.image_settings.color_depth = '8'
    sc.render.filepath = OUT
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    t_render = time.time() - t0
finally:
    show(hidden_stack)


# ---- 7) 恢复光照状态（仅落盘 PNG，不残留 M24_ 物体 / 夜世界）----
def restore():
    for o in list(bpy.data.objects):
        if o.name.startswith(PREFIX):
            bpy.data.objects.remove(o, do_unlink=True)
    for c in [c for c in bpy.data.cameras if c.name.startswith(PREFIX)]:
        bpy.data.cameras.remove(c)
    if "M24_NightWorld" in bpy.data.worlds:
        bpy.data.worlds.remove(bpy.data.worlds["M24_NightWorld"])
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
    "milestone": "M24",
    "device": sc.cycles.device,
    "compute_device_type": cpref.compute_device_type,
    "denoiser": sc.cycles.denoiser,
    "samples": sc.cycles.samples,
    "resolution": [2560, 1440],
    "hero_cam_loc": list(HERO_LOC),
    "towers_lit": len(towers),
    "out": OUT,
    "size": _os.path.getsize(OUT) if _os.path.exists(OUT) else None,
    "time_s": round(t_render, 1),
    "n_obj_after_restore": len(bpy.data.objects),
    "restored_world": sc.world.name,
}
