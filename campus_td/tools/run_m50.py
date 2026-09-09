# run_m50.py — 直连 Blender MCP addon @9876，执行 M50 构建 + 双机位渲染
import sys, json
sys.path.insert(0, r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/tools")
from blmcp_client import send_execute

ROOT = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
BUILD = ROOT + r"/build/m50_bike_lane.py"
PRE = ROOT + r"/previews"

code = open(BUILD, encoding="utf-8").read()
resp = send_execute(code, strict_json=False, timeout=300.0)
print("=== BUILD RESP ===")
print(json.dumps(resp, ensure_ascii=False)[:3000])

render_code = r'''
import bpy, mathutils
sc = bpy.context.scene
sc.render.engine = "CYCLES"
try:
    sc.cycles.device = "GPU"
except Exception:
    pass
try:
    sc.cycles.compute_device_type = "OPTIX"
except Exception:
    pass
sc.cycles.samples = 256
sc.render.resolution_x = 1280
sc.render.resolution_y = 720
sc.view_settings.view_transform = "AgX"
sc.view_settings.exposure = 0.0
OUT = r"%s/m50_bikelane_closeup.png"
cam = bpy.data.objects.get("M50_Cam")
sc.camera = cam
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
HERO = r"%s/m50_bikelane_hero.png"
hc = bpy.data.objects.get("M19C_HeroDay")
sc.camera = hc
sc.render.filepath = HERO
bpy.ops.render.render(write_still=True)
result = {"closeup": OUT, "hero": HERO, "active_cam": (sc.camera.name if sc.camera else None), "objects": len(bpy.data.objects)}
''' % (PRE, PRE)

resp2 = send_execute(render_code, strict_json=False, timeout=540.0)
print("=== RENDER RESP ===")
print(json.dumps(resp2, ensure_ascii=False)[:2000])
