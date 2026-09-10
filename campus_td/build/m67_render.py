# m67_render.py — M67 渲染（仅出图，不建物体）：白昼 OptiX 终帧
# 英雄机位 M67_Cam（3/4 看入读书角）+ 校园语境机位 M11_CamAerial；结束恢复 M19C_HeroDay。
import bpy, mathutils, os

PREV = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/previews"
HERO = os.path.join(PREV, "m67_speed_bumps_hero.png")
AERIAL = os.path.join(PREV, "m67_speed_bumps_aerial.png")

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

# 临时隐藏遮挡 hero 主体的 overhead clutter（非破坏、渲染后恢复可见性）。
# 关键：Cycles 渲染看的是 hide_render，不是 hide_viewport，故两者都要设置并恢复。
# 隐藏列表：M10D_血条 / M10C_波次UI / Enemy_敌人 / M41_Bleacher_看台 / M7_Path_路径 / M7_Ring_Tower_玩法塔基。
# 仅对 hero 生效；aerial 展示完整校园语境，恢复后再拍。
_hidden_states = []  # (object_name, original_hide_render)
_hero_hide_prefixes = ("M10D_", "M10C_", "Enemy_", "M41_Bleacher_", "M7_Path", "M7_Ring_Tower_", "M46_", "M50_", "M58_")
for o in bpy.data.objects:
    if any(o.name.startswith(p) for p in _hero_hide_prefixes):
        orig = o.hide_render
        o.hide_render = True
        o.hide_viewport = True
        _hidden_states.append((o.name, orig))

hero = render_with("M67_Cam", HERO)
# aerial 恢复所有隐藏物体后再拍
for nm, orig in _hidden_states:
    o = bpy.data.objects.get(nm)
    if o is not None:
        o.hide_render = orig
        o.hide_viewport = False
_hidden_states = []
aerial = render_with("M11_CamAerial", AERIAL)

# （_hidden_states 已在 aerial 前清空并恢复；下面是最终兜底，不重复操作）
# 恢复活动相机
restore = bpy.data.objects.get("M19C_HeroDay")
if restore is not None:
    sc.camera = restore

result = {"hero": hero, "aerial": aerial, "n_total": len(bpy.data.objects), "engine": sc.render.engine}
