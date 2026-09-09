# -*- coding: utf-8 -*-
"""
M54 · 校训石碑（School Motto Stele · 校园生活细节 / 仪式感收尾）
==========================================================================
项目已收官（M0–M53 ✅）。按「无未完成里程碑时自行增加改进项」新增 M54：
在校门内前庭院（中央轴线、校门与教学楼之间开阔带）立一座**校训石碑**
（花岗岩碑座 + 碑身 + 阴刻校名与校训），把"晨光中学"的仪式感收尾补齐。

为什么做这个：
  - 校训石是中国高中最标志性的仪式性构筑物：新生入学、毕业合影、升旗都围绕它。
    原型此前有 M14 校门匾文 / M37 校旗 / M52 门卫室，独缺校训石，校门仪式带不完整。
  - 自成一体、零破坏其它物体：仅新建 M54_ 前缀物体，坐标全部从场景当前几何
    动态读取（校门由 M11_GatePlaque 定位，不硬编码），并做撞楼自检。

设计（原型级，无 Boolean、无 mode_set，全 box 拼装，铁律安全）：
  - 两层花岗岩碑座（底台 3.2×2.0×0.4 / 二级台 2.6×1.6×0.3）+ 直立碑身
    （2.4×0.45×2.6，高 3.3m）。碑身略大、碑座收分，呈纪念性碑体。
  - 碑身正面(-y，朝校门/入口，d=(0,-1,0) 右手系旋转不镜像)阴刻三行 CJK：
    校名「晨光中学」(大) + 校训「明德博学」「求实创新」(两行小)。
  - 阴刻做法：字用深色(炭灰)微自发光(Emission 0.12)贴在碑面微前处，模拟刻槽内
    着色可读；沿用 M14/M44/M52/M53 验证过的 pick_font 字形尺寸自检（避空匾）。
  - 花岗岩材质新建 M54_Stone（暖灰、糙 0.88）；字材质 M54_Engrave（炭灰、糙 1.0）。

坐标（M11 之后禁止硬编码）：
  - 校门中心 ← 读 M11_GatePlaque（兜底 (0,-48)）。
  - 碑体中心 = 校门中心 + ( 0 , +6.5 )：中央轴线、校门内 6.5m（y=-41.5），
    介于校门(y=-48)与教学楼南沿(y=-37.5)之间的开阔前庭院，距门卫室(12,-40.3)
    约 12m，不撞任何楼体、不压中央道路轴线以外的物体。

避坑（沿用 PLAN.md + M43..M53 经验）：
  - 顶层执行：MCP 用 exec(compile(open().read()))，逻辑在顶层，result 顶层赋值。
  - 不调 mode_set；全部 bmesh/primitive 直建 + 旋转矩阵，物体 scale 保持 1。
  - 删旧物体先取 nm=o.name 再 remove（防 StructRNA ReferenceError）。
  - 幂等 + 前缀隔离：只清 M54_，绝不 select_all+delete。
  - CJK 字体必须量实际字形尺寸（pick_font 自检），否则出空匾。
"""
import bpy
import bmesh
import os
import math
from mathutils import Vector, Matrix

PREFIX = "M54_"
PREVIEW_DIR = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/previews"
FONT_CANDIDATES = [
    r"C:/Windows/Fonts/simhei.ttf",
    r"C:/Windows/Fonts/Dengb.ttf",
    r"C:/Windows/Fonts/msyhbd.ttc",
    r"C:/Windows/Fonts/simsun.ttc",
]
FONT_H_MIN = 0.55
FONT_W_MIN = 0.55

SCHOOL_NAME = "晨光中学"
MOTTO_LINE1 = "明德博学"
MOTTO_LINE2 = "求实创新"
OUT_OFF = 0.02   # 字距碑面前退（m）


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


def get_mat(name, color, metal=0.0, rough=0.88, emit=0.0):
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


def add_text(text, face_pt, d, up, target_h, mat, max_w):
    """在 face_pt 处、以 d 为正面法线、up 为上方向放置居中的阴刻 CJK 字。"""
    font, h_unit, w_unit, _tried = pick_font_once(text)
    if font is None:
        return None, "no usable CJK font"
    X = up.cross(d)
    rot = Matrix((
        (X.x, X.y, X.z, 0.0),
        (up.x, up.y, up.z, 0.0),
        (d.x, d.y, d.z, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    ))
    size = target_h / h_unit
    est_w = w_unit * size
    if est_w > max_w:
        size *= max_w / est_w
    bpy.ops.object.text_add(location=(0.0, 0.0, -9999.0))
    txt = bpy.context.active_object
    td = txt.data
    td.body = text
    td.font = font
    td.align_x = "CENTER"
    td.align_y = "CENTER"
    td.size = size
    td.extrude = 0.02
    td.bevel_depth = 0.004
    td.bevel_resolution = 1
    txt.matrix_world = Matrix.Translation(face_pt + d * OUT_OFF) @ rot
    txt.data.materials.append(mat)
    bpy.context.view_layer.update()
    return txt, {"size": round(size, 3), "dim": [round(v, 2) for v in txt.dimensions]}


# ---------------------------------------------------------------- 主构建
n_removed = clear_old()
STONE = get_mat(PREFIX + "Stone", (0.66, 0.65, 0.62), 0.0, 0.88)
ENGRAVE = get_mat(PREFIX + "Engrave", (0.11, 0.11, 0.12), 0.0, 1.0, emit=0.12)

# 校门中心（动态读取，不硬编码）
gp = bpy.data.objects.get("M11_GatePlaque")
if gp is not None:
    gx, gy = gp.location.x, gp.location.y
else:
    gx, gy = 0.0, -48.0
cx = gx + 0.0
cy = gy + 6.5

# 两层碑座 + 碑身
add_box("Base1", cx, cy, 0.20, 3.2, 2.0, 0.40, STONE)   # 底台
add_box("Base2", cx, cy, 0.55, 2.6, 1.6, 0.30, STONE)   # 二级台
SLAB_W, SLAB_D, SLAB_H = 2.4, 0.45, 2.6
SLAB_CZ = 0.70 + SLAB_H / 2.0
add_box("Slab", cx, cy, SLAB_CZ, SLAB_W, SLAB_D, SLAB_H, STONE)

# 碑身正面朝向 -y（朝校门/入口）
d = Vector((0.0, -1.0, 0.0))
up = Vector((0.0, 0.0, 1.0))
face_y = cy - SLAB_D / 2.0
texts = []
txt_name, info1 = add_text(SCHOOL_NAME, Vector((cx, face_y, 2.55)), d, up, 0.50, ENGRAVE, SLAB_W - 0.4)
if txt_name is not None:
    txt_name.name = PREFIX + "TextName"
    texts.append(txt_name.name)
txt_m1, info2 = add_text(MOTTO_LINE1, Vector((cx, face_y, 1.90)), d, up, 0.32, ENGRAVE, SLAB_W - 0.4)
if txt_m1 is not None:
    txt_m1.name = PREFIX + "TextMotto1"
    texts.append(txt_m1.name)
txt_m2, info3 = add_text(MOTTO_LINE2, Vector((cx, face_y, 1.45)), d, up, 0.32, ENGRAVE, SLAB_W - 0.4)
if txt_m2 is not None:
    txt_m2.name = PREFIX + "TextMotto2"
    texts.append(txt_m2.name)

# ---------------------------------------------------------------- 撞楼自检（不破坏，仅断言）
stele_a = aabb(bpy.data.objects[PREFIX + "Slab"])
collide = []
for o in bpy.data.objects:
    if o.name.startswith("Bldg_"):
        ba = aabb(o)
        # 外扩 1.0m 留余量
        if not (stele_a[1] + 1.0 < ba[0] or stele_a[0] - 1.0 > ba[1]
                or stele_a[3] + 1.0 < ba[2] or stele_a[2] - 1.0 > ba[3]):
            collide.append(o.name)
in_walls = (-48.0 < stele_a[0] and stele_a[1] < 48.0 and -48.0 < stele_a[2] and stele_a[3] < 48.0)

# ---------------------------------------------------------------- 相机
hero = bpy.data.objects.get("M19C_HeroDay")
cam = bpy.data.objects.get(PREFIX + "Cam")
if cam is None:
    bpy.ops.object.camera_add(location=(cx, cy - 7.0, 2.0))
    cam = bpy.context.active_object
    cam.name = PREFIX + "Cam"
cam.location = (cx, cy - 7.0, 2.0)
cam.data.lens = 35.0
cam.rotation_euler = (Vector((cx, cy, 1.8)) - cam.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.view_layer.update()

# ---------------------------------------------------------------- 渲染（Cycles GPU OptiX，与 M43..M53 一致）
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
        sc.render.filepath = PREVIEW_DIR + "/m54_motto_stele_hero.png"
        bpy.ops.render.render(write_still=True)
        rendered.append(sc.render.filepath)
    # 2) 校训石碑特写（加临时补光，避免碑面在楼影里；结束后清理零孤儿）
    sc.camera = cam
    fill = bpy.data.lights.new(PREFIX + "FillLight", "POINT")
    fill.energy = 140.0
    fill.color = (1.0, 0.97, 0.90)
    fill_obj = bpy.data.objects.new(PREFIX + "Fill", fill)
    fill_obj.location = cam.location + Vector((0.0, 0.0, 0.8))
    bpy.context.scene.collection.objects.link(fill_obj)
    bpy.context.view_layer.update()
    sc.render.filepath = PREVIEW_DIR + "/m54_motto_stele_closeup.png"
    bpy.ops.render.render(write_still=True)
    rendered.append(sc.render.filepath)
    bpy.data.objects.remove(fill_obj, do_unlink=True)
    bpy.data.lights.remove(fill)
    if hero is not None:
        sc.camera = hero
except Exception as e:
    rendered.append("RENDER_WARN:" + str(e))

# ---------------------------------------------------------------- 统计
n_m54 = sum(1 for o in bpy.data.objects if o.name.startswith(PREFIX))
result = {
    "milestone": "M54",
    "ok": True,
    "n_removed_old": n_removed,
    "n_m54_objects": n_m54,
    "n_total_objects": len(bpy.data.objects),
    "gate": [round(gx, 1), round(gy, 1)],
    "stele_center": [round(cx, 1), round(cy, 1)],
    "slab_aabb": [round(v, 1) for v in stele_a],
    "collide_bldgs": collide,
    "in_walls": in_walls,
    "school_name": SCHOOL_NAME,
    "motto": [MOTTO_LINE1, MOTTO_LINE2],
    "texts": texts,
    "rendered": rendered,
}
print("M54_RESULT=" + repr(result))
