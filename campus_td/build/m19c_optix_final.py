# m19c_optix_final.py — 里程碑 M19c：Cycles GPU (OptiX) 终帧渲染
# 非破坏：不删除任何场景物体，仅配置 GPU 渲染设备并出图。
# 出图：白昼英雄 3/4 俯角（塔防层+建筑同框）+ 暮色鸟瞰（96m 全场布局）。
import bpy, mathutils, importlib.util, os, time

BASE = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
M06 = BASE + r"/build/m06_lighting.py"
OUT_HERO = BASE + r"/previews/m19c_optix_hero_day.png"
OUT_AERIAL = BASE + r"/previews/m19c_optix_aerial_dusk.png"

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
sc.cycles.device = 'GPU'
sc.cycles.denoiser = 'OPTIX'
sc.cycles.use_denoising = True
sc.view_settings.view_transform = 'AgX'

m06 = load(M06, "m06l")

def hide_previews():
    hidden = []
    for o in bpy.data.objects:
        if o.name.startswith("Mat_Preview_"):
            hidden.append((o, o.hide_render))
            o.hide_render = True
    return hidden

def show(hidden):
    for o, was in hidden:
        o.hide_render = was

def make_cam(name, loc, target, lens=35.0):
    cam = bpy.data.objects.get(name)
    if cam is None:
        bpy.ops.object.camera_add(location=loc)
        cam = bpy.context.active_object
        cam.name = name
    cam.data.lens = lens
    cam.location = loc
    cam.rotation_euler = (mathutils.Vector(target) - mathutils.Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return cam

def cfg_samples():
    sc.cycles.device = 'GPU'
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = 'OPTIX'
    sc.cycles.samples = 512
    sc.cycles.max_bounces = 12
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.view_settings.view_transform = 'AgX'

hidden_stack = []
try:
    # ---- 2) 白昼英雄：塔防层 + 全建筑同框 ----
    m06.build_lighting("day")
    hero = make_cam("M19C_HeroDay", (-52.0, -58.0, 48.0), (0.0, -2.0, 6.0), lens=35.0)
    sc.camera = hero
    hidden_stack += hide_previews()
    cfg_samples()
    sc.render.resolution_x = 2560
    sc.render.resolution_y = 1440
    sc.render.resolution_percentage = 100
    sc.render.filepath = OUT_HERO
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    t_hero = time.time() - t0

    # ---- 3) 暮色鸟瞰：96m 全场布局 ----
    m06.build_lighting("dusk")
    aer = bpy.data.objects.get("M11_CamAerial")
    if aer is None:
        aer = make_cam("M19C_AerialDusk", (-99.0, -99.0, 140.0), (0.0, 0.0, 0.0), lens=35.0)
    sc.camera = aer
    hidden_stack += hide_previews()
    cfg_samples()
    sc.render.resolution_x = 2560
    sc.render.resolution_y = 1440
    sc.render.resolution_percentage = 100
    sc.render.filepath = OUT_AERIAL
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    t_aerial = time.time() - t0
finally:
    show(hidden_stack)

import os as _os
result = {
    "device": sc.cycles.device,
    "compute_device_type": cpref.compute_device_type,
    "active_devices": [d.name for d in cpref.devices if d.use],
    "denoiser": sc.cycles.denoiser,
    "samples": sc.cycles.samples,
    "hero": OUT_HERO,
    "aerial": OUT_AERIAL,
    "hero_size": _os.path.getsize(OUT_HERO) if _os.path.exists(OUT_HERO) else None,
    "aerial_size": _os.path.getsize(OUT_AERIAL) if _os.path.exists(OUT_AERIAL) else None,
    "time_hero_s": round(t_hero, 1),
    "time_aerial_s": round(t_aerial, 1),
}
