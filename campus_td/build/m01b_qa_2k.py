# m01b_qa_2k.py — V1.1 验证：探测每个 Mat_CC0_* 实际使用的分辨率 + 渲染预览球做像素统计回归
# 运行：execute_blender_code(code='exec(compile(open(r"...m01b_qa_2k.py").read(),"qa2k","exec"))')
import bpy, mathutils, os

OUT = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/previews/m01b_qa_2k.png"
sc = bpy.context.scene

# 1) 分辨率探测：每个 CC0 材质用到了哪些 res 的图
res_used = {}
for m in bpy.data.materials:
    if m.name.startswith("Mat_CC0_") and m.use_nodes:
        used = set()
        for n in m.node_tree.nodes:
            if n.type == "TEX_IMAGE" and n.image:
                b = os.path.basename(n.image.filepath)
                for r in ("4k", "2k", "1k"):
                    if f"_{r}" in b:
                        used.add(r)
        res_used[m.name] = sorted(used)

# 2) 取预览球世界 AABB 框机位
previews = [o for o in bpy.data.objects if o.name.startswith("Mat_CC0_Preview_")]
coords = []
for o in previews:
    for c in o.bound_box:
        coords.append(o.matrix_world @ mathutils.Vector(c))
if coords:
    xs = [v.x for v in coords]; ys = [v.y for v in coords]; zs = [v.z for v in coords]
    cx = (min(xs) + max(xs)) / 2; cy = (min(ys) + max(ys)) / 2; cz = (min(zs) + max(zs)) / 2
else:
    cx, cy, cz = 69, 4, 1.4

cam = bpy.data.objects.get("M1b_QA_Cam")
if cam is None:
    bpy.ops.object.camera_add(location=(cx, cy - 30, cz + 6))
    cam = bpy.context.active_object
    cam.name = "M1b_QA_Cam"
cam.location = (cx, cy - 22, cz + 5)
cam.data.lens = 35
target = mathutils.Vector((cx, cy, cz))
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
sc.camera = cam

# 预览球 QA 专用光照：场景灯已在下面被 hide_render，这里加一盏 AREA 主光确保球体被充分打亮
qa_light = bpy.data.objects.get("M1b_QA_Light")
if qa_light is None:
    bpy.ops.object.light_add(type="AREA", location=(cx, cy - 6, cz + 12))
    qa_light = bpy.context.active_object
    qa_light.name = "M1b_QA_Light"
qa_light.location = (cx, cy - 6, cz + 12)
qa_light.data.energy = 2500.0
qa_light.data.size = 12.0
qa_light.hide_render = False

# 仅渲染预览球 + QA 灯（其余临时隐藏，渲染后恢复）
for o in bpy.data.objects:
    o.hide_render = not (o.name.startswith("Mat_CC0_Preview_") or o.name == "M1b_QA_Light")

sc.render.engine = "CYCLES"
try:
    sc.cycles.device = "CPU"
except Exception:
    pass
sc.cycles.samples = 128
sc.render.resolution_x = 640
sc.render.resolution_y = 360
sc.render.resolution_percentage = 100
sc.render.film_transparent = True
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
sc.render.film_transparent = False

for o in bpy.data.objects:
    o.hide_render = False

result = {"res_used": res_used, "rendered": OUT, "preview_count": len(previews)}
print("M1b QA:", result)
