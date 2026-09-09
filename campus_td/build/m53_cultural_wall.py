# -*- coding: utf-8 -*-
"""
M53 · 校园围墙文化墙（Perimeter Wall Cultural Wall · 校园生活细节）
==========================================================================
项目已收官（M0–M52 ✅）。按「无未完成里程碑时自行增加改进项」新增 M53：
在 5 段外围围墙（M11_Wall*）的**内侧墙面**挂一圈校园文化墙（励志标语展板）——
中国高中最典型的"文化墙/励志墙"，此前缺失。让围墙不只是混凝土，而是有
"书香校园"气息的育人空间，与 M14 校门匾文 / M37 校旗 / M43 路灯 / M48 长椅
/ M49 宣传栏 / M50 自行车道 / M51 花坛绿篱 / M52 门卫室 共同构成可居住的校园。

为什么做这个：
  - 围墙是校园最大面积的连续立面，目前只有 M16 垛口 + M43 路灯，缺"内容"。
    文化墙把冷墙面变成有教育意义的展示面，原型观感提升明显。
  - 自成一体、零破坏其它物体：仅新建 M53_ 前缀物体，坐标全部从场景当前
    M11_Wall* AABB 动态读取（M11 之后铁律，不硬编码）。

设计（原型级，无 Boolean、无 mode_set，全 box+Text 拼装，铁律安全）：
  - 每块展板 = 深色边框(frame) + 彩色底板(board) + CJK 励志标语(text)，贴合墙
    内侧、距墙内退 0.12m、中心高 z=1.55m（底板 0.9–2.2m，低于 coping 顶 ~2.95m、
    高于 M51 绿篱 0.6m，互不遮挡）。
  - 沿每段墙长方向每 7.0m 采样一块（板宽 4.2m，留 ~2.8m 缝），板面朝向校园中心
    （内法线 d，用 up.cross(d) 右手系基 → 文字不镜像，与 M44/M52 同源验证）。
  - 南墙校门洞 x∈[-9,9] 留空；避让 M49 宣传栏（其 XY 中心 3m 内不挂板，避免板被
    栏遮挡浪费）。
  - 12 条 4 字励志标语循环（明德博学/求实创新/…/书香校园），6 套校园色循环
    （navy/teal/maroon/forest/bronze/indigo），文字近白 + Emission 0.4 保阴影面可读。
  - 复用 pick_font 自检（SimHei 首选）规避可变字体空匾。

坐标（M11 之后禁止硬编码）：
  - 收集 M11_Wall*（排除 Coping/GatePlaque/FlagPole/Flag）→ 每段 AABB 求内法线
    （指向校园中心 (0,0) 的主导水平轴）→ 内立面坐标 → 沿墙长采样。

避坑（沿用 PLAN.md + M43..M52 经验）：
  - 顶层执行：MCP 用 exec(compile(open().read()))，逻辑不包 main()。
  - 不调 mode_set；box/Text 直建 + 旋转矩阵，物体 scale 保持 1 后再设 matrix_world。
  - 删旧物体先取 nm=o.name 再 remove（防 StructRNA ReferenceError）。
  - 幂等 + 前缀隔离：只清 M53_，绝不 select_all+delete。
  - Blender 5.2：Principled 输入名 Base Color / Metallic / Roughness /
    Emission Color / Emission Strength；TextCurve 量尺寸用 object.dimensions。
  - CJK 字体必须量实际字形尺寸（pick_font 自检），否则出空匾。
"""
import bpy
import bmesh
import os
import math
from mathutils import Vector, Matrix

PREFIX = "M53_"
PREVIEW_DIR = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/previews"
FONT_CANDIDATES = [
    r"C:/Windows/Fonts/simhei.ttf",
    r"C:/Windows/Fonts/Dengb.ttf",
    r"C:/Windows/Fonts/msyhbd.ttc",
    r"C:/Windows/Fonts/simsun.ttc",
]
FONT_H_MIN = 0.55
FONT_W_MIN = 0.55

# 12 条 4 字励志标语（校园精神）
SLOGANS = ["明德博学", "求实创新", "励志图强", "厚德载物",
           "博学笃行", "自强不息", "青春飞扬", "志存高远",
           "勤学善思", "立德树人", "晨光熠熠", "书香校园"]
# 6 套校园色（哑光，非纯）
BOARD_COLORS = [(0.10, 0.16, 0.30), (0.08, 0.26, 0.28),
                (0.30, 0.10, 0.14), (0.10, 0.24, 0.14),
                (0.28, 0.20, 0.06), (0.14, 0.10, 0.24)]

BW, BH, T_BOARD, T_FRAME = 4.2, 1.4, 0.06, 0.05
Z_CENTER = 1.55
OUT_OFF = 0.12        # 距墙内立面内退
SPACING = 7.0         # 沿墙采样间距
GATE_HALF = 9.0       # 南墙校门洞半宽，留空
TEXT_H = 0.9          # 目标字高（m）


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


def get_mat(name, color, metal=0.0, rough=0.85, emit=0.0):
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


def add_box(name, pos, rot, sx, sy, sz, mat):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    me = bpy.data.meshes.new(PREFIX + name + "Mesh")
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(PREFIX + name, me)
    o.scale = (sx, sy, sz)
    o.matrix_world = Matrix.Translation(pos) @ rot
    o.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.update()
    return o


def add_text(name, body, font, pos, rot, size, mat):
    bpy.ops.object.text_add(location=(0.0, 0.0, -9999.0))
    o = bpy.context.active_object
    o.name = PREFIX + name
    td = o.data
    td.body = body
    td.font = font
    td.align_x = "CENTER"
    td.align_y = "CENTER"
    td.size = size
    td.extrude = 0.02
    td.bevel_depth = 0.004
    td.bevel_resolution = 1
    o.matrix_world = Matrix.Translation(pos) @ rot
    o.data.materials.append(mat)
    bpy.context.view_layer.update()
    return o


# ---------------------------------------------------------------- 主构建
n_removed = clear_old()

FRAME_MAT = get_mat(PREFIX + "Frame", (0.05, 0.05, 0.06), 0.0, 0.7)
TEXT_MAT = get_mat(PREFIX + "Text", (0.93, 0.95, 0.97), 0.0, 0.6, emit=0.4)
BOARD_MATS = [get_mat(PREFIX + "Board%d" % i, c, 0.0, 0.75) for i, c in enumerate(BOARD_COLORS)]

font, h_unit, w_unit, tried = pick_font_once("晨光熠熠")
font_ok = font is not None
font_info = {"ok": font_ok, "tried": tried}

# 收集围墙（排除 Coping/GatePlaque/FlagPole/Flag）
walls = []
for o in bpy.data.objects:
    nm = o.name
    if nm.startswith("M11_Wall") and not any(k in nm for k in ("Coping", "GatePlaque", "FlagPole", "Flag")):
        walls.append(o)

# 宣传栏中心（避让）
bb_centers = []
for o in bpy.data.objects:
    if o.name.startswith("M49_") and "Board" not in o.name and "Glass" not in o.name:
        bb_centers.append((o.location.x, o.location.y))

up = Vector((0.0, 0.0, 1.0))
built = 0
skipped_gate = 0
skipped_bb = 0
detail = []

for w in walls:
    bb = aabb(w)
    wx0, wx1, wy0, wy1 = bb[0], bb[1], bb[2], bb[3]
    horiz = (wx1 - wx0) >= (wy1 - wy0)
    cx, cy = (wx0 + wx1) / 2.0, (wy0 + wy1) / 2.0
    if horiz:
        # 内法线沿 Y
        if 0.0 >= cy:
            d = Vector((0.0, 1.0, 0.0))      # 南墙，中心在 y>墙 → 内朝 +Y
            face_y = wy1
        else:
            d = Vector((0.0, -1.0, 0.0))
            face_y = wy0
        lo, hi = wx0, wx1
        axis = "x"
    else:
        # 内法线沿 X
        if 0.0 >= cx:
            d = Vector((1.0, 0.0, 0.0))       # 西墙，中心在 x>墙 → 内朝 +X
            face_x = wx1
        else:
            d = Vector(((-1.0), 0.0, 0.0))
            face_x = wx0
        lo, hi = wy0, wy1
        axis = "y"
    X = up.cross(d)                            # 文字右向（不镜像，与 M52 同源）
    rot = Matrix(((X.x, X.y, X.z, 0.0),
                  (up.x, up.y, up.z, 0.0),
                  (d.x, d.y, d.z, 0.0),
                  (0.0, 0.0, 0.0, 1.0)))
    margin = BW / 2.0 + 0.6
    step = SPACING
    coord = lo + margin
    idx = 0
    while coord <= hi - margin:
        # 面板中心（墙内侧）
        if axis == "x":
            px, py = coord, face_y
        else:
            px, py = face_x, coord
        # 校门洞避让（仅南墙 front，内法线 +Y 即 d.y>0）
        if d.y > 0 and abs(px) <= GATE_HALF:
            skipped_gate += 1
            coord += step
            continue
        # 宣传栏避让
        hit_bb = False
        for (bx, by) in bb_centers:
            if abs(px - bx) < 3.0 and abs(py - by) < 3.0:
                hit_bb = True
                break
        if hit_bb:
            skipped_bb += 1
            coord += step
            continue
        slogan = SLOGANS[(built + idx) % len(SLOGANS)]
        bcol = BOARD_COLORS[(built + idx) % len(BOARD_COLORS)]
        bmat = BOARD_MATS[(built + idx) % len(BOARD_COLORS)]
        face = Vector((px, py, Z_CENTER))
        p_frame = face + d * (OUT_OFF - 0.015)
        p_board = face + d * (OUT_OFF + 0.02)
        p_text = face + d * (OUT_OFF + 0.075)
        add_box("Frame%d" % built, p_frame, rot, BW + 0.15, BH + 0.15, T_FRAME, FRAME_MAT)
        add_box("Board%d" % built, p_board, rot, BW, BH, T_BOARD, bmat)
        if font_ok:
            size = TEXT_H / h_unit
            est_w = w_unit * size
            max_w = BW * 0.82
            if est_w > max_w:
                size *= max_w / est_w
            add_text("Text%d" % built, slogan, font, p_text, rot, size, TEXT_MAT)
        built += 1
        idx += 1
        coord += step
    detail.append({"wall": w.name, "axis": axis, "len": round(hi - lo, 1),
                   "normal": [round(d.x, 1), round(d.y, 1), round(d.z, 1)]})

# ---------------------------------------------------------------- 相机
hero = bpy.data.objects.get("M19C_HeroDay")
cam = bpy.data.objects.get(PREFIX + "Cam")
if cam is None:
    bpy.ops.object.camera_add(location=(0.0, 12.0, 2.6))
    cam = bpy.context.active_object
    cam.name = PREFIX + "Cam"
cam.location = (0.0, 12.0, 2.6)
cam.data.lens = 38.0
cam.rotation_euler = (Vector((0.0, 46.0, 1.5)) - cam.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.view_layer.update()

# ---------------------------------------------------------------- 渲染（Cycles GPU OptiX，与 M43..M52 一致）
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
    # 1) 文化墙特写（北墙，M53_Cam）
    sc.camera = cam
    sc.render.filepath = PREVIEW_DIR + "/m53_cultural_wall_closeup.png"
    bpy.ops.render.render(write_still=True)
    rendered.append(sc.render.filepath)
    # 2) 校园语境（英雄机位）
    if hero is not None:
        sc.camera = hero
        sc.render.filepath = PREVIEW_DIR + "/m53_cultural_wall_hero.png"
        bpy.ops.render.render(write_still=True)
        rendered.append(sc.render.filepath)
except Exception as e:
    rendered.append("RENDER_WARN:" + str(e))
if hero is not None:
    sc.camera = hero

# ---------------------------------------------------------------- 统计
n_m53 = sum(1 for o in bpy.data.objects if o.name.startswith(PREFIX))
result = {
    "milestone": "M53",
    "ok": True,
    "n_removed_old": n_removed,
    "n_m53_objects": n_m53,
    "n_panels": built,
    "n_total_objects": len(bpy.data.objects),
    "skipped_gate": skipped_gate,
    "skipped_bulletin": skipped_bb,
    "n_walls": len(walls),
    "font_ok": font_ok,
    "rendered": rendered,
    "walls": detail,
}
print("M53_RESULT=" + repr(result))
