# blmcp_client.py — Direct TCP Socket client for the Blender MCP addon @ localhost:9876
# Protocol (confirmed from addon mcp_to_blender_server.py):
#   request : b'{"type":"execute","code":<str>,"strict_json":<bool>}\0'
#   response: b'{"status":"ok","result":{...},"stdout":"","stderr":""}\0'  (null-delimited)
# Usage:
#   python blmcp_client.py objects            -> scene probe
#   python blmcp_client.py m02                -> run campus_td/build/m02_archimesh.py
#   python blmcp_client.py render_m02         -> frame buildings + Cycles render -> previews/m02_archimesh.png
#   python blmcp_client.py "<raw code>"       -> execute arbitrary code (must set result=dict)

import socket
import json
import sys

HOST = "localhost"
PORT = 9876
BASE = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59"
M02 = BASE + r"/campus_td/build/m02_archimesh.py"
M03 = BASE + r"/campus_td/build/m03_interior.py"
M04 = BASE + r"/campus_td/build/m04_buildings.py"
M05 = BASE + r"/campus_td/build/m05_site.py"
M06 = BASE + r"/campus_td/build/m06_lighting.py"
OUT_PNG = BASE + r"/campus_td/previews/m02_archimesh.png"
M03_PNG = BASE + r"/campus_td/previews/m03_interior.png"
M04_PNG = BASE + r"/campus_td/previews/m04_buildings.png"
M05_PNG = BASE + r"/campus_td/previews/m05_site.png"
M05B = BASE + r"/campus_td/build/m05b_refine.py"
M05B_PNG = BASE + r"/campus_td/previews/m05b_refine.png"
M06_PNG_DAY = BASE + r"/campus_td/previews/m06_lighting_day.png"
M06_PNG_DUSK = BASE + r"/campus_td/previews/m06_lighting_dusk.png"
M07 = BASE + r"/campus_td/build/m07_towerdefense.py"
M07_PNG = BASE + r"/campus_td/previews/m07_towerdefense_day.png"
M07_PNG_DUSK = BASE + r"/campus_td/previews/m07_towerdefense_dusk.png"
M08 = BASE + r"/campus_td/build/m08_interior.py"
M08_PNG_LIB = BASE + r"/campus_td/previews/m08_library_interior_day.png"
M08_PNG_GYM = BASE + r"/campus_td/previews/m08_gym_court_day.png"
M08B = BASE + r"/campus_td/build/m08b_light.py"
M08B_PNG_LIB = BASE + r"/campus_td/previews/m08b_library_interior_day.png"
M08B_PNG_GYM = BASE + r"/campus_td/previews/m08b_gym_court_day.png"
M08C = BASE + r"/campus_td/build/m08c_upper.py"
M08C_PNG = BASE + r"/campus_td/previews/m08c_upper_floors.png"
M08D = BASE + r"/campus_td/build/m08d_upperlight.py"
M08D_PNG = BASE + r"/campus_td/previews/m08d_upper_light.png"
M08E = BASE + r"/campus_td/build/m08e_books.py"
M08E_PNG = BASE + r"/campus_td/previews/m08e_library_books.png"
M10B = BASE + r"/campus_td/build/m10b_slots.py"
M10B_PNG = BASE + r"/campus_td/previews/m10b_slots.png"
M10D = BASE + r"/campus_td/build/m10d_enemies.py"
M10D_CODE = 'exec(compile(open(r"%s").read(), "m10d", "exec"))' % M10D
M14 = BASE + r"/campus_td/build/m14_plaque.py"
M15 = BASE + r"/campus_td/build/m15_stairs.py"
M15_PNG = BASE + r"/campus_td/previews/m15_stairs.png"
M15_CODE = 'exec(compile(open(r"%s").read(), "m15", "exec"))' % M15
M16 = BASE + r"/campus_td/build/m16_crenellations.py"
M16_PNG = BASE + r"/campus_td/previews/m16_crenellations.png"
M16_CODE = 'exec(compile(open(r"%s").read(), "m16", "exec"))' % M16
M14_PNG = BASE + r"/campus_td/previews/m14_plaque.png"
M14_CODE = 'exec(compile(open(r"%s").read(), "m14", "exec"))' % M14
M13 = BASE + r"/campus_td/build/m13_groundfix.py"
M13_CODE = 'exec(compile(open(r"%s").read(), "m13", "exec"))' % M13
M12 = BASE + r"/campus_td/build/m12_uppercheck.py"
M12_CODE = 'exec(compile(open(r"%s").read(), "m12", "exec"))' % M12
M11 = BASE + r"/campus_td/build/m11_masterplan.py"
M11_PNG = BASE + r"/campus_td/previews/m11_masterplan.png"
M11_CODE = 'exec(compile(open(r"%s").read(), "m11", "exec"))' % M11
M09 = BASE + r"/campus_td/build/m09_walkthrough.py"
M09_MP4 = BASE + r"/campus_td/previews/m09_walkthrough.mp4"
M09_FRAMES = BASE + r"/campus_td/previews/m09_frames/m09_"


def send_execute(code: str, strict_json: bool = False, timeout: float = 300.0) -> dict:
    req = json.dumps({"type": "execute", "code": code, "strict_json": strict_json}).encode("utf-8") + b"\0"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        sock.connect((HOST, PORT))
        sock.sendall(req)
        buf = bytearray()
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            buf.extend(chunk)
            if b"\0" in buf:
                break
    line, _, _ = buf.partition(b"\0")
    if not line:
        raise RuntimeError("empty response from Blender")
    return json.loads(line.decode("utf-8"))


M02_CODE = 'exec(compile(open(r"%s").read(), "m02", "exec"))' % M02
M03_CODE = 'exec(compile(open(r"%s").read(), "m03", "exec"))' % M03
M04_CODE = 'exec(compile(open(r"%s").read(), "m04", "exec"))' % M04
M05_CODE = 'exec(compile(open(r"%s").read(), "m05", "exec"))' % M05
M05B_CODE = 'exec(compile(open(r"%s").read(), "m05b", "exec"))' % M05B
M06_CODE = 'exec(compile(open(r"%s").read(), "m06", "exec"))' % M06
M07_CODE = 'exec(compile(open(r"%s").read(), "m07", "exec"))' % M07
M08_CODE = 'exec(compile(open(r"%s").read(), "m08", "exec"))' % M08
M08B_CODE = 'exec(compile(open(r"%s").read(), "m08b", "exec"))' % M08B
M08C_CODE = 'exec(compile(open(r"%s").read(), "m08c", "exec"))' % M08C
M08D_CODE = 'exec(compile(open(r"%s").read(), "m08d", "exec"))' % M08D
M08E_CODE = 'exec(compile(open(r"%s").read(), "m08e", "exec"))' % M08E
M10B_CODE = 'exec(compile(open(r"%s").read(), "m10b", "exec"))' % M10B
M09_CODE = 'exec(compile(open(r"%s").read(), "m09", "exec"))' % M09

RENDER_CODE = r'''
import bpy
sc = bpy.context.scene
targets = [o for o in bpy.data.objects if o.name in ("Bldg_Teach", "Bldg_Lab")]
if not targets:
    targets = [o for o in bpy.data.objects if o.type == "MESH"]
cam = bpy.data.objects.get("Camera")
if cam is None:
    bpy.ops.object.camera_add(location=(0, 0, 0))
    cam = bpy.context.active_object
    cam.name = "Camera"
sc.camera = cam
view3d = None
for area in bpy.context.screen.areas:
    if area.type == "VIEW_3D":
        view3d = area
        break
for o in bpy.data.objects:
    o.select_set(False)
for o in targets:
    o.select_set(True)
bpy.context.view_layer.objects.active = targets[0] if targets else None
if view3d is not None:
    region = next((r for r in view3d.regions if r.type == "WINDOW"), None)
    if region is not None:
        with bpy.context.temp_override(area=view3d, region=region):
            bpy.ops.view3d.view_selected()
            bpy.ops.view3d.camera_to_view()
sc.render.engine = "CYCLES"
try:
    sc.cycles.device = "CPU"
except Exception:
    pass
sc.cycles.samples = 64
sc.render.resolution_x = 1600
sc.render.resolution_y = 900
sc.render.resolution_percentage = 100
sc.render.filepath = r"%s"
bpy.ops.render.render(write_still=True)
result = {"rendered": sc.render.filepath, "engine": sc.render.engine, "objects": len(bpy.data.objects)}
''' % OUT_PNG

RENDER_M04_CODE = r'''
import bpy, mathutils
sc = bpy.context.scene
# 框选 M4 五栋新建筑（行政楼/宿舍楼/体育馆/食堂/图书馆），从前区入口外看向校园
targets = [o for o in bpy.data.objects if o.name.startswith(("Bldg_Admin", "Bldg_Dorm", "Bldg_Gym", "Bldg_Canteen", "Bldg_Library"))]
if not targets:
    targets = [o for o in bpy.data.objects if o.type == "MESH"]
cam = bpy.data.objects.get("Camera")
if cam is None:
    bpy.ops.object.camera_add(location=(0, -50, 20))
    cam = bpy.context.active_object
    cam.name = "Camera"
hidden_preview = []
for o in bpy.data.objects:
    if o.name.startswith("Mat_Preview_"):
        hidden_preview.append((o, o.hide_render))
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
for o, was in hidden_preview:
    o.hide_render = was
result = {"rendered": sc.render.filepath, "engine": sc.render.engine, "objects": len(bpy.data.objects)}
''' % M04_PNG

RENDER_M05_CODE = r'''
import bpy, mathutils
sc = bpy.context.scene
# 校园全景：从南向俯视，框进门牌坊 + 前庭院 + 五栋楼 + 天空（Sky Texture 背景）
targets = [o for o in bpy.data.objects if o.name.startswith(("M5_", "Bldg_", "Ground", "Road", "Tower"))]
if not targets:
    targets = [o for o in bpy.data.objects if o.type == "MESH"]
cam = bpy.data.objects.get("Camera")
if cam is None:
    bpy.ops.object.camera_add(location=(0, -60, 30))
    cam = bpy.context.active_object
    cam.name = "Camera"
hidden_preview = []
for o in bpy.data.objects:
    if o.name.startswith("Mat_Preview_") or o.name.startswith(("Furn_", "Int_", "Stair_")):
        hidden_preview.append((o, o.hide_render))
        o.hide_render = True
sc.camera = cam
cam.location = (-42.0, -68.0, 95.0)
target = mathutils.Vector((0.0, -3.0, 0.0))
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
sc.render.engine = "CYCLES"
try:
    sc.cycles.device = "CPU"
except Exception:
    pass
sc.cycles.samples = 128
sc.render.resolution_x = 1920
sc.render.resolution_y = 1080
sc.render.resolution_percentage = 100
sc.render.filepath = r"%s"
bpy.ops.render.render(write_still=True)
for o, was in hidden_preview:
    o.hide_render = was
result = {"rendered": sc.render.filepath, "engine": sc.render.engine, "objects": len(bpy.data.objects)}
''' % M05_PNG

RENDER_M05B_CODE = r'''
import bpy, mathutils
sc = bpy.context.scene
# M5 精修后全景：含 M5B_ 新树丛/压顶/嵌板；从南向俯视框进门牌坊+前庭院+五栋楼+天空
targets = [o for o in bpy.data.objects if o.name.startswith(("M5_", "M5B_", "Bldg_", "Ground", "Road", "Tower"))]
if not targets:
    targets = [o for o in bpy.data.objects if o.type == "MESH"]
cam = bpy.data.objects.get("Camera")
if cam is None:
    bpy.ops.object.camera_add(location=(0, -60, 30))
    cam = bpy.context.active_object
    cam.name = "Camera"
hidden = []
for o in bpy.data.objects:
    if o.name.startswith("Mat_Preview_") or o.name.startswith(("Furn_", "Int_", "Stair_")):
        hidden.append((o, o.hide_render))
        o.hide_render = True
sc.camera = cam
cam.location = (-42.0, -68.0, 95.0)
target = mathutils.Vector((0.0, -3.0, 0.0))
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
sc.render.engine = "CYCLES"
try:
    sc.cycles.device = "CPU"
except Exception:
    pass
sc.cycles.samples = 128
sc.render.resolution_x = 1920
sc.render.resolution_y = 1080
sc.render.resolution_percentage = 100
sc.render.filepath = r"%s"
bpy.ops.render.render(write_still=True)
for o, was in hidden:
    o.hide_render = was
result = {"rendered": sc.render.filepath, "engine": sc.render.engine, "objects": len(bpy.data.objects)}
''' % M05B_PNG

RENDER_DAY_BODY = r'''
import bpy, mathutils
sc = bpy.context.scene
cam = bpy.data.objects.get("Camera")
if cam is None:
    bpy.ops.object.camera_add(location=(-45.0, -65.0, 40.0))
    cam = bpy.context.active_object
    cam.name = "Camera"
hidden = []
for o in bpy.data.objects:
    if o.name.startswith("Mat_Preview_") or o.name.startswith(("Furn_", "Int_", "Stair_")):
        hidden.append((o, o.hide_render))
        o.hide_render = True
sc.camera = cam
# 白昼英雄 3/4 低角度：西南看向校园，凸显建筑体量
cam.location = (-48.0, -64.0, 34.0)
target = mathutils.Vector((0.0, -2.0, 7.0))
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
sc.render.engine = "CYCLES"
try:
    sc.cycles.device = "CPU"
except Exception:
    pass
sc.cycles.samples = 192
sc.render.resolution_x = 1920
sc.render.resolution_y = 1080
sc.render.resolution_percentage = 100
sc.render.filepath = r"%s"
bpy.ops.render.render(write_still=True)
for o, was in hidden:
    o.hide_render = was
result = {"rendered": sc.render.filepath, "engine": sc.render.engine, "objects": len(bpy.data.objects), "mode": "day"}
'''

RENDER_DUSK_BODY = r'''
import bpy, mathutils
sc = bpy.context.scene
cam = bpy.data.objects.get("Camera")
if cam is None:
    bpy.ops.object.camera_add(location=(0.0, -60.0, 30.0))
    cam = bpy.context.active_object
    cam.name = "Camera"
hidden = []
for o in bpy.data.objects:
    if o.name.startswith("Mat_Preview_") or o.name.startswith(("Furn_", "Int_", "Stair_")):
        hidden.append((o, o.hide_render))
        o.hide_render = True
sc.camera = cam
# 暮色鸟瞰：框进全校园 + 暮空
cam.location = (-42.0, -68.0, 95.0)
target = mathutils.Vector((0.0, -3.0, 0.0))
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
sc.render.engine = "CYCLES"
try:
    sc.cycles.device = "CPU"
except Exception:
    pass
sc.cycles.samples = 192
sc.render.resolution_x = 1920
sc.render.resolution_y = 1080
sc.render.resolution_percentage = 100
sc.render.filepath = r"%s"
bpy.ops.render.render(write_still=True)
for o, was in hidden:
    o.hide_render = was
result = {"rendered": sc.render.filepath, "engine": sc.render.engine, "objects": len(bpy.data.objects), "mode": "dusk"}
'''

RENDER_M06_CODE = (M06_CODE + "\nbuild_lighting('day')\n" + RENDER_DAY_BODY) % M06_PNG_DAY
RENDER_M06_DUSK_CODE = (M06_CODE + "\nbuild_lighting('dusk')\n" + RENDER_DUSK_BODY) % M06_PNG_DUSK

RENDER_TD_BODY = r'''
import bpy, mathutils
sc = bpy.context.scene
cam = bpy.data.objects.get("Camera")
if cam is None:
    bpy.ops.object.camera_add(location=(-50.0, -58.0, 48.0))
    cam = bpy.context.active_object
    cam.name = "Camera"
hidden = []
for o in bpy.data.objects:
    if o.name.startswith("Mat_Preview_") or o.name.startswith(("Furn_", "Int_", "Stair_")):
        hidden.append((o, o.hide_render))
        o.hide_render = True
sc.camera = cam
# 塔防英雄 3/4 俯角：框进 U 形路径 + 四角射程穹顶 + 类型信标
cam.location = (-52.0, -58.0, 48.0)
target = mathutils.Vector((0.0, -2.0, 6.0))
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
sc.render.engine = "CYCLES"
try:
    sc.cycles.device = "CPU"
except Exception:
    pass
sc.cycles.samples = 192
sc.render.resolution_x = 1920
sc.render.resolution_y = 1080
sc.render.resolution_percentage = 100
sc.render.filepath = r"%s"
bpy.ops.render.render(write_still=True)
for o, was in hidden:
    o.hide_render = was
result = {"rendered": sc.render.filepath, "engine": sc.render.engine, "objects": len(bpy.data.objects), "mode": "td"}
'''

RENDER_M07_CODE = (M06_CODE + "\nbuild_lighting('day')\n" + M07_CODE + "\nbuild_towerdefense()\nplace_enemies_at_frame(90)\nupdate_beams(90)\n" + RENDER_TD_BODY) % M07_PNG
RENDER_M07_DUSK_CODE = (M06_CODE + "\nbuild_lighting('dusk')\n" + M07_CODE + "\nbuild_towerdefense()\nplace_enemies_at_frame(90)\nupdate_beams(90)\n" + RENDER_TD_BODY) % M07_PNG_DUSK

# ---- M8 室内扩展：人视英雄镜头（验证"可进入"）----
# 图书馆阅览室：相机置于 +Y 内墙附近、人眼高 1.6m，看向 -Y 跨越书架与阅读桌
RENDER_M08_LIB_BODY = r'''
import bpy, mathutils
sc = bpy.context.scene
cam = bpy.data.objects.get("Camera")
if cam is None:
    bpy.ops.object.camera_add(location=(2.0, 4.0, 1.6))
    cam = bpy.context.active_object
    cam.name = "Camera"
hidden = []
for o in bpy.data.objects:
    if o.name.startswith("Mat_Preview_"):
        hidden.append((o, o.hide_render))
        o.hide_render = True
sc.camera = cam
# 南立面门洞(door at x=5)外侧，眼高 1.6m，看向 -y 跨越门洞进入阅览室
cam.location = (5.0, -10.0, 1.6)
target = mathutils.Vector((5.0, -3.0, 1.2))
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
sc.render.engine = "CYCLES"
try:
    sc.cycles.device = "CPU"
except Exception:
    pass
sc.cycles.samples = 128
sc.render.resolution_x = 1920
sc.render.resolution_y = 1080
sc.render.resolution_percentage = 100
sc.render.filepath = r"%s"
bpy.ops.render.render(write_still=True)
for o, was in hidden:
    o.hide_render = was
result = {"rendered": sc.render.filepath, "engine": sc.render.engine, "objects": len(bpy.data.objects), "mode": "m08_library", "cam": list(cam.location)}
'''

# 体育馆球场：相机置于 +Y 内墙、看向 -Y 跨越球场线+看台+篮板
RENDER_M08_GYM_BODY = r'''
import bpy, mathutils
sc = bpy.context.scene
cam = bpy.data.objects.get("Camera")
if cam is None:
    bpy.ops.object.camera_add(location=(15.0, -9.0, 1.6))
    cam = bpy.context.active_object
    cam.name = "Camera"
hidden = []
for o in bpy.data.objects:
    if o.name.startswith("Mat_Preview_"):
        hidden.append((o, o.hide_render))
        o.hide_render = True
sc.camera = cam
# 南立面门洞外侧（x=15, 门洞宽 3.6），观赛视角 2.5m，看向远端篮板
# 相机必须落在 46m 地面内（y>-23）且 M6 天穹球内（距原点<~30m），y=-22 安全
cam.location = (15.0, -22.0, 2.5)
target = mathutils.Vector((15.0, -15.0, 1.0))
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
sc.render.engine = "CYCLES"
try:
    sc.cycles.device = "CPU"
except Exception:
    pass
sc.cycles.samples = 128
sc.render.resolution_x = 1920
sc.render.resolution_y = 1080
sc.render.resolution_percentage = 100
sc.render.filepath = r"%s"
bpy.ops.render.render(write_still=True)
for o, was in hidden:
    o.hide_render = was
result = {"rendered": sc.render.filepath, "engine": sc.render.engine, "objects": len(bpy.data.objects), "mode": "m08_gym", "cam": list(cam.location)}
'''

RENDER_M08_LIB_CODE = (M06_CODE + "\nbuild_lighting('day')\n" + M08_CODE + "\nbuild_interiors()\n" + RENDER_M08_LIB_BODY) % M08_PNG_LIB
RENDER_M08_GYM_CODE = (M06_CODE + "\nbuild_lighting('day')\n" + M08_CODE + "\nbuild_interiors()\n" + RENDER_M08_GYM_BODY) % M08_PNG_GYM
# M8B：在 M8 重建后追加补光精修（energy/size 提亮），再渲染人视英雄镜头验证
RENDER_M08B_LIB_CODE = (M06_CODE + "\nbuild_lighting('day')\n" + M08_CODE + "\nbuild_interiors()\n" + M08B_CODE + "\ntune()\n" + RENDER_M08_LIB_BODY) % M08B_PNG_LIB
RENDER_M08B_GYM_CODE = (M06_CODE + "\nbuild_lighting('day')\n" + M08_CODE + "\nbuild_interiors()\n" + M08B_CODE + "\ntune()\n" + RENDER_M08_GYM_BODY) % M08B_PNG_GYM

# ---- M8C 上层重复房间：前排西南中景（验证楼板/楼梯/上层家具透过 ribbon 窗可读）----
RENDER_M08C_BODY = r'''
import bpy, mathutils
sc = bpy.context.scene
cam = bpy.data.objects.get("Camera")
if cam is None:
    bpy.ops.object.camera_add(location=(-34.0, -46.0, 20.0))
    cam = bpy.context.active_object
    cam.name = "Camera"
hidden = []
for o in bpy.data.objects:
    if o.name.startswith("Mat_Preview_"):
        hidden.append((o, o.hide_render))
        o.hide_render = True
sc.camera = cam
# 西南中景：正对前排 Admin/Dorm，略仰角读出多层 ribbon 窗 + 楼板分层 + 楼梯井
cam.location = (-34.0, -46.0, 20.0)
target = mathutils.Vector((-2.0, -14.0, 10.0))
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
sc.render.engine = "CYCLES"
try:
    sc.cycles.device = "CPU"
except Exception:
    pass
sc.cycles.samples = 128
sc.render.resolution_x = 1920
sc.render.resolution_y = 1080
sc.render.resolution_percentage = 100
sc.render.filepath = r"%s"
bpy.ops.render.render(write_still=True)
for o, was in hidden:
    o.hide_render = was
result = {"rendered": sc.render.filepath, "engine": sc.render.engine, "objects": len(bpy.data.objects), "mode": "m08c_upper", "cam": list(cam.location)}
'''

RENDER_M08C_CODE = (M06_CODE + "\nbuild_lighting('day')\n" + M08_CODE + "\nbuild_interiors()\n" + M08B_CODE + "\ntune()\n" + M08C_CODE + "\n" + RENDER_M08C_BODY) % M08C_PNG

# ---- M8D 上层补光：与 M8C 同机位同构图（cam(-34,-46,20)->(-2,-14,10)），便于前后对比 ----
# 场景灯光由 5 盏增至 17 盏 AREA，Cycles CPU 单采样成本显著上升 →
# 降采样 64s + 1600x900 控制耗时，仍足够判读上层是否点亮。
RENDER_M08D_BODY = r'''
import bpy, mathutils
sc = bpy.context.scene
cam = bpy.data.objects.get("Camera")
if cam is None:
    bpy.ops.object.camera_add(location=(-34.0, -46.0, 20.0))
    cam = bpy.context.active_object
    cam.name = "Camera"
hidden = []
for o in bpy.data.objects:
    if o.name.startswith("Mat_Preview_"):
        hidden.append((o, o.hide_render))
        o.hide_render = True
sc.camera = cam
cam.location = (-34.0, -46.0, 20.0)
target = mathutils.Vector((-2.0, -14.0, 10.0))
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
sc.render.engine = "CYCLES"
try:
    sc.cycles.device = "CPU"
except Exception:
    pass
sc.cycles.samples = 64
sc.render.resolution_x = 1600
sc.render.resolution_y = 900
sc.render.resolution_percentage = 100
sc.render.filepath = r"%s"
bpy.ops.render.render(write_still=True)
for o, was in hidden:
    o.hide_render = was
result = {"rendered": sc.render.filepath, "engine": sc.render.engine, "objects": len(bpy.data.objects), "mode": "m08d_upper_light", "cam": list(cam.location), "lights": len([o for o in bpy.data.objects if o.type == "LIGHT"])}
'''

RENDER_M08D_CODE = (M06_CODE + "\nbuild_lighting('day')\n" + M08_CODE + "\nbuild_interiors()\n" + M08B_CODE + "\ntune()\n" + M08C_CODE + "\n" + M08D_CODE + "\n" + RENDER_M08D_BODY) % M08D_PNG

# ---- M8E 书架书条：室内侧向机位对准右侧书架(x=8.3) ----
# 注意：M8/M8B 的图书馆机位 cam(5,-10,1.6)->(5,-3,1.2) 视锥半宽约 2.5m，
#   而书架在 x=-4.3 / 8.3，均在画面外 → 必须用专用机位才能拍到书条。
#   相机置于室内 (5,-6,1.5)（在门洞 x=5 进深之内、x=8.3 的南墙外侧无墙），侧看右书架。
RENDER_M08E_BODY = r'''
import bpy, mathutils
sc = bpy.context.scene
cam = bpy.data.objects.get("Camera")
if cam is None:
    bpy.ops.object.camera_add(location=(5.0, -6.0, 1.5))
    cam = bpy.context.active_object
    cam.name = "Camera"
hidden = []
for o in bpy.data.objects:
    if o.name.startswith("Mat_Preview_"):
        hidden.append((o, o.hide_render))
        o.hide_render = True
sc.camera = cam
cam.data.lens = 35.0
cam.location = (5.0, -6.0, 1.5)
target = mathutils.Vector((8.3, -3.5, 1.1))
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
result = {"rendered": sc.render.filepath, "engine": sc.render.engine, "objects": len(bpy.data.objects), "mode": "m08e_books", "cam": list(cam.location)}
'''

RENDER_M08E_CODE = (M06_CODE + "\nbuild_lighting('day')\n" + M08_CODE + "\nbuild_interiors()\n" + M08B_CODE + "\ntune()\n" + M08C_CODE + "\n" + M08D_CODE + "\n" + M08E_CODE + "\n" + RENDER_M08E_BODY) % M08E_PNG

# ---- M11 总平重排：96m 场地鸟瞰（Cycles CPU）----
# 机位由 m11_masterplan.py 的 build_cam() 建好（M11_CamAerial），这里只负责出图。
RENDER_M11_BODY = r'''
import bpy, mathutils
sc = bpy.context.scene
cam = bpy.data.objects.get("M11_CamAerial")
if cam is None:
    bpy.ops.object.camera_add(location=(-99.0, -99.0, 140.0))
    cam = bpy.context.active_object
    cam.name = "M11_CamAerial"
    target = mathutils.Vector((0.0, 0.0, 0.0))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
hidden = []
for o in bpy.data.objects:
    if o.name.startswith("Mat_Preview_"):
        hidden.append((o, o.hide_render))
        o.hide_render = True
sc.camera = cam
cam.data.lens = 35.0
sc.render.engine = "CYCLES"
try:
    sc.cycles.device = "CPU"
except Exception:
    pass
sc.cycles.samples = 96
sc.render.resolution_x = 1920
sc.render.resolution_y = 1080
sc.render.resolution_percentage = 100
sc.render.filepath = r"%s"
bpy.ops.render.render(write_still=True)
for o, was in hidden:
    o.hide_render = was
result = {"rendered": sc.render.filepath, "engine": sc.render.engine, "objects": len(bpy.data.objects), "mode": "m11_masterplan", "cam": list(cam.location)}
'''

RENDER_M11_CODE = (M06_CODE + "\nbuild_lighting('day')\n" + M11_CODE + "\n" + RENDER_M11_BODY) % M11_PNG

# ---- M14 校门匾文特写：M6 光照 + M11 总平(建校门) + M14 匾文，M14_Cam 正对匾面 ----
# 机位由 m14_plaque.py 的 build_cam() 建好（M14_Cam，y=-62 / 70mm）。
RENDER_M14_BODY = r'''
import bpy, mathutils
sc = bpy.context.scene
cam = bpy.data.objects.get("M14_Cam")
if cam is None:
    plaque = bpy.data.objects.get("M11_GatePlaque")
    cz = plaque.location.z if plaque is not None else 6.6
    bpy.ops.object.camera_add(location=(0.0, -62.0, cz))
    cam = bpy.context.active_object
    cam.name = "M14_Cam"
    target = mathutils.Vector((0.0, -48.0, cz))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
hidden = []
for o in bpy.data.objects:
    if o.name.startswith("Mat_Preview_"):
        hidden.append((o, o.hide_render))
        o.hide_render = True
sc.camera = cam
cam.data.lens = 70.0
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
txt = bpy.data.objects.get("M14_Text")
result = {"rendered": sc.render.filepath, "engine": sc.render.engine,
          "objects": len(bpy.data.objects), "mode": "m14_plaque",
          "cam": list(cam.location),
          "text_present": txt is not None,
          "text_body": (txt.data.body if txt is not None else None)}
'''

RENDER_M14_CODE = (M06_CODE + "\nbuild_lighting('day')\n" + M11_CODE + "\n" + M14_CODE + "\n" + RENDER_M14_BODY) % M14_PNG

# ---- M15 楼梯踏步特写 ----
# ⚠ 顺序铁律：M15 必须排在 M11 **之后**。M11 的 owner() 不认识 M15_* 前缀，
#   不会挪动它们；若 M15 先跑，读到的还是 M11 之前的旧坐标，楼梯会错位。
RENDER_M15_BODY = r'''
import bpy, mathutils
sc = bpy.context.scene
cam = bpy.data.objects.get("M15_Cam")
if cam is None:
    o = bpy.data.objects.get("M15_Dorm_1_Steps")
    if o is None:
        result = {"error": "M15_Dorm_1_Steps not found"}
    else:
        bb = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
        cx = (min(v.x for v in bb) + max(v.x for v in bb)) * 0.5
        cy = (min(v.y for v in bb) + max(v.y for v in bb)) * 0.5
        cz = (min(v.z for v in bb) + max(v.z for v in bb)) * 0.5
        bpy.ops.object.camera_add(location=(cx + 4.2, cy - 1.0, cz + 1.4))
        cam = bpy.context.active_object
        cam.name = "M15_Cam"
        target = mathutils.Vector((cx, cy, cz))
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
hidden = []
for o in bpy.data.objects:
    if o.name.startswith("Mat_Preview_"):
        hidden.append((o, o.hide_render))
        o.hide_render = True
sc.camera = cam
cam.data.lens = 28.0
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
n_steps = sum(1 for o in bpy.data.objects if o.name.endswith("_Steps"))
result = {"rendered": sc.render.filepath, "engine": sc.render.engine,
          "objects": len(bpy.data.objects), "mode": "m15_stairs",
          "cam": list(cam.location), "step_objects": n_steps}
'''

RENDER_M15_CODE = (M06_CODE + "\nbuild_lighting('day')\n" + M08_CODE + "\nbuild_interiors()\n" + M08B_CODE + "\ntune()\n" + M08C_CODE + "\n" + M08D_CODE + "\n" + M08E_CODE + "\n" + M11_CODE + "\n" + M15_CODE + "\n" + RENDER_M15_BODY) % M15_PNG

# ---- M9 导航导出 + 整合：脚本化漫游视频（EEVEE Next + FFmpeg 直出 MP4）----
# 整合 M6 光照(白昼) + M8 室内 + M7 塔防层，相机沿 M9 关键帧漫游 120 帧(4s @30fps)。
RENDER_M09_BODY = r'''
import bpy, mathutils, os
sc = bpy.context.scene
cam = bpy.data.objects.get("M9_Cam")
if cam is None:
    bpy.ops.object.camera_add(location=(0.0, -22.0, 2.0))
    cam = bpy.context.active_object
    cam.name = "M9_Cam"
    cam.data.lens = 35.0
sc.camera = cam
# 隐藏 M1 预览球，避免远景出现巨大白球
hidden = []
for o in bpy.data.objects:
    if o.name.startswith("Mat_Preview_"):
        hidden.append((o, o.hide_render))
        o.hide_render = True
# EEVEE：实时级速度，足以支撑 120 帧漫游；AgX 色调映射仍生效，M6 场景内辉光壳保塔光
sc.render.engine = "BLENDER_EEVEE"
try:
    sc.eevee.taa_render_samples = 48
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
# 本 Blender 5.2 构建仅暴露图像格式（无 FFmpeg 视频写入）→ 渲 PNG 序列，外部 imageio-ffmpeg 合成 MP4
seq_path = r"%s"
os.makedirs(os.path.dirname(seq_path), exist_ok=True)
sc.render.image_settings.file_format = "PNG"
sc.render.filepath = seq_path
bpy.ops.render.render(animation=True, write_still=True)
for o, was in hidden:
    o.hide_render = was
result = {"rendered_seq": sc.render.filepath, "engine": sc.render.engine, "frames": sc.frame_end, "fps": sc.render.fps, "objects": len(bpy.data.objects), "mode": "m09_walkthrough"}
'''

RENDER_M09_CODE = (M06_CODE + "\nbuild_lighting('day')\n" + M08_CODE + "\nbuild_interiors()\n" + M07_CODE + "\nbuild_towerdefense()\nplace_enemies_at_frame(90)\nupdate_beams(90)\n" + M09_CODE + "\nbuild_walkthrough()\n" + RENDER_M09_BODY) % M09_FRAMES

RENDER_M03_CODE = r'''
import bpy, mathutils
sc = bpy.context.scene
# 框选教学楼外壳 + 室内对象，从正门(+Y)外略高处看入室内
targets = [o for o in bpy.data.objects if o.name.startswith(("Bldg_Teach", "Int_Teach_", "Stair_Teach_", "Furn_Teach_"))]
    targets = [o for o in bpy.data.objects if o.type == "MESH"]
cam = bpy.data.objects.get("Camera")
if cam is None:
    bpy.ops.object.camera_add(location=(-18.0, 42.0, 4.0))
    cam = bpy.context.active_object
    cam.name = "Camera"
# 临时隐藏 M1 预览球，避免远景出现巨大白球干扰
hidden_preview = []
for o in bpy.data.objects:
    if o.name.startswith("Mat_Preview_"):
        hidden_preview.append((o, o.hide_render))
        o.hide_render = True

sc.camera = cam
cam.location = (-35.0, 8.0, 1.6)
target = mathutils.Vector((-15.0, 12.0, 1.5))
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
# 恢复 M1 预览球渲染可见性
for o, was in hidden_preview:
    o.hide_render = was

result = {"rendered": sc.render.filepath, "engine": sc.render.engine, "objects": len(bpy.data.objects)}
''' % M03_PNG


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "objects"
    if action == "objects":
        code = 'import bpy\nresult={"count":len(bpy.data.objects),"names":[o.name for o in bpy.data.objects]}'
        timeout = 30.0
    elif action == "m02":
        code = M02_CODE
        timeout = 180.0
    elif action == "m03":
        code = M03_CODE
        timeout = 180.0
    elif action == "m04":
        code = M04_CODE
        timeout = 180.0
    elif action == "render_m04":
        code = RENDER_M04_CODE
        timeout = 320.0
    elif action == "m05":
        code = M05_CODE
        timeout = 180.0
    elif action == "render_m05":
        code = RENDER_M05_CODE
        timeout = 320.0
    elif action == "m05_refine":
        code = M05B_CODE
        timeout = 180.0
    elif action == "render_m05_refine":
        code = RENDER_M05B_CODE
        timeout = 420.0
    elif action == "m06":
        code = M06_CODE + "\nbuild_lighting('day')"
        timeout = 180.0
    elif action == "render_m06":
        code = RENDER_M06_CODE
        timeout = 420.0
    elif action == "render_m06_dusk":
        code = RENDER_M06_DUSK_CODE
        timeout = 420.0
    elif action == "m07":
        code = M07_CODE + "\nbuild_towerdefense()"
        timeout = 180.0
    elif action == "render_m07":
        code = RENDER_M07_CODE
        timeout = 420.0
    elif action == "render_m07_dusk":
        code = RENDER_M07_DUSK_CODE
        timeout = 420.0
    elif action == "m08":
        code = M08_CODE + "\nbuild_interiors()"
        timeout = 180.0
    elif action == "render_m08":
        code = RENDER_M08_LIB_CODE
        timeout = 420.0
    elif action == "render_m08_gym":
        code = RENDER_M08_GYM_CODE
        timeout = 420.0
    elif action == "m08b":
        code = M08B_CODE
        timeout = 120.0
    elif action == "render_m08b":
        code = RENDER_M08B_LIB_CODE
        timeout = 420.0
    elif action == "render_m08b_gym":
        code = RENDER_M08B_GYM_CODE
        timeout = 420.0
    elif action == "m08c":
        code = M08C_CODE
        timeout = 180.0
    elif action == "render_m08c":
        code = RENDER_M08C_CODE
        timeout = 540.0
    elif action == "m08d":
        code = M08D_CODE
        timeout = 120.0
    elif action == "render_m08d":
        code = RENDER_M08D_CODE
        timeout = 600.0
    elif action == "m08e":
        code = M08E_CODE
        timeout = 180.0
    elif action == "render_m08e":
        code = RENDER_M08E_CODE
        timeout = 600.0
    elif action == "m10b":
        code = M10B_CODE + "\nbuild_slots()"
        timeout = 180.0
    elif action == "m10d":
        # 脚本内部自带 Cycles 渲染（1600x900 / 96 samples），超时要给足
        code = M10D_CODE
        timeout = 900.0
    elif action == "m13":
        # 三档能量扫描，各一张 1280x720 @64 samples
        code = M13_CODE + "\nresult = sweep((240.0, 340.0, 460.0))"
        timeout = 900.0
    elif action == "m13w":
        # World 环境光扫描，同样三张
        code = M13_CODE + "\nresult = sweep_world((1.0, 1.6, 2.2))"
        timeout = 900.0
    elif action == "m12cams":
        code = M12_CODE + "\nresult = build_cams()"
        timeout = 120.0
    elif action == "m12_upper":
        code = M12_CODE + "\nresult = render_shot('upper')"
        timeout = 900.0
    elif action == "m12_ground":
        code = M12_CODE + "\nresult = render_shot('ground')"
        timeout = 900.0
    elif action == "m11":
        code = M11_CODE
        timeout = 240.0
    elif action == "render_m11":
        code = RENDER_M11_CODE
        timeout = 600.0
    elif action == "m14":
        # 只建模不渲染：建匾文 + 石框 + 特写机位
        code = M14_CODE
        timeout = 240.0
    elif action == "render_m14":
        # 全流程重建（M6 光照 + M11 总平/校门 + M14 匾文）再出图，1600x900 @96
        code = RENDER_M14_CODE
        timeout = 900.0
    elif action == "m15":
        # 只建模不渲染：12 段斜板楼梯 -> Array 真实踏步
        code = M15_CODE
        timeout = 240.0
    elif action == "render_m15":
        # 全链条重建，M15 排在 M11 之后（顺序铁律），1600x900 @96
        code = RENDER_M15_CODE
        timeout = 900.0
    elif action == "m16":
        # 只建模不渲染：M11 围墙顶加垛口 merlon + M16_Cam
        code = M16_CODE
        timeout = 240.0
    elif action == "render_m16":
        # 确保白昼光照 + 用 M16_Cam 出图（1600x900 @128），见 _render_m16.py
        code = 'exec(compile(open(r"%s").read(), "r", "exec"))' % (BASE + r"/campus_td/build/_render_m16.py")
        timeout = 540.0
    elif action == "m09":
        code = M09_CODE + "\nbuild_walkthrough()"
        timeout = 180.0
    elif action == "render_m09":
        code = RENDER_M09_CODE
        timeout = 1800.0
    elif action == "render_m03":
        code = RENDER_M03_CODE
        timeout = 320.0
    elif action == "render_m02":
        code = RENDER_CODE
        timeout = 300.0
    elif action == "status":
        code = 'import bpy\nresult={"engine":bpy.context.scene.render.engine,"samples":getattr(bpy.context.scene.cycles,"samples",None),"objs":len(bpy.data.objects),"m2_present":any(o.name in ("Bldg_Teach","Bldg_Lab") for o in bpy.data.objects)}'
        timeout = 30.0
    else:
        code = action
        timeout = 120.0
    resp = send_execute(code, strict_json=False, timeout=timeout)
    print(json.dumps(resp, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
