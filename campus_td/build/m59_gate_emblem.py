# -*- coding: utf-8 -*-
"""
M59 · 校门广场校徽地面雕 (Gate Plaza School Emblem Medallion)
============================================================================
项目已收官（M0–M58 ✅）。按「无未完成里程碑时自行增加改进项」新增 M59：
把 M14 匾文→M37 校旗→M52 门卫室→M54 校训碑→M55 花池 组成的「校门仪式带」
在校门与前庭院之间补上一座地面校徽圆雕，让"进门—见徽—见训"的仪式动线完整。

选址（M11 之后铁律，禁止硬编码）：
  - 校门中心从 M11_GatePlaque 世界 AABB 动态读取（北立面 y≈-48.29）。
  - 石碑花园从 M55_* 世界 AABB 并集动态读取（南侧边 y≈-43.6）。
  - 圆雕中心 = 二者之间开阔前庭院中点（中央轴线 x=0）。
  - 做楼体/校门/石碑/花池 AABB 碰撞自检，重叠则缩小半径（兜底）。

设计（原型级、纯地面薄体、零结构、零碰撞风险）：
  - 石质底盘（浅暖灰花岗岩）。
  - 金边圆环（金属金，弱自发光增质感）。
  - 蓝场内盘（校色蓝，弱自发光）。
  - 金星（5 角，金属金）。
  - 金色内圈细环点缀。

避坑（沿用 PLAN.md + M58 经验）：
  - 顶层执行：MCP 用 exec(compile(open().read()))，逻辑不包 main()。
  - 不调 mode_set；全部 primitive + bmesh 直建，物体 scale 保持 1。
  - 删旧物体先取 nm=o.name 再 remove（防 StructRNA ReferenceError）。
  - 幂等 + 前缀隔离：只清 M59_，绝不 select_all+delete。
  - 5.2 Principled 输入名 Base Color / Roughness / Metallic / Emission Strength。
"""
import bpy
import bmesh
import math
from mathutils import Vector

PREFIX = "M59_"

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


def new_mat(name, base, rough, metal=0.0, emit=0.0, emit_col=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        out = m.node_tree.nodes.get("Material Output")
        if out:
            m.node_tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = base + (1.0,)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emit > 0.0 and "Emission Strength" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = (emit_col or base) + (1.0,)
        bsdf.inputs["Emission Strength"].default_value = emit
    return m


# ---------------------------------------------------------------- 选址
# 校门结构北缘：取全部 M11_Gate* MESH 的 max y（门楣北沿，而非仅匾文）。
gate_objs = [o for o in bpy.data.objects if o.name.startswith("M11_Gate") and o.type == "MESH"]
gate_north = max((aabb(o)[3] for o in gate_objs), default=-46.6)

# 石碑花园南缘：仅取 M55_* MESH（排除 M55_Cam 等相机，否则其 y≈-48.85 会把
# 花园误判到校门以南，导致圆雕被挤到校门门楣里）。
garden = [aabb(o) for o in bpy.data.objects if o.name.startswith("M55_") and o.type == "MESH"]
if garden:
    g_min_y = min(b[2] for b in garden)
    g_max_y = max(b[3] for b in garden)
else:
    g_min_y, g_max_y = -43.6, -39.9

# 校门结构北缘 与 石碑花园南缘 之间的开阔轴带中点（中央轴线 x=0）
cy = (gate_north + g_min_y) / 2.0
cx = 0.0

R = 1.3  # 候选半径（前庭院轴带约 3m 宽，留余量）


CHECK_PREFIXES = ("M11_Gate", "M54_", "M55_", "Bldg_")


def overlaps(ox, oy, r):
    ax0, ax1 = ox - r, ox + r
    ay0, ay1 = oy - r, oy + r
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        if not o.name.startswith(CHECK_PREFIXES):
            continue
        b = aabb(o)
        if b is None:
            continue
        # 跳过贴近地面的铺装/路面/浅花坛：地面雕本就该落在上面，不算碰撞
        if b[5] < 0.6:
            continue
        if ax0 < b[1] and ax1 > b[0] and ay0 < b[3] and ay1 > b[2]:
            return o.name
    return None


collide = overlaps(cx, cy, R)
shrink = 0
while collide and R > 0.8:
    R -= 0.25
    shrink += 1
    collide = overlaps(cx, cy, R)

placement = {"cx": round(cx, 2), "cy": round(cy, 2), "R": round(R, 2),
             "shrink": shrink, "collide": collide,
             "gate_north": round(gate_north, 2), "garden_south": round(g_min_y, 2)}

# ---------------------------------------------------------------- 清旧 + 材质
# ⚠ 必须在创建材质【之前】clear_old()：否则刚建的 M59_ 材质会被清掉（M18 同坑）。
n_removed = clear_old()
stone = new_mat(PREFIX + "Stone", (0.52, 0.51, 0.49), 0.85, 0.0)
gold = new_mat(PREFIX + "Gold", (0.86, 0.66, 0.22), 0.33, 1.0, 0.06, (0.86, 0.66, 0.22))
blue = new_mat(PREFIX + "Blue", (0.14, 0.34, 0.78), 0.35, 0.0, 0.15, (0.14, 0.34, 0.78))


# ---------------------------------------------------------------- 主构建

# 1) 石质底盘（底盘底落在 M11_PlazaFront 顶面 z≈0.10 上，整体抬高做地面浮雕）
BASE_BOTTOM = 0.10
BASE_TOP = BASE_BOTTOM + 0.08
bpy.ops.mesh.primitive_cylinder_add(radius=R, depth=0.08, location=(cx, cy, (BASE_BOTTOM + BASE_TOP) / 2.0))
base = bpy.context.active_object
base.name = PREFIX + "Base"
base.data.materials.clear()
base.data.materials.append(stone)

# 2) 蓝场内盘（高出底盘顶面 0.04，避免与底盘/广场 z-fighting）
FIELD_RAISE = 0.04
FIELD_BOTTOM = BASE_TOP
FIELD_TOP = FIELD_BOTTOM + 0.04
bpy.ops.mesh.primitive_cylinder_add(radius=max(R - 0.35, 0.30), depth=FIELD_TOP - FIELD_BOTTOM,
                                     location=(cx, cy, (FIELD_BOTTOM + FIELD_TOP) / 2.0))
field = bpy.context.active_object
field.name = PREFIX + "Field"
field.data.materials.clear()
field.data.materials.append(blue)

# 3) 金边外环（垂直立环，底缘落在底盘顶面）
RING_MINOR = 0.07
RING_CENTER_Z = BASE_TOP + RING_MINOR
bpy.ops.mesh.primitive_torus_add(major_radius=R - 0.12, minor_radius=RING_MINOR,
                                  location=(cx, cy, RING_CENTER_Z))
ring = bpy.context.active_object
ring.name = PREFIX + "Ring"
ring.rotation_euler = (math.pi / 2, 0.0, 0.0)
ring.data.materials.clear()
ring.data.materials.append(gold)

# 4) 金色内细环（立在蓝场上）
INNER_MINOR = 0.03
INNER_CENTER_Z = FIELD_TOP + 0.02
bpy.ops.mesh.primitive_torus_add(major_radius=0.5, minor_radius=INNER_MINOR,
                                  location=(cx, cy, INNER_CENTER_Z))
inner = bpy.context.active_object
inner.name = PREFIX + "InnerRing"
inner.rotation_euler = (math.pi / 2, 0.0, 0.0)
inner.data.materials.clear()
inner.data.materials.append(gold)

# 5) 金星（5 角，平面）
def star_mesh(outer, inner_r, pts=5):
    bm = bmesh.new()
    vs = []
    N = pts * 2
    for i in range(N):
        ang = math.pi / 2 + i * math.pi / pts
        r = outer if (i % 2 == 0) else inner_r
        vs.append(bm.verts.new((r * math.cos(ang), r * math.sin(ang), 0.0)))
    c = bm.verts.new((0.0, 0.0, 0.0))
    for i in range(N):
        bm.faces.new([c, vs[i], vs[(i + 1) % N]])
    bm.normal_update()
    me = bpy.data.meshes.new(PREFIX + "StarMesh")
    bm.to_mesh(me)
    bm.free()
    return me

# 金星：缩小到 0.62，立在蓝场上，略高于内细环
star_outer = 0.62
star_me = star_mesh(star_outer, star_outer * 0.42)
star = bpy.data.objects.new(PREFIX + "Star", star_me)
star.location = (cx, cy, FIELD_TOP + 0.04)
star.rotation_euler = (math.pi / 2, 0.0, 0.0)
star.data.materials.clear()
star.data.materials.append(gold)
bpy.context.collection.objects.link(star)

# 6) 验证相机（校门内、半俯视看向圆雕）
cam = bpy.data.objects.get(PREFIX + "Cam")
if cam is None:
    cam = bpy.data.objects.new(PREFIX + "Cam", bpy.data.cameras.new(PREFIX + "Cam"))
    bpy.context.collection.objects.link(cam)
cam.data.lens = 35.0
# 抬高、更俯视，让地面圆雕顶面（蓝场+金星）清晰可读
cam.location = (cx, cy - 3.8, 4.5)
look = Vector((cx, cy, 0.15))
cam.rotation_euler = (look - cam.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.view_layer.update()

# ---------------------------------------------------------------- 渲染设定
sc = bpy.context.scene
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
except Exception:
    pass

n_m59 = sum(1 for o in bpy.data.objects if o.name.startswith(PREFIX))
result = {
    "milestone": "M59",
    "ok": True,
    "n_removed_old": n_removed,
    "placement": placement,
    "n_m59_objects": n_m59,
    "n_total_objects": len(bpy.data.objects),
}
print("M59_RESULT=" + repr(result))
