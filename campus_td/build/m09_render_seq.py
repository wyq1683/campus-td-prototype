# m09_render_seq.py — M9 漫游视频：PNG 序列渲染（本构建无 FFMPEG，故先出序列，外部分帧编码 MP4）
# 复用 M6 光照 + M8 室内 + M7 塔防 + M9 漫游相机，EEVEE Next 实时级渲染 120 帧。
import bpy, mathutils, os

BASE = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59"
M06 = BASE + r"/campus_td/build/m06_lighting.py"
M08 = BASE + r"/campus_td/build/m08_interior.py"
M07 = BASE + r"/campus_td/build/m07_towerdefense.py"
M09 = BASE + r"/campus_td/build/m09_walkthrough.py"

# 1) 依次构建各里程碑（幂等、前缀隔离）
exec(compile(open(M06).read(), "m06", "exec")); build_lighting('day')
exec(compile(open(M08).read(), "m08", "exec")); build_interiors()
exec(compile(open(M07).read(), "m07", "exec")); build_towerdefense(); place_enemies_at_frame(90); update_beams(90)
exec(compile(open(M09).read(), "m09", "exec")); build_walkthrough()

sc = bpy.context.scene

# 2) 隐藏 M1 预览球，避免远景巨大白球
hidden = []
for o in bpy.data.objects:
    if o.name.startswith("Mat_Preview_"):
        hidden.append((o, o.hide_render))
        o.hide_render = True

# 3) EEVEE Next 实时级渲染（EEVEE 仅 GPU，速度远快于 Cycles；AgX 仍生效）
sc.render.engine = "BLENDER_EEVEE"
try:
    sc.eevee.taa_render_samples = 32
except Exception:
    pass
try:
    sc.eevee.use_raytracing = True
except Exception:
    pass
sc.render.resolution_x = 1280
sc.render.resolution_y = 720
sc.render.resolution_percentage = 100
sc.render.fps = 30
sc.frame_start = 1
sc.frame_end = 120

# 4) PNG 序列输出（本构建 image_settings.file_format 无 FFMPEG 枚举）
frames_dir = BASE + r"/campus_td/previews/m09_frames"
os.makedirs(frames_dir, exist_ok=True)
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGB"
sc.render.filepath = frames_dir + r"/frame_"

bpy.ops.render.render(animation=True, write_still=False)

for o, was in hidden:
    o.hide_render = was

result = {
    "m9_seq": True,
    "engine": sc.render.engine,
    "frames": sc.frame_end,
    "fps": sc.render.fps,
    "objects": len(bpy.data.objects),
    "frames_dir": frames_dir,
    "current_frame": sc.frame_current,
}
