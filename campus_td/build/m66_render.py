# m66_render.py — M66 渲染（仅出图，不建物体）：白昼 OptiX 终帧
# 英雄机位 M66_Cam（南侧 3/4 看入器材区）+ 校园语境机位 M11_CamAerial；结束恢复 M19C_HeroDay。
import bpy, mathutils, os

PREV = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/previews"
HERO = os.path.join(PREV, "m66_fitness_hero.png")
AERIAL = os.path.join(PREV, "m66_fitness_aerial.png")

sc = bpy.context.scene
sc.render.engine = "CYCLES"
try:
    sc.cycles.device = "GPU"
except Exception:
    pass
try:
    pref = bpy.context.preferences.addons["cycles"].preferences
    pref.compute_device_type = "OPTIX"
    for d in pref.devices:
        d.use = True
except Exception:
    pass
sc.cycles.samples = 256
sc.cycles.use_denoising = True
sc.view_settings.look = "AgX - Base Contrast"

# 白昼光照（复用 m06 权威基线，避免孤儿天光累积）
M06 = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/build/m06_lighting.py"
try:
    exec(compile(open(M06).read(), "m06", "exec"))
    build_lighting("day")
except Exception as e:
    print("lighting reuse skipped:", e)

def render_with(cam_name, out_path):
    cam = bpy.data.objects.get(cam_name)
    if cam is None:
        raise RuntimeError("camera %s missing" % cam_name)
    sc.camera = cam
    sc.render.resolution_x = 1920
    sc.render.resolution_y = 1080
    sc.render.resolution_percentage = 100
    sc.render.filepath = out_path
    bpy.ops.render.render(write_still=True)
    return out_path

hero = render_with("M66_Cam", HERO)
aerial = render_with("M11_CamAerial", AERIAL)

# 恢复活动相机
restore = bpy.data.objects.get("M19C_HeroDay")
if restore is not None:
    sc.camera = restore

result = {"hero": hero, "aerial": aerial, "n_total": len(bpy.data.objects), "engine": sc.render.engine}
