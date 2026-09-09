# -*- coding: utf-8 -*-
"""
M44 · 楼牌指示牌（Building Name Signs · CJK plaques on facade facing campus center）
================================================================================
项目已收官（M0–M43 ✅）。按「无未完成里程碑时自行增加改进项」新增 M44：
给 7 栋楼各挂一块中文楼牌，让校园一眼可辨识——教学楼/实验楼/行政楼/图书馆/
宿舍楼/体育馆/食堂。这是 M14 校门匾文（黑底金字）的"轻量版"补全：校园里每栋楼
目前都没有名字，走到哪栋都不认得。

为什么做这个：
  - 真实高中每栋楼门口都有楼牌；当前场景 7 栋楼无名无姓，识别度低。
  - 复用 M14 验证过的 CJK 字体管线 pick_font()（带字形尺寸自检，换机器不静默出空匾）。
  - 楼牌 = 深色哑光底板 + 白字（比校门金字更"指示牌"气质，且白字在阴影面也读得清）。

坐标全部**从场景当前几何读取**（PLAN.md 铁律：M11 之后禁止硬编码建筑坐标）：
  - 楼体 AABB ← 按 "Bldg_<Name>" 前缀收集该楼所有部件求并集。
  - 朝向 ← 楼中心指向校园中心(由 M11_Wall AABB 并集得)的方向，取主导轴决定挂在
    哪个外立面（朝中庭的那一面），楼再挪也贴合。
  - 高度 ← 距地 ~3.2m（人视入口标高），不随楼高乱飘。

避坑（沿用 PLAN.md 清单 + M14 经验）：
  - 顶层执行：MCP 用 exec(compile(open().read())) 跑，__name__ != "__main__"，逻辑不包 main()。
  - 不调 bpy.ops.*.mode_set（MCP exec 内 poll fail）。
  - 删旧物体先取 nm=o.name 再 remove（防 StructRNA ReferenceError）。
  - 幂等 + 前缀隔离：只清 M44_ 前缀，绝不 select_all+delete。
  - Blender 5.2 Principled 输入名：Emission Color / Emission Strength（非旧版 Emission）。
  - 文字朝向：用旋转矩阵把本地 +Z(正面) 钉到外法线 d、本地 +Y 钉到世界上、本地 +X = up×d，
    避免镜像且"字顶朝上、字序沿视线右向"正确读（沿用 M14 绕 X+90° 等价结论）。
  - 字体不能只看文件在不在：用 pick_font() 量实际字形尺寸，不合格自动换下一个。
"""
import bpy
import math
import mathutils
from mathutils import Vector, Matrix

PREFIX = "M44_"

# 7 栋楼：前缀 + 中文名（2~3 字）
BUILDINGS = [
    ("Bldg_Teach",   "教学楼"),
    ("Bldg_Lab",     "实验楼"),
    ("Bldg_Admin",   "行政楼"),
    ("Bldg_Library", "图书馆"),
    ("Bldg_Dorm",    "宿舍楼"),
    ("Bldg_Gym",     "体育馆"),
    ("Bldg_Canteen", "食堂"),
]

TEXT_H = 0.62        # 目标字高（m）
BOARD_T = 0.12       # 底板厚（m）
OUT_OFF = 0.10       # 底板背面距墙面外退（m）
Z_SIGN = 3.2         # 楼牌中心离地高度（m）

# 字体候选链（沿用 M14 实测：首选 simhei 最饱满；VF/Deng/SimSunExtB 在本机坏）
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\Dengb.ttf",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simsun.ttc",
]
FONT_H_MIN = 0.55
FONT_W_MIN = 0.55

BOARD = (0.055, 0.060, 0.075)   # 深蓝灰哑光底
TEXT_COLOR = (0.93, 0.94, 0.96)  # 近白字


# ---------------------------------------------------------------- 工具
def aabb(o):
    cs = [o.matrix_world @ Vector(c) for c in o.bound_box]
    xs = [c.x for c in cs]; ys = [c.y for c in cs]; zs = [c.z for c in cs]
    return [min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)]


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


def get_mat(name, color, metal=0.0, rough=0.6, emit=0.0):
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
    """量一次字形尺寸，返回 (font, h_unit, w_unit, tried)；不合格链下一字体。"""
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


def campus_center():
    walls = [o for o in bpy.data.objects if o.name.startswith("M11_Wall")]
    if not walls:
        return Vector((0.0, 0.0))
    bs = [aabb(o) for o in walls]
    xmin = min(b[0] for b in bs); xmax = max(b[1] for b in bs)
    ymin = min(b[2] for b in bs); ymax = max(b[3] for b in bs)
    return Vector(((xmin + xmax) / 2.0, (ymin + ymax) / 2.0))


def build_sign(bname, label, font, h_unit, w_unit, cc):
    objs = [o for o in bpy.data.objects if o.name.startswith(bname)]
    if not objs:
        return None
    bs = [aabb(o) for o in objs]
    xmin = min(b[0] for b in bs); xmax = max(b[1] for b in bs)
    ymin = min(b[2] for b in bs); ymax = max(b[3] for b in bs)
    zmin = min(b[4] for b in bs); zmax = max(b[5] for b in bs)
    bcx, bcy = (xmin + xmax) / 2.0, (ymin + ymax) / 2.0

    # 楼中心指向校园中心，取主导轴决定挂哪面
    dx, dy = cc.x - bcx, cc.y - bcy
    if abs(dx) >= abs(dy):
        nx, ny = (1.0 if dx > 0 else -1.0), 0.0
        face_pt = Vector((xmax if nx > 0 else xmin, bcy, 0.0))
    else:
        nx, ny = 0.0, (1.0 if dy > 0 else -1.0)
        face_pt = Vector((bcx, ymax if ny > 0 else ymin, 0.0))
    d = Vector((nx, ny, 0.0))  # 外法线（水平）

    zc = min(zmin + Z_SIGN, zmax - 1.0)
    zc = max(zc, zmin + 1.0)
    face_pt.z = zc

    # 朝向旋转矩阵：本地 +Z->d（正面朝外），+Y->世界上，+X = up×d（字不镜像、字顶朝上）
    up = Vector((0.0, 0.0, 1.0))
    X = up.cross(d)
    Y = up
    Z = d
    rot = Matrix((
        (X.x, X.y, X.z, 0.0),
        (Y.x, Y.y, Y.z, 0.0),
        (Z.x, Z.y, Z.z, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    ))

    # 字号：按目标字高反算，再按最大板宽回缩
    size = TEXT_H / h_unit
    est_w = w_unit * size
    MAX_W = 4.2
    if est_w > MAX_W:
        size *= MAX_W / est_w

    # ---- 文字 ----
    bpy.ops.object.text_add(location=(0.0, 0.0, -9999.0))
    txt = bpy.context.active_object
    txt.name = PREFIX + bname.split("_")[-1] + "_Text"
    td = txt.data
    td.body = label
    td.font = font
    td.align_x = "CENTER"
    td.align_y = "CENTER"
    td.size = size
    td.extrude = 0.03
    td.bevel_depth = 0.006
    td.bevel_resolution = 1
    txt.matrix_world = Matrix.Translation(face_pt + d * (OUT_OFF + BOARD_T + 0.02)) @ rot
    set_mat_safe(txt, get_mat(PREFIX + "SignText", TEXT_COLOR, metal=0.0, rough=0.6, emit=0.35))
    bpy.context.view_layer.update()

    # ---- 底板 ----
    bw = txt.dimensions.x + 0.6
    bh = txt.dimensions.y + 0.6
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, -9999.0))
    board = bpy.context.active_object
    board.name = PREFIX + bname.split("_")[-1] + "_Board"
    board.scale = (bw, bh, BOARD_T)
    board.matrix_world = Matrix.Translation(face_pt + d * (OUT_OFF + BOARD_T / 2.0)) @ rot
    set_mat_safe(board, get_mat(PREFIX + "SignBoard", BOARD, metal=0.0, rough=0.7))
    bpy.context.view_layer.update()

    return {
        "bname": bname, "label": label,
        "face": [round(v, 2) for v in face_pt],
        "normal": [round(nx, 1), round(ny, 1), 0.0],
        "board": [round(bw, 2), round(bh, 2), BOARD_T],
        "text_size": round(size, 3),
        "text_dim": [round(v, 2) for v in txt.dimensions],
        "aabb": [round(v, 1) for v in (xmin, xmax, ymin, ymax, zmin, zmax)],
    }


def set_mat_safe(o, mat):
    if o.data.materials:
        o.data.materials[0] = mat
    else:
        o.data.materials.append(mat)


# ---------------------------------------------------------------- 主构建
n_removed = clear_old()
cc = campus_center()

font, h_unit, w_unit, tried = pick_font_once("教学楼")
if font is None:
    result = {"ok": False, "why": "no usable CJK font", "tried": tried,
              "n_total_objects": len(bpy.data.objects)}
    print("M44_RESULT=" + repr(result))
    raise SystemExit(0)

built = []
for bname, label in BUILDINGS:
    info = build_sign(bname, label, font, h_unit, w_unit, cc)
    if info is not None:
        built.append(info)

# ---- 专用近景相机：框住 Teach 楼牌（南带、面朝 +Y，相机站楼前 +Y 方向看回）----
teach = next((b for b in built if b["bname"] == "Bldg_Teach"), None)
cam = bpy.data.objects.get(PREFIX + "Cam")
if cam is None:
    bpy.ops.object.camera_add(location=(0.0, 0.0, 3.5))
    cam = bpy.context.active_object
    cam.name = PREFIX + "Cam"
if teach is not None:
    n = Vector((teach["normal"][0], teach["normal"][1], 0.0))
    tgt = Vector((teach["face"][0], teach["face"][1], teach["face"][2]))
    cam.location = tgt + n * 8.0
    cam.data.lens = 35.0
    cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()

# ---- 渲染设定（确定性，与 M38..M43 一致）----
sc = bpy.context.scene
try:
    sc.render.engine = "CYCLES"
    sc.cycles.device = "GPU"
    sc.cycles.compute_device_type = "OPTIX"
    sc.cycles.samples = 256
    sc.render.resolution_x = 1280
    sc.render.resolution_y = 720
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.exposure = 0.0
except Exception as e:
    built.append("RENDER_CFG_WARN:" + str(e))

n_m44 = sum(1 for o in bpy.data.objects if o.name.startswith(PREFIX))
result = {
    "milestone": "M44",
    "ok": True,
    "n_removed_old": n_removed,
    "n_signs": len(built),
    "n_m44_objects": n_m44,
    "n_total_objects": len(bpy.data.objects),
    "font": {"used": font.name, "tried": tried},
    "campus_center": [round(v, 1) for v in cc],
    "signs": built,
}
print("M44_RESULT=" + repr(result))
