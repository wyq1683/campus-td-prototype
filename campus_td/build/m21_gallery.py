# m21_gallery.py — 里程碑 M21：镜头画廊（多机位 Cycles GPU OptiX 终帧集）
# 非破坏：不删除/重建任何场景物体，仅复用已有命名相机（M19C_HeroDay / M11_CamAerial /
#   M14_Cam / M16_Cam / M17_Cam / M15_Cam）配置 GPU 渲染设备并出一组 2560x1440 终帧。
# 目的：把已收官原型的关键视角统一升到 OptiX 终帧质量，形成一套可对外展示的画廊。
import bpy, mathutils, importlib.util, os, time

BASE = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
M06 = BASE + r"/build/m06_lighting.py"
OUT = BASE + r"/previews"

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
sc.view_settings.view_transform = 'AgX'

m06 = load(M06, "m06l")

def hide_previews():
    hidden = []
    for o in bpy.data.objects:
        if o.name.startswith("Mat_Preview_"):
            hidden.append((o, o.hide_render))
            o.hide_render = True
    return hidden

def show(h):
    for o, was in h:
        o.hide_render = was

def cfg():
    sc.cycles.device = 'GPU'
    sc.cycles.denoiser = 'OPTIX'
    sc.cycles.use_denoising = True
    sc.cycles.samples = 512
    sc.cycles.max_bounces = 12
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.view_settings.view_transform = 'AgX'

# ---- 2) 画廊镜头清单（全部复用场景中已存在的命名相机）----
# (输出后缀, 相机名, 光照模式, 宽, 高)
SHOTS = [
    ("hero_day",      "M19C_HeroDay", "day",  2560, 1440),  # 白昼英雄 3/4 俯角：塔防层+全建筑同框
    ("aerial_dusk",   "M11_CamAerial","dusk", 2560, 1440),  # 暮色鸟瞰：96m 全场布局
    ("gate_plaque",   "M14_Cam",      "day",  2560, 1440),  # 校门匾文特写
    ("crenellations", "M16_Cam",      "day",  2560, 1440),  # 围墙垛口转角
    ("classroom",     "M17_Cam",      "day",  2560, 1440),  # 教学楼教室英雄机位
    ("stairs",        "M15_Cam",      "day",  2560, 1440),  # 真实踏步楼梯特写
]

report = []
for suf, camn, mode, W, H in SHOTS:
    cam = bpy.data.objects.get(camn)
    if cam is None:
        report.append({"shot": suf, "camera": camn, "status": "skip_no_cam"})
        continue
    m06.build_lighting(mode)
    sc.camera = cam
    h = hide_previews()
    cfg()
    sc.render.resolution_x = W
    sc.render.resolution_y = H
    sc.render.resolution_percentage = 100
    out = os.path.join(OUT, "m21_gallery_%s.png" % suf)
    sc.render.filepath = out
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    dt = round(time.time() - t0, 1)
    show(h)
    report.append({
        "shot": suf, "camera": camn, "mode": mode, "out": out,
        "size": os.path.getsize(out) if os.path.exists(out) else None,
        "time_s": dt,
    })

result = {
    "device": sc.cycles.device,
    "compute_device_type": cpref.compute_device_type,
    "denoiser": sc.cycles.denoiser,
    "samples": sc.cycles.samples,
    "shots": report,
    "n_obj": len(bpy.data.objects),
}
