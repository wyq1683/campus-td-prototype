# -*- coding: utf-8 -*-
"""
M52 · 校门卫室（Gate Guardhouse · 校园生活细节）
==========================================================================
项目已收官（M0–M51 ✅）。按「无未完成里程碑时自行增加改进项」新增 M52：
在大门（南墙校门洞）内侧东侧加一座**门卫室（保安亭）**——中国高中最典型的
校门设施，此前缺失。让"有人值守"的校园感更完整，与 M14 校门匾文 / M37 校旗 /
M43 路灯 / M48 长椅垃圾桶 / M49 宣传栏 / M50 自行车道 / M51 花坛绿篱 共同构成
可居住的校园生活带。

为什么做这个：
  - 校门是校园的"脸面"，门卫室是校门的标志性附属建筑；原型里只有匾文+旗杆，
    缺一个能让人一眼认出"这里是校门"的小房子。
  - 自成一体、零破坏其它物体：仅新建 M52_ 前缀物体，坐标全部从场景当前几何
    动态读取（校门由 M11_GatePlaque 定位，不硬编码）。

设计（原型级，无 Boolean、无 mode_set，全 box 面板拼装，铁律安全）：
  - 平面 3.2×3.2m、高 3.0m 的小房子；门朝南（面向校门/校外，d=(0,-1,0)，
    用 PLAN.md M44 验证过的右手系旋转 → 文字不镜像）。
  - 前墙(-y)留真实门洞（左板+右板+门楣，中间 1.0×2.1m 门洞）+ 门扇(木) +
    右板嵌玻璃窗(自发光玻璃，阴影面可读) + 门楣上方 CJK 招牌「门卫室」(pick_font
    自检 SimHei 通过，Emission 0.35 保阴影面可读)。
  - 后墙/左右墙实心；平屋顶(带 0.2m 出檐)；地面薄板。
  - 复用既有 PBR_Concrete / PBR_Wood（避免 M18 提过的"重建材质丢槽"）；
    新建 M52_Glass / M52_SignBoard / M52_SignText 仅本里程碑使用。

坐标（M11 之后禁止硬编码）：
  - 校门中心 ← 读 M11_GatePlaque（兜底 (0,-48)）。
  - 门卫室中心 = 校门中心 + ( +12 , +8 )：东偏 12m（避开校门洞 x∈[-8,8] 与旗杆
    x=-3）、内退 8m（y=-40，距南墙 8m，留足取景空间且不与任何楼体重叠）。
  - 门朝 -y（南、向校门），相机站门卫室南侧(y=-45)、校门墙(y=-48)在其身后，不挡。

避坑（沿用 PLAN.md + M43..M51 经验）：
  - 顶层执行：MCP 用 exec(compile(open().read()))，逻辑不包 main()。
  - 不调 mode_set；全部 bmesh / primitive 直建 + 旋转矩阵，物体 scale 保持 1。
  - 删旧物体先取 nm=o.name 再 remove（防 StructRNA ReferenceError）。
  - 幂等 + 前缀隔离：只清 M52_，绝不 select_all+delete。
  - Blender 5.2 锥/柱用 radius1/radius2；Principled 输入名 Emission Color /
    Emission Strength / Transmission Weight（旧 Transmission 改 Transmission Weight）。
  - CJK 字体必须量实际字形尺寸（pick_font 自检），否则出空匾。
"""
import bpy
import bmesh
import os
import math
from mathutils import Vector, Matrix

PREFIX = "M52_"
PREVIEW_DIR = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/previews"
FONT_CANDIDATES = [
    r"C:/Windows/Fonts/simhei.ttf",
    r"C:/Windows/Fonts/Dengb.ttf",
    r"C:/Windows/Fonts/msyhbd.ttc",
    r"C:/Windows/Fonts/simsun.ttc",
]
FONT_H_MIN = 0.55
FONT_W_MIN = 0.55
SIGN_TEXT = "门卫室"
TEXT_H = 0.5            # 目标字高（m）
BOARD_T = 0.05          # 招牌底板厚（m）
OUT_OFF = 0.06          # 招牌距墙外退（m）


# ---------------------------------------------------------------- 工具
def aabb(o):
    cs = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return [min(c.x for c in cs), max(c.x for c in cs),
            min(c.y for c in cs), max(c.y for c in cs),
            min(c.z for c in cs), max(c.z for c in cs)]


def clear_old():
    n = 0
    for o in list(bpy.data.objects):
        if o.name.startswith(PREFIX):
            nm = o.name
            bpy.data.objects.remove(o, do_unlink=True)
            n += 1
    for me in list(bpy.data.meshes):
        if me.name.startswith(PREFIX):
            bpy.data.meshes.remove(me)
    for m in list(bpy.data.materials):
        if m.name.startswith(PREFIX):
            bpy.data.materials.remove(m)
    return n


def get_mat(name, color, metal=0.0, rough=0.8, emit=0.0):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is not None:
            bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
            bsdf.inputs["Metallic"].default_value = metal
            bsdf.inputs["Roughness"].default_value = rough
            if emit > 0.0 and "Emission Strength" in bsdf.inputs:
                bsdf.inputs["Emission Strength"].default_value = emit
    return m


def get_glass():
    name = PREFIX + "Glass"
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is not None:
            bsdf.inputs["Base Color"].default_value = (0.80, 0.86, 0.92, 1.0)
            bsdf.inputs["Metallic"].default_value = 0.0
            bsdf.inputs["Roughness"].default_value = 0.08
            if "Transmission Weight" in bsdf.inputs:
                bsdf.inputs["Transmission Weight"].default_value = 0.9
            elif "Transmission" in bsdf.inputs:
                bsdf.inputs["Transmission"].default_value = 0.9
            if "IOR" in bsdf.inputs:
                bsdf.inputs["IOR"].default_value = 1.45
    return m


def add_box(name, cx, cy, cz, sx, sy, sz, mat):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.transform(Matrix.Diagonal((sx, sy, sz, 1.0)))
    bm.transform(Matrix.Translation((cx, cy, cz)))
    me = bpy.data.meshes.new(PREFIX + name + "Mesh")
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(PREFIX + name, me)
    o.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(o)
    return o


def pick_font_once(text):
    tried = []
    n = max(1, len(text))
    for p in FONT_CANDIDATES:
        try:
            f = bpy.data.fonts.load(p)
        except Exception as e:
            tried.append({"file": p.split("\\")[-1], "ok": False, "err": str(e)[:60]})
            continue
        bpy.ops.object.text_add(location=(0.0, 0.0, -9999.0))
        o = bpy.context.active_object
        o.data.body = text
        o.data.font = f
        o.data.size = 1.0
        o.data.align_x = "CENTER"
        bpy.context.view_layer.update()
        h_unit, w_unit = o.dimensions.y, o.dimensions.x
        bpy.data.objects.remove(o, do_unlink=True)
        ok = (h_unit >= FONT_H_MIN) and (w_unit >= n * FONT_W_MIN)
        tried.append({"file": p.split("\\")[-1], "ok": True,
                      "h": round(h_unit, 3), "w": round(w_unit, 3), "pass": bool(ok)})
        if ok:
            return f, h_unit, w_unit, tried
    return None, 0.0, 0.0, tried


# ---------------------------------------------------------------- 主构建
n_removed = clear_old()
CONC = bpy.data.materials.get("PBR_Concrete") or get_mat(PREFIX + "Concrete", (0.62, 0.62, 0.60), 0.0, 0.85)
WOOD = bpy.data.materials.get("PBR_Wood") or get_mat(PREFIX + "Wood", (0.40, 0.27, 0.15), 0.0, 0.6)
GLASS = get_glass()
SIGN_BOARD = get_mat(PREFIX + "SignBoard", (0.12, 0.14, 0.18), 0.0, 0.7)
MAT_SIGN_TEXT = get_mat(PREFIX + "SignText", (0.92, 0.94, 0.96), 0.0, 0.6, emit=0.35)

# 校门中心（动态读取，不硬编码）
gp = bpy.data.objects.get("M11_GatePlaque")
if gp is not None:
    gx, gy = gp.location.x, gp.location.y
else:
    gx, gy = 0.0, -48.0
gx0 = gx + 12.0
gy0 = gy + 8.0

HX, HY, H = 1.6, 1.6, 3.0   # 半宽(x)/半深(y)/墙高
T = 0.15                     # 墙厚

# 地面薄板
add_box("Floor", gx0, gy0, 0.06, 3.5, 3.5, 0.12, CONC)
# 后墙（+y，实心）
add_box("WallBack", gx0, gy0 + HY, 1.5, 3.2, T, H, CONC)
# 左右墙（实心）
add_box("WallE", gx0 + HX, gy0, 1.5, T, 3.2, H, CONC)
add_box("WallW", gx0 - HX, gy0, 1.5, T, 3.2, H, CONC)
# 前墙(-y)左/右板（门洞左右）
add_box("WallFrontL", gx0 - 1.05, gy0 - HY, 1.5, 1.1, T, H, CONC)
add_box("WallFrontR", gx0 + 1.05, gy0 - HY, 1.5, 1.1, T, H, CONC)
# 门楣（门洞上方）
add_box("Lintel", gx0, gy0 - HY, 2.55, 1.0, T, 0.9, CONC)
# 门扇（木，填门洞）
add_box("Door", gx0, gy0 - HY, 1.05, 0.95, 0.06, 2.05, WOOD)
# 窗（玻璃，嵌前墙右板、朝 -y 微凸）
add_box("Window", gx0 + 1.05, gy0 - HY - 0.02, 1.4, 0.9, 0.04, 0.9, GLASS)
# 平屋顶（带 0.2m 出檐）
add_box("Roof", gx0, gy0, 3.1, 3.7, 3.7, 0.2, CONC)

# ---- CJK 招牌「门卫室」：前墙(-y)门楣上方，朝 -y（门朝向，右手系不镜像）----
font, h_unit, w_unit, tried = pick_font_once(SIGN_TEXT)
sign_info = {"font_ok": font is not None, "tried": tried}
if font is not None:
    d = Vector((0.0, -1.0, 0.0))          # 外法线（-y，朝校门）
    up = Vector((0.0, 0.0, 1.0))
    X = up.cross(d)                        # (1,0,0) 不镜像
    rot = Matrix((
        (X.x, X.y, X.z, 0.0),
        (up.x, up.y, up.z, 0.0),
        (d.x, d.y, d.z, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    ))
    face_pt = Vector((gx0, gy0 - HY, 2.55))
    size = TEXT_H / h_unit
    est_w = w_unit * size
    MAX_W = 2.6
    if est_w > MAX_W:
        size *= MAX_W / est_w
    bpy.ops.object.text_add(location=(0.0, 0.0, -9999.0))
    txt = bpy.context.active_object
    txt.name = PREFIX + "SignText"
    td = txt.data
    td.body = SIGN_TEXT
    td.font = font
    td.align_x = "CENTER"
    td.align_y = "CENTER"
    td.size = size
    td.extrude = 0.03
    td.bevel_depth = 0.006
    td.bevel_resolution = 1
    txt.matrix_world = Matrix.Translation(face_pt + d * (OUT_OFF + BOARD_T + 0.02)) @ rot
    txt.data.materials.append(MAT_SIGN_TEXT)
    bpy.context.view_layer.update()
    bw = txt.dimensions.x + 0.6
    bh = txt.dimensions.y + 0.6
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, -9999.0))
    board = bpy.context.active_object
    board.name = PREFIX + "SignBoard"
    board.scale = (bw, bh, BOARD_T)
    board.matrix_world = Matrix.Translation(face_pt + d * (OUT_OFF + BOARD_T / 2.0)) @ rot
    board.data.materials.append(SIGN_BOARD)
    bpy.context.view_layer.update()
    sign_info["board"] = [round(bw, 2), round(bh, 2), BOARD_T]
    sign_info["text_size"] = round(size, 3)
    sign_info["text_dim"] = [round(v, 2) for v in txt.dimensions]
else:
    sign_info["warn"] = "no usable CJK font; sign skipped"

# ---------------------------------------------------------------- 相机
hero = bpy.data.objects.get("M19C_HeroDay")
cam = bpy.data.objects.get(PREFIX + "Cam")
if cam is None:
    bpy.ops.object.camera_add(location=(gx0, gy0 - HY - 3.4, 1.6))
    cam = bpy.context.active_object
    cam.name = PREFIX + "Cam"
cam.location = (gx0, gy0 - HY - 3.4, 1.6)
cam.data.lens = 35.0
cam.rotation_euler = (Vector((gx0, gy0, 1.5)) - cam.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.view_layer.update()

# ---------------------------------------------------------------- 渲染（Cycles GPU OptiX，与 M43..M51 一致）
sc = bpy.context.scene
os.makedirs(PREVIEW_DIR, exist_ok=True)
rendered = []
try:
    sc.render.engine = "CYCLES"
    sc.cycles.device = "GPU"
    try:
        sc.cycles.compute_device_type = "OPTIX"
    except Exception:
        pass
    sc.cycles.samples = 256
    sc.render.resolution_x = 1280
    sc.render.resolution_y = 720
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.exposure = 0.0
    # 1) 校园语境（英雄机位）
    if hero is not None:
        sc.camera = hero
        sc.render.filepath = PREVIEW_DIR + "/m52_guardhouse_hero.png"
        bpy.ops.render.render(write_still=True)
        rendered.append(sc.render.filepath)
    # 2) 门卫室特写（加临时补光，避免前墙在楼影里；结束后清理零孤儿）
    sc.camera = cam
    fill = bpy.data.lights.new(PREFIX + "FillLight", "POINT")
    fill.energy = 120.0
    fill.color = (1.0, 0.96, 0.88)
    fill_obj = bpy.data.objects.new(PREFIX + "Fill", fill)
    fill_obj.location = cam.location + Vector((0.0, 0.0, 0.5))
    bpy.context.scene.collection.objects.link(fill_obj)
    bpy.context.view_layer.update()
    sc.render.filepath = PREVIEW_DIR + "/m52_guardhouse_closeup.png"
    bpy.ops.render.render(write_still=True)
    rendered.append(sc.render.filepath)
    fnm = fill_obj.name
    bpy.data.objects.remove(fill_obj, do_unlink=True)
    bpy.data.lights.remove(fill)
    if hero is not None:
        sc.camera = hero
except Exception as e:
    rendered.append("RENDER_WARN:" + str(e))

# ---------------------------------------------------------------- 统计
n_m52 = sum(1 for o in bpy.data.objects if o.name.startswith(PREFIX))
result = {
    "milestone": "M52",
    "ok": True,
    "n_removed_old": n_removed,
    "n_m52_objects": n_m52,
    "n_total_objects": len(bpy.data.objects),
    "gate": [round(gx, 1), round(gy, 1)],
    "guardhouse_center": [round(gx0, 1), round(gy0, 1)],
    "materials_reused": [CONC.name, WOOD.name],
    "materials_new": [GLASS.name, SIGN_BOARD.name, MAT_SIGN_TEXT.name],
    "sign": sign_info,
    "rendered": rendered,
}
print("M52_RESULT=" + repr(result))
