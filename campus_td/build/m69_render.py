# m69_render.py — M69 渲染（仅出图，不建物体）：白昼 OptiX 终帧
# 英雄机位 M69_Cam（南侧 3/4 看入升旗台）+ 校园语境机位 M11_CamAerial。
import bpy, mathutils, os

PREV = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/previews"
HERO = os.path.join(PREV, "m69_flag_platform_hero.png")
AERIAL = os.path.join(PREV, "m69_flag_platform_aerial.png")

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


def render_with(cam_name, out_path, exposure=None):
    cam = bpy.data.objects.get(cam_name)
    if cam is None:
        raise RuntimeError("camera %s missing" % cam_name)
    sc.camera = cam
    sc.render.resolution_x = 1920
    sc.render.resolution_y = 1080
    sc.render.resolution_percentage = 100
    sc.render.filepath = out_path
    orig_exp = sc.view_settings.exposure
    if exposure is not None:
        sc.view_settings.exposure = exposure
    bpy.ops.render.render(write_still=True)
    sc.view_settings.exposure = orig_exp
    return out_path


# 升旗台位于北侧开阔地，白昼光照充足，hero 维持 0.0 曝光；先出 hero 再出 aerial。
hero = render_with("M69_Cam", HERO, exposure=0.0)
aerial = render_with("M11_CamAerial", AERIAL, exposure=0.0)

# 恢复活动相机
restore = bpy.data.objects.get("M19C_HeroDay")
if restore is not None:
    sc.camera = restore

result = {"hero": hero, "aerial": aerial, "n_total": len(bpy.data.objects),
          "engine": sc.render.engine}
print("M69_RENDER_RESULT=" + repr(result))
