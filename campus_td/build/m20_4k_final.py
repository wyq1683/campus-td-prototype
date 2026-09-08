# m20_4k_final.py — 里程碑 M20：4K-class OptiX 超采样终帧（改进 / 完善）【已探明受硬件限制】
# 非破坏：不删除任何场景物体，仅配置 GPU 渲染设备并输出高分辨率静帧。
#
# ⚠️ 硬件限制（2026-09-08 实测，RTX 5060 = 8GB VRAM）：
#   Cycles OptiX 降噪需要全分辨率 beauty+albedo+normal 缓冲区。本场景 1098 物体 + CC0 2K 纹理，
#   在 >2560×1440 时该缓冲区超出 8GB → 写帧阶段 OOM（"Error writing tile to file"）。
#   实测：3840×2160（降噪 / 无降噪 1024s）与 3200×1800（降噪）均 OOM 失败；
#        仅 2560×1440（==M19c）可行。故本脚本只跑 2560×1440，绝不尝试 4K/3200 以免空耗数十分钟。
#   真 4K 路径：换 >8GB GPU，或改用分块渲染 / 序列帧 / 降低纹理内存占用。
import bpy, mathutils, importlib.util, os, time

BASE = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
M06 = BASE + r"/build/m06_lighting.py"
OUT_HERO = BASE + r"/previews/m20_4k_hero_day.png"
OUT_AERIAL = BASE + r"/previews/m20_4k_aerial_dusk.png"

# 仅保留可行档（2560×1440，==M19c）；不再尝试 4K/3200（OOM）。
TIERS = [
    (2560, 1440, True, 512),
]

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

cpref = bpy.context.preferences.addons['cycles'].preferences
cpref.compute_device_type = 'OPTIX'
cpref.get_devices()
for d in cpref.devices:
    if d.type in ('OPTIX', 'CUDA'):
        d.use = True

sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.render.image_settings.file_format = 'PNG'
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

def render_frame(cam, out, label):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    rw, rh, denoise, samples = TIERS[0]
    sc.cycles.device = 'GPU'
    sc.cycles.use_denoising = denoise
    sc.cycles.denoiser = 'OPTIX' if denoise else 'NONE'
    sc.cycles.samples = samples
    sc.cycles.max_bounces = 12
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.view_settings.view_transform = 'AgX'
    sc.render.resolution_x = rw
    sc.render.resolution_y = rh
    sc.render.resolution_percentage = 100
    sc.render.filepath = out
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    return 0, round(time.time() - t0, 1)

m06.build_lighting("day")
hero = make_cam("M19C_HeroDay", (-52.0, -58.0, 48.0), (0.0, -2.0, 6.0), lens=35.0)
sc.camera = hero
hidden = hide_previews()
hero_tier, hero_t = render_frame(hero, OUT_HERO, "hero")
show(hidden)

m06.build_lighting("dusk")
aer = bpy.data.objects.get("M11_CamAerial")
if aer is None:
    aer = make_cam("M19C_AerialDusk", (-99.0, -99.0, 140.0), (0.0, 0.0, 0.0), lens=35.0)
sc.camera = aer
hidden = hide_previews()
aerial_tier, aerial_t = render_frame(aer, OUT_AERIAL, "aerial")
show(hidden)

result = {
    "device": sc.cycles.device,
    "compute_device_type": cpref.compute_device_type,
    "res": TIERS[0][:2],
    "note": "RTX 5060 8GB VRAM 无法承载 >2560x1440 OptiX 降噪；真 4K 需 >8GB GPU 或分块渲染",
    "hero": OUT_HERO,
    "aerial": OUT_AERIAL,
    "hero_size": os.path.getsize(OUT_HERO) if os.path.exists(OUT_HERO) else None,
    "aerial_size": os.path.getsize(OUT_AERIAL) if os.path.exists(OUT_AERIAL) else None,
    "time_hero_s": hero_t,
    "time_aerial_s": aerial_t,
}
