# run_m18.py — 执行 M18 材质 Vector 修复 + 渲染建筑材质预览
# 复用已验证的 Direct TCP Socket 链路（blmcp_client.send_execute，超时 540s 覆盖 Cycles）。
import sys, json
sys.path.insert(0, r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/tools")
import blmcp_client as C

BASE = C.BASE
M18 = BASE + r"/campus_td/build/m18_pbr_vector.py"
M18_PNG = BASE + r"/campus_td/previews/m18_pbr_vector.png"

# 1) 就地给所有 PBR_* 材质接通纹理 Vector（不删/不重建，零破坏其他物体）
build_code = 'exec(compile(open(r"%s").read(), "m18", "exec"))' % M18
resp1 = C.send_execute(build_code, strict_json=False, timeout=180.0)
print("BUILD:", json.dumps(resp1, ensure_ascii=False))

# 2) 白昼光照 + 西南建筑英雄机位渲染（框进砖/混凝土/草地/沥青材质是否仍发灰）
RENDER_M18_BODY = r'''
import bpy, mathutils
sc = bpy.context.scene
cam = bpy.data.objects.get("Camera")
if cam is None:
    bpy.ops.object.camera_add(location=(-38.0, -58.0, 30.0))
    cam = bpy.context.active_object
    cam.name = "Camera"
hidden = []
for o in bpy.data.objects:
    if o.name.startswith("Mat_Preview_") or o.name.startswith(("Furn_", "Int_", "Stair_")):
        hidden.append((o, o.hide_render))
        o.hide_render = True
sc.camera = cam
cam.location = (-38.0, -58.0, 30.0)
target = mathutils.Vector((2.0, -8.0, 5.0))
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
sc.render.engine = "CYCLES"
try:
    sc.cycles.device = "CPU"
except Exception:
    pass
sc.cycles.samples = 96
sc.render.resolution_x = 1600
sc.render.resolution_y = 900
sc.render.resolution_percentage = 100
sc.render.filepath = r"%s"
bpy.ops.render.render(write_still=True)
for o, was in hidden:
    o.hide_render = was
result = {"rendered": sc.render.filepath, "engine": sc.render.engine,
          "objects": len(bpy.data.objects), "mode": "m18_pbr_vector"}
'''
render_code = (C.M06_CODE + "\nbuild_lighting('day')\n" + RENDER_M18_BODY) % M18_PNG
resp2 = C.send_execute(render_code, strict_json=False, timeout=540.0)
print("RENDER:", json.dumps(resp2, ensure_ascii=False))
