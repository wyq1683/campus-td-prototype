# m23_panorama.py — 里程碑 M23：360° 等距矩形全景图（Cycles GPU OptiX 终帧）
# 非破坏：不删除/重建任何场景物体，仅新建一个全景相机 M23_Pano（前缀 M23_，幂等）。
# 思路：把当前已收官的校园场景渲染成一张 2:1 等距矩形（Equirectangular）全景，
#   可在 360° 全景查看器里沉浸式环视校园。输出格式属"完善/对外展示"范畴，
#   与 M21 画廊 / M22 漫游视频同一脉（不新增场景、不突破硬件）。
# 分辨率 2560×1280（2:1）：总像素 3.27M < M20 实测安全上限 2560×1440=3.69M，8GB VRAM 不 OOM。
import bpy, mathutils, importlib.util, os, time, math

BASE = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
M06 = BASE + r"/build/m06_lighting.py"
OUT = BASE + r"/previews/m23_panorama.png"
PREFIX = "M23_"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ---- 1) 配置 Cycles GPU (OptiX)（与 m19c / m22 同套路）----
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


# ---- 2) 自动寻找"最居中且不在建筑内"的地面落点：距场地中心最近的开阔点 ----
# 360° 全景讲究沉浸式——站在校园中庭、四周被楼体环抱最佳；故取"不在任一 Bldg AABB 内、
# 且距原点最近"的网格点，而不是"距所有楼最远"的边角（边角大半视野是围墙/天）。
def best_spot():
    bldgs = [o for o in bpy.data.objects if o.name.startswith("Bldg_") and o.type == 'MESH']
    if not bldgs:
        return mathutils.Vector((0.0, 0.0, 1.6))

    def inside(p):
        for b in bldgs:
            bb = [b.matrix_world @ mathutils.Vector(c) for c in b.bound_box]
            xs = [v.x for v in bb]
            ys = [v.y for v in bb]
            if min(xs) <= p.x <= max(xs) and min(ys) <= p.y <= max(ys):
                return True
        return False

    best = (0, 0)
    best_d = 1e9
    for gx in range(-44, 45, 2):
        for gy in range(-44, 45, 2):
            p = mathutils.Vector((float(gx), float(gy), 0.0))
            if inside(p):
                continue
            d = math.hypot(gx, gy)
            if d < best_d:
                best_d = d
                best = (gx, gy)
    return mathutils.Vector((float(best[0]), float(best[1]), 1.6))


spot = best_spot()

# ---- 3) 建/清 M23 全景相机（Equirectangular）----
for o in list(bpy.data.objects):
    if o.name.startswith(PREFIX):
        bpy.data.objects.remove(o, do_unlink=True)
for c in [c for c in bpy.data.cameras if c.name.startswith(PREFIX)]:
    bpy.data.cameras.remove(c)

cam_data = bpy.data.cameras.new(PREFIX + "Pano")
cam_data.type = 'PANO'
cam_data.panorama_type = 'EQUIRECTANGULAR'
cam_data.sensor_width = 36.0
cam_data.clip_start = 0.05
cam_data.clip_end = 500.0
cam = bpy.data.objects.new(PREFIX + "Pano", cam_data)
bpy.context.collection.objects.link(cam)
cam.location = spot
cam.rotation_euler = (0.0, 0.0, 0.0)  # 全景相机方向由全景类型固定捕获全周天，北向对齐即可


# ---- 4) 渲染配置 ----
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
    m06.build_lighting("day")
    sc.camera = cam                      # build_lighting 不改 sc.camera，但保险起见渲染前再指派
    hidden_stack += hide_previews()
    cfg_samples()
    sc.render.resolution_x = 2560
    sc.render.resolution_y = 1280
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

import os as _os
result = {
    "milestone": "M23",
    "device": sc.cycles.device,
    "compute_device_type": cpref.compute_device_type,
    "denoiser": sc.cycles.denoiser,
    "samples": sc.cycles.samples,
    "resolution": [2560, 1280],
    "panorama_type": cam_data.panorama_type,
    "spot": [round(spot.x, 2), round(spot.y, 2), round(spot.z, 2)],
    "out": OUT,
    "size": _os.path.getsize(OUT) if _os.path.exists(OUT) else None,
    "time_s": round(t_render, 1),
    "n_obj": len(bpy.data.objects),
}
