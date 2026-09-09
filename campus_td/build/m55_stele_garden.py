# -*- coding: utf-8 -*-
"""
M55 · 校训石碑基座花池与景观灯带 (Stele Base Flower Bed & Uplights)
==========================================================================
M0–M54 已收官。按「无未完成里程碑时自行增加改进项」新增 M55：
在校训石碑(M54)两层花岗岩碑座外围加一圈低矮石材花池，沿四边摆彩色花簇，
并在花池前角加两盏暖色地灯（自发光灯体 + 弱 POINT 补光），补齐校门仪式轴的景观细节。

为什么做：
  - M54 立了校训石碑，但碑座周围仍是裸地，仪式轴收尾不完整。真实高中校训石
    周围通常有花池/绿植点缀。
  - 自成一体、零破坏其它物体：仅新建 M55_ 前缀物体，坐标全部从 M11_GatePlaque
    动态读取（不硬编码），撞楼自检。

设计（原型级，全 box/ico 拼装，无 mode_set、无 Boolean，铁律安全）：
  - 矩形石材花池外框（4 边 border，暖灰花岗岩 M55_Stone），围住 M54 两层碑座，
    顶面 z≈0.45，内框留出 base1(3.2×2.0) 余量。
  - 沿 4 边顶摆 22 朵彩色花簇（茎 PBR_Grass + 花冠 M55_Flower0..3 确定性调色板、
    Emission 0.35 保阴影面可读），按颜色分组合并为 4 个单 mesh。
  - 花池前角(-y 朝校门侧)两盏暖色地灯：自发光灯体(M55_Uplight, Emission 2.0)
    + 弱 POINT 补光(energy 8) 提供夜间仪式微光，白天几乎无感。

坐标（M11 之后禁止硬编码）：
  - 校门中心 ← 读 M11_GatePlaque（兜底 (0,-48)）。
  - 碑体/花池中心 = 校门中心 + (0, +6.5) = (0, -41.8)，与 M54 同源。
"""
import bpy
import bmesh
import os
from mathutils import Vector, Matrix

PREFIX = "M55_"
PREVIEW_DIR = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/previews"

FLOWER_COLORS = [
    (0.85, 0.20, 0.22),  # 红
    (0.95, 0.62, 0.15),  # 橙
    (0.93, 0.83, 0.18),  # 黄
    (0.30, 0.55, 0.85),  # 蓝
]
FLOWER_EMIT = 0.35


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


def build_flower_group(name, pts, grass_mat, cap_mat):
    """每个花 = 茎(box, 材质槽0) + 花冠(ico, 材质槽1)，合并成单 mesh。"""
    bm = bmesh.new()
    for (fx, fy) in pts:
        # 茎
        nf0 = len(bm.faces); n0 = len(bm.verts)
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts[n0:]:
            v.co = (v.co.x * 0.04 + fx, v.co.y * 0.04 + fy, v.co.z * 0.35 + 0.675)
        for f in bm.faces[nf0:]:
            f.material_index = 0
        # 花冠
        nf1 = len(bm.faces); n1 = len(bm.verts)
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
        for v in bm.verts[n1:]:
            v.co = (v.co.x * 0.13 + fx, v.co.y * 0.13 + fy, v.co.z * 0.13 + 0.90)
        for f in bm.faces[nf1:]:
            f.material_index = 1
    me = bpy.data.meshes.new(PREFIX + name + "Mesh")
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(PREFIX + name, me)
    o.data.materials.append(grass_mat)
    o.data.materials.append(cap_mat)
    bpy.context.scene.collection.objects.link(o)
    return o


# ---------------------------------------------------------------- 主构建
n_before = len(bpy.data.objects)
n_removed = clear_old()
STONE = get_mat(PREFIX + "Stone", (0.66, 0.65, 0.62), 0.0, 0.88)
UPLIGHT = get_mat(PREFIX + "Uplight", (1.0, 0.95, 0.85), 0.0, 0.6, emit=2.0)
grass = bpy.data.materials.get("PBR_Grass")
if grass is None:
    grass = get_mat("PBR_Grass", (0.18, 0.30, 0.14), 0.0, 0.9)
cap_mats = [get_mat(PREFIX + "Flower%d" % i, FLOWER_COLORS[i], 0.0, 0.7, emit=FLOWER_EMIT)
            for i in range(4)]

# 中心点（动态读取，与 M54 同源）
gp = bpy.data.objects.get("M11_GatePlaque")
if gp is not None:
    gx, gy = gp.location.x, gp.location.y
else:
    gx, gy = 0.0, -48.0
cx = gx + 0.0
cy = gy + 6.5

# 花池外框：外半 2.4(x)/1.8(y)、边宽 0.35、高 0.45
HX, HY, BT, HZ = 2.4, 1.8, 0.35, 0.45
add_box("PlanterFront", cx, cy - (HY - BT / 2.0), HZ / 2.0, 2 * HX, BT, HZ, STONE)
add_box("PlanterBack", cx, cy + (HY - BT / 2.0), HZ / 2.0, 2 * HX, BT, HZ, STONE)
add_box("PlanterLeft", cx - (HX - BT / 2.0), cy, HZ / 2.0, BT, 2 * (HY - BT), HZ, STONE)
add_box("PlanterRight", cx + (HX - BT / 2.0), cy, HZ / 2.0, BT, 2 * (HY - BT), HZ, STONE)

# 花簇：沿 4 边顶(z=0.5)，按颜色分组
front_xs = [-2.0, -1.4, -0.8, -0.2, 0.4, 1.0, 1.6]
side_ys = [-1.0, -0.4, 0.2, 0.8]
pts = []
for x in front_xs:
    pts.append((cx + x, cy - (HY - BT / 2.0)))
    pts.append((cx + x, cy + (HY - BT / 2.0)))
for y in side_ys:
    pts.append((cx - (HX - BT / 2.0), cy + y))
    pts.append((cx + (HX - BT / 2.0), cy + y))
groups = [[] for _ in range(4)]
for i, p in enumerate(pts):
    groups[i % 4].append(p)
for i, g in enumerate(groups):
    if g:
        build_flower_group("Flowers%d" % i, g, grass, cap_mats[i])

# 景观地灯：花池前角两盏（朝校门 -y 侧），自发光灯体 + 弱 POINT 补光
for k, sx in enumerate((-1.9, 1.9)):
    add_box("UpLamp%d" % k, cx + sx, cy - (HY + 0.1), 0.47, 0.25, 0.25, 0.06, UPLIGHT)
    l = bpy.data.lights.new(PREFIX + "UpLight%d" % k, "POINT")
    l.energy = 8.0
    l.color = (1.0, 0.92, 0.78)
    l.shadow_soft_size = 0.3
    lo = bpy.data.objects.new(PREFIX + "UpLightObj%d" % k, l)
    lo.location = (cx + sx, cy - (HY + 0.1), 0.55)
    bpy.context.scene.collection.objects.link(lo)

# ---------------------------------------------------------------- 撞楼自检（不破坏，仅断言）
planter_a = [cx - HX, cx + HX, cy - HY, cy + HY, 0.0, HZ]
collide = []
for o in bpy.data.objects:
    if o.name.startswith("Bldg_"):
        ba = aabb(o)
        if not (planter_a[1] + 1.0 < ba[0] or planter_a[0] - 1.0 > ba[1]
                or planter_a[3] + 1.0 < ba[2] or planter_a[2] - 1.0 > ba[3]):
            collide.append(o.name)
in_walls = (-48.0 < planter_a[0] and planter_a[1] < 48.0 and -48.0 < planter_a[2] and planter_a[3] < 48.0)

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

# ---------------------------------------------------------------- 渲染（Cycles GPU OptiX）
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
        sc.render.filepath = PREVIEW_DIR + "/m55_stele_garden_hero.png"
        bpy.ops.render.render(write_still=True)
        rendered.append(sc.render.filepath)
    # 2) 校训石碑+花池特写（加临时补光，结束后清理零孤儿）
    sc.camera = cam
    fill = bpy.data.lights.new(PREFIX + "FillLight", "POINT")
    fill.energy = 60.0
    fill.color = (1.0, 0.97, 0.90)
    fill_obj = bpy.data.objects.new(PREFIX + "Fill", fill)
    fill_obj.location = cam.location + Vector((0.0, 0.0, 0.8))
    bpy.context.scene.collection.objects.link(fill_obj)
    bpy.context.view_layer.update()
    sc.render.filepath = PREVIEW_DIR + "/m55_stele_garden_closeup.png"
    bpy.ops.render.render(write_still=True)
    rendered.append(sc.render.filepath)
    bpy.data.objects.remove(fill_obj, do_unlink=True)
    bpy.data.lights.remove(fill)
    if hero is not None:
        sc.camera = hero
except Exception as e:
    rendered.append("RENDER_WARN:" + str(e))

# ---------------------------------------------------------------- 统计
n_m55 = sum(1 for o in bpy.data.objects if o.name.startswith(PREFIX))
n_after = len(bpy.data.objects)
result = {
    "milestone": "M55",
    "ok": True,
    "n_before": n_before,
    "n_removed_old": n_removed,
    "n_m55_objects": n_m55,
    "n_after_objects": n_after,
    "delta": n_after - n_before,
    "stele_center": [round(cx, 1), round(cy, 1)],
    "planter_aabb": [round(v, 1) for v in planter_a],
    "collide_bldgs": collide,
    "in_walls": in_walls,
    "flowers": len(pts),
    "rendered": rendered,
}
print("M55_RESULT=" + repr(result))
