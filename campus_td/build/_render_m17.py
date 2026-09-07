# _render_m17.py — M17 预览渲染运行器
# 确保白昼光照（import m06_lighting 并 build_lighting('day')），用 M17_Cam 出图。
import bpy, mathutils, importlib.util

BASE = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
OUT = BASE + r"/previews/m17_props.png"

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

m06 = load(BASE + r"/build/m06_lighting.py", "m06l")
m06.build_lighting("day")

sc = bpy.context.scene
cam = bpy.data.objects.get("M17_Cam")
if cam is None:
    cam = bpy.data.objects.get("Camera")
    if cam is None:
        bpy.ops.object.camera_add(location=(0.0, -23.0, 4.5))
        cam = bpy.context.active_object
sc.camera = cam

hidden = []
for o in bpy.data.objects:
    if o.name.startswith("Mat_Preview_"):
        hidden.append((o, o.hide_render))
        o.hide_render = True

sc.render.engine = "CYCLES"
try:
    sc.cycles.device = "CPU"
except Exception:
    pass
sc.cycles.samples = 128
sc.render.resolution_x = 1600
sc.render.resolution_y = 900
sc.render.resolution_percentage = 100
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)

for o, was in hidden:
    o.hide_render = was

m17 = len([o for o in bpy.data.objects if o.name.startswith("M17_") and "Cam" not in o.name])
result = {
    "rendered": sc.render.filepath,
    "engine": sc.render.engine,
    "objects": len(bpy.data.objects),
    "m17_props": m17,
    "cam": cam.name,
}
