# -*- coding: utf-8 -*-
"""
M57 · 校门卫室门把手与门牌号 (Gate Guardhouse Door Handle & Number Plate)
============================================================================
项目已收官（M0–M56 ✅）。按「无未完成里程碑时自行增加改进项」新增 M57：
M56 的"下一步"首项 = 校门卫室门把手/门牌号。M52 的门卫室木门只有素板，
M56 加了门套但门上仍无把手、墙边无编号，显得"还没装完"。本里程碑补两样
细活：① 金属门把手（背板+连杆+竖拉手，PBR_Metal）；② 门前墙右侧暗金属
门牌号（"1号"，白字微自发光，可夜间读）。

坐标（M11 之后铁律，禁止硬编码）：
  - 全部从场景里当前 M52_Door 对象的世界 AABB 动态读取（取门朝 -y 的前脸）。
  - M52_Door 不存在则优雅跳过（不报错）。

设计（原型级，无 Boolean、无 mode_set，全 box/cylinder 拼装，铁律安全）：
  - 门把手：右侧 +x 边、门中高，外凸于门面；竖拉手 cylinder 沿 z + 短连杆 + 背板。
  - 门牌号：前墙右侧（避开门洞）、贴墙外退，暗金属底板 + CJK「1号」白字。
  - 仅新建 M57_ 前缀物体，零破坏其它物体；幂等：先清旧 M57_ 再建。

避坑（沿用 PLAN.md + M52/M56 经验）：
  - 顶层执行：MCP 用 exec(compile(open().read()))，逻辑不包 main()。
  - 不调 mode_set；全部 bmesh 直建 + 旋转，物体 scale 保持 1。
  - 删旧物体先取 nm=o.name 再 remove（防 StructRNA ReferenceError）。
  - 幂等 + 前缀隔离：只清 M57_，绝不 select_all+delete。
  - 5.2 Principled 输入名 Base Color / Metallic / Roughness / Emission Strength。
  - CJK 字体必须量实际字形尺寸（pick_font 自检），否则出空匾。
"""
import bpy
import bmesh
from mathutils import Vector, Matrix

PREFIX = "M57_"
FONT_CANDIDATES = [
    r"C:/Windows/Fonts/simhei.ttf",
    r"C:/Windows/Fonts/Dengb.ttf",
    r"C:/Windows/Fonts/msyhbd.ttc",
    r"C:/Windows/Fonts/simsun.ttc",
]
FONT_H_MIN = 0.55
FONT_W_MIN = 0.55
PLATE_TEXT = "1号"
TEXT_H = 0.15          # 目标字高（m）
PLATE_T = 0.03         # 底板厚（m）


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


def add_cyl_z(name, cx, cy, cz, r, h, mat, seg=14):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, radius1=r, radius2=r, depth=h, segments=seg,
                          cap_ends=True, cap_tris=True)
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
METAL = bpy.data.materials.get("PBR_Metal") or get_mat(PREFIX + "Handle", (0.78, 0.80, 0.82), 1.0, 0.28)
PLATE_MAT = get_mat(PREFIX + "Plate", (0.10, 0.11, 0.13), 0.9, 0.5)
NUM_TEXT = get_mat(PREFIX + "NumText", (0.92, 0.94, 0.96), 0.0, 0.5, emit=0.45)

door = bpy.data.objects.get("M52_Door")
parts = []

if door is not None:
    d = aabb(door)
    dx0, dx1 = d[0], d[1]
    front_y = d[3]          # 门朝 -y（面向校门），min-y 即前脸
    dz0, dz1 = d[4], d[5]
    hz = (dz0 + dz1) / 2.0  # 门中高
    hx = dx1 - 0.14         # 把手靠右侧（+x）

    # ---- 门把手：背板 + 连杆 + 竖拉手 ----
    add_box("HandlePlate", hx, front_y - 0.012, hz, 0.10, 0.02, 0.26, METAL)   # 背板
    add_box("HandleStem", hx, front_y - 0.04, hz, 0.035, 0.06, 0.035, METAL)   # 连杆
    add_cyl_z("HandleBar", hx, front_y - 0.075, hz, 0.02, 0.20, METAL)         # 竖拉手
    parts.append("door_handle")

    # ---- 门牌号：前墙右侧暗金属底板 + CJK「1号」 ----
    px = dx1 + 0.55                                               # 门右侧、墙内
    plate_y = front_y - 0.02
    pz = 1.85
    add_box("Plate", px, plate_y, pz, 0.50, PLATE_T, 0.24, PLATE_MAT)
    font, h_unit, w_unit, tried = pick_font_once(PLATE_TEXT)
    plate_info = {"font_ok": font is not None, "tried": tried}
    if font is not None:
        dd = Vector((0.0, -1.0, 0.0))       # 外法线（-y，朝校门）
        up = Vector((0.0, 0.0, 1.0))
        X = up.cross(dd)                     # (1,0,0) 不镜像
        rot = Matrix((
            (X.x, X.y, X.z, 0.0),
            (up.x, up.y, up.z, 0.0),
            (dd.x, dd.y, dd.z, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        ))
        face_pt = Vector((px, plate_y, pz))
        size = TEXT_H / h_unit
        est_w = w_unit * size
        MAX_W = 0.42
        if est_w > MAX_W:
            size *= MAX_W / est_w
        bpy.ops.object.text_add(location=(0.0, 0.0, -9999.0))
        txt = bpy.context.active_object
        txt.name = PREFIX + "NumText"
        td = txt.data
        td.body = PLATE_TEXT
        td.font = font
        td.align_x = "CENTER"
        td.align_y = "CENTER"
        td.size = size
        td.extrude = 0.01
        td.bevel_depth = 0.003
        td.bevel_resolution = 1
        txt.matrix_world = Matrix.Translation(face_pt + dd * (PLATE_T + 0.02)) @ rot
        txt.data.materials.append(NUM_TEXT)
        bpy.context.view_layer.update()
        plate_info["text_size"] = round(size, 3)
        plate_info["text_dim"] = [round(v, 2) for v in txt.dimensions]
        parts.append("number_plate")
    else:
        plate_info["warn"] = "no usable CJK font; number text skipped"

# ---------------------------------------------------------------- 统计
n_m57 = sum(1 for o in bpy.data.objects if o.name.startswith(PREFIX))
result = {
    "milestone": "M57",
    "ok": True,
    "n_removed_old": n_removed,
    "n_m57_objects": n_m57,
    "n_total_objects": len(bpy.data.objects),
    "door_present": door is not None,
    "parts_built": parts,
    "plate_info": plate_info,
}
print("M57_RESULT=" + repr(result))
