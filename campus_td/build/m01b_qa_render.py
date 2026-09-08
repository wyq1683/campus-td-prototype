# m01b_qa_render.py — 渲染 CC0 预览球（y=4 行）与程序化预览球（y=0 行）做对比 QA
# 低分辨率 Cycles 快速渲染，输出 previews/m01b_qa.png；结束后清理临时相机/灯/目标。
import bpy, os

ROOT = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
OUT = os.path.join(ROOT, "previews", "m01b_qa.png")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

scn = bpy.context.scene
# 预览球中心：7 个 CC0 球在 x=60..78 step3, y=4；程序化在 y=0
cx = 69.0
cy = 2.0
cz = 1.4

# 临时目标 empty
tgt = bpy.data.objects.new("M1bQA_Tgt", None)
tgt.location = (cx, cy, cz)
scn.collection.objects.link(tgt)

# 相机
cam = bpy.data.cameras.new("M1bQA_Cam")
cam.lens = 35
cam_obj = bpy.data.objects.new("M1bQA_Cam", cam)
cam_obj.location = (cx, cy - 14.0, cz + 3.0)
scn.collection.objects.link(cam_obj)
trk = cam_obj.constraints.new("TRACK_TO")
trk.target = tgt
trk.track_axis = "TRACK_NEGATIVE_Z"
trk.up_axis = "UP_Y"
scn.camera = cam_obj

# 临时灯（预览球在 x~69，远离校园主光照）
lit = bpy.data.lights.new("M1bQA_Light", "AREA")
lit.energy = 800.0
lit.size = 12.0
lit_obj = bpy.data.objects.new("M1bQA_Light", lit)
lit_obj.location = (cx, cy, cz + 9.0)
lit_obj.rotation_euler = (0.0, 0.0, 0.0)
scn.collection.objects.link(lit_obj)

# 渲染设置：低分辨率快速验证
scn.render.engine = "CYCLES"
scn.cycles.samples = 24
scn.render.resolution_x = 640
scn.render.resolution_y = 360
scn.render.resolution_percentage = 100
scn.render.filepath = OUT
# 用 GPU 若可用，否则 CPU
try:
    scn.cycles.device = "GPU"
except Exception:
    scn.cycles.device = "CPU"

bpy.ops.render.render(write_still=True)

# 清理临时对象
for o in (cam_obj, lit_obj, tgt):
    scn.collection.objects.unlink(o)
    bpy.data.objects.remove(o, do_unlink=True)
bpy.data.cameras.remove(cam)
bpy.data.lights.remove(lit)

result = {"qa": True, "png": OUT, "res": (640, 360)}
print("M1b QA:", result)
